from transformers import pipeline
from .asr_interface import ASRInterface
from src.audio_utils import save_audio_to_file
import os

class WhisperASR(ASRInterface):
    def __init__(self, **kwargs):
        model_name = kwargs.get('model_name', "openai/whisper-large-v3")
        self.asr_pipeline = pipeline("automatic-speech-recognition", model=model_name)

    async def transcribe(self, client):
        print(f"Saving {len(client.scratch_buffer)/(16000*2)} seconds of audio to {client.get_file_name()}")
        file_path = await save_audio_to_file(client.scratch_buffer, client.get_file_name())
        to_return = self.asr_pipeline(file_path)['text']
        os.remove(file_path)
        return to_return
