from flask import Flask, request, jsonify, send_from_directory, render_template, send_file
from flask_cors import CORS, cross_origin
import logging
import boto3

# We need to access environment variables
import os
os.environ["COQUI_TOS_AGREED"] = "1" # for XTTS models
from dotenv import load_dotenv
load_dotenv()

from typing import Dict, Optional
import time
import numpy as np
from scipy.io.wavfile import read, write
from io import BytesIO
import ssl
from werkzeug.utils import secure_filename
from collections import deque
from translator import Translator
import torch
import torchaudio

# XTTS models
from TTS.api import TTS
from TTS.utils.manage import ModelManager
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.generic_utils import get_user_data_dir

# Vietnamese XTTS
from huggingface_hub import snapshot_download

# For indic model
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf

# we import those for Kokoro-82M model
from models import build_model
import sys
kokoro_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Kokoro-82M'))
sys.path.append(kokoro_dir)
from kokoro import generate

# System, Model and Certificate constants
from constants import POLLY_SAMPLE_RATE, POLLY_LANGUAGE_NAMES
from constants import XTTS_SAMPLE_RATE, XTTS_LANGUAGE_NAMES
from constants import KOKORO_VOICE_CHOICES
from constants import INDIC_VOICES, INDIC_LANG_CODES
from model_constants import VIETNAMESE_REPO_ID, XTTS_BASE_MODEL_NAME, INDIC_MODEL_NAME, KOKORO_MODEL_NAME
from certificate_constants import KEY_PATH, CERT_PATH

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


vn_model_path = os.path.join(BASE_DIR, "vn_model")
if not os.path.exists(vn_model_path):
                print("Downloading Vietnamese model from Hugging Face...")
                snapshot_download(
                    repo_id=VIETNAMESE_REPO_ID,
                    repo_type="model",
                    local_dir=vn_model_path
                )

def load_voice(voice_name, device):
    # Use the path to voices directory in Kokoro-82M folder
    voice_path = os.path.join(kokoro_dir, 'voices', f'{voice_name}.pt')
    print(f"Loading voice from: {voice_path}")
    return torch.load(voice_path, weights_only=True).to(device)

def text_to_speech(model, text, voice_name, device):
    if not text.strip():
        return None, ""
    
    voicepack = load_voice(voice_name, device)
    lang_code = voice_name[0]  # 'a' or 'b' for en-us/en-gb
    audio, phonemes = generate(model, text, voicepack, lang=lang_code)
    print(f"Returning: sample_rate, audio, phonemes")
    return XTTS_SAMPLE_RATE, audio, phonemes

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

AUDIO_OUTPUT_DIR = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BASE_DIR, 'app.log'))
    ]
)

class TTSManager:
    def __init__(self):
        self.init_class()

    def init_class(self):
        self.polly_client = boto3.client(
               'polly',
                region_name="eu-central-1",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
        print("Polly is ready!")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

# ----------------------------------------------------------------------
        xtts_base_model_name = XTTS_BASE_MODEL_NAME
        self.xtts_base_model = self.get_xtts(xtts_base_model_name)
        print("xtts-v2 is ready!")        
# ----------------------------------------------------------------------
        self.xtts_vietnamese_model = self.get_vietnamese_xtts(vn_model_path)
        print("Vietnamese XTTS is ready!")
# ----------------------------------------------------------------------
        self.set_indic_model_tokenizers(INDIC_MODEL_NAME)
        self.indic_voices = INDIC_VOICES
        self.indic_lang_codes = INDIC_LANG_CODES
        print("Indic Parler TTS is ready!")
# ----------------------------------------------------------------------
        model_path = os.path.join(kokoro_dir, KOKORO_MODEL_NAME)
        print(f"Loading Kokoro model from: {model_path}")
        self.kokoro = self.get_kokoro(model_path)
        print("Kokoro is ready!")
# ----------------------------------------------------------------------
        self.speakers = {
            "male": "/home/ubuntu/t2s/POLLY_TTS/man.wav",
            "female": "/home/ubuntu/t2s/POLLY_TTS/woman.wav"
        }
        self._voices = None
        self._update_voices()        
        self.speech_queue = {}        
        self.translator = Translator()

    def get_xtts(self, xtts_base_model_name):
        ModelManager().download_model(xtts_base_model_name)
        model_path = os.path.join(get_user_data_dir("tts"), xtts_base_model_name.replace("/", "--"))
        config = XttsConfig()
        config.load_json(os.path.join(model_path, "config.json"))
        xtts_base_model = Xtts.init_from_config(config)
        xtts_base_model.load_checkpoint(
            config,
            checkpoint_dir=model_path,
            eval=True,
        )
        return xtts_base_model.to(self.device)

    def get_vietnamese_xtts(self, vn_model_path):
        vn_config = XttsConfig()
        vn_config.load_json(os.path.join(vn_model_path, "config.json"))
        
        xtts_vietnamese_model = Xtts.init_from_config(vn_config)
        xtts_vietnamese_model.load_checkpoint(
            vn_config, 
            checkpoint_dir=vn_model_path
        )
        xtts_vietnamese_model.eval()
        return xtts_vietnamese_model.to(self.device)

    def set_indic_model_tokenizers(self, model_path):
        self.indic_model = ParlerTTSForConditionalGeneration.from_pretrained(model_path).to(self.device)
        self.indic_tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.description_tokenizer = AutoTokenizer.from_pretrained(self.indic_model.config.text_encoder._name_or_path)

    def get_kokoro(self, model_path):
        return build_model(model_path, self.device)

    def _update_voices(self):
        """
        Update the list of available voices from both AWS Polly, XTTS, and KOKORO
        Organized by engine type
        """
        try:
            grouped_voices = {
                "Polly": {},
                "XTTS": {},
                "Kokoro": {},
                "Vietnamese XTTS": {},
                "Indic Parler": {}
            }

            # Add Polly voices
            response = self.polly_client.describe_voices()
            voices = sorted(response['Voices'], key=lambda x: (x['LanguageCode'], x['Name']))
            
            for voice in voices:
                lang = voice['LanguageCode']
                lang_name = POLLY_LANGUAGE_NAMES.get(lang, lang)
                if lang_name not in grouped_voices["Polly"]:
                    grouped_voices["Polly"][lang_name] = []

                # Add only neural voices
                if 'SupportedEngines' in voice and 'neural' in voice['SupportedEngines']:
                    voice_info = {
                        'id': voice['Id'],
                        'name': f"{voice['Name']} ({voice['Gender']} - Neural)",
                        'description': voice.get('Description', ''),
                        'language_name': voice.get('LanguageName', ''),
                        "engine": "polly",
                        "gender": voice['Gender']
                    }
                    grouped_voices["Polly"][lang_name].append(voice_info)

            # Add XTTS voices
            for code, name in sorted(XTTS_LANGUAGE_NAMES.items()):  # Sort languages alphabetically
                if name not in grouped_voices["XTTS"]:
                    grouped_voices["XTTS"][name] = []
                
                # Add male voice
                male_voice_info = {
                    'id': f'xtts_{code}_male',
                    'name': f'XTTS Male Voice ({name})',
                    'description': 'Local XTTS neural voice',
                    'language_name': name,
                    'engine': 'xtts',
                    'gender': 'Male'
                }
                grouped_voices["XTTS"][name].append(male_voice_info)
                
                # Add female voice
                female_voice_info = {
                    'id': f'xtts_{code}_female',
                    'name': f'XTTS Female Voice ({name})',
                    'description': 'Local XTTS neural voice',
                    'language_name': name,
                    'engine': 'xtts',
                    'gender': 'Female'
                }
                grouped_voices["XTTS"][name].append(female_voice_info)

            # Add KOKORO voices
            grouped_voices["Kokoro"]["US English"] = []
            grouped_voices["Kokoro"]["GB English"] = []
            
            for name, code, gender in KOKORO_VOICE_CHOICES:
                # Determine language based on the code prefix
                language = "US English" if code.startswith('a') else "GB English"
                
                voice_info = {
                    'id': f'kokoro_{code}',
                    'name': name,
                    'description': 'Local KOKORO neural voice',
                    'language_name': language,
                    'engine': 'kokoro',
                    'gender': 'Male' if gender == 'm' else 'Female'
                }
                grouped_voices["Kokoro"][language].append(voice_info)


            grouped_voices["Vietnamese XTTS"]["Vietnamese"] = []
            # Add female vocie
            grouped_voices["Vietnamese XTTS"]["Vietnamese"].append({
                    'id': 'vn_xtts_female',
                    'name': 'Vietnamese XTTS Female',
                    'description': 'Vietnamese XTTS neural voice',
                    'language_name': 'Vietnamese',
                    'engine': 'vn_xtts',
                    'gender': 'Female'
                })
            # Add male voice
            grouped_voices["Vietnamese XTTS"]["Vietnamese"].append({
                'id': 'vn_xtts_male',
                'name': 'Vietnamese XTTS Male',
                'description': 'Vietnamese XTTS neural voice',
                'language_name': 'Vietnamese',
                'engine': 'vn_xtts',
                'gender': 'Male'
            })

            grouped_voices["Indic Parler"] = {}
            for language, voices in self.indic_voices.items():
                grouped_voices["Indic Parler"][language] = []
                for voice_name, gender in voices:
                    voice_info = {
                        'id': f'indic_{self.indic_lang_codes[language]}_{voice_name.lower()}',
                        'name': f"{voice_name} ({language})",
                        'description': f'Indic Parler TTS neural voice for {language}',
                        'language_name': language,
                        'engine': 'indic',
                        'gender': gender
                    }
                    grouped_voices["Indic Parler"][language].append(voice_info)

            # Clean up empty language groups and sort everything
            cleaned_voices = {}
            for engine in sorted(grouped_voices.keys()):
                if grouped_voices[engine]:
                    cleaned_voices[engine] = {
                        k: sorted(v, key=lambda x: x['name']) 
                        for k, v in sorted(grouped_voices[engine].items()) 
                        if v
                    }

            self._voices = cleaned_voices

        except Exception as e:
            logging.error(f"Error fetching voices: {e}")
            self._voices = {}

    def get_voices(self) -> Dict:
        """
        Get the organized voice list
        """
        if not self._voices:
            self._update_voices()
        return self._voices
    
    def get_last_sentence(self, text: str) -> Optional[str]:
        """
        Get the last word from text
        If no word exists, return None
        """
        text = text.strip()
        if not text:
            return None

        words = text.split()
            
        return words[-1] if words else None

    def synthesize_speech(self, text: str, voice_id: str, session_id: str) -> Optional[bytes]:
        """
        Synthesize speech using either AWS Polly or XTTS based on voice_id
        """
        try:
            timestamp = int(time.time() * 10000000)
            output_filename = f"realtime_{session_id}_{timestamp}.wav"
            output_path = os.path.join(AUDIO_OUTPUT_DIR, output_filename)

            if voice_id.startswith('xtts_'):
                print("Using coqui/XTTS-v2")
                _, lang_code, gender = voice_id.split('_')
                reference_audio = self.speakers[gender.lower()]
                gpt_cond_latent, speaker_embedding = self.xtts_base_model.get_conditioning_latents(
                    audio_path=reference_audio,
                    gpt_cond_len=30,
                    gpt_cond_chunk_len=4,
                    max_ref_length=60
                )
                out = self.xtts_base_model.inference(
                    text,
                    lang_code,
                    gpt_cond_latent,
                    speaker_embedding,
                    temperature=0.75,
                    repetition_penalty=5.0
                )    
                # Save the generated wav to file
                print(f"{output_path=}")
                audio_array = np.array(out["wav"])
                write(output_path, XTTS_SAMPLE_RATE, audio_array)

            elif voice_id.startswith("kokoro_"):
                print("Using KOKORO-82M")
                _, voice_code = voice_id.split("kokoro_")
                print(f"{voice_code=}")
                print(f"{text=}")
                kokoro_sample_rate, audio, _ = text_to_speech(self.kokoro, text, voice_code, self.device)
                write(output_path, kokoro_sample_rate, audio)

            elif voice_id.startswith("vn_xtts"):
                print("Using Vietnamese XTTS")
                if self.xtts_vietnamese_model is None:
                    raise ValueError("Vietnamese TTS not initialized")
                
                # Get gender from voice_id
                gender = voice_id.split('_')[-1]
                reference_audio = self.speakers[gender.lower()]  # Uses the same speakers dict as other models
                
                # Compute conditioning latents for the selected gender
                gpt_cond_latent, speaker_embedding = self.xtts_vietnamese_model.get_conditioning_latents(
                    audio_path=reference_audio,
                    gpt_cond_len=self.xtts_vietnamese_model.config.gpt_cond_len,
                    max_ref_length=self.xtts_vietnamese_model.config.max_ref_len,
                    sound_norm_refs=self.xtts_vietnamese_model.config.sound_norm_refs
                )
                
                out = self.xtts_vietnamese_model.inference(
                    text=text,
                    language="vi",
                    gpt_cond_latent=gpt_cond_latent,
                    speaker_embedding=speaker_embedding,
                    temperature=0.3,
                    length_penalty=1.0,
                    repetition_penalty=10.0,
                    top_k=30,
                    top_p=0.85
                )
                
                write(output_path, XTTS_SAMPLE_RATE, out["wav"])
            
            elif voice_id.startswith('indic_'):
                print("Using Indic Parler TTS")
                _, lang_code, voice_name = voice_id.split('_')
                voice_name = voice_name.capitalize()
                print(f"{voice_name=}")

                # Find the language name from the code
                language = next(lang for lang, code in self.indic_lang_codes.items() 
                   if self.indic_lang_codes[lang] == lang_code)
                print(f"{language}")
                description = f"{voice_name} delivers a slightly expressive and animated speech with a moderate speed and pitch. The recording is of very high quality, with the speaker's voice sounding clear and very close up."
                print("Description:")
                description_inputs = self.description_tokenizer(
                    description, 
                    return_tensors="pt"
                ).to(self.device)
                
                prompt_inputs = self.indic_tokenizer(
                    text, 
                    return_tensors="pt"
                ).to(self.device)
                print(f"Generating audio for text: {text}")
                # Generate audio
                generation = self.indic_model.generate(
                    input_ids=description_inputs.input_ids,
                    attention_mask=description_inputs.attention_mask,
                    prompt_input_ids=prompt_inputs.input_ids,
                    prompt_attention_mask=prompt_inputs.attention_mask
                )
                print("Audio generated successfully")
                # Convert to numpy and save
                audio_array = generation.cpu().numpy().squeeze()
                sf.write(output_path, audio_array, self.indic_model.config.sampling_rate)
                print(f"Audio saved to: {output_path}")

            else:
                print("Using AWS Polly")
                # Use Polly for synthesis
                response = self.polly_client.synthesize_speech(
                    Engine="neural",
                    OutputFormat='pcm',
                    Text=text,
                    VoiceId=voice_id,
                    SampleRate=str(POLLY_SAMPLE_RATE)
                )
                
                # Convert PCM to WAV format
                audio_data = response['AudioStream'].read()
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Write directly to file
                write(output_path, POLLY_SAMPLE_RATE, audio_array)
                print(f"{output_path=}")
                
            if os.path.exists(output_path):
                print(f"Successfully generated audio at: {output_path}")
                return output_filename
            else:
                print(f"Failed to generate audio at: {output_path}")
                return None
            
        except Exception as e:
            logging.error(f"Error in speech synthesis: {e}")
            raise

    def clear_session(self, session_id: str):
        """Clear the last word for a session"""
        if session_id in self.speech_queue:
            del self.speech_queue[session_id]
  
     
polly_manager = TTSManager()

@app.route("/", methods=["GET"])
@cross_origin(origin='*')
def index():
    return render_template("index.html")

@app.route("/recover", methods=["GET"])
@cross_origin(origin='*')
def recover():
    polly_manager.init_class()

@app.route("/voices", methods=["GET"])
@cross_origin(origin='*')
def get_voices():
    """Return available Polly voices"""
    return jsonify({
        "success": True,
        "voices": polly_manager.get_voices()
    })

@app.route("/translate", methods=["POST"])
@cross_origin(origin='*')
def translate():
    data = request.get_json()
    target_language = data.get("target_language")
    text_to_synthesize = data.get("text")
    return polly_manager.translator.translate_text(text_to_synthesize, target_language)

@app.route("/languages", methods=["GET"])
@cross_origin(origin="*")
def get_languages():
    """Return available languages and their support information"""
    return jsonify({
        "success": True,
        "languages": polly_manager.get_available_languages()
    })

@app.route("/generate-realtime", methods=["POST"])
@cross_origin(origin='*')
def generate_realtime():
    try:
        data = request.get_json()
        text = data.get("text")
        voice_id = data.get("voice_id")  # Optional, for Polly
        session_id = data.get("session_id")
        target_language = data.get("target_language")

        if not text or not session_id:
            return jsonify({
                "success": False,
                "message": "Missing text or session_id",
                "needs_audio": False
            })
            
        if polly_manager.speech_queue.get(session_id) is None:
            polly_manager.speech_queue[session_id] = deque()
            
        polly_manager.speech_queue.get(session_id).append(text)
        
        text_to_synthesize = polly_manager.speech_queue.get(session_id).popleft()
        
        text_to_synthesize = polly_manager.translator.translate_text(text_to_synthesize, target_language) if target_language is not None and target_language.strip() != '' else text_to_synthesize

        start_time = time.time()
        
        # Generate and get filename
        filename = polly_manager.synthesize_speech(
            text=text_to_synthesize,
            voice_id=voice_id,
            session_id=session_id
        )
        
        if not filename:
            return jsonify({
                "success": False,
                "message": "No new complete sentence to process",
                "needs_audio": False
            })

        generation_time = time.time() - start_time
        audio_url = f"/audio/{filename}"

        return jsonify({
            "success": True,
            "file_path": audio_url,
            "message": "Audio generated successfully",
            "needs_audio": True,
            "timing_info": {
                "total_generation_time": generation_time
            }
        })

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error generating voice: {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@app.route("/clear-session", methods=["POST"])
@cross_origin(origin='*')
def clear_session():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        
        if not session_id:
            raise ValueError("Missing session_id")
            
        polly_manager.clear_session(session_id)
        
        return jsonify({
            "success": True,
            "message": "Session cleared successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files"""
    try:
        # Secure the filename and strip any path components
        filename = secure_filename(os.path.basename(filename))
        file_path = os.path.join(AUDIO_OUTPUT_DIR, filename)
        
        print(f"Attempting to serve audio from: {file_path}")
        
        # Check if file exists before attempting to serve
        if not os.path.exists(file_path):
            logging.error(f"Audio file not found at path: {file_path}")
            # List directory contents for debugging
            dir_contents = os.listdir(AUDIO_OUTPUT_DIR)
            print(f"Directory contents: {dir_contents}")
            return jsonify({
                "success": False,
                "error": "Audio file not found"
            }), 404
            
        return send_from_directory(
            AUDIO_OUTPUT_DIR,
            filename,
            mimetype='audio/wav',
            as_attachment=True
        )
    
    except Exception as e:
        logging.error(f"Error serving audio file: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/health", methods=["GET"])
@cross_origin(origin='*')
def health_check():
    """Health check endpoint to verify service status."""
    return jsonify({
        "status": "healthy",
        "available_voices": len(polly_manager.get_voices()),
        "timestamp": time.time()
    })


if __name__ == "__main__":
    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
    logging.info("Starting Flask application with AWS Polly")
    logging.info(f"Output directory: {AUDIO_OUTPUT_DIR}")
    certificates_folder = r"/home/ubuntu/t2s/POLLY_TTS/certificates/"
    port = 5000
    try:       
        if not os.path.exists(CERT_PATH):
            raise FileNotFoundError(f"Certificate file not found: {CERT_PATH}")
        if not os.path.exists(KEY_PATH):
            raise FileNotFoundError(f"Key file not found: {KEY_PATH}")
            
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(CERT_PATH, KEY_PATH)
        app.run(host="0.0.0.0", port=port, ssl_context=context)
        
    except Exception as e:
        logging.error(f"SSL Error: {e}")
        logging.info("Running without SSL")
        app.run(host="0.0.0.0", port=port)