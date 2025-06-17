"""
OCR Text Extraction using Google Drive API
Extracts text from images using Google Drive's built-in OCR capabilities.

Version: 1.0.0
Release: Initial modular release with enhanced functionality

This is the main entry point for the OCR Text Extractor.
The application features a modular architecture for better maintainability and organization.

Key Features:
- Modular, maintainable codebase
- Clean output without duplicate logging
- Enhanced command line interface
- Comprehensive error handling
- Flexible text combination options
"""

import sys
from pathlib import Path

# Add current directory to Python path to allow local imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from config import OCRConfig, Colors
from ocr_processor import OCRProcessor
from cli import (
    setup_argument_parser,
    create_config_from_args,
    display_final_results
)


def main():
    """Main function to run the OCR processor with enhanced configuration and error handling."""
    try:
        # Parse command line arguments
        parser = setup_argument_parser()
        args = parser.parse_args()
        
        # Create configuration from arguments
        config = create_config_from_args(args)
        
        # Initialize processor with configuration and parsed flags
        processor = OCRProcessor(config, args)
        
        # Process all images and get detailed results
        results = processor.process_all_images()
        
        # Display final results
        display_final_results(processor, results)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user.{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}Fatal error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == '__main__':
    main()
