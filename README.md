# OCR Text Extractor

A powerful OCR (Optical Character Recognition) tool that uses Google Drive API to extract text from images with advanced features for text processing and combination.

**Version 1.0.0**: Modular architecture for better maintainability and extensibility!

## Features

- **Multiple Image Format Support**: Supports JPG, JPEG, PNG, GIF, BMP, TIFF formats
- **Automatic Text Cleaning**: Removes metadata and cleans extracted text
- **Flexible Text Combination**: Combine texts with or without file headers
- **Comprehensive Logging**: Detailed processing logs with colored output
- **Error Handling**: Robust error handling with detailed reporting
- **Configurable Processing**: Command-line options for customization
- **Modular Architecture**: Clean, maintainable code structure with 8 focused modules
- **No Duplicate Logging**: Clean output without repetitive messages
- **Progress Tracking**: Real-time progress indicators during processing

## Prerequisites

- [Python 3.6+](https://www.python.org/) (recommended: Python 3.8+)
- Google Drive API credentials
- Internet connection for API access

## Setup

1. **Install Python Dependencies**

   ```bash
   pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib oauth2client
   ```

2. **Get Google Drive API Credentials**

   - Follow the [Python Quickstart Guide](https://developers.google.com/workspace/drive/api/quickstart/python)
   - Download `credentials.json` file
   - Place `credentials.json` in the project directory

3. **Prepare Images**
   - Create an `images` folder in the project directory
   - Place your images in the `images` folder
   - Supported formats: JPG, JPEG, PNG, GIF, BMP, TIFF

## Preparing Images

### Converting PDF Files to Images

If you need to convert PDF documents to images before processing:

- **PDF-XChange Editor (Free)**: Recommended free solution for converting PDF pages to supported image formats
  - Additional feature: Crop unwanted sections (headers, footers, page numbers) from all images
- **Online PDF Converters**: Various web-based conversion tools available
- **Desktop Applications**: Adobe Acrobat, other PDF utilities
- **Alternative Tools**: Any reliable PDF-to-image conversion software

### Image Placement

After conversion, place all resulting images in the `images` folder within your project directory.

## Usage

### Basic Usage

```bash
python main.py
```

### Advanced Usage with Options

```bash
# Combine only processed texts (no raw texts) - this is the default
python main.py --no-combine-texts

# Include raw text combination
python main.py --combine-raw

# Include file headers in combined files
python main.py --include-headers

# Combine both raw and processed texts with headers
python main.py --combine-raw --include-headers

# Specify custom credentials file
python main.py --credentials my_credentials.json

# Support only specific image formats
python main.py --extensions .jpg .jpeg .png

# Enable verbose output for detailed logging
python main.py --verbose

# Enable file logging (creates ocr_processing.log)
python main.py --enable-file-logging

# Check version information
python main.py --version

# Combination example: verbose mode with raw text combination and headers
python main.py --verbose --combine-raw --include-headers
```

### Command Line Options

- `--credentials PATH`: Path to Google credentials JSON file (default: credentials.json)
- `--no-combine-texts`: Do not combine processed text files
- `--combine-raw`: Also combine raw text files
- `--include-headers`: Include file headers in combined files
- `--extensions LIST`: Supported image file extensions
- `--verbose`: Enable verbose logging output with detailed information
- `--enable-file-logging`: Enable logging to file (creates ocr_processing.log)
- `--version`: Show version information and exit

## Output Structure

```
project/
├── images/                 # Input images
├── raw_texts/             # Raw OCR output
├── texts/                 # Cleaned OCR output
├── credentials.json       # Google API credentials (user-provided)
├── token.json            # OAuth token (auto-generated)
└── main.py               # Main script
```

## Text Combination

The tool offers two combination modes:

1. **Without Headers**: Simple text concatenation with file separators
2. **With Headers**: Detailed file information and structured output

Combined files are saved with timestamps: `combined_cleaned_TIMESTAMP.txt` or `combined_raw_TIMESTAMP.txt`

## Error Handling

- Comprehensive error logging
- Graceful handling of API failures
- Automatic retry mechanisms
- Detailed error reporting

## Project Structure

The application has been refactored into a modular architecture:

```
OCR/
├── images/               # Input images directory
├── raw_texts/            # Raw OCR output directory
├── texts/                # Cleaned OCR output directory
├── __init__.py            # Package initialization
├── auth.py                # Google Drive authentication and service setup
├── cli.py                 # Command line interface and argument parsing
├── config.py              # Configuration classes and constants
├── credentials.json       # Google API credentials (user-provided)
├── logger.py              # Logging utilities with colored output
├── main.py                 # Main entry point
├── ocr_processor.py       # Core OCR processing logic
├── PROJECT_STRUCTURE.md   # Architecture documentation
├── README.md              # User documentation
├── text_processor.py      # Text cleaning and combination utilities
└── token.json            # OAuth token (auto-generated)
```

For detailed information about the modular architecture, see `PROJECT_STRUCTURE.md`.

## Authentication

On first run, the tool will:

1. Open a browser for Google OAuth
2. Request permission to access Google Drive
3. Save authentication token for future use

## Troubleshooting

1. **Credentials Error**: Ensure `credentials.json` is in the project directory
2. **No Images Found**: Check image formats and file extensions
3. **API Quota Exceeded**: Wait and retry, or check Google Cloud Console quotas
4. **Permission Denied**: Re-run OAuth flow by deleting `token.json`

## Performance

- Processing time depends on image size and API response
- Large images may take longer to process
- Multiple files are processed sequentially
- Progress tracking shows current file being processed
