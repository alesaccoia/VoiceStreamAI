import numpy as np


def convert_audio_bytes_to_numpy(audio_bytes):
    """Convert little-endian 16-bit PCM bytes to normalized mono samples."""
    if len(audio_bytes) % 2:
        raise ValueError("PCM16 audio must contain an even number of bytes")

    return np.frombuffer(audio_bytes, dtype="<i2").astype(np.float32) / 32768.0
