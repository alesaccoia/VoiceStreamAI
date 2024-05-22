import asyncio
import json
import os
import unittest

from pydub import AudioSegment
from sentence_transformers import SentenceTransformer, util

from src.asr.asr_factory import ASRFactory
from src.client import Client


class TestWhisperASR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use an environment variable to get the ASR model type
        cls.asr_type = os.getenv("ASR_TYPE", "whisper")

    def setUp(self):
        self.asr = ASRFactory.create_asr_pipeline(self.asr_type)
        self.annotations_path = os.path.join(
            os.path.dirname(__file__), "../audio_files/annotations.json"
        )
        self.client = Client("test_client", 16000, 2)  # Example client
        self.similarity_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    def load_annotations(self):
        with open(self.annotations_path, "r") as file:
            return json.load(file)

    def get_audio_segment(self, file_path, start, end):
        with open(file_path, "rb") as file:
            audio = AudioSegment.from_file(file, format="wav")
        # pydub works in milliseconds
        return audio[start * 1000 : end * 1000]  # noqa: E203

    def test_transcribe_segments(self):
        annotations = self.load_annotations()

        for audio_file, data in annotations.items():
            audio_file_path = os.path.join(
                os.path.dirname(__file__), f"../audio_files/{audio_file}"
            )
            similarities = []

            for segment in data["segments"]:
                audio_segment = self.get_audio_segment(
                    audio_file_path, segment["start"], segment["end"]
                )
                self.client.scratch_buffer = bytearray(audio_segment.raw_data)
                self.client.config["language"] = None

                transcription = asyncio.run(self.asr.transcribe(self.client))[
                    "text"
                ]

                embedding_1 = self.similarity_model.encode(
                    transcription.lower().strip(), convert_to_tensor=True
                )
                embedding_2 = self.similarity_model.encode(
                    segment["transcription"].lower().strip(),
                    convert_to_tensor=True,
                )
                similarity = util.pytorch_cos_sim(
                    embedding_1, embedding_2
                ).item()
                similarities.append(similarity)

                print(
                    f"\nSegment from '{audio_file}' "
                    f"({segment['start']}-{segment['end']}s):"
                )
                print(f"Expected: {segment['transcription']}")
                print(f"Actual: {transcription}")
                print(f"Similarity: {similarity}")

                self.client.scratch_buffer.clear()

            # Calculate average similarity for the file
            avg_similarity = sum(similarities) / len(similarities)
            print(f"\nAverage similarity for '{audio_file}': {avg_similarity}")

            # Assert that the average similarity is above the threshold
            self.assertGreaterEqual(
                avg_similarity, 0.7
            )  # Adjust the threshold as needed


if __name__ == "__main__":
    unittest.main()
