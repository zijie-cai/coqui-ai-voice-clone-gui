# Audio Processing GUI

This project is an advanced GUI for audio processing using `tkinter` and `customtkinter`, allowing for:

- Text-to-Speech (TTS) generation using Coqui TTS.
- AI-powered text generation using Hugging Face models.
- Language detection and translation using Google Cloud API.
- Audio recording and playback with `sounddevice`.
- Multilingual support with dynamic UI updates.

## Features

- **Record and Upload Audio**: Record audio or upload WAV files for further processing.
- **Generate TTS**: Enter text and generate speech using a TTS model.
- **Translate Text**: Select text and translate it into different languages using Google Cloud Translation.
- **AI Text Generation**: Use Hugging Face models to generate prompts and texts.

## Dependencies

The project requires the following Python packages:

- `tkinter`
- `customtkinter`
- `wave`
- `sounddevice`
- `numpy`
- `huggingface_hub`
- `translate`
- `google-cloud-translate`
- `TTS`
- `torch`
- `lingua`

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/audio-processing-gui.git
   cd audio-processing-gui
