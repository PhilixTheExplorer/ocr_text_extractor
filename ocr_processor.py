"""
Core OCR processing functionality.
Handles image processing and text extraction using Google Drive API.
"""

import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
from socket import timeout as SocketTimeout

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.discovery import build

from config import OCRConfig, Colors
from logger import OCRLogger
from auth import GoogleDriveAuth
from text_processor import TextProcessor


class OCRProcessor:
    """Handles OCR processing using Google Drive API with improved error handling and logging."""
    
    def __init__(self, config_or_credentials=None, flags=None):
        """Initialize OCR processor with configuration or credentials."""
        if isinstance(config_or_credentials, OCRConfig):
            self.config = config_or_credentials
            self.logger = OCRLogger(enable_file_logging=self.config.enable_file_logging)
            self.auth = GoogleDriveAuth(self.config, flags)
            self.service = None
        else:
            # For GUI usage with direct credentials
            self.config = OCRConfig()
            self.logger = OCRLogger(enable_file_logging=False)  # Disable file logging for GUI
            self.service = build('drive', 'v3', credentials=config_or_credentials)
            
        self.flags = flags
        self._setup_directories()
        
        # Initialize text processor
        self.text_processor = TextProcessor(
            self.config, 
            self.texts_dir, 
            self.raw_texts_dir
        )
        
        # Configure retry settings
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.upload_timeout = 300  # 5 minutes
        self.download_timeout = 300  # 5 minutes
        self.chunk_size = 262144  # 256KB chunks for upload/download
    
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
    
    def _execute_with_retry(self, request, operation_name="API request"):
        """Execute a request with retry logic."""
        for attempt in range(self.max_retries):
            try:
                if self.config.verbose:
                    self.logger.debug(f"Attempt {attempt + 1} of {self.max_retries} for {operation_name}")
                return request.execute()
            except (HttpError, SocketTimeout, TimeoutError) as e:
                if attempt == self.max_retries - 1:  # Last attempt
                    raise
                wait_time = self.retry_delay * (attempt + 1)  # Exponential backoff
                if self.config.verbose:
                    self.logger.warning(f"{operation_name} failed, retrying in {wait_time} seconds... Error: {str(e)}")
                time.sleep(wait_time)
    
    def extract_text_from_image(self, image_path: Path) -> Tuple[bool, Optional[str]]:
        """Extract text from a single image using Google Drive OCR."""
        try:
            imgname = image_path.name
            # Get the PDF name and page number from the image path
            # Expected format: .../pdf_name/page_X.jpg
            pdf_name = image_path.parent.name
            page_num = ''.join(filter(str.isdigit, image_path.stem))  # Extract number from page_X
            
            # Create text files with the expected naming convention
            raw_txtfile = self.raw_texts_dir / f'{pdf_name}_page_{page_num}.txt'
            txtfile = self.texts_dir / f'{pdf_name}_page_{page_num}.txt'
            
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
            
            media = MediaFileUpload(
                str(image_path), 
                mimetype=mime_type, 
                resumable=True,
                chunksize=self.chunk_size
            )
            
            upload_request = self.service.files().create(
                body={
                    'name': imgname,
                    'mimeType': mime_type
                },
                media_body=media
            )
            
            res = self._execute_with_retry(upload_request, f"Upload of {imgname}")
            file_id = res['id']
            
            try:
                # Download OCR text
                export_request = self.service.files().export_media(
                    fileId=file_id, 
                    mimeType="text/plain"
                )
                
                # Download OCR text to a temporary buffer
                temp_buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(
                    temp_buffer,
                    export_request,
                    chunksize=self.chunk_size
                )
                
                done = False
                download_timeout = time.time() + self.download_timeout
                
                while not done and time.time() < download_timeout:
                    try:
                        status, done = downloader.next_chunk()
                        if status and self.config.verbose:
                            self.logger.debug(f"Download progress: {int(status.progress() * 100)}%")
                    except (HttpError, SocketTimeout) as e:
                        if time.time() >= download_timeout:
                            raise TimeoutError(f"Download timeout for {imgname}")
                        time.sleep(2)  # Short delay before retry
                        continue
                
                if not done:
                    raise TimeoutError(f"Download timeout for {imgname}")
                
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
                
                # Save cleaned version of the text
                cleaned_text = self.text_processor.clean_text(cleaned_content)
                with open(txtfile, 'w', encoding='utf-8') as f:
                    f.write(cleaned_text)
                
                if self.config.verbose:
                    self.logger.success(f"{imgname} processed successfully")
                return True, None
                
            finally:
                # Clean up temporary file from Google Drive
                try:
                    self.service.files().delete(fileId=file_id).execute()
                except Exception as e:
                    self.logger.warning(f"Failed to delete temporary file {file_id} from Google Drive: {e}")
            
        except TimeoutError as e:
            error_msg = f"Timeout error processing {image_path.name}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
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
