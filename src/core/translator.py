from typing import Dict
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
import html
import logging
from pathlib import Path
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ConfigLoader import AppConfig
from core.error_handlers import TranslationError

class Translator:
    def __init__(self, config: AppConfig):
        self.logger = logging.getLogger(__name__)
        self.client = self._initialize_client(config.paths.google_credentials)

    def _initialize_client(self, credentials_path: str) -> translate.Client:
        """
        Initialize the translation client with proper credentials handling.
        
        Args:
            credentials_path: Path to the Google Cloud credentials JSON file
            
        Returns:
            translate.Client: Initialized translation client
            
        Raises:
            TranslationError: If client initialization fails
        """
        try:
            # Convert to Path object for better path handling
            cred_path = Path(credentials_path)
            
            if not cred_path.exists():
                raise TranslationError(
                    message=f"Credentials file not found: {cred_path}",
                    details={"credentials_path": str(cred_path)}
                )

            # Load credentials from the JSON file
            credentials = service_account.Credentials.from_service_account_file(
                str(cred_path),
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )

            # Create client with explicit credentials
            return translate.Client(credentials=credentials)

        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(
                message=f"Failed to initialize translation client: {str(e)}",
                details={"credentials_path": str(credentials_path)}
            )

    def translate_text(self, text: str, target_language: str) -> str:
        """
        Translates text into the target language.
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            str: Translated text
            
        Raises:
            TranslationError: If translation fails
        """
        try:
            # Convert bytes to string if necessary
            if isinstance(text, bytes):
                text = text.decode("utf-8")

            # Validate input
            if not text.strip():
                raise TranslationError(
                    message="Empty text provided for translation",
                    details={"target_language": target_language}
                )

            # Log translation attempt
            self.logger.debug(f"Translating text to {target_language}: {text[:100]}...")

            # Perform translation
            result = self.client.translate(
                text, 
                target_language=target_language,
                model='nmt'  # Use Neural Machine Translation model
            )

            # Log results
            self.logger.info(
                f"Translation completed: {result['detectedSourceLanguage']} -> {target_language}"
            )
            self.logger.debug(f"Original: {text[:100]}...")
            self.logger.debug(f"Translated: {result['translatedText'][:100]}...")

            return html.unescape(result['translatedText'])

        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(
                message=f"Translation failed: {str(e)}",
                details={
                    "target_language": target_language,
                    "text_length": len(text) if text else 0
                }
            )

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages.
        
        Returns:
            list: List of supported language codes and names
            
        Raises:
            TranslationError: If fetching languages fails
        """
        try:
            results = self.client.get_languages()
            return [
                {
                    'language_code': lang['language'],
                    'name': lang.get('name', lang['language'])
                }
                for lang in results
            ]
        except Exception as e:
            raise TranslationError(
                message=f"Failed to fetch supported languages: {str(e)}"
            )

    def detect_language(self, text: str) -> Dict:
        """
        Detect the language of the input text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict: Detected language information
            
        Raises:
            TranslationError: If language detection fails
        """
        try:
            result = self.client.detect_language(text)
            return {
                'language': result['language'],
                'confidence': result['confidence']
            }
        except Exception as e:
            raise TranslationError(
                message=f"Language detection failed: {str(e)}",
                details={"text_length": len(text) if text else 0}
            )