# NeviTechTTS

## Kullanım için gerekenler
1. .env dosyasına eklenmesi gerekenler
   AWS_ACCESS_KEY_ID=<here>
   AWS_SECRET_ACCESS_KEY=<here>

2. certificate_constants.py dosyasında KEY_PATH ve CERT_PATH düzenlenmeli

```bash
pip install -r requirements.txt
python app.py
```

# TODO
- tests
- better readme
- fix polly stops working

# Multi-Engine Text-to-Speech Service

A comprehensive Text-to-Speech (TTS) service that integrates multiple TTS engines including AWS Polly, XTTS, Kokoro, Vietnamese XTTS, and Indic Parler. The service provides a unified API for text-to-speech synthesis across various languages and voices.

## Project Structure
```
src/
├── api/
│   ├── routes.py          # API endpoints
│   └── __init__.py
├── config/
│   ├── ConfigLoader.py    # Configuration management
│   └── __init__.py
├── core/
│   ├── constants.py       # System constants
│   ├── error_handlers.py  # Error handling
│   ├── translator.py      # Translation service
│   ├── tts_manager.py     # TTS orchestration
│   └── __init__.py
├── services/
│   ├── base.py           # Base service class
│   ├── IndicService.py   # Indic languages TTS
│   ├── KokoroService.py  # Kokoro TTS
│   ├── PollyService.py   # AWS Polly integration
│   ├── ViXttsService.py  # Vietnamese XTTS
│   ├── XttsService.py    # Multi-language XTTS
│   └── __init__.py
├── static/
│   └── style.css         # UI styles
├── templates/
│   └── index.html        # Web interface
├── audio/                # Generated audio files
└── main.py              # Application entry point
```

## Supported Models and Languages

### AWS Polly (Neural)
| Language | Variants |
|----------|----------|
| Arabic | Standard, Gulf |
| Chinese | Cantonese, Mandarin |
| Dutch | Standard, Belgian |
| English | US, UK, Australian, Indian, New Zealand, South African, Welsh |
| French | Standard, Belgian, Canadian |
| German | Standard, Austrian, Swiss |
| Spanish | Spain, Mexican, US |
| Portuguese | Brazilian, European |
| + 20 more languages | See AWS Polly documentation |

### XTTS (Base Model)
| Language | Code |
|----------|------|
| English | en |
| Spanish | sp |
| French | fr |
| German | de |
| Italian | it |
| Portuguese | pt |
| Chinese | zh-cn |
| Japanese | ja |
| Korean | ko |
| + 7 more languages | See XTTS documentation |

### Kokoro
| Language | Voice Count | Gender Distribution |
|----------|-------------|-------------------|
| English (US) | 20 | 12 Female, 8 Male |
| English (UK) | 8 | 4 Female, 4 Male |
| Japanese | 5 | 4 Female, 1 Male |
| Chinese | 8 | 4 Female, 4 Male |
| Italian | 2 | 1 Female, 1 Male |
| French | 1 | 1 Female |
| Spanish | 3 | 1 Female, 2 Male |
| Portuguese | 3 | 1 Female, 2 Male |

### Indic Parler
| Language | Voice Count |
|----------|-------------|
| Assamese | 2 |
| Bengali | 2 |
| Gujarati | 2 |
| Hindi | 2 |
| Kannada | 2 |
| Malayalam | 2 |
| Tamil | 1 |
| Telugu | 2 |
| + 9 more Indian languages | Various voice counts |

### Vietnamese XTTS
- Dedicated model for Vietnamese language
- Male and Female voices available
- Neural-based synthesis

## Features
- Multi-engine TTS synthesis
- Language detection and translation
- Real-time audio generation
- Automatic file cleanup
- Error handling and logging
- Health monitoring
- REST API
- Web interface

## Setup Requirements
1. Python 3.8+
2. AWS credentials (for Polly)
3. Google Cloud credentials (for translation)
4. Required Python packages (see requirements.txt)
5. 10GB+ disk space for models

## Configuration
Configuration is managed through `config.yaml`:
```yaml
models:
  xtts_base_model: "tts_models/multilingual/multi-dataset/xtts_v2"
  xtts_vietnamese: "capleaf/viXTTS"
  indic_model: "ai4bharat/indic-parler-tts-pretrained"

kokoro_speed: 1

directories:
  audio_output_dir: "audio"
  vietnamese_model_dir: "vn_model"

paths:
  key_path: "./.com.key"
  cert_path: "./.crt"
  google_credentials: "./.json"

flask:
  port: 5000
  host: "0.0.0.0"

reference_audio_paths:
  male: "./man.wav"
  female: "./woman.wav"

cleanup:
  max_age_hours: 3
  min_free_space_mb: 1000
  cleanup_interval_minutes: 30
```

## API Endpoints
- `GET /voices` - List available voices
- `POST /generate-realtime` - Generate speech
- `POST /translate` - Translate text
- `GET /health` - Service health check
- `GET /audio/<filename>` - Retrieve generated audio
- `POST /clear-session` - Clear session data
