# Use NVIDIA CUDA base image for GPU support
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

ENV COQUI_TOS_AGREED=1
ENV ACCEPT_TOS=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    espeak \
 && add-apt-repository ppa:deadsnakes/ppa \
 && apt-get update

RUN apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    libsndfile1 \
    ffmpeg \
    git \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/myenv
RUN python3.10 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install numpy first to handle dependencies
RUN pip3 install --no-cache-dir numpy==1.26.4
RUN pip3 install --no-cache-dir typing-extensions>=4.10.0
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Install packages that don't have numpy dependencies first
RUN pip3 install --no-cache-dir \
    Flask==3.1.0 \
    Flask-Cors==5.0.0 \
    boto3==1.36.11 \
    pyyaml==6.0.2 \
    google-api-core==2.24.1 \
    google-auth==2.38.0 \
    googleapis-common-protos==1.67.0 \
    google-cloud-translate==3.20.0 \
    schedule==1.2.2 \
    python-dotenv==1.0.1 \
    cutlet==0.5.0

# Install scipy after numpy
RUN pip3 install --no-cache-dir scipy==1.11.4

# Install kokoro
RUN pip3 install --no-cache-dir kokoro==0.3.4

# Install misaki with optional dependencies
RUN pip3 install --no-cache-dir "misaki==0.6.7" "misaki[ja,zh]"

# Install git repositories
# Install parler-tts from git
RUN pip3 install --no-cache-dir git+https://github.com/huggingface/parler-tts.git#egg=parler-tts

# Install TTS in editable mode
RUN pip3 install -e git+https://github.com/g-hano/TTS.git#egg=TTS

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Create necessary directories and set permissions
RUN mkdir -p /app/src/audio /app/src/certificates /app/src/references /app/src/vn_model && \
    chmod -R 777 /app/src/audio

# Default command
CMD ["python3", "src/main.py"]
