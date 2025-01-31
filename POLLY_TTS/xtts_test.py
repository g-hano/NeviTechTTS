import os
import torch
import torchaudio
from TTS.utils.manage import ModelManager
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.generic_utils import get_user_data_dir

# Setup environment
os.environ["COQUI_TOS_AGREED"] = "1"

# Download and load XTTS model
model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
ModelManager().download_model(model_name)
model_path = os.path.join(get_user_data_dir("tts"), model_name.replace("/", "--"))
print(f"{model_path=}")

files_needed = ["model.pth", "config.json", "vocab.json", "speakers_xtts.pth"]
for file in files_needed:
    path = os.path.join(model_path, file)
    print(f"Checking {file}: {'exists' if os.path.exists(path) else 'missing'}")

# Load model configuration
config = XttsConfig()
config.load_json(os.path.join(model_path, "config.json"))

# Initialize and load the model
model = Xtts.init_from_config(config)
model.load_checkpoint(
    config,
    checkpoint_dir=model_path,  # Added this line
    eval=True,
)
model.cuda()

def generate_speech():
    # Input parameters
    text = "Hello. I am okay.  "
    language = "en"
    reference_audio = "POLLY_TTS/woman.wav"  # Put your reference audio file here
    output_file = "output.wav"
    
    # Generate voice latents from reference audio
    try:
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=reference_audio,
            gpt_cond_len=30,
            gpt_cond_chunk_len=4,
            max_ref_length=60
        )
    except Exception as e:
        print(f"Error processing reference audio: {str(e)}")
        return

    # Generate speech
    try:
        print("Generating speech...")
        out = model.inference(
            text,
            language,
            gpt_cond_latent,
            speaker_embedding,
            temperature=0.75,
            repetition_penalty=5.0
        )
        
        # Save output
        torchaudio.save(output_file, torch.tensor(out["wav"]).unsqueeze(0), 24000)
        print(f"Speech generated successfully: {output_file}")
        
    except Exception as e:
        print(f"Error during speech generation: {str(e)}")

if __name__ == "__main__":
    generate_speech()