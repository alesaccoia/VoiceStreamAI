"""
VoiceStreamAI Server: Real-time audio transcription using self-hosted Whisper and WebSocket

Contributors:
- Alessandro Saccoia - alessandro.saccoia@gmail.com
"""

import asyncio
import websockets
import uuid
import json
import wave
import os
import time
import torch
import logging
import time
from transformers import pipeline
from pyannote.core import Segment
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from utils.log import configure_logging
logger = configure_logging()


HOST = '0.0.0.0'
PORT = 9876
SAMPLING_RATE = 16000
AUDIO_CHANNELS = 1
SAMPLES_WIDTH = 2 # int16
DEBUG = True
VAD_AUTH_TOKEN = os.environ.get("HF_TOKEN") # get your key here -> https://huggingface.co/pyannote/segmentation

DEFAULT_CLIENT_CONFIG = {
    "language" : None, # multilingual
    "chunk_length_seconds" : 5,
    "chunk_offset_seconds" : 1
}



audio_dir = "audio_files"
os.makedirs(audio_dir, exist_ok=True)
device = torch.device("cuda", 1)

## ---------- INSTANTIATES VAD --------
model = Model.from_pretrained("pyannote/segmentation", use_auth_token=VAD_AUTH_TOKEN)
vad_pipeline = VoiceActivityDetection(segmentation=model, device=device)
vad_pipeline.instantiate({"onset": 0.5, "offset": 0.5, "min_duration_on": 0.3, "min_duration_off": 0.3})

## ---------- INSTANTIATES SPEECH --------
#recognition_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3")
recognition_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-medium.en", device=device)


connected_clients = {}
client_buffers = {}
client_temp_buffers = {}
client_configs = {}
# Counter for each client to keep track of file numbers
file_counters = {}
recv_time = {}



async def transcribe_and_send(client_id, websocket, new_audio_data):
    global file_counters

    logger.info(f"Client ID {client_id}: new_audio_data length in seconds at transcribe_and_send: {float(len(new_audio_data)) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")

    # Initialize temporary buffer for new clients
    if client_id not in client_temp_buffers:
        client_temp_buffers[client_id] = bytearray()

    logger.info(f"Client ID {client_id}: client_temp_buffers[client_id] length in seconds at transcribe_and_send: {float(len(client_temp_buffers[client_id])) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")

    # Add new audio data to the temporary buffer
    old_audio_data = bytes(client_temp_buffers[client_id])

    logger.info(f"Client ID {client_id}: old_audio_data length in seconds at transcribe_and_send: {float(len(old_audio_data)) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")


    audio_data = old_audio_data + new_audio_data

    logger.info(f"Client ID {client_id}: audio_data length in seconds at transcribe_and_send: {float(len(audio_data)) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")
    
    # Initialize file counter for new clients
    if client_id not in file_counters:
        file_counters[client_id] = 0

    # File path
    file_name = f"{audio_dir}/{client_id}_{file_counters[client_id]}.wav"

    logger.info(f"Client ID {client_id}: Filename : {file_name}")

    file_counters[client_id] += 1

    # Save the audio data
    with wave.open(file_name, 'wb') as wav_file:
        wav_file.setnchannels(AUDIO_CHANNELS)
        wav_file.setsampwidth(SAMPLES_WIDTH)
        wav_file.setframerate(SAMPLING_RATE)
        wav_file.writeframes(audio_data)

    # Measure VAD time
    start_time_vad = time.time()
    result = vad_pipeline(file_name)
    vad_time = time.time() - start_time_vad

    # Logging after VAD
    logger.info(f"Client ID {client_id}: VAD result segments count: {len(result)}")
    logger.info(f"Client ID {client_id}: VAD inference time: {vad_time:.2f}")

    if len(result) == 0: # this should happen just if there's no old audio data
        os.remove(file_name)
        client_temp_buffers[client_id].clear() 
        return
    
    
    
    # Get last recognized segment
    last_segment = None
    for segment in result.itersegments():
        last_segment = segment

    logger.info(f"Client ID {client_id}: VAD last Segment end : {last_segment.end}")
    
    accumulated_secs = len(audio_data) / (SAMPLES_WIDTH * SAMPLING_RATE)
    # if the voice ends before chunk_offset_seconds process it all
    timeout_flag = accumulated_secs > 5
    seg_flag = last_segment.end < accumulated_secs - float(client_configs[client_id]['chunk_offset_seconds'])
    if timeout_flag or seg_flag :
        start_time_transcription = time.time()
        
        # if client_configs[client_id]['language'] is not None:
        #     result = recognition_pipeline(file_name, generate_kwargs={"language": client_configs[client_id]['language']})
        # else:
        result = recognition_pipeline(file_name)

        transcription_time = time.time() - start_time_transcription

        logger.info(f"Transcription Time: {transcription_time:.2f} seconds")

        logger.info(f"Client ID {client_id}: Transcribed : {result['text']}")

        if result['text']:
            
            time_delta = time.time() - recv_time[client_id]
            time_delta_str = f"|{time_delta:.3f}s|"
            sep_text = time_delta_str if seg_flag else f"......{time_delta_str}"
            await websocket.send(result['text'] + sep_text)
            client_temp_buffers[client_id].clear() # Clear temp buffer after processing
    else:
        client_temp_buffers[client_id].clear()
        client_temp_buffers[client_id].extend(audio_data)
        logger.info(f"Skipping because {last_segment.end} falls after {(len(audio_data) / (SAMPLES_WIDTH * SAMPLING_RATE)) - float(client_configs[client_id]['chunk_offset_seconds'])}")

    os.remove(file_name) # in the end always delete the created file

async def receive_audio(websocket, path):
    logger.info(f"websocket type: {websocket}")
    client_id = str(uuid.uuid4())
    connected_clients[client_id] = websocket
    client_buffers[client_id] = bytearray()
    recv_time[client_id] = None # recv time list
    client_configs[client_id] = DEFAULT_CLIENT_CONFIG
    
    logger.info(f"Client {client_id} connected")
    

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                client_buffers[client_id].extend(message)
                recv_time[client_id] = time.time()
            elif isinstance(message, str):
                config = json.loads(message)
                if config.get('type') == 'config':
                    client_configs[client_id] = config['data']
                    logger.info(f"Config for {client_id}: {client_configs[client_id]}")
                    continue
            else:
                logger.info(f"Unexpected message type from {client_id}")

            # Process audio when enough data is received
            config_buf_size = float(client_configs[client_id]['chunk_length_seconds']) * SAMPLING_RATE * SAMPLES_WIDTH
            if len(client_buffers[client_id]) > config_buf_size:
                logger.info(f"Client ID {client_id}: receive_audio calling transcribe_and_send with length: {len(client_buffers[client_id])}, max length: {config_buf_size}")
                await transcribe_and_send(client_id, websocket, client_buffers[client_id])
                client_buffers[client_id].clear()
                recv_time[client_id] = list()

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
