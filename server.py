import asyncio
import websockets
import uuid
import json
import wave
import os
import time
import torch
import logging
import sys
import time
from transformers import pipeline
from pyannote.core import Segment
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from utils.log import configure_logging
import numpy as np
import io
from utils.llm import chat
import soundfile as sf

logger = configure_logging()


HOST = "0.0.0.0"
PORT = 9876
SAMPLING_RATE = 16000
AUDIO_CHANNELS = 1
SAMPLES_WIDTH = 2  # int16
VAD_AUTH_TOKEN = os.environ.get(
    "HF_TOKEN"
)  # get your key here -> https://huggingface.co/pyannote/segmentation

DEFAULT_CLIENT_CONFIG = {
    "language": None,  # multilingual
    "chunk_length_seconds": 2,
    "chunk_offset_seconds": 0.5,
}


device = torch.device("cuda", 1)

## ---------- INSTANTIATES VAD --------
model = Model.from_pretrained("pyannote/segmentation", use_auth_token=VAD_AUTH_TOKEN)
vad_pipeline = VoiceActivityDetection(segmentation=model, device=device)
vad_pipeline.instantiate(
    {"onset": 0.5, "offset": 0.5, "min_duration_on": 0.3, "min_duration_off": 0.3}
)

## ---------- INSTANTIATES SPEECH --------
# recognition_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3")
recognition_pipeline = pipeline(
    "automatic-speech-recognition", model="openai/whisper-medium.en", device=device
)


connected_clients = {}
client_buffers = {}
client_temp_buffers = {}
client_configs = {}
recv_time = {}
file_count = 0

async def transcribe_and_send(client_id, websocket):
    global file_count
    if client_id in client_temp_buffers:
        client_temp_buffers[client_id] = client_temp_buffers[client_id] + client_buffers[client_id]
    else:
        client_temp_buffers[client_id] = client_buffers[client_id]

    cur_data = client_temp_buffers[client_id]
    duration = float(len(cur_data)) / (SAMPLES_WIDTH * SAMPLING_RATE)

    # vad inference
    numpy_audio = np.frombuffer(cur_data, dtype=np.int16)
    tensor_audio = torch.tensor(numpy_audio, dtype=torch.float32).view(1, -1)
    start_time_vad = time.time()
    vad_result = vad_pipeline({"waveform":tensor_audio, "sample_rate":SAMPLING_RATE})
    vad_time = time.time() - start_time_vad
    logger.info(f"Client ID {client_id}: VAD infer time:{vad_time:.2f}, VAD segments: {len(vad_result)}, current audio length: {duration:.2f}s")

    if len(vad_result) == 0:
        logger.info("drop this segment due to no voice activity found")
        client_temp_buffers[client_id]= bytearray()
        return
    
    end = 0
    for segment in vad_result.itersegments():
        # if segment.start - end > client_configs[client_id]['chunk_offset_seconds']:
        #     # ASR pipeline
        #     cut_point = int(end * (SAMPLES_WIDTH * SAMPLING_RATE))
        #     cur_numpy = np.frombuffer(cur_data[:cut_point], dtype=np.int16)
        #     asr_result = recognition_pipeline(cur_numpy)
        #     client_buffers[client_id] = client_buffers[client_id][cut_point:]
        #     if asr_result["text"]:
        #         question = asr_result['text']
        #         answer = chat(question)
        #         await websocket.send(f"Q: {question}  A: {answer}")
        #     return 
        # else:
        end = segment.end
    if duration - end > client_configs[client_id]['chunk_offset_seconds']:
        cut_point = int(end * SAMPLING_RATE) * SAMPLES_WIDTH
        logger.info(f"buffer size: {len(cur_data)}, cut_point: {cut_point}")
        cur_numpy = np.frombuffer(cur_data[:cut_point], dtype=np.int16)
        asr_result = recognition_pipeline(cur_numpy)
        client_temp_buffers[client_id] = cur_data[cut_point:]
        if asr_result["text"]:
            file_count += 1
            question = asr_result['text']
            file_name = os.path.join('audio_files', f"{question}_{file_count}.wav")
            with wave.open(file_name, 'wb') as wav_file:
                wav_file.setnchannels(AUDIO_CHANNELS)
                wav_file.setsampwidth(SAMPLES_WIDTH)
                wav_file.setframerate(SAMPLING_RATE)
                wav_file.writeframes(cur_data[:cut_point])
            answer = chat(question)
            await websocket.send(f"Q: {question}  A: {answer}")
        return 
    


async def receive_audio(websocket, path):
    logger.info(f"websocket type: {websocket}")
    client_id = str(uuid.uuid4())
    connected_clients[client_id] = websocket
    client_buffers[client_id] = bytearray()
    recv_time[client_id] = None  # recv time list
    client_configs[client_id] = DEFAULT_CLIENT_CONFIG

    logger.info(f"Client {client_id} connected")

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                client_buffers[client_id].extend(message)
                recv_time[client_id] = time.time()
            elif isinstance(message, str):
                # config = json.loads(message)
                # if config.get("type") == "config":
                #     client_configs[client_id] = config["data"]
                #     logger.info(f"Config for {client_id}: {client_configs[client_id]}")
                continue
            else:
                logger.info(f"Unexpected message type from {client_id}")

            # Process audio when enough data is received
            config_buf_size = (
                float(client_configs[client_id]["chunk_length_seconds"])
                * SAMPLING_RATE
                * SAMPLES_WIDTH
            )
            if len(client_buffers[client_id]) > config_buf_size:
                logger.info(
                    f"Client ID {client_id}: receive_audio calling transcribe_and_send with length: {len(client_buffers[client_id])}, max length: {config_buf_size}"
                )
                await transcribe_and_send(
                    client_id, websocket
                )
                client_buffers[client_id].clear()
                recv_time[client_id] = None

    except websockets.ConnectionClosed as e:
        logger.info(f"Connection with {client_id} closed: {e}")
    finally:
        del connected_clients[client_id]
        del client_buffers[client_id]


async def main():
    async with websockets.serve(receive_audio, HOST, PORT):
        logger.info(f"WebSocket server started on ws://{HOST}:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
