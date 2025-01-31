from google.cloud import translate_v2 as translate

import html

import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"/home/ubuntu/t2s/POLLY_TTS/klassifier-translation-322b40f8ffce.json"

class Translator:

    def __init__(self):
        self.x = ''
        self.translate_client = translate.Client()

    def translate_text(self, text, target_language):
        """Translates text into the target language."""

        if isinstance(text, bytes):
            text = text.decode("utf-8")

        # Translate the text
        result = self.translate_client.translate(text, target_language=target_language)

        print(f"Text: {text}")
        print(f"Translation: {result['translatedText']}")
        print(f"Detected Source Language: {result['detectedSourceLanguage']}")

        return html.unescape(result['translatedText'])

