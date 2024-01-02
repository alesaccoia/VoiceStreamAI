# tests/asr/test_whisper_asr.py

import asyncio
import unittest
import json
import os
from pydub import AudioSegment
from src.asr.whisper_asr import WhisperASR

class TestWhisperASR(unittest.TestCase):
    def setUp(self):
        self.asr = WhisperASR()
        self.audio_file_path = os.path.join(os.path.dirname(__file__), "../audio_files/eng_speech.wav")
        self.annotations_path = os.path.join(os.path.dirname(__file__), "../audio_files/annotations.json")

    def load_annotations(self):
        with open(self.annotations_path, 'r') as file:
            return json.load(file)

    def get_audio_segment(self, start, end):
        audio = AudioSegment.from_wav(self.audio_file_path)
        return audio[start * 1000:end * 1000]  # pydub works in milliseconds

    def test_transcribe_segments(self):
        annotations = self.load_annotations()

        for segment in annotations["eng_speech.wav"]["segments"]:
            audio_segment = self.get_audio_segment(segment["start"], segment["end"])
            transcription = asyncio.run(self.asr.transcribe(audio_segment))
            print(transcription)
            self.assertEqual(transcription.strip(), segment["transcription"])

if __name__ == '__main__':
    unittest.main()
