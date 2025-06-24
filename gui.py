import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pdf2image import convert_from_path
from PIL import Image, ImageTk
import threading
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from pathlib import Path
import time
import humanize
from datetime import datetime, timedelta
import psutil
import shutil
from ocr_processor import OCRProcessor
from text_processor import TextProcessor
from typing import Dict, List, Optional, Tuple, Union

class ResourceMonitor:
    """Monitors system resources during OCR processing."""
    
    def __init__(self) -> None:
        self.process = psutil.Process()
    
    def get_usage(self) -> Dict[str, Union[float, int]]:
        return {
            'memory_percent': self.process.memory_percent(),
            'cpu_percent': self.process.cpu_percent(),
            'memory_info': self.process.memory_info(),
            'num_threads': self.process.num_threads()
        }
    
    def get_formatted_usage(self) -> str:
        usage = self.get_usage()
        return (
            f"Memory: {usage['memory_percent']:.1f}% | "
            f"CPU: {usage['cpu_percent']:.1f}% | "
            f"Threads: {usage['num_threads']}"
        )

class ScanAnimation:
    """Handles the scanning animation overlay during OCR processing."""
    
    def __init__(self, canvas: tk.Canvas, preview_height: int) -> None:
        self.canvas = canvas
        self.preview_height = preview_height
        self.scan_line = None
        self.is_running = False
        self.y_position = 0
        self.animation_speed = 2  # pixels per frame
        self.after_id = None  # Track the after callback
        
    def start(self) -> None:
        """Start or restart the scanning animation from the top."""
        self.stop()  # Clear any existing animation
        self.is_running = True
        self.y_position = 0  # Reset to top
        
        # Create the scan line if it doesn't exist
        if not self.scan_line:
            self.scan_line = self.canvas.create_line(
                0, 0, self.canvas.winfo_width(), 0,
                fill='#00ff00', width=2,
                tags=('scan_line',)  # Add a tag for easier management
            )
        else:
            # Move existing line to top
            self.canvas.coords(
                self.scan_line,
                0, 0,
                self.canvas.winfo_width(), 0
            )
            
        self.canvas.tag_raise(self.scan_line)  # Ensure line is on top
        self.animate()
    
    def stop(self) -> None:
        """Stop the scanning animation."""
        self.is_running = False
        if self.after_id:
            self.canvas.after_cancel(self.after_id)
            self.after_id = None
        if self.scan_line:
            self.canvas.delete(self.scan_line)
            self.scan_line = None
    
    def animate(self) -> None:
        """Animate the scanning line moving down."""
        if not self.is_running:
            return
            
        # Reset to top if reached bottom
        if self.y_position >= self.preview_height:
            self.y_position = 0
        
        try:
            # Update line position
            self.canvas.coords(
                self.scan_line,
                0, self.y_position,
                self.canvas.winfo_width(), self.y_position
            )
            self.canvas.tag_raise(self.scan_line)  # Keep line on top
            
            # Move down
            self.y_position += self.animation_speed
            
            # Schedule next frame
            if self.is_running:
                self.after_id = self.canvas.after(20, self.animate)
                
        except tk.TclError:
            # Handle case where canvas was modified
            self.scan_line = None
            if self.is_running:
                # Recreate line and continue animation
                self.scan_line = self.canvas.create_line(
                    0, self.y_position,
                    self.canvas.winfo_width(), self.y_position,
                    fill='#00ff00', width=2,
                    tags=('scan_line',)
                )
                self.after_id = self.canvas.after(20, self.animate)

    def update_canvas_size(self, new_height: int) -> None:
        """Update the animation bounds when canvas size changes."""
        self.preview_height = new_height
        if self.y_position >= self.preview_height:
            self.y_position = 0
        if self.scan_line:
            # Update line width to match new canvas size
            self.canvas.coords(
                self.scan_line,
                0, self.y_position,
                self.canvas.winfo_width(), self.y_position
            )

class OCRApp(ctk.CTk):
    """Main application class for the OCR Text Extractor GUI."""
    
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("OCR Text Extractor")
        self.geometry("1200x900")  # Increased size for preview
        ctk.set_appearance_mode("system")
        
        # Initialize cache
        self._image_cache = {}
        self._cache_size_limit = 50  # Maximum number of cached images
        
        # Processing state
        self.is_processing = False
        self.is_paused = False
        self.current_thread = None
        
        # Initialize variables
        self.credentials = None
        self.auth_status = False
        self.ocr_processor = None
        self.selected_pdfs = []
        self.output_dir = os.path.join(os.getcwd(), "output")
        self.current_preview = None
        self.start_time = None
        self.processing_times = []
        self.text_processor = TextProcessor(
            config=None,  # We'll use default config
            texts_dir=os.path.join(os.getcwd(), "texts"),
            raw_texts_dir=os.path.join(os.getcwd(), "raw_texts")
        )
        
        # Initialize resource monitor
        self.resource_monitor = ResourceMonitor()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=3)  # Main area
        self.grid_columnconfigure(1, weight=1)  # Preview area
        self.grid_rowconfigure(3, weight=1)
        
        # Create UI elements
        self.create_theme_controls()
        self.create_auth_status()
        self.create_file_management()
        self.create_output_settings()
        self.create_processing_area()
        self.create_preview_panel()
        self.create_status_bar()
        
        # Start resource monitoring
        self.start_resource_monitoring()
        
        # Check authentication status
        self.check_auth_status()

    def create_theme_controls(self):
        """Create theme selection controls in the GUI.
        
        Creates a frame with buttons to switch between Light, Dark, and System themes.
        """
        self.theme_frame = ctk.CTkFrame(self)
        self.theme_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(10,0), sticky="ew")
        
        # Theme selection
        theme_label = ctk.CTkLabel(
            self.theme_frame,
            text="Theme:",
            font=("Arial", 12)
        )
        theme_label.pack(side="left", padx=10)
        
        self.theme_var = ctk.StringVar(value="system")
        theme_options = ["Light", "Dark", "System"]
        
        for theme in theme_options:
            theme_btn = ctk.CTkButton(
                self.theme_frame,
                text=theme,
                width=80,
                command=lambda t=theme: self.change_theme(t.lower()),
                font=("Arial", 12)
            )
            theme_btn.pack(side="left", padx=5)
    
    def create_status_bar(self):
        """Create status bar with system resource information."""
        self.status_bar = ctk.CTkFrame(self)
        self.status_bar.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Resource usage label
        self.resource_label = ctk.CTkLabel(
            self.status_bar,
            text="Resource Usage: --",
            font=("Arial", 10)
        )
        self.resource_label.pack(side="left", padx=10)
        
        # Version info
        version_label = ctk.CTkLabel(
            self.status_bar,
            text="v1.0.0",
            font=("Arial", 10)
        )
        version_label.pack(side="right", padx=10)
    
    def change_theme(self, theme: str):
        """Change the application theme."""
        ctk.set_appearance_mode(theme)
        self.theme_var.set(theme)
    
    def start_resource_monitoring(self):
        """Start monitoring system resources."""
        def update_resources():
            usage = self.resource_monitor.get_formatted_usage()
            self.resource_label.configure(text=f"Resource Usage: {usage}")
            self._monitoring_after_id = self.after(2000, update_resources)  # Store the after ID
        
        update_resources()

    def create_auth_status(self):
        """Create authentication status display and controls.
        
        Creates a frame showing Google API authentication status and authentication button.
        """
        self.auth_frame = ctk.CTkFrame(self)
        self.auth_frame.grid(row=0, column=0, padx=20, pady=(20,10), sticky="ew")
        
        # Status indicator and button in same row
        self.auth_label = ctk.CTkLabel(
            self.auth_frame,
            text="⚠️ Not authenticated with Google API",
            text_color="red",
            font=("Arial", 14, "bold")
        )
        self.auth_label.pack(side="left", pady=10, padx=10)
        
        self.auth_button = ctk.CTkButton(
            self.auth_frame,
            text="Authenticate with Google",
            command=self.authenticate,
            font=("Arial", 12)
        )
        self.auth_button.pack(side="right", pady=10, padx=10)

    def create_file_management(self):
        """Create file management controls.
        
        Creates a frame with buttons for PDF selection and file management operations.
        Includes:
        - Select PDFs button
        - Selected files counter
        - Clear selection button
        """
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        # PDF Selection
        self.select_button = ctk.CTkButton(
            self.file_frame,
            text="Select PDFs",
            command=self.select_pdfs,
            state="disabled",
            font=("Arial", 12)
        )
        self.select_button.pack(side="left", padx=10, pady=10)
        
        # Selected files counter
        self.files_label = ctk.CTkLabel(
            self.file_frame,
            text="No files selected",
            font=("Arial", 12)
        )
        self.files_label.pack(side="left", padx=10, pady=10)
        
        # Clear selection button
        self.clear_button = ctk.CTkButton(
            self.file_frame,
            text="Clear Selection",
            command=self.clear_selection,
            state="disabled",
            font=("Arial", 12)
        )
        self.clear_button.pack(side="right", padx=10, pady=10)

    def select_pdfs(self) -> None:
        """Open file dialog to select PDF files."""
        files = filedialog.askopenfilenames(
            title="Select PDF Files",
            filetypes=[("PDF files", "*.pdf")]
        )
        if files:
            self.selected_pdfs = list(files)
            self.files_label.configure(text=f"{len(self.selected_pdfs)} PDF(s) selected")
            self.clear_button.configure(state="normal")
            self.process_button.configure(state="normal")
            self.log_message("Selected PDF files: " + "\n".join(self.selected_pdfs))

    def clear_selection(self) -> None:
        """Clear the selected PDF files."""
        self.selected_pdfs = []
        self.files_label.configure(text="No files selected")
        self.clear_button.configure(state="disabled")
        self.process_button.configure(state="disabled")
        self.log_message("Cleared file selection")

    def select_output_dir(self) -> None:
        """Open directory dialog to select output directory."""
        dir_path = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir
        )
        if dir_path:
            self.output_dir = dir_path
            self.output_path.delete(0, tk.END)
            self.output_path.insert(0, dir_path)
            self.log_message(f"Output directory set to: {dir_path}")

    def create_output_settings(self):
        """Create output directory settings controls.
        
        Creates a frame with:
        - Output directory selection
        - Directory path display
        - Browse button
        - Start processing button
        """
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # Output directory selection
        self.output_label = ctk.CTkLabel(
            self.settings_frame,
            text="Output Directory:",
            font=("Arial", 12)
        )
        self.output_label.pack(side="left", padx=10, pady=10)
        
        self.output_path = ctk.CTkEntry(
            self.settings_frame,
            width=400,
            font=("Arial", 12)
        )
        self.output_path.insert(0, self.output_dir)
        self.output_path.pack(side="left", padx=10, pady=10)
        
        self.browse_button = ctk.CTkButton(
            self.settings_frame,
            text="Browse",
            command=self.select_output_dir,
            font=("Arial", 12)
        )
        self.browse_button.pack(side="left", padx=10, pady=10)
        
        # Start processing button
        self.process_button = ctk.CTkButton(
            self.settings_frame,
            text="Start Processing",
            command=self.start_processing,
            state="disabled",
            font=("Arial", 12, "bold")
        )
        self.process_button.pack(side="right", padx=10, pady=10)

    def create_processing_area(self):
        """Create the main processing area interface.
        
        Creates a frame containing:
        - Processing controls (pause/cancel)
        - Progress bars for PDF and OCR processing
        - Status labels
        - Processing log
        """
        self.processing_frame = ctk.CTkFrame(self)
        self.processing_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        
        # Add processing controls
        self.control_frame = ctk.CTkFrame(self.processing_frame)
        self.control_frame.pack(fill="x", padx=10, pady=5)
        
        self.pause_button = ctk.CTkButton(
            self.control_frame,
            text="Pause",
            command=self.toggle_processing,
            state="disabled",
            width=100,
            font=("Arial", 12)
        )
        self.pause_button.pack(side="left", padx=5)
        
        self.cancel_button = ctk.CTkButton(
            self.control_frame,
            text="Cancel",
            command=self.cancel_processing,
            state="disabled",
            width=100,
            font=("Arial", 12)
        )
        self.cancel_button.pack(side="left", padx=5)
        
        # Rest of the processing area UI
        self.pdf_progress_label = ctk.CTkLabel(
            self.processing_frame,
            text="PDF to Image Conversion:",
            font=("Arial", 12)
        )
        self.pdf_progress_label.pack(fill="x", padx=10, pady=(10,5))
        
        self.pdf_progress = ctk.CTkProgressBar(self.processing_frame)
        self.pdf_progress.pack(fill="x", padx=10, pady=(0,10))
        self.pdf_progress.set(0)
        
        # OCR Progress
        self.ocr_progress_label = ctk.CTkLabel(
            self.processing_frame,
            text="OCR Processing:",
            font=("Arial", 12)
        )
        self.ocr_progress_label.pack(fill="x", padx=10, pady=(10,5))
        
        self.ocr_progress = ctk.CTkProgressBar(self.processing_frame)
        self.ocr_progress.pack(fill="x", padx=10, pady=(0,10))
        self.ocr_progress.set(0)
        
        # Status and Log
        self.status_label = ctk.CTkLabel(
            self.processing_frame,
            text="Ready",
            font=("Arial", 12),
            anchor="w"
        )
        self.status_label.pack(fill="x", padx=10, pady=5)
        
        # Create a frame for the log with a title
        self.log_frame = ctk.CTkFrame(self.processing_frame)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_title = ctk.CTkLabel(
            self.log_frame,
            text="Processing Log",
            font=("Arial", 12, "bold")
        )
        self.log_title.pack(pady=5)
        
        self.log_text = ctk.CTkTextbox(self.log_frame, height=200)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)

    def handle_drop(self, event):
        """Handle drag and drop of PDF files."""
        files = event.data
        if files:
            # Convert the dropped data to a list of files
            if isinstance(files, str):
                files = self.normalize_drop_data(files)
            
            # Filter for PDF files
            pdf_files = [f for f in files if f.lower().endswith('.pdf')]
            
            if pdf_files:
                self.selected_pdfs.extend(pdf_files)
                self.files_label.configure(text=f"{len(self.selected_pdfs)} PDF(s) selected")
                self.clear_button.configure(state="normal")
                self.process_button.configure(state="normal")
                self.log_message("Added PDF files via drag & drop:\n" + "\n".join(pdf_files))
            else:
                messagebox.showwarning("Invalid Files", "Please drop only PDF files.")

    def normalize_drop_data(self, data):
        """Normalize dropped file data to a list of file paths."""
        # Handle different formats of drop data
        if '{' in data:  # Windows/Unix file list
            files = data.strip('{}').split('} {')
        else:  # Single file
            files = [data]
        return files

    def toggle_processing(self):
        """Pause or resume processing."""
        if self.is_processing:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_button.configure(text="Resume")
                self.status_label.configure(text="Processing paused")
                self.log_message("\n⏸️ Processing paused")
                # Stop scanning animation while paused
                if hasattr(self, 'scan_animation'):
                    self.scan_animation.stop()
            else:
                self.pause_button.configure(text="Pause")
                self.status_label.configure(text="Processing resumed")
                self.log_message("\n▶️ Processing resumed")
                # Restart scanning animation if we were processing OCR
                if hasattr(self, 'preview_canvas') and self.preview_canvas.find_withtag("all"):
                    self.scan_animation.start()

    def cancel_processing(self):
        """Cancel the current processing job."""
        if self.is_processing:
            self.is_processing = False
            self.status_label.configure(text="⚠️ Processing cancelled by user")
            self.log_message("\n⚠️ Processing cancelled by user")
            
            # Stop the scanning animation if active
            if self.scan_animation:
                self.scan_animation.stop()
            
            # Clear preview if it was showing a processing page
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                self.preview_canvas.winfo_width() // 2,
                self.preview_canvas.winfo_height() // 2,
                text="Processing cancelled",
                fill="red",
                font=("Arial", 14, "bold")
            )
            self.file_info_label.configure(text="No file processing")
            
            # Reset progress indicators
            self.pdf_progress.set(0)
            self.ocr_progress.set(0)
            
            # Reset time estimates
            self.elapsed_time_label.configure(text="Elapsed Time: --:--")
            self.remaining_time_label.configure(text="Est. Remaining: --:--")
            self.avg_time_label.configure(text="Avg. Time per Page: --:--")
            
            # Reset processing state
            self.is_paused = False
            self.pause_button.configure(text="Pause", state="disabled")
            self.cancel_button.configure(state="disabled")
            
            # Re-enable file selection controls
            self.process_button.configure(state="normal")
            self.select_button.configure(state="normal")
            if self.selected_pdfs:
                self.clear_button.configure(state="normal")

    def reset_ui(self):
        """Reset UI elements after processing is done or cancelled."""
        # Reset buttons
        self.process_button.configure(state="normal")
        self.select_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Pause")
        self.cancel_button.configure(state="disabled")
        
        # Reset progress bars
        self.pdf_progress.set(0)
        self.ocr_progress.set(0)
        
        # Reset preview
        if hasattr(self, 'preview_canvas'):
            self.preview_canvas.delete("all")
            # Show ready state message
            self.preview_canvas.create_text(
                self.preview_canvas.winfo_width() // 2,
                self.preview_canvas.winfo_height() // 2,
                text="Ready for processing",
                fill="gray",
                font=("Arial", 14)
            )
        if hasattr(self, 'file_info_label'):
            self.file_info_label.configure(text="No file processing")
        
        # Reset time tracking
        if hasattr(self, 'elapsed_time_label'):
            self.elapsed_time_label.configure(text="Elapsed Time: --:--")
        if hasattr(self, 'remaining_time_label'):
            self.remaining_time_label.configure(text="Est. Remaining: --:--")
        if hasattr(self, 'avg_time_label'):
            self.avg_time_label.configure(text="Avg. Time per Page: --:--")
        
        # Reset processing state
        self.is_paused = False
        self.is_processing = False
        
        # Update clear button state based on selection
        if hasattr(self, 'clear_button'):
            if self.selected_pdfs:
                self.clear_button.configure(state="normal")
            else:
                self.clear_button.configure(state="disabled")
        
        # Stop scanning animation if active
        if hasattr(self, 'scan_animation'):
            self.scan_animation.stop()

    def start_processing(self):
        if not self.selected_pdfs:
            messagebox.showwarning("No Files", "Please select PDF files to process")
            return
        
        # Update UI state
        self.process_button.configure(state="disabled")
        self.select_button.configure(state="disabled")
        self.clear_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pause")
        self.cancel_button.configure(state="normal")
        
        # Reset progress bars and preview
        self.pdf_progress.set(0)
        self.ocr_progress.set(0)
        self.preview_canvas.delete("all")
        self.file_info_label.configure(text="Starting processing...")
        
        # Set processing flags
        self.is_processing = True
        self.is_paused = False
        
        # Start processing in a separate thread
        self.current_thread = threading.Thread(target=self.process_files)
        self.current_thread.daemon = True  # Make thread daemon so it stops when app closes
        self.current_thread.start()

    def process_files(self):
        """Process selected PDF files with OCR.
        
        Main processing function that:
        1. Converts PDFs to images
        2. Processes images with OCR
        3. Creates corpus documents with metadata
        4. Handles progress updates and UI feedback
        5. Manages temporary files and cleanup
        
        Includes comprehensive error handling and processing state management.
        """
        try:
            total_pdfs = len(self.selected_pdfs)
            self.reset_time_tracking()
            
            for pdf_index, pdf_path in enumerate(self.selected_pdfs):
                if not self.is_processing:  # Check if cancelled
                    self.log_message("\n⚠️ Processing cancelled by user")
                    return
                    
                pdf_size = os.path.getsize(pdf_path)
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                self.log_message(f"\nProcessing PDF {pdf_index + 1} of {total_pdfs}: {os.path.basename(pdf_path)}")
                self.log_message(f"File size: {humanize.naturalsize(pdf_size)}")
                self.status_label.configure(text=f"Converting PDF {pdf_index + 1} of {total_pdfs}")
                
                # Get the output directory from the entry widget
                current_output_dir = self.output_path.get()
                if not current_output_dir:
                    current_output_dir = self.output_dir
                
                # Create PDF-specific output directory
                pdf_output_dir = os.path.join(current_output_dir, pdf_name)
                os.makedirs(pdf_output_dir, exist_ok=True)
                
                # Create temporary directory for intermediate files
                temp_dir = os.path.join(os.getcwd(), "temp_processing", pdf_name)
                os.makedirs(temp_dir, exist_ok=True)
                
                try:
                    # Convert PDF to images
                    images = convert_from_path(pdf_path)
                    total_pages = len(images)
                    
                    self.log_message(f"Found {total_pages} pages")
                    
                    # Save images to temporary directory
                    image_paths = []
                    for i, image in enumerate(images):
                        while self.is_paused:  # Handle pause
                            if not self.is_processing:  # Check if cancelled during pause
                                return
                            time.sleep(0.1)
                        if not self.is_processing:  # Check if cancelled
                            return
                            
                        image_path = os.path.join(temp_dir, f'page_{i+1}.jpg')
                        image.save(image_path, 'JPEG')
                        image_paths.append(image_path)
                        
                        # Update progress and preview
                        pdf_progress = (i + 1) / total_pages
                        self.pdf_progress.set(pdf_progress)
                        self.status_label.configure(text=f"Saved page {i+1} of {total_pages}")
                        self.log_message(f"Saved page {i+1}")
                        self.update_preview(image_path, is_ocr_processing=False)
                    
                    if not self.is_processing:  # Check if cancelled
                        return
                    
                    # Process images with OCR
                    self.log_message("Starting OCR processing...")
                    self.status_label.configure(text=f"Processing OCR for PDF {pdf_index + 1} of {total_pdfs}")
                    
                    if not self.ocr_processor:
                        self.ocr_processor = OCRProcessor(self.credentials)
                    
                    for i, image_path in enumerate(image_paths):
                        while self.is_paused:  # Handle pause
                            if not self.is_processing:  # Check if cancelled during pause
                                return
                            time.sleep(0.1)
                        if not self.is_processing:  # Check if cancelled
                            return
                            
                        # Update preview with scanning animation
                        self.update_preview(image_path, is_ocr_processing=True)
                        
                        success, error = self.ocr_processor.extract_text_from_image(Path(image_path))
                        if not success:
                            raise Exception(error)
                        
                        ocr_progress = (i + 1) / total_pages
                        self.ocr_progress.set(ocr_progress)
                        self.status_label.configure(text=f"OCR processed page {i+1} of {total_pages}")
                        self.log_message(f"OCR processed page {i+1}")
                        self.update_time_estimates(i + 1, total_pages)
                    
                    if not self.is_processing:  # Check if cancelled
                        return
                    
                    # Stop scanning animation
                    self.scan_animation.stop()
                    
                    # Create corpus document with metadata
                    metadata = {
                        "processing_date": datetime.now().isoformat(),
                        "original_file_size": os.path.getsize(pdf_path),
                        "total_pages": total_pages,
                        "ocr_engine": "Google Drive OCR",
                        "language": "auto-detect",
                        "output_directory": pdf_output_dir
                    }
                    
                    # Process document for corpus
                    corpus_file = self.text_processor.process_document(
                        pdf_path=pdf_path,
                        output_dir=Path(pdf_output_dir),
                        metadata=metadata
                    )
                    
                    if corpus_file:
                        self.log_message(f"Created corpus file: {corpus_file.name}")
                        self.log_message(f"Output directory: {pdf_output_dir}")
                        corpus_size = os.path.getsize(corpus_file)
                        self.log_message(f"Corpus file size: {humanize.naturalsize(corpus_size)}")
                    
                finally:
                    # Cleanup temporary files for this PDF
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
            if self.is_processing:  # Only show completion message if not cancelled
                self.status_label.configure(text="✅ All processing completed!")
                self.log_message("\n✅ All PDFs processed successfully!")
                messagebox.showinfo("Success", "All PDFs have been processed successfully!")
            
        except Exception as e:
            self.status_label.configure(text="❌ Error occurred during processing")
            self.log_message(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.reset_ui()

    def check_auth_status(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if creds and creds.valid:
            self.auth_status = True
            self.credentials = creds
            self.update_auth_status()

    def update_auth_status(self):
        if self.auth_status:
            self.auth_label.configure(
                text="✅ Authenticated with Google API",
                text_color="green"
            )
            self.auth_button.configure(state="disabled")
            self.select_button.configure(state="normal")
        else:
            self.auth_label.configure(
                text="⚠️ Not authenticated with Google API",
                text_color="red"
            )
            self.auth_button.configure(state="normal")
            self.select_button.configure(state="disabled")

    def authenticate(self):
        SCOPES = ['https://www.googleapis.com/auth/drive']
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            
            self.credentials = creds
            self.auth_status = True
            self.update_auth_status()
            self.log_message("Successfully authenticated with Google API")
        except Exception as e:
            messagebox.showerror("Authentication Error", str(e))
            self.log_message(f"Authentication error: {str(e)}")

    def log_message(self, message: str) -> None:
        """Add a message to the log text widget."""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def update_preview(self, image_path, is_ocr_processing=False):
        """Update the preview panel with the current image.
        
        Args:
            image_path (str): Path to the image file to display
            is_ocr_processing (bool): Whether to show the scanning animation overlay
            
        The preview maintains aspect ratio and centers the image in the available space.
        Also updates file information and handles the scanning animation if OCR is in progress.
        """
        try:
            # Load and resize image
            image = Image.open(image_path)
            
            # Calculate scaling factors
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            # Get image dimensions
            img_width, img_height = image.size
            
            # Calculate scaling factors
            width_ratio = canvas_width / img_width
            height_ratio = canvas_height / img_height
            scale_factor = min(width_ratio, height_ratio)
            
            # Calculate new dimensions
            new_width = int(img_width * scale_factor)
            new_height = int(img_height * scale_factor)
            
            # Resize image
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(resized_image)
            
            # Clear existing content
            self.preview_canvas.delete("all")
            
            # Calculate position to center the image
            x_position = (canvas_width - new_width) // 2
            y_position = (canvas_height - new_height) // 2
            
            # Display image
            self.preview_canvas.create_image(x_position, y_position, anchor="nw", image=photo)
            self.preview_canvas.image = photo  # Keep a reference
            
            # Update file info
            file_name = os.path.basename(image_path)
            dimensions = f"{img_width}x{img_height}"
            file_size = os.path.getsize(image_path)
            info_text = f"File: {file_name}\nDimensions: {dimensions}\nSize: {humanize.naturalsize(file_size)}"
            self.file_info_label.configure(text=info_text)
            
            # Handle scanning animation
            if is_ocr_processing:
                if not hasattr(self, 'scan_animation'):
                    self.scan_animation = ScanAnimation(self.preview_canvas, canvas_height)
                else:
                    self.scan_animation.update_canvas_size(canvas_height)
                self.scan_animation.start()  # This will now reset the scan line to the top
            elif hasattr(self, 'scan_animation'):
                self.scan_animation.stop()
            
        except Exception as e:
            self.log_message(f"Error updating preview: {str(e)}")
            # Clear preview and show error
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                self.preview_canvas.winfo_width() // 2,
                self.preview_canvas.winfo_height() // 2,
                text="Error loading preview",
                fill="red"
            )

    def _manage_cache(self):
        """Manage the image cache size."""
        if len(self._image_cache) >= self._cache_size_limit:
            # Remove oldest items
            items_to_remove = len(self._image_cache) - self._cache_size_limit + 1
            for _ in range(items_to_remove):
                self._image_cache.pop(next(iter(self._image_cache)))

    def cleanup_resources(self):
        """Clean up resources before closing."""
        # Clear image cache
        self._image_cache.clear()
        
        # Clear temporary files
        temp_dir = os.path.join(os.getcwd(), "temp_processing")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                self.log_message(f"Error cleaning up temporary files: {e}")
        
        # Stop any ongoing processing
        if self.is_processing:
            self.cancel_processing()
        
        # Stop resource monitoring
        if hasattr(self, '_monitoring_after_id'):
            self.after_cancel(self._monitoring_after_id)

    def __del__(self):
        """Clean up resources when the application is closed."""
        self.cleanup_resources()

    def update_time_estimates(self, current_page: int, total_pages: int) -> None:
        """Update processing time estimates based on current progress."""
        if not self.start_time:
            self.start_time = time.time()
            return
        
        current_time = time.time()
        elapsed = current_time - self.start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        
        # Calculate average time per page
        if current_page > 0:
            avg_time = elapsed / current_page
            self.processing_times.append(avg_time)
            
            # Use rolling average of last 5 pages
            recent_avg = sum(self.processing_times[-5:]) / len(self.processing_times[-5:])
            pages_remaining = total_pages - current_page
            estimated_remaining = pages_remaining * recent_avg
            
            # Update labels
            self.elapsed_time_label.configure(text=f"Elapsed Time: {elapsed_str}")
            self.remaining_time_label.configure(
                text=f"Est. Remaining: {str(timedelta(seconds=int(estimated_remaining)))}"
            )
            self.avg_time_label.configure(
                text=f"Avg. Time per Page: {int(recent_avg)}s"
            )

    def reset_time_tracking(self) -> None:
        """Reset all time tracking variables and displays."""
        self.start_time = None
        self.processing_times = []
        self.elapsed_time_label.configure(text="Elapsed Time: --:--")
        self.remaining_time_label.configure(text="Est. Remaining: --:--")
        self.avg_time_label.configure(text="Avg. Time per Page: --:--")
        self.file_info_label.configure(text="No file processing")
        self.preview_canvas.delete("all")
        if self.scan_animation:
            self.scan_animation.stop()

    def create_preview_panel(self):
        """Create the preview panel for displaying current page and processing status.
        
        Creates a frame containing:
        - Preview canvas for displaying current page
        - File information display
        - Time estimates and progress information
        - Scanning animation overlay
        """
        # Preview Frame with fixed size
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=1, rowspan=4, padx=10, pady=10, sticky="nsew")
        
        # Preview Label
        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="Current Page Preview",
            font=("Arial", 12, "bold")
        )
        self.preview_label.pack(pady=5)
        
        # Create a fixed-size frame to contain the canvas
        self.preview_container = ctk.CTkFrame(
            self.preview_frame,
            width=400,  # Fixed width
            height=500  # Fixed height
        )
        self.preview_container.pack(padx=10, pady=5)
        self.preview_container.pack_propagate(False)  # Prevent size changes
        
        # Preview Canvas with fixed size
        self.preview_canvas = tk.Canvas(
            self.preview_container,
            width=380,  # Slightly smaller than container to account for padding
            height=480,  # Slightly smaller than container to account for padding
            bg='#2b2b2b'  # Dark background
        )
        self.preview_canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # File Info Frame
        self.file_info_frame = ctk.CTkFrame(self.preview_frame)
        self.file_info_frame.pack(fill="x", padx=10, pady=5)
        
        # Current File Info
        self.file_info_label = ctk.CTkLabel(
            self.file_info_frame,
            text="No file processing",
            font=("Arial", 11),
            wraplength=280
        )
        self.file_info_label.pack(pady=5)
        
        # Time Estimates Frame
        self.time_frame = ctk.CTkFrame(self.preview_frame)
        self.time_frame.pack(fill="x", padx=10, pady=5)
        
        # Time Labels
        self.elapsed_time_label = ctk.CTkLabel(
            self.time_frame,
            text="Elapsed Time: --:--",
            font=("Arial", 11)
        )
        self.elapsed_time_label.pack(pady=2)
        
        self.remaining_time_label = ctk.CTkLabel(
            self.time_frame,
            text="Estimated Time Remaining: --:--",
            font=("Arial", 11)
        )
        self.remaining_time_label.pack(pady=2)
        
        self.avg_time_label = ctk.CTkLabel(
            self.time_frame,
            text="Avg. Time per Page: --:--",
            font=("Arial", 11)
        )
        self.avg_time_label.pack(pady=2)

        # Initialize scan animation after canvas creation
        self.scan_animation = ScanAnimation(self.preview_canvas, 480)

if __name__ == "__main__":
    app = OCRApp()
    try:
        app.mainloop()
    finally:
        app.cleanup_resources() 