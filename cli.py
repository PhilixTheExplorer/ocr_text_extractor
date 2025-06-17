"""
Command line interface and argument parsing utilities.
"""

import argparse
from typing import Dict

from oauth2client import tools

from config import OCRConfig, Colors
from logger import OCRLogger


def create_default_config() -> OCRConfig:
    """Create a default configuration for OCR processing."""
    return OCRConfig(
        combine_texts=True,
        combine_raw=False,
        include_headers=False
    )


def create_config_from_args(args: argparse.Namespace) -> OCRConfig:
    """Create configuration from command line arguments."""
    return OCRConfig(
        credentials_file=getattr(args, 'credentials', 'credentials.json'),
        combine_texts=getattr(args, 'combine_texts', True),
        combine_raw=getattr(args, 'combine_raw', False),
        include_headers=getattr(args, 'include_headers', False),
        supported_extensions=getattr(args, 'extensions', ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']),
        verbose=getattr(args, 'verbose', False),
        enable_file_logging=getattr(args, 'enable_file_logging', False)
    )


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description='OCR Text Extraction using Google Drive API - Version 1.0.0',
        parents=[tools.argparser],
        conflict_handler='resolve'
    )
    
    parser.add_argument(
        '--credentials', 
        default='credentials.json',
        help='Path to Google credentials JSON file (default: credentials.json)'
    )
    
    parser.add_argument(
        '--no-combine-texts', 
        dest='combine_texts', 
        action='store_false',
        help='Do not combine processed text files'
    )
    
    parser.add_argument(
        '--combine-raw', 
        action='store_true',
        help='Also combine raw text files'
    )
    
    parser.add_argument(
        '--include-headers', 
        action='store_true',
        help='Include file headers in combined files'
    )
    
    parser.add_argument(
        '--extensions', 
        nargs='*',
        default=['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
        help='Supported image file extensions'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging output'
    )
    
    parser.add_argument(
        '--enable-file-logging', 
        action='store_true',
        help='Enable logging to file (ocr_processing.log)'
    )
    
    parser.add_argument(
        '--version', 
        action='version',
        version='OCR Text Extractor 1.0.0'
    )
    
    return parser


def display_final_results(processor, results: Dict[str, any]) -> None:
    """Display comprehensive final results."""
    logger = OCRLogger()
    
    logger.info(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}")
    logger.info("OCR PROCESSING AND TEXT COMBINATION COMPLETE!")
    logger.info(f"{'='*60}{Colors.RESET}")
    
    # Processing statistics
    logger.info(f"Total files processed: {results['total']}")
    if results['successful'] > 0:
        logger.success(f"Successfully processed: {results['successful']} files")
    if results['failed'] > 0:
        logger.error(f"Failed to process: {results['failed']} files")
    
    # Directory information
    logger.info("\nResults can be found in:")
    logger.info(f"📁 Individual cleaned text files: {processor.texts_dir}")
    logger.info(f"📁 Individual raw text files: {processor.raw_texts_dir}")
    
    if results['successful'] > 0:
        if processor.config.combine_texts:
            logger.success("📄 Combined cleaned text: Look for 'combined_cleaned_*.txt' in texts directory")
        if processor.config.combine_raw:
            logger.success("📄 Combined raw text: Look for 'combined_raw_*.txt' in raw_texts directory")
    
    # Performance summary
    if results['total'] > 0:
        success_rate = (results['successful'] / results['total']) * 100
        logger.info(f"\nSuccess rate: {success_rate:.1f}%")
    
    logger.info(f"\n{Colors.CYAN}Thank you for using OCR Text Extractor!{Colors.RESET}")
