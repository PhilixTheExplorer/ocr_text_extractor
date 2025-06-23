"""
Configuration module for OCR Text Extractor.
Contains all configuration classes and settings.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class ProcessingMode(Enum):
    """Processing modes for text combination."""
    CLEAN_ONLY = "clean_only"
    RAW_ONLY = "raw_only"
    BOTH = "both"


@dataclass
class OCRConfig:
    """Configuration settings for OCR processing."""
    scopes: str = 'https://www.googleapis.com/auth/drive'
    credentials_file: str = 'credentials.json'
    application_name: str = 'OCR Text Extractor'
    supported_extensions: List[str] = None
    images_dir: str = 'images'
    raw_texts_dir: str = 'raw_texts'
    texts_dir: str = 'texts'
    combine_texts: bool = True
    combine_raw: bool = False
    include_headers: bool = False
    verbose: bool = False  # Control logging verbosity
    enable_file_logging: bool = False  # Enable file logging
    
    def __post_init__(self):
        if self.supported_extensions is None:
            self.supported_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
