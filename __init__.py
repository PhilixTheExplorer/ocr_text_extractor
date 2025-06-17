"""
Package initialization file for OCR Text Extractor.
Provides convenient imports for the main components.
"""

from config import OCRConfig, ProcessingMode, Colors
from logger import OCRLogger
from auth import GoogleDriveAuth
from text_processor import TextProcessor
from ocr_processor import OCRProcessor
from cli import (
    create_default_config,
    create_config_from_args,
    setup_argument_parser,
    display_final_results
)

__version__ = "1.0.0"
__author__ = "Philix Hein"

__all__ = [
    'OCRConfig',
    'ProcessingMode', 
    'Colors',
    'OCRLogger',
    'GoogleDriveAuth',
    'TextProcessor',
    'OCRProcessor',
    'create_default_config',
    'create_config_from_args',
    'setup_argument_parser',
    'display_final_results'
]
