import asyncio

import torch
from transformers import pipeline

from src.utils.audio_utils import convert_audio_bytes_to_numpy

from .asr_interface import ASRInterface


class WhisperASR(ASRInterface):
    def __init__(self, **kwargs):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = kwargs.get("model_name", "openai/whisper-large-v3")
        self.asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=device,
        )

    async def transcribe(self, client):
        audio = convert_audio_bytes_to_numpy(client.scratch_buffer)

        if client.config["language"] is not None:
            result = await asyncio.to_thread(
                self.asr_pipeline,
                audio,
                generate_kwargs={"language": client.config["language"]},
            )
        else:
            result = await asyncio.to_thread(self.asr_pipeline, audio)

        to_return = result["text"]

        to_return = {
            "language": "UNSUPPORTED_BY_HUGGINGFACE_WHISPER",
            "language_probability": None,
            "text": to_return.strip(),
            "words": "UNSUPPORTED_BY_HUGGINGFACE_WHISPER",
        }
        return to_return
