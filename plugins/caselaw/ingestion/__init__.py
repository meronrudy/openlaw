# CAP Caselaw Plugin - Data Ingestion Pipeline
# HuggingFace dataset streaming and ETL for 37M+ legal documents

from .hf_ingestion_pipeline import HuggingFaceIngestionPipeline
from .data_processor import CaselawDataProcessor
from .batch_processor import BatchProcessor
from .ingestion_manager import IngestionManager

__all__ = [
    "HuggingFaceIngestionPipeline",
    "CaselawDataProcessor",
    "BatchProcessor", 
    "IngestionManager"
]