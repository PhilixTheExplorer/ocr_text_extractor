"""
Google Drive authentication and service initialization.
Handles OAuth2 authentication flow and API service setup.
"""

import sys
import httplib2
from pathlib import Path
from typing import Optional
import argparse

from googleapiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from config import OCRConfig
from logger import OCRLogger


class GoogleDriveAuth:
    """Handles Google Drive API authentication and service initialization."""
    
    def __init__(self, config: OCRConfig, flags: Optional[argparse.Namespace] = None):
        self.config = config
        self.flags = flags
        self.logger = OCRLogger(enable_file_logging=config.enable_file_logging)
        self.service = None
    
    def get_credentials(self) -> client.OAuth2Credentials:
        """Get valid user credentials from storage with improved error handling."""
        current_directory = Path.cwd()
        credential_path = current_directory / 'token.json'
        store = Storage(str(credential_path))
        credentials = store.get()
        
        if not credentials or credentials.invalid:
            credentials_file = Path(self.config.credentials_file)
            if not credentials_file.exists():
                raise FileNotFoundError(
                    f"Credentials file '{credentials_file}' not found. "
                    f"Please ensure you have downloaded the credentials from Google Cloud Console."
                )
            
            flow = client.flow_from_clientsecrets(
                str(credentials_file), 
                self.config.scopes
            )
            flow.user_agent = self.config.application_name
            
            if self.flags:
                credentials = tools.run_flow(flow, store, self.flags)
            else:
                credentials = tools.run(flow, store)
            
            self.logger.success(f'Credentials stored to {credential_path}')
        
        return credentials
    
    def initialize_service(self):
        """Initialize Google Drive API service with comprehensive error handling."""
        try:
            credentials = self.get_credentials()
            http = credentials.authorize(httplib2.Http())
            self.service = discovery.build('drive', 'v3', http=http)
            if self.config.verbose:
                self.logger.success("Google Drive API service initialized successfully")
            return self.service
        except FileNotFoundError as e:
            self.logger.error(str(e))
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive service: {e}")
            sys.exit(1)
