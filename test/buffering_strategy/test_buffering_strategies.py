import asyncio
import json
import unittest

from src.client import Client


class RecordingWebSocket:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(json.loads(message))


class ImmediateVAD:
    async def detect_activity(self, client):
        return [{"start": 0.0, "end": 0.0, "confidence": 1.0}]


class SlowASR:
    def __init__(self):
        self.inputs = []

    async def transcribe(self, client):
        self.inputs.append(bytes(client.scratch_buffer))
        await asyncio.sleep(0.01)
        return {"text": "ok"}


class BufferingStrategyTests(unittest.IsolatedAsyncioTestCase):
    async def test_audio_received_during_inference_is_not_dropped(self):
        client = Client("test", sampling_rate=16000, samples_width=2)
        client.update_config(
            {
                "processing_args": {
                    "chunk_length_seconds": 0.01,
                    "chunk_offset_seconds": 0.001,
                }
            }
        )
        websocket = RecordingWebSocket()
        vad = ImmediateVAD()
        asr = SlowASR()

        first_chunk = b"\x00\x00" * 200
        second_chunk = b"\x01\x00" * 200
        client.append_audio_data(first_chunk)
        client.process_audio(websocket, vad, asr)
        await asyncio.sleep(0)
        client.append_audio_data(second_chunk)
        client.process_audio(websocket, vad, asr)
        await asyncio.sleep(0.05)

        self.assertEqual(asr.inputs, [first_chunk, second_chunk])
        self.assertEqual(
            [message["text"] for message in websocket.messages], ["ok", "ok"]
        )


if __name__ == "__main__":
    unittest.main()
