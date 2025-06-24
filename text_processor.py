"""
Text processing utilities for OCR Text Extractor.
Handles text cleaning and combination with NLP-friendly formatting.
"""

import os
from pathlib import Path
import json
from datetime import datetime
import re

class TextProcessor:
    """Handles text processing and combination with NLP corpus creation."""
    
    def __init__(self, config, texts_dir, raw_texts_dir):
        self.config = config
        self.texts_dir = Path(texts_dir)
        self.raw_texts_dir = Path(raw_texts_dir)
        
    def clean_text(self, text: str) -> str:
        """Clean extracted text with NLP-friendly processing."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove multiple newlines but preserve paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove non-printable characters except newlines
        text = ''.join(char for char in text if char.isprintable() or char == '\n')
        
        # Strip whitespace from lines while preserving paragraphs
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        # Remove empty lines at start and end
        text = text.strip()
        
        return text

    def create_corpus_document(self, pdf_path: str, page_texts: list, metadata: dict = None) -> str:
        """
        Create a single document for the corpus with metadata and cleaned text.
        
        Args:
            pdf_path: Path to the original PDF
            page_texts: List of texts from each page
            metadata: Optional dictionary of metadata
            
        Returns:
            Processed text with metadata header
        """
        # Prepare metadata
        doc_metadata = {
            "source_file": os.path.basename(pdf_path),
            "creation_date": datetime.now().isoformat(),
            "num_pages": len(page_texts),
            "file_size": os.path.getsize(pdf_path),
        }
        
        if metadata:
            doc_metadata.update(metadata)
        
        # Create document structure
        document = []
        
        # Add metadata as JSON header
        document.append("---")
        document.append(json.dumps(doc_metadata, indent=2))
        document.append("---\n")
        
        # Process and combine page texts
        processed_text = ""
        for i, page_text in enumerate(page_texts, 1):
            # Clean the text
            cleaned_text = self.clean_text(page_text)
            
            # Add page marker (useful for some NLP tasks)
            processed_text += f"[Page {i}]\n{cleaned_text}\n\n"
        
        document.append(processed_text.strip())
        
        return '\n'.join(document)

    def save_corpus_document(self, pdf_path: str, output_dir: Path) -> Path:
        """
        Process all pages from a PDF and save as a single corpus document.
        
        Args:
            pdf_path: Path to the original PDF
            output_dir: Directory to save the processed text
            
        Returns:
            Path to the saved corpus file
        """
        pdf_name = Path(pdf_path).stem
        page_texts = []
        
        # Collect all page texts
        i = 1
        while True:
            page_file = self.raw_texts_dir / f"{pdf_name}_page_{i}.txt"
            if not page_file.exists():
                break
                
            with open(page_file, 'r', encoding='utf-8') as f:
                page_texts.append(f.read())
            i += 1
        
        if not page_texts:
            return None
        
        # Create corpus document
        corpus_text = self.create_corpus_document(pdf_path, page_texts)
        
        # Save corpus file
        output_file = output_dir / f"{pdf_name}_corpus.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(corpus_text)
        
        return output_file

    def process_document(self, pdf_path: str, output_dir: Path, metadata: dict = None) -> Path:
        """
        Main entry point for processing a document for the corpus.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save processed text
            metadata: Optional metadata to include
            
        Returns:
            Path to the processed corpus file
        """
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process and save corpus document
            corpus_file = self.save_corpus_document(pdf_path, output_dir)
            
            if corpus_file and corpus_file.exists():
                # Clean up individual page files if successful
                self._cleanup_page_files(Path(pdf_path).stem)
                return corpus_file
                
        except Exception as e:
            print(f"Error processing document {pdf_path}: {str(e)}")
            return None
    
    def _cleanup_page_files(self, pdf_name: str):
        """Remove individual page files after successful corpus creation."""
        i = 1
        while True:
            raw_file = self.raw_texts_dir / f"{pdf_name}_page_{i}.txt"
            processed_file = self.texts_dir / f"{pdf_name}_page_{i}.txt"
            
            if not raw_file.exists() and not processed_file.exists():
                break
                
            if raw_file.exists():
                raw_file.unlink()
            if processed_file.exists():
                processed_file.unlink()
            i += 1
