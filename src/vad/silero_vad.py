import asyncio

import torch
from silero_vad import get_speech_timestamps, load_silero_vad

from src.utils.audio_utils import convert_audio_bytes_to_numpy

from .vad_interface import VADInterface


class SileroVAD(VADInterface):
    """Token-free, in-memory voice activity detector."""

    def __init__(self, **kwargs):
        self.model = load_silero_vad()

    async def detect_activity(self, client):
        audio = torch.from_numpy(
            convert_audio_bytes_to_numpy(client.scratch_buffer)
        )
        timestamps = await asyncio.to_thread(
            get_speech_timestamps,
            audio,
            self.model,
            sampling_rate=client.sampling_rate,
        )
        return [
            {
                "start": timestamp["start"] / client.sampling_rate,
                "end": timestamp["end"] / client.sampling_rate,
                "confidence": 1.0,
            }
            for timestamp in timestamps
        ]
