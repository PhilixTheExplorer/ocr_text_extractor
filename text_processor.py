"""
Text processing utilities for OCR output.
Handles text cleaning, combination, and file operations.
"""

import time
import shutil
from pathlib import Path
from typing import List, Optional

from config import OCRConfig
from logger import OCRLogger


class TextProcessor:
    """Handles text file processing, cleaning, and combination."""
    
    def __init__(self, config: OCRConfig, texts_dir: Path, raw_texts_dir: Path):
        self.config = config
        self.texts_dir = texts_dir
        self.raw_texts_dir = raw_texts_dir
        self.logger = OCRLogger(enable_file_logging=config.enable_file_logging)
    
    def clean_text_file(self, raw_file: Path, clean_file: Path) -> None:
        """Clean the raw OCR text by replacing line breaks with spaces."""
        try:
            with open(raw_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace all line breaks with spaces
            cleaned_content = content.replace('\n', ' ').replace('\r', ' ')
            
            # Remove excessive whitespace (multiple spaces become single space)
            cleaned_content = ' '.join(cleaned_content.split())
            
            with open(clean_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            if self.config.verbose:
                self.logger.debug(f"Cleaned text saved: {clean_file.name}")
                
        except Exception as e:
            self.logger.warning(f"Error cleaning text file {raw_file.name}: {e}")
            # If cleaning fails, copy raw content
            try:
                with open(raw_file, 'r', encoding='utf-8') as raw_f:
                    with open(clean_file, 'w', encoding='utf-8') as clean_f:
                        clean_f.write(raw_f.read())
            except Exception as copy_error:
                self.logger.error(f"Failed to copy raw content: {copy_error}")
    
    def combine_texts(self, output_dir: str = "texts") -> Optional[str]:
        """Combine all processed text files into a single file without headers."""
        try:
            text_dir = self._get_text_directory(output_dir)
            if not text_dir:
                return None
            
            txt_files = self._get_combinable_files(text_dir)
            if not txt_files:
                self.logger.warning(f"No text files found in {text_dir}")
                return None
            
            # Create output filename with timestamp
            timestamp = int(time.time())
            outfilename = f'combined_all_{timestamp}.txt'
            output_path = text_dir / outfilename
            
            self.logger.info(f"Combining {len(txt_files)} text files without headers...")
            
            with open(output_path, 'wb') as outfile:
                for i, txt_file in enumerate(sorted(txt_files)):
                    if self.config.verbose:
                        self.logger.debug(f"Adding: {txt_file.name}")
                    
                    with open(txt_file, 'rb') as readfile:
                        shutil.copyfileobj(readfile, outfile)
                        
                        # Add separator between files (except for last file)
                        if i < len(txt_files) - 1:
                            outfile.write(b'\n\n--- Next File ---\n\n')
            
            self.logger.success(f"Combined text saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error combining text files: {e}")
            return None
    
    def combine_texts_with_headers(self, output_dir: str = "texts") -> Optional[str]:
        """Combine all processed text files into a single file with clear file separators."""
        try:
            text_dir = self._get_text_directory(output_dir)
            if not text_dir:
                return None
            
            file_prefix = "cleaned" if output_dir == "texts" else "raw"
            txt_files = self._get_combinable_files(text_dir)
            
            if not txt_files:
                self.logger.warning(f"No text files found in {text_dir}")
                return None
            
            # Create output filename with timestamp
            timestamp = int(time.time())
            outfilename = f'combined_{file_prefix}_{timestamp}.txt'
            output_path = text_dir / outfilename
            
            self.logger.info(f"Combining {len(txt_files)} {file_prefix} text files with headers...")
            
            with open(output_path, 'w', encoding='utf-8') as outfile:
                # Write header for the combined file
                self._write_combined_file_header(outfile, file_prefix, len(txt_files))
                
                for i, txt_file in enumerate(sorted(txt_files)):
                    if self.config.verbose:
                        self.logger.debug(f"Adding: {txt_file.name}")
                    
                    # Write file header
                    self._write_file_separator(outfile, i + 1, txt_file.name)
                    
                    # Write file content
                    self._write_file_content(outfile, txt_file)
                    
                    # Add separator (except for last file)
                    if i < len(txt_files) - 1:
                        outfile.write('\n' + '-'*40 + '\n\n')
            
            self.logger.success(f"Combined {file_prefix} text with headers saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error combining text files with headers: {e}")
            return None
    
    def _get_text_directory(self, output_dir: str) -> Optional[Path]:
        """Get the appropriate text directory based on output_dir parameter."""
        if output_dir == "texts":
            return self.texts_dir
        elif output_dir == "raw_texts":
            return self.raw_texts_dir
        else:
            self.logger.error(f"Invalid output directory: {output_dir}")
            return None
    
    def _get_combinable_files(self, text_dir: Path) -> List[Path]:
        """Get all txt files excluding already combined files."""
        all_txt_files = list(text_dir.glob('*.txt'))
        return [f for f in all_txt_files if not f.name.startswith('combined_')]
    
    def _write_combined_file_header(self, outfile, file_prefix: str, file_count: int) -> None:
        """Write header information for the combined file."""
        outfile.write(f"Combined {file_prefix.upper()} OCR Text Files\n")
        outfile.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        outfile.write(f"Total files: {file_count}\n")
        outfile.write(f"{'='*80}\n\n")
    
    def _write_file_separator(self, outfile, file_number: int, filename: str) -> None:
        """Write file separator header."""
        outfile.write(f"{'='*60}\n")
        outfile.write(f"FILE {file_number}: {filename}\n")
        outfile.write(f"{'='*60}\n\n")
    
    def _write_file_content(self, outfile, txt_file: Path) -> None:
        """Write content of a single file to the combined output."""
        try:
            with open(txt_file, 'r', encoding='utf-8') as readfile:
                content = readfile.read().strip()
                if content:
                    outfile.write(content)
                else:
                    outfile.write("[No content or empty file]")
                outfile.write('\n')
        except Exception as file_error:
            outfile.write(f"[Error reading file: {file_error}]\n")
            if self.config.verbose:
                self.logger.warning(f"Error reading file {txt_file.name}: {file_error}")
