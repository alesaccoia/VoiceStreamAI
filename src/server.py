from aiohttp import web
import uuid
import json

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

    def __init__(
        self,
        vad_pipeline,
        asr_pipeline,
        host="localhost",
        port=80,
        sampling_rate=16000,
        samples_width=2,
        static_files_path="./static",
    ):
        self.vad_pipeline = vad_pipeline
        self.asr_pipeline = asr_pipeline
        self.host = host
        self.port = port
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.connected_clients = {}
        self.static_files_path = static_files_path
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_get("/", self.index_handler)
        self.app.router.add_static(
            "/static/", path=self.static_files_path, name="static"
        )

    async def index_handler(self, request):
        return web.FileResponse(path=f"{self.static_files_path}/index.html")

    def setup_routes(self):
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_get("/", self.serve_index)
        self.app.router.add_static("/", path=self.static_files_path, name="static")

    async def serve_index(self, request):
        return web.FileResponse(path=f"{self.static_files_path}/index.html")

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        client_id = str(uuid.uuid4())
        client = Client(client_id, self.sampling_rate, self.samples_width)
        self.connected_clients[client_id] = client

        print(f"Client {client_id} connected.")
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                message_text = msg.data
                if message_text == "close":
                    await ws.close()
                else:
                    # Handle textual WebSocket messages
                    config = json.loads(message_text)
                    if config.get("type") == "config":
                        client.update_config(config["data"])
            elif msg.type == web.WSMsgType.BINARY:
                # Handle binary WebSocket messages
                client.append_audio_data(msg.data)
                client.process_audio(ws, self.vad_pipeline, self.asr_pipeline)
            elif msg.type == web.WSMsgType.ERROR:
                print(f"WebSocket connection closed with exception {ws.exception()}")

        print(f"Client {client_id} disconnected.")
        del self.connected_clients[client_id]
        return ws

    def start(self):
        web.run_app(self.app, host=self.host, port=self.port)
