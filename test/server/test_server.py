# tests/server/test_server.py

import unittest
import os
import json
import asyncio
import websockets
from pydub import AudioSegment
from src.server import Server
from src.vad.pyannote_vad import PyannoteVAD
from src.asr.whisper_asr import WhisperASR

class TestServer(unittest.TestCase):
    def setUp(self):
        # Initialize VAD and ASR pipelines (add necessary arguments)
        self.vad_pipeline = PyannoteVAD()
        self.asr_pipeline = WhisperASR()
        self.server = Server(self.vad_pipeline, self.asr_pipeline, host='localhost', port=8766)
        self.annotations_path = os.path.join(os.path.dirname(__file__), "../audio_files/annotations.json")
        self.received_transcriptions = []

    async def receive_transcriptions(self, websocket):
        try:
            while True:
                transcription = await websocket.recv()
                self.received_transcriptions.append(transcription)
                print(f"Received transcription: {transcription}")
        except websockets.exceptions.ConnectionClosed:
            pass  # Expected when server closes the connection

    async def mock_client(self, audio_file):
        uri = "ws://localhost:8766"
        async with websockets.connect(uri) as websocket:
            # Start receiving transcriptions in a separate task
            receive_task = asyncio.create_task(self.receive_transcriptions(websocket))

            # Stream the entire audio file in chunks
            with open(audio_file, 'rb') as file:
                audio = AudioSegment.from_file(file, format="wav")
            
            for i in range(0, len(audio), 250):  # 4000 samples = 250 ms at 16000 Hz
                chunk = audio[i:i+250]
                await websocket.send(chunk.raw_data)
                await asyncio.sleep(0.25)  # Wait for the chunk duration
                
            # Stream 10 seconds of silence
            silence = AudioSegment.silent(duration=10000)
            await websocket.send(silence.raw_data)
            await asyncio.sleep(10)  # Wait for the silence duration

            # Close the receive task
            receive_task.cancel()

    def test_server_response(self):
        # Start the server
        start_server = self.server.start()
        asyncio.get_event_loop().run_until_complete(start_server)

        annotations = self.load_annotations()
        for audio_file_name, data in annotations.items():
            audio_file_path = os.path.join(os.path.dirname(__file__), f"../audio_files/{audio_file_name}")

            # Run the mock client for each audio file
            asyncio.get_event_loop().run_until_complete(self.mock_client(audio_file_path))

            # Compare received transcriptions with expected transcriptions
            expected_transcriptions = [seg["transcription"] for seg in data['segments']]
            for transcription in self.received_transcriptions:
                self.assertTrue(any(expected in transcription for expected in expected_transcriptions))

    def load_annotations(self):
        with open(self.annotations_path, 'r') as file:
            return json.load(file)

if __name__ == '__main__':
    unittest.main()
