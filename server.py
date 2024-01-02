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
import logging

from transformers import pipeline
from pyannote.core import Segment
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection

HOST = '0.0.0.0'
PORT = 8765
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

## ---------- INSTANTIATES VAD --------
model = Model.from_pretrained("pyannote/segmentation", use_auth_token=VAD_AUTH_TOKEN)
vad_pipeline = VoiceActivityDetection(segmentation=model)
vad_pipeline.instantiate({"onset": 0.5, "offset": 0.5, "min_duration_on": 0.3, "min_duration_off": 0.3})

## ---------- INSTANTIATES SPEECH --------
recognition_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3")


connected_clients = {}
client_buffers = {}
client_temp_buffers = {}
client_configs = {}
# Counter for each client to keep track of file numbers
file_counters = {}



async def transcribe_and_send(client_id, websocket, new_audio_data):
    global file_counters

    if DEBUG: print(f"Client ID {client_id}: new_audio_data length in seconds at transcribe_and_send: {float(len(new_audio_data)) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")

    # Initialize temporary buffer for new clients
    if client_id not in client_temp_buffers:
        client_temp_buffers[client_id] = bytearray()

    if DEBUG: print(f"Client ID {client_id}: client_temp_buffers[client_id] length in seconds at transcribe_and_send: {float(len(client_temp_buffers[client_id])) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")

    # Add new audio data to the temporary buffer
    old_audio_data = bytes(client_temp_buffers[client_id])

    if DEBUG: print(f"Client ID {client_id}: old_audio_data length in seconds at transcribe_and_send: {float(len(old_audio_data)) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")


    audio_data = old_audio_data + new_audio_data

    if DEBUG: print(f"Client ID {client_id}: audio_data length in seconds at transcribe_and_send: {float(len(audio_data)) / float(SAMPLING_RATE * SAMPLES_WIDTH)}")
    
    # Initialize file counter for new clients
    if client_id not in file_counters:
        file_counters[client_id] = 0

    # File path
    file_name = f"{audio_dir}/{client_id}_{file_counters[client_id]}.wav"

    if DEBUG: print(f"Client ID {client_id}: Filename : {file_name}")

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
    if DEBUG: print(f"Client ID {client_id}: VAD result segments count: {len(result)}")
    print(f"Client ID {client_id}: VAD inference time: {vad_time:.2f}")

    if len(result) == 0: # this should happen just if there's no old audio data
        os.remove(file_name)
        client_temp_buffers[client_id].clear() 
        return
    
    
    
    # Get last recognized segment
    last_segment = None
    for segment in result.itersegments():
        last_segment = segment

    if DEBUG: print(f"Client ID {client_id}: VAD last Segment end : {last_segment.end}")
    
    # if the voice ends before chunk_offset_seconds process it all
    if last_segment.end < (len(audio_data) / (SAMPLES_WIDTH * SAMPLING_RATE)) - int(client_configs[client_id]['chunk_offset_seconds']):
        start_time_transcription = time.time()
        
        if client_configs[client_id]['language'] is not None:
            print("Entering recognition pipeline no language")
            result = recognition_pipeline(file_name, generate_kwargs={"language": client_configs[client_id]['language']})
        else:
            print("Entering recognition pipeline has language")
            result = recognition_pipeline(file_name)

        transcription_time = time.time() - start_time_transcription
        print("result is ", result)

        if DEBUG: print(f"Transcription Time: {transcription_time:.2f} seconds")

        print(f"Client ID {client_id}: Transcribed : {result['text']}")

        if result['text']:
            await websocket.send(result['text'])
            client_temp_buffers[client_id].clear() # Clear temp buffer after processing
    else:
        client_temp_buffers[client_id].clear()
        client_temp_buffers[client_id].extend(audio_data)
        if DEBUG: print(f"Skipping because {last_segment.end} falls after {(len(audio_data) / (SAMPLES_WIDTH * SAMPLING_RATE)) - int(client_configs[client_id]['chunk_offset_seconds'])}")

    os.remove(file_name) # in the end always delete the created file

async def receive_audio(websocket, path):
    client_id = str(uuid.uuid4())
    connected_clients[client_id] = websocket
    client_buffers[client_id] = bytearray()
    client_configs[client_id] = DEFAULT_CLIENT_CONFIG
    
    print(f"Client {client_id} connected")

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                client_buffers[client_id].extend(message)
            elif isinstance(message, str):
                config = json.loads(message)
                if config.get('type') == 'config':
                    client_configs[client_id] = config['data']
                    print(f"Config for {client_id}: {client_configs[client_id]}")
                    continue
            else:
                print(f"Unexpected message type from {client_id}")

            # Process audio when enough data is received
            if len(client_buffers[client_id]) > int(client_configs[client_id]['chunk_length_seconds']) * SAMPLING_RATE * SAMPLES_WIDTH:
                if DEBUG: print(f"Client ID {client_id}: receive_audio calling transcribe_and_send with length: {len(client_buffers[client_id])}")
                await transcribe_and_send(client_id, websocket, client_buffers[client_id])
                client_buffers[client_id].clear()

    except websockets.ConnectionClosed as e:
        print(f"Connection with {client_id} closed: {e}")
    finally:
        del connected_clients[client_id]
        del client_buffers[client_id]

async def main():
    async with websockets.serve(receive_audio, HOST, PORT):
        print(f"WebSocket server started on ws://{HOST}:{PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
