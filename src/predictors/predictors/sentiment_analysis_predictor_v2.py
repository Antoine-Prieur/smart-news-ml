import tempfile
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from transformers.utils.quantization_config import BitsAndBytesConfig

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
    def predictor_version(self) -> int:
        return 2

    async def _download_predictor(self) -> Path:
        self.logger.info(
            f"Downloading sentiment analysis model with quantization: {self.MODEL_NAME}"
        )

        temp_dir = Path(tempfile.mkdtemp())

        try:
            tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)  # type: ignore

            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )

            model = AutoModelForSequenceClassification.from_pretrained(  # type: ignore
                self.MODEL_NAME,
                quantization_config=quantization_config,
                device_map="auto",
            )

            temp_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(temp_dir)  # type: ignore
            model.save_pretrained(temp_dir)  # type: ignore

            self.logger.info(
                f"Successfully downloaded and quantized model at {temp_dir}"
            )
            return temp_dir

        except Exception as e:
            self.logger.error(f"Failed to download sentiment analysis model: {e}")
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)
            raise

    async def _load_predictor(self, predictor_weights_path: Path) -> None:
        self.logger.info(
            f"Loading quantized sentiment analysis model from {predictor_weights_path}"
        )

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(predictor_weights_path))  # type: ignore

            self.model = AutoModelForSequenceClassification.from_pretrained(  # type: ignore
                str(predictor_weights_path),
                device_map="auto",
            )

            if hasattr(self.model, "hf_device_map"):  # type: ignore
                self.logger.info(
                    f"Model loaded with device map: {self.model.hf_device_map}"  # type: ignore
                )
            else:
                self.logger.info(
                    f"Model loaded on device: {next(self.model.parameters()).device}"  # type: ignore
                )

        except Exception as e:
            self.logger.error(f"Failed to load quantized sentiment analysis model: {e}")
            raise

    async def _unload_predictor(self) -> None:
        self.logger.info("Unloading sentiment analysis model")

        if self.model is not None:  # type: ignore
            self.model = self.model.cpu() if hasattr(self.model, "cpu") else self.model  # type: ignore
            del self.model
            self.model = None

        if self.tokenizer is not None:  # type: ignore
            del self.tokenizer
            self.tokenizer = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    async def _forward(self, predictor_input: Any) -> Prediction:
        if self.model is None or self.tokenizer is None:  # type: ignore
            raise RuntimeError("Model not loaded. Call load_predictor() first.")

        if isinstance(predictor_input, str):
            text: str = predictor_input
        else:
            raise ValueError(
                f"Invalid input format. Expected string, got {type(predictor_input)}"
            )

        if not text:
            raise ValueError("Input text cannot be empty")

        try:
            inputs = self.tokenizer(  # type: ignore
                text, return_tensors="pt", truncation=True, padding=True, max_length=512
            )

            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}  # type: ignore

            with torch.no_grad():
                outputs = self.model(**inputs)  # type: ignore
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)  # type: ignore
                predicted_class = torch.argmax(predictions, dim=-1).item()
                confidence = predictions[0][predicted_class].item()  # type: ignore

            sentiment = self.SENTIMENT_MAP.get(int(predicted_class), "unknown")

            price = len(text) * 0.001

            return Prediction(
                prediction_value=sentiment,
                prediction_confidence=confidence,
                price=price,
            )

        except Exception as e:
            self.logger.error(
                f"Error during quantized sentiment analysis prediction: {e}"
            )
            raise
