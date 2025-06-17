"""
Logging utilities for OCR Text Extractor.
Provides colored console output and optional file logging.
"""

import logging
from config import Colors


class OCRLogger:
    """Custom logger for OCR processing with colored output only."""
    
    def __init__(self, name: str = "OCRProcessor", enable_file_logging: bool = False):
        self.name = name
        self.enable_file_logging = enable_file_logging
        
        if enable_file_logging:
            self.logger = logging.getLogger(name)
            self.logger.setLevel(logging.INFO)
            
            if not self.logger.handlers:
                handler = logging.FileHandler('ocr_processing.log')
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
        else:
            self.logger = None
    
    def info(self, message: str, color: str = Colors.WHITE):
        print(f"{color}{message}{Colors.RESET}")
        if self.logger:
            self.logger.info(message)
    
    def success(self, message: str):
        print(f"{Colors.GREEN}{message}{Colors.RESET}")
        if self.logger:
            self.logger.info(f"SUCCESS: {message}")
    
    def warning(self, message: str):
        print(f"{Colors.YELLOW}{message}{Colors.RESET}")
        if self.logger:
            self.logger.warning(message)
    
    def error(self, message: str):
        print(f"{Colors.RED}{message}{Colors.RESET}")
        if self.logger:
            self.logger.error(message)
    
    def debug(self, message: str):
        if self.logger:
            self.logger.debug(message)
