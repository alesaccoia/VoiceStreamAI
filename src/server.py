import websockets
import uuid
import json
import asyncio

from src.audio_utils import save_audio_to_file
from src.client import Client

class Server:
    """
    Represents the WebSocket server for handling real-time audio transcription.

    This class manages WebSocket connections, processes incoming audio data,
    and interacts with VAD and ASR pipelines for voice activity detection and
    speech recognition.

    Attributes:
        vad_pipeline: An instance of a voice activity detection pipeline.
        asr_pipeline: An instance of an automatic speech recognition pipeline.
        host (str): Host address of the server.
        port (int): Port on which the server listens.
        sampling_rate (int): The sampling rate of audio data in Hz.
        samples_width (int): The width of each audio sample in bits.
        connected_clients (dict): A dictionary mapping client IDs to Client objects.
    """
    def __init__(self, vad_pipeline, asr_pipeline, host='localhost', port=8765, sampling_rate=16000, samples_width=2):
        self.vad_pipeline = vad_pipeline
        self.asr_pipeline = asr_pipeline
        self.host = host
        self.port = port
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.connected_clients = {}

    async def handle_audio(self, client, websocket):
        while True:
            message = await websocket.recv()

            if isinstance(message, bytes):
                client.append_audio_data(message)
            elif isinstance(message, str):
                config = json.loads(message)
                if config.get('type') == 'config':
                    client.update_config(config['data'])
                    continue
            else:
                print(f"Unexpected message type from {client.client_id}")

            chunk_length_in_bytes = int(client.config.get('chunk_length_seconds', 5)) * self.sampling_rate * self.samples_width

            if client.config.get('processing_strategy') == 1:
                if len(client.buffer) > chunk_length_in_bytes:
                    # Schedule the processing in a separate task
                    client.scratch_buffer += client.buffer
                    client.buffer.clear()
                    asyncio.create_task(self.process_audio_strategy_1(client, websocket))

    async def process_audio_strategy_1(self, client, websocket):
        # This is the heavy processing part
        vad_results = await self.vad_pipeline.detect_activity(client)

        if len(vad_results) == 0:
            client.scratch_buffer.clear()
            client.buffer.clear()
            return

        last_segment_should_end_before = ((len(client.scratch_buffer) / (self.sampling_rate * self.samples_width)) - int(client.config.get('chunk_offset_seconds')))
        if vad_results[-1]['end'] < last_segment_should_end_before:
            transcription = await self.asr_pipeline.transcribe(client)
            if transcription != '':
                await websocket.send(transcription)

            client.scratch_buffer.clear()
            client.increment_file_counter()
        

    async def handle_websocket(self, websocket, path):
        client_id = str(uuid.uuid4())
        client = Client(client_id, self.sampling_rate, self.samples_width)
        self.connected_clients[client_id] = client

        print(f"Client {client_id} connected")

        try:
            await self.handle_audio(client, websocket)
        except websockets.ConnectionClosed as e:
            print(f"Connection with {client_id} closed: {e}")
        finally:
            del self.connected_clients[client_id]

    def start(self):
        print("Websocket server ready to accept connections")
        return websockets.serve(self.handle_websocket, self.host, self.port)
