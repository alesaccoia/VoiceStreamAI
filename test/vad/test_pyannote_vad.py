# tests/vad/test_pyannote_vad.py

import asyncio
import json
import os
import unittest

from pydub import AudioSegment

from src.client import Client
from src.vad.pyannote_vad import PyannoteVAD


class TestPyannoteVAD(unittest.TestCase):
    def setUp(self):
        self.vad = PyannoteVAD()
        self.annotations_path = os.path.join(
            os.path.dirname(__file__), "../audio_files/annotations.json"
        )
        self.client = Client("test_client", 16000, 2)  # Example client

    def load_annotations(self):
        with open(self.annotations_path, "r") as file:
            return json.load(file)

    def test_detect_activity(self):
        annotations = self.load_annotations()

        for audio_file, data in annotations.items():
            audio_file_path = os.path.join(
                os.path.dirname(__file__), f"../audio_files/{audio_file}"
            )

            for annotated_segment in data["segments"]:
                # Load the specific audio segment for VAD
                audio_segment = self.get_audio_segment(
                    audio_file_path,
                    annotated_segment["start"],
                    annotated_segment["end"],
                )
                self.client.scratch_buffer = bytearray(audio_segment.raw_data)

                vad_results = asyncio.run(
                    self.vad.detect_activity(self.client)
                )

                # Adjust VAD-detected times by adding the start time of the
                # annotated segment
                adjusted_vad_results = [
                    {
                        "start": segment["start"] + annotated_segment["start"],
                        "end": segment["end"] + annotated_segment["start"],
                    }
                    for segment in vad_results
                ]

                detected_segments = [
                    segment
                    for segment in adjusted_vad_results
                    if segment["start"] <= annotated_segment["start"] + 1.0
                    and segment["end"] <= annotated_segment["end"] + 2.0
                ]

                # Print formatted information about the test
                print(
                    f"\nTesting segment from '{audio_file}': Annotated Start: "
                    f"{annotated_segment['start']}, Annotated End: "
                    f"{annotated_segment['end']}"
                )
                print(f"VAD segments: {adjusted_vad_results}")
                print(f"Overlapping, Detected segments: {detected_segments}")

                # Assert that at least one detected segment meets the condition
                self.assertTrue(
                    len(detected_segments) > 0,
                    "No detected segment matches the annotated segment",
                )

    def get_audio_segment(self, file_path, start, end):
        with open(file_path, "rb") as file:
            audio = AudioSegment.from_file(file, format="wav")
        # pydub works in milliseconds
        return audio[start * 1000 : end * 1000]  # noqa: E203


if __name__ == "__main__":
    unittest.main()
