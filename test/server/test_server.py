# tests/server/test_server.py

import asyncio
import json
import os
import unittest

import websockets
from pydub import AudioSegment
from sentence_transformers import SentenceTransformer, util

from src.asr.asr_factory import ASRFactory
from src.server import Server
from src.vad.vad_factory import VADFactory


class TestServer(unittest.TestCase):
    """
    Test suite for testing the Server class responsible for real-time audio
    transcription.

    This test suite contains tests that verify the functionality of the Server
    class, particularly focusing on its ability to handle audio data,
    process it through VAD (Voice Activity Detection) and
    ASR (Automatic Speech Recognition) pipelines, and return accurate
    transcriptions.

    Methods:
        setUp: Prepares the environment before each test method is executed.
        receive_transcriptions: Asynchronously receives transcriptions from the
                                server and stores them.
        mock_client: Simulates a client sending audio data to the server for
                     processing.
        test_server_response: Tests the server's response accuracy by comparing
                              received and expected transcriptions.
        load_annotations: Loads transcription annotations for comparison with
                          server responses.
    """

    @classmethod
    def setUpClass(cls):
        # Use an environment variable to get the ASR model type
        cls.asr_type = os.getenv("ASR_TYPE", "faster_whisper")
        cls.vad_type = os.getenv("VAD_TYPE", "pyannote")

    def setUp(self):
        """
        Set up the test environment.

        Initializes the VAD and ASR pipelines, the server, the path to the
        annotations, a list to store received transcriptions, and the sentence
        similarity model.
        """
        self.vad_pipeline = VADFactory.create_vad_pipeline(self.vad_type)
        self.asr_pipeline = ASRFactory.create_asr_pipeline(self.asr_type)
        self.server = Server(
            self.vad_pipeline, self.asr_pipeline, host="127.0.0.1", port=8767
        )
        self.annotations_path = os.path.join(
            os.path.dirname(__file__), "../audio_files/annotations.json"
        )
        self.received_transcriptions = []
        self.similarity_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    async def receive_transcriptions(self, websocket):
        """
        Asynchronously receive and store transcriptions from the server.

        Args:
            websocket (Websocket): The websocket connection to receive
            transcriptions from.
        """
        try:
            while True:
                transcription_str = await websocket.recv()
                transcription = json.loads(transcription_str)
                self.received_transcriptions.append(transcription["text"])
                print(
                    f"Received transcription: {transcription['text']}, "
                    f"processing time: {transcription['processing_time']}"
                )
        except websockets.exceptions.ConnectionClosed:
            pass  # Expected when server closes the connection

    async def mock_client(self, audio_file):
        """
        Simulate a client sending audio data to the server.

        Streams audio data in chunks to the server and then streams silence to
        signify the end of the audio.

        Args:
            audio_file (str): Path to the audio file to be sent to the server.
        """
        uri = "ws://127.0.0.1:8767"
        async with websockets.connect(uri) as websocket:
            # Start receiving transcriptions in a separate task
            receive_task = asyncio.create_task(
                self.receive_transcriptions(websocket)
            )

            # Stream the entire audio file in chunks
            with open(audio_file, "rb") as file:
                audio = AudioSegment.from_file(file, format="wav")

            # 4000 samples = 250 ms at 16000 Hz
            for i in range(0, len(audio), 250):
                chunk = audio[i : i + 250]  # noqa: E203
                await websocket.send(chunk.raw_data)
                await asyncio.sleep(0.25)  # Wait for the chunk duration

            # Stream 10 seconds of silence
            silence = AudioSegment.silent(duration=10000)
            await websocket.send(silence.raw_data)
            await asyncio.sleep(10)  # Wait for the silence duration

            # Close the receive task
            receive_task.cancel()

    def test_server_response(self):
        """
        Test the server's response accuracy.

        Compares the received transcriptions from the server with expected
        transcriptions from annotations. Validates the similarity of these
        transcriptions using a sentence transformer model.
        """
        # Start the server
        start_server = self.server.start()
        asyncio.get_event_loop().run_until_complete(start_server)

        annotations = self.load_annotations()
        for audio_file_name, data in annotations.items():
            audio_file_path = os.path.join(
                os.path.dirname(__file__), f"../audio_files/{audio_file_name}"
            )

            # Run the mock client for each audio file
            asyncio.get_event_loop().run_until_complete(
                self.mock_client(audio_file_path)
            )

            # Compare received transcriptions with expected transcriptions
            expected_transcriptions = " ".join(
                [seg["transcription"] for seg in data["segments"]]
            )
            received_transcriptions = " ".join(self.received_transcriptions)

            embedding_1 = self.similarity_model.encode(
                expected_transcriptions.lower().strip(), convert_to_tensor=True
            )
            embedding_2 = self.similarity_model.encode(
                received_transcriptions.lower().strip(), convert_to_tensor=True
            )
            similarity = util.pytorch_cos_sim(embedding_1, embedding_2).item()

            # Print summary before assertion
            print(f"Test file: {audio_file_name}")
            print(f"Expected Transcriptions: {expected_transcriptions}")
            print(f"Received Transcriptions: {received_transcriptions}")
            print(f"Similarity Score: {similarity}")

            self.received_transcriptions = []

            self.assertGreaterEqual(similarity, 0.7)

    def load_annotations(self):
        """
        Load annotations from a JSON file for transcription comparison.

        Returns:
            dict: A dictionary containing expected transcriptions for
                  test audio files.
        """
        with open(self.annotations_path, "r") as file:
            return json.load(file)


if __name__ == "__main__":
    unittest.main()
