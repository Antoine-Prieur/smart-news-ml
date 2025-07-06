import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import torch
from optimum.onnxruntime import ORTModelForSequenceClassification  # type: ignore
from transformers import AutoTokenizer

from src.core.logger import Logger
from src.database.repositories.metrics_repository import MetricsRepository
from src.predictors.base_predictor import BasePredictor
from src.services.models.predictor_models import Prediction
from src.services.predictor_service import PredictorService


class NewsClassificationPredictorV2(BasePredictor):
    MODEL_NAME = "prajjwal1/bert-small"

    CANDIDATE_LABELS = [
        "politics",
        "business",
        "technology",
        "sports",
        "health",
        "entertainment",
        "world news",
        "crime",
        "science",
        "environment",
        "breaking news",
        "opinion",
        "local news",
        "economy",
        "education",
        "military",
        "weather",
        "lifestyle",
    ]

    def __init__(
        self,
        predictor_service: PredictorService,
        metrics_repository: MetricsRepository,
        logger: Logger,
    ) -> None:
        super().__init__(predictor_service, metrics_repository, logger)

        self.tokenizer: Any | None = None
        self.model: Any | None = None
        self.cached_hypothesis_embeddings: dict[str, Any] = {}

    @property
    def prediction_type(self) -> str:
        return "news_classification"

    @property
    def predictor_description(self) -> str:
        return f"ONNX version of prajjwal1/bert-small for news classification with {len(self.CANDIDATE_LABELS)} predefined categories"

    @property
    def predictor_version(self) -> int:
        return 2

    async def _download_predictor(self) -> Path:
        self.logger.info(f"Downloading news classification model: {self.MODEL_NAME}")

        temp_dir = Path(tempfile.mkdtemp())

        try:
            tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)  # type: ignore

            model = ORTModelForSequenceClassification.from_pretrained(  # type: ignore
                self.MODEL_NAME,
                export=True,
                providers=["CPUExecutionProvider"],
            )
            self.logger.info("Successfully converted PyTorch model to ONNX")

            temp_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(temp_dir)  # type: ignore
            model.save_pretrained(temp_dir)  # type: ignore

            self.logger.info(f"Successfully downloaded model to {temp_dir}")
            return temp_dir

        except Exception as e:
            self.logger.error(f"Failed to download news classification model: {e}")
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)
            raise

    async def _load_predictor(self, predictor_weights_path: Path) -> None:
        self.logger.info(
            f"Loading news classification model from {predictor_weights_path}"
        )

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(predictor_weights_path))  # type: ignore

            self.model = ORTModelForSequenceClassification.from_pretrained(  # type: ignore
                str(predictor_weights_path),
                providers=["CPUExecutionProvider"],
            )

            self.logger.info("ONNX model loaded on CPU with optimized execution")

            await self._precompute_hypothesis_embeddings()

        except Exception as e:
            self.logger.error(f"Failed to load news classification model: {e}")
            raise

    async def _precompute_hypothesis_embeddings(self) -> None:
        """Pre-compute and cache hypothesis embeddings for all candidate labels."""
        self.logger.info(
            f"Pre-computing hypothesis embeddings for {len(self.CANDIDATE_LABELS)} labels"
        )

        self.cached_hypothesis_embeddings = {}

        for label in self.CANDIDATE_LABELS:
            hypothesis = f"This example is {label}."

            hypothesis_inputs = self.tokenizer(  # type: ignore
                hypothesis,
                return_tensors="np",
                padding=True,
                max_length=128,
                add_special_tokens=True,
                truncation="only_first",
            )

            self.cached_hypothesis_embeddings[label] = {
                "hypothesis": hypothesis,
                "input_ids": hypothesis_inputs["input_ids"],
                "attention_mask": hypothesis_inputs["attention_mask"],
            }

        self.logger.info("Hypothesis embeddings pre-computed and cached")

    async def _unload_predictor(self) -> None:
        self.logger.info("Unloading news classification model")

        if self.model is not None:  # type: ignore
            del self.model
            self.model = None

        if self.tokenizer is not None:  # type: ignore
            del self.tokenizer
            self.tokenizer = None

        self.cached_hypothesis_embeddings.clear()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self.logger.info("Model unloaded successfully")

    async def _forward(self, predictor_input: Any) -> Prediction:
        if self.model is None or self.tokenizer is None:  # type: ignore
            raise RuntimeError("Model not loaded. Call load_predictor() first.")

        if isinstance(predictor_input, str):
            text = predictor_input
        else:
            raise ValueError(
                f"Invalid input format. Expected string, got {type(predictor_input)}"
            )

        if not text:
            raise ValueError("Input text cannot be empty")

        try:
            label_scores: dict[str, Any] = {}

            for label in self.CANDIDATE_LABELS:
                cached_hyp = self.cached_hypothesis_embeddings[label]

                inputs = self.tokenizer(  # type: ignore
                    text,
                    cached_hyp["hypothesis"],
                    return_tensors="np",
                    padding=True,
                    max_length=512,
                    truncation="only_first",
                )

                outputs = self.model(**inputs)  # type: ignore
                logits = outputs.logits  # type: ignore

                if hasattr(logits, "numpy"):  # type: ignore
                    logits = logits.numpy()  # type: ignore

                if logits.shape[1] == 2:
                    exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
                    probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
                    prob_label_is_true = probs[0, 1].item()
                else:
                    entail_contradiction_logits = logits[:, [0, 2]]
                    exp_logits = np.exp(
                        entail_contradiction_logits
                        - np.max(entail_contradiction_logits, axis=-1, keepdims=True)
                    )
                    probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
                    prob_label_is_true = probs[0, 1].item()
                label_scores[label] = prob_label_is_true

            sorted_labels_scores = sorted(
                label_scores.items(), key=lambda x: x[1], reverse=True
            )
            sorted_labels = [label for label, _ in sorted_labels_scores]
            sorted_scores = [score for _, score in sorted_labels_scores]

            price = len(text) * len(self.CANDIDATE_LABELS) * 0.002

            classification_result = {
                "labels": sorted_labels,
                "scores": sorted_scores,
            }

            return Prediction(
                prediction_value=classification_result,
                prediction_confidence=(
                    sum(sorted_scores) / len(sorted_scores) if sorted_scores else 1
                ),
                price=price,
            )

        except Exception as e:
            self.logger.error(f"Error during news classification prediction: {e}")
            raise
