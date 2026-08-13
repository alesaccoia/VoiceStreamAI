import asyncio
import json
import logging
import os
import time

from .buffering_strategy_interface import BufferingStrategyInterface


class SilenceAtEndOfChunk(BufferingStrategyInterface):
    """
    A buffering strategy that processes audio at the end of each chunk with
    silence detection.

    This class is responsible for handling audio chunks, detecting silence at
    the end of each chunk, and initiating the transcription process for the
    chunk.

    Attributes:
        client (Client): The client instance associated with this buffering
                         strategy.
        chunk_length_seconds (float): Length of each audio chunk in seconds.
        chunk_offset_seconds (float): Offset time in seconds to be considered
                                      for processing audio chunks.
    """

    def __init__(self, client, **kwargs):
        """
        Initialize the SilenceAtEndOfChunk buffering strategy.

        Args:
            client (Client): The client instance associated with this buffering
                             strategy.
            **kwargs: Additional keyword arguments, including
                      'chunk_length_seconds' and 'chunk_offset_seconds'.
        """
        self.client = client

        self.chunk_length_seconds = os.environ.get(
            "BUFFERING_CHUNK_LENGTH_SECONDS"
        )
        if not self.chunk_length_seconds:
            self.chunk_length_seconds = kwargs.get("chunk_length_seconds")
        self.chunk_length_seconds = float(self.chunk_length_seconds)

        self.chunk_offset_seconds = os.environ.get(
            "BUFFERING_CHUNK_OFFSET_SECONDS"
        )
        if not self.chunk_offset_seconds:
            self.chunk_offset_seconds = kwargs.get("chunk_offset_seconds")
        self.chunk_offset_seconds = float(self.chunk_offset_seconds)

        self.pending_audio = bytearray()
        self.processing_task = None
        self.retry_after_bytes = 0

    def process_audio(self, websocket, vad_pipeline, asr_pipeline):
        """
        Process audio chunks by checking their length and scheduling
        asynchronous processing.

        This method checks if the length of the audio buffer exceeds the chunk
        length and, if so, it schedules asynchronous processing of the audio.

        Args:
            websocket: The WebSocket connection for sending transcriptions.
            vad_pipeline: The voice activity detection pipeline.
            asr_pipeline: The automatic speech recognition pipeline.
        """
        chunk_length_in_bytes = (
            self.chunk_length_seconds
            * self.client.sampling_rate
            * self.client.samples_width
        )
        if self.client.buffer:
            self.pending_audio.extend(self.client.buffer)
            self.client.buffer.clear()
        self._start_processing_if_ready(
            websocket, vad_pipeline, asr_pipeline, chunk_length_in_bytes
        )

    def _start_processing_if_ready(
        self, websocket, vad_pipeline, asr_pipeline, chunk_length_in_bytes
    ):
        if self.processing_task is not None or len(self.pending_audio) < max(
            chunk_length_in_bytes, self.retry_after_bytes
        ):
            return

        audio = bytes(self.pending_audio)
        self.pending_audio.clear()
        self.retry_after_bytes = 0
        self.processing_task = asyncio.get_running_loop().create_task(
            self.process_audio_async(
                audio,
                websocket,
                vad_pipeline,
                asr_pipeline,
                chunk_length_in_bytes,
            )
        )

    async def process_audio_async(
        self,
        audio,
        websocket,
        vad_pipeline,
        asr_pipeline,
        chunk_length_in_bytes,
    ):
        """
        Asynchronously process audio for activity detection and transcription.

        This method performs heavy processing, including voice activity
        detection and transcription of the audio data. It sends the
        transcription results through the WebSocket connection.

        Args:
            websocket (Websocket): The WebSocket connection for sending
                                   transcriptions.
            vad_pipeline: The voice activity detection pipeline.
            asr_pipeline: The automatic speech recognition pipeline.
        """
        try:
            start = time.time()
            self.client.scratch_buffer = bytearray(audio)
            if vad_pipeline is None:
                vad_results = [{"end": 0.0}]
                speech_finished = True
            else:
                vad_results = await vad_pipeline.detect_activity(self.client)
                speech_finished = bool(vad_results) and vad_results[-1][
                    "end"
                ] < (
                    len(audio)
                    / (self.client.sampling_rate * self.client.samples_width)
                    - self.chunk_offset_seconds
                )

            if not vad_results:
                return

            if speech_finished:
                transcription = await asr_pipeline.transcribe(self.client)
                if transcription["text"]:
                    transcription["processing_time"] = time.time() - start
                    await websocket.send(json.dumps(transcription))
                self.client.increment_file_counter()
            else:
                # Keep unfinished speech and wait for at least one offset of
                # new audio before retrying, without dropping incoming data.
                self.pending_audio = bytearray(audio) + self.pending_audio
                self.retry_after_bytes = len(audio) + int(
                    self.chunk_offset_seconds
                    * self.client.sampling_rate
                    * self.client.samples_width
                )
        except Exception:
            logging.exception(
                "Audio processing failed for client %s", self.client.client_id
            )
        finally:
            self.client.scratch_buffer.clear()
            self.processing_task = None
            chunk_length_in_bytes = (
                self.chunk_length_seconds
                * self.client.sampling_rate
                * self.client.samples_width
            )
            self._start_processing_if_ready(
                websocket, vad_pipeline, asr_pipeline, chunk_length_in_bytes
            )

    def close(self):
        if self.processing_task is not None:
            self.processing_task.cancel()
