"""
Google Drive authentication and service initialization.
Handles OAuth2 authentication flow and API service setup.
"""

import sys
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import OCRConfig
from logger import OCRLogger


class GoogleDriveAuth:
    """Handles Google Drive API authentication and service initialization."""
    
    def __init__(self, config: OCRConfig, flags: Optional[object] = None):
        self.config = config
        # Kept for backward compatibility with existing call sites.
        self.flags = flags
        self.logger = OCRLogger(enable_file_logging=config.enable_file_logging)
        self.service = None

    def _get_scopes(self) -> list[str]:
        """Normalize scope config to a list accepted by Google auth flow."""
        return self.config.scopes if isinstance(self.config.scopes, list) else [self.config.scopes]
    
    def get_credentials(self) -> Credentials:
        """Get valid user credentials from storage with improved error handling."""
        current_directory = Path.cwd()
        token_path = current_directory / 'token.json'
        scopes = self._get_scopes()
        credentials = None

        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(token_path), scopes)
        
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                credentials_file = Path(self.config.credentials_file)
                if not credentials_file.exists():
                    raise FileNotFoundError(
                        f"Credentials file '{credentials_file}' not found. "
                        f"Please ensure you have downloaded the credentials from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), scopes)
                credentials = flow.run_local_server(port=0)

            token_path.write_text(credentials.to_json(), encoding='utf-8')
            self.logger.success(f'Credentials stored to {token_path}')

        return credentials

    def initialize_service(self):
        """Initialize Google Drive API service with comprehensive error handling."""
        try:
            credentials = self.get_credentials()
            self.service = build('drive', 'v3', credentials=credentials)
            if self.config.verbose:
                self.logger.success("Google Drive API service initialized successfully")
            return self.service
        except FileNotFoundError as e:
            self.logger.error(str(e))
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive service: {e}")
            sys.exit(1)

def authenticate_google_drive():
    """
    Authenticate with Google Drive and return the service object.
    This is a convenience function for the GUI application.
    """
    config = OCRConfig()
    auth = GoogleDriveAuth(config)
    return auth.initialize_service()
