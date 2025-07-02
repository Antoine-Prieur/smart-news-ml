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


class SentimentAnalysisPredictorV2(BasePredictor):
    MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"
    SENTIMENT_MAP: dict[int, str] = {
        0: "negative",
        1: "negative",
        2: "neutral",
        3: "positive",
        4: "positive",
    }

    def __init__(
        self,
        predictor_service: PredictorService,
        metrics_repository: MetricsRepository,
        logger: Logger,
    ) -> None:
        super().__init__(predictor_service, metrics_repository, logger)

        self.tokenizer = None
        self.model = None

    @property
    def prediction_type(self) -> str:
        return "sentiment_analysis"

    @property
    def predictor_description(self) -> str:
        return "ONNX version of nlptown/bert-base-multilingual-uncased-sentiment"

    @property
    def predictor_version(self) -> int:
        return 2

    async def _download_predictor(self) -> Path:
        self.logger.info(f"Downloading sentiment analysis model: {self.MODEL_NAME}")

        temp_dir = Path(tempfile.mkdtemp())

        try:
            tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)  # type: ignore

            model = ORTModelForSequenceClassification.from_pretrained(  # type: ignore
                self.MODEL_NAME, export=True
            )
            self.logger.info("Successfully converted PyTorch model to ONNX")

            temp_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(temp_dir)  # type: ignore
            model.save_pretrained(temp_dir)  # type: ignore

            self.logger.info(f"Successfully downloaded model to {temp_dir}")
            return temp_dir

        except Exception as e:
            self.logger.error(f"Failed to download sentiment analysis model: {e}")
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)
            raise

    async def _load_predictor(self, predictor_weights_path: Path) -> None:
        self.logger.info(
            f"Loading sentiment analysis model from {predictor_weights_path}"
        )

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(predictor_weights_path))  # type: ignore

            self.model = ORTModelForSequenceClassification.from_pretrained(  # type: ignore
                str(predictor_weights_path),
                providers=["CPUExecutionProvider"],
            )

            self.logger.info("ONNX model loaded on CPU with optimized execution")

        except Exception as e:
            self.logger.error(f"Failed to load sentiment analysis model: {e}")
            raise

    async def _unload_predictor(self) -> None:
        self.logger.info("Unloading sentiment analysis model")

        if self.model is not None:  # type: ignore
            del self.model
            self.model = None

        if self.tokenizer is not None:  # type: ignore
            del self.tokenizer
            self.tokenizer = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self.logger.info("Model unloaded successfully")

    async def _forward(self, predictor_input: Any) -> Prediction:
        if self.model is None or self.tokenizer is None:  # type: ignore
            raise RuntimeError("Model not loaded. Call load_predictor() first.")

        if isinstance(predictor_input, str):
            text: str = predictor_input
        else:
            raise ValueError(
                f"Invalid input format. Expected string or dict with 'text' key, got {type(predictor_input)}"
            )

        if not text:
            raise ValueError("Input text cannot be empty")

        try:
            inputs = self.tokenizer(  # type: ignore
                text,
                return_tensors="np",
                truncation=True,
                padding=True,
                max_length=512,
            )

            outputs = self.model(**inputs)  # type: ignore

            logits = outputs.logits  # type: ignore

            if hasattr(logits, "numpy"):  # type: ignore
                logits = logits.numpy()  # type: ignore

            exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))  # type: ignore
            predictions = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

            predicted_class = np.argmax(predictions, axis=-1).item()
            confidence = predictions[0][predicted_class].item()

            sentiment = self.SENTIMENT_MAP.get(int(predicted_class), "unknown")

            price = len(text) * 0.001  # $0.001 per character

            return Prediction(
                prediction_value=sentiment,
                prediction_confidence=confidence,
                price=price,
            )

        except Exception as e:
            self.logger.error(f"Error during sentiment analysis prediction: {e}")
            raise
