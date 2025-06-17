"""
Core OCR processing functionality.
Handles image processing and text extraction using Google Drive API.
"""

import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from config import OCRConfig, Colors
from logger import OCRLogger
from auth import GoogleDriveAuth
from text_processor import TextProcessor


class OCRProcessor:
    """Handles OCR processing using Google Drive API with improved error handling and logging."""
    
    def __init__(self, config: Optional[OCRConfig] = None, flags=None):
        """Initialize OCR processor with configuration."""
        self.config = config or OCRConfig()
        self.logger = OCRLogger(enable_file_logging=self.config.enable_file_logging)
        self.flags = flags
        self.service = None
        self._setup_directories()
        
        # Initialize Google Drive authentication
        self.auth = GoogleDriveAuth(self.config, flags)
        
        # Initialize text processor
        self.text_processor = TextProcessor(
            self.config, 
            self.texts_dir, 
            self.raw_texts_dir
        )
    
    def _setup_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.current_directory = Path.cwd()
        self.images_dir = self.current_directory / self.config.images_dir
        self.raw_texts_dir = self.current_directory / self.config.raw_texts_dir
        self.texts_dir = self.current_directory / self.config.texts_dir
        
        # Create directories
        for directory in [self.raw_texts_dir, self.texts_dir]:
            directory.mkdir(exist_ok=True)
            if self.config.verbose:
                self.logger.debug(f"Ensured directory exists: {directory}")
        
        if not self.images_dir.exists():
            self.images_dir.mkdir(exist_ok=True)
            self.logger.warning(f"Images folder was empty and has been created at: {self.images_dir}")
    
    def initialize_service(self) -> None:
        """Initialize Google Drive API service."""
        self.service = self.auth.initialize_service()
    
    def get_image_files(self) -> List[Path]:
        """Get all supported image files from the images directory."""
        image_files = []
        for ext in self.config.supported_extensions:
            image_files.extend(self.images_dir.rglob(f'*{ext}'))
            image_files.extend(self.images_dir.rglob(f'*{ext.upper()}'))  # Also check uppercase
        
        if not image_files:
            self.logger.warning("No supported image files found in the images directory.")
            self.logger.info(f"Supported formats: {', '.join(self.config.supported_extensions)}")
            return []
        
        # Remove duplicates and filter out already combined files
        unique_files = []
        seen_stems = set()
        for file_path in sorted(image_files):
            if file_path.stem not in seen_stems:
                unique_files.append(file_path)
                seen_stems.add(file_path.stem)
        
        self.logger.info(f"Found {len(unique_files)} unique image file(s) to process")
        return unique_files
    
    def extract_text_from_image(self, image_path: Path) -> Tuple[bool, Optional[str]]:
        """Extract text from a single image using Google Drive OCR."""
        try:
            imgname = image_path.name
            name_without_ext = image_path.stem
            raw_txtfile = self.raw_texts_dir / f'{name_without_ext}.txt'
            txtfile = self.texts_dir / f'{name_without_ext}.txt'
            
            # Skip if already processed
            if txtfile.exists() and raw_txtfile.exists():
                if self.config.verbose:
                    self.logger.warning(f"{imgname} already processed. Skipping...")
                return True, None
            
            if self.config.verbose:
                self.logger.info(f"Processing: {imgname}")
            else:
                print(f"Processing: {imgname}")  # Simple progress indicator
            
            # Upload image to Google Drive for OCR
            mime_type = 'application/vnd.google-apps.document'
            
            upload_request = self.service.files().create(
                body={
                    'name': imgname,
                    'mimeType': mime_type
                },
                media_body=MediaFileUpload(
                    str(image_path), 
                    mimetype=mime_type, 
                    resumable=True
                )
            )
            
            res = upload_request.execute()
            file_id = res['id']
            
            # Download OCR text
            export_request = self.service.files().export_media(
                fileId=file_id, 
                mimeType="text/plain"
            )
              # Download OCR text to a temporary buffer
            temp_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(
                temp_buffer,
                export_request
            )
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status and self.config.verbose:
                    self.logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            
            # Process the downloaded content to remove Google metadata
            temp_buffer.seek(0)
            content = temp_buffer.read().decode('utf-8')
            
            # Remove first 2 lines (Google metadata)
            lines = content.split('\n')
            if len(lines) > 2:
                cleaned_content = '\n'.join(lines[2:])
            else:
                cleaned_content = content
            
            # Save the cleaned raw text
            with open(raw_txtfile, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            # Clean up temporary file from Google Drive
            self.service.files().delete(fileId=file_id).execute()
            
            # Process and clean the extracted text
            self.text_processor.clean_text_file(raw_txtfile, txtfile)
            
            if self.config.verbose:
                self.logger.success(f"{imgname} processed successfully")
            return True, None
            
        except HttpError as e:
            error_msg = f"Google API error processing {image_path.name}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error processing {image_path.name}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def process_all_images(self) -> Dict[str, any]:
        """Process all images in the images directory with detailed reporting."""
        if not self.service:
            self.initialize_service()
        
        image_files = self.get_image_files()
        if not image_files:
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'errors': [],
                'processed_files': []
            }
        
        if self.config.verbose:
            self.logger.info(f"Starting OCR processing for {len(image_files)} image(s)...")
        else:
            print(f"Starting OCR processing for {len(image_files)} image(s)...")
        
        successful = 0
        failed = 0
        errors = []
        processed_files = []
        
        for i, image_path in enumerate(image_files, 1):
            if not self.config.verbose:
                print(f"[{i}/{len(image_files)}] ", end="")  # Simple progress
            elif self.config.verbose:
                self.logger.info(f"Processing file {i}/{len(image_files)}: {image_path.name}")
            
            success, error_msg = self.extract_text_from_image(image_path)
            if success:
                successful += 1
                processed_files.append(str(image_path))
            else:
                failed += 1
                if error_msg:
                    errors.append(error_msg)
        
        # Display summary
        self._display_processing_summary(successful, failed, errors)
        
        # Process text combination if requested and successful extractions exist
        results = {
            'total': len(image_files),
            'successful': successful,
            'failed': failed,
            'errors': errors,
            'processed_files': processed_files
        }
        
        if successful > 0:
            self._handle_text_combination()
        
        return results
    
    def _display_processing_summary(self, successful: int, failed: int, errors: List[str]) -> None:
        """Display a formatted summary of processing results."""
        self.logger.info("\n" + "="*60)
        self.logger.info("PROCESSING SUMMARY", Colors.BOLD)
        self.logger.info("="*60)
        
        if successful > 0:
            self.logger.success(f"Successfully processed: {successful} files")
        
        if failed > 0:
            self.logger.error(f"Failed to process: {failed} files")
            if errors:
                self.logger.error("Error details:")
                for error in errors[-5:]:  # Show last 5 errors
                    self.logger.error(f"  - {error}")
        
        if successful == 0 and failed > 0:
            self.logger.error("No files were successfully processed. Please check your configuration and try again.")
    
    def _handle_text_combination(self) -> None:
        """Handle text file combination based on configuration."""
        if self.config.combine_texts:
            self.logger.info("\n" + "="*50, Colors.CYAN)
            if self.config.include_headers:
                self.logger.info("COMBINING PROCESSED TEXT FILES (WITH HEADERS)", Colors.CYAN)
                self.text_processor.combine_texts_with_headers("texts")
            else:
                self.logger.info("COMBINING PROCESSED TEXT FILES (NO HEADERS)", Colors.CYAN)
                self.text_processor.combine_texts("texts")
            self.logger.info("="*50, Colors.CYAN)
        
        if self.config.combine_raw:
            self.logger.info("\n" + "="*50, Colors.CYAN)
            if self.config.include_headers:
                self.logger.info("COMBINING RAW TEXT FILES (WITH HEADERS)", Colors.CYAN)
                self.text_processor.combine_texts_with_headers("raw_texts")
            else:
                self.logger.info("COMBINING RAW TEXT FILES (NO HEADERS)", Colors.CYAN)
                self.text_processor.combine_texts("raw_texts")
            self.logger.info("="*50, Colors.CYAN)
