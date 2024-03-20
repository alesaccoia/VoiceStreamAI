# VoiceStreamAI

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

VoiceStreamAI is a Python 3 -based server and JavaScript client solution that enables near-realtime audio streaming and transcription using WebSocket. The system employs Huggingface's Voice Activity Detection (VAD) and OpenAI's Whisper model ([faster-whisper](https://github.com/SYSTRAN/faster-whisper) being the default) for accurate speech recognition and processing.

## Features

- Real-time audio streaming through WebSocket.
- Modular design for easy integration of different VAD and ASR technologies.
- Factory and strategy pattern implementation for flexible component management.
- Unit testing framework for robust development.
- Customizable audio chunk processing strategies.
- Support for multilingual transcription.

## Demo

[View Demo Video](https://raw.githubusercontent.com/TyreseDev/VoiceStreamAI/main/img/voicestreamai_test.mp4)

![Demo Image](https://raw.githubusercontent.com/TyreseDev/VoiceStreamAI/main/img/client.png)

## Running with Docker

This will not guide you in detail on how to use CUDA in docker, see for example [here](https://medium.com/@kevinsjy997/configure-docker-to-use-local-gpu-for-training-ml-models-70980168ec9b).

Still, these are the commands for Linux:

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
&& curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
&& curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo nvidia-ctk runtime configure --runtime=docker

sudo systemctl restart docker
```

You can build the image with:

```bash
sudo docker build -t voicestreamai .
```

After getting your VAD token (see next sections) run:

```bash

sudo docker volume create huggingface_models

sudo docker run --gpus all -p 80:80 -v huggingface_models:/root/.cache/huggingface  -e PYANNOTE_AUTH_TOKEN='VAD_TOKEN_HERE' voicestreamai
```

The "volume" stuff will allow you not to re-download the huggingface models each time you re-run the container. If you don't need this, just use:

```bash
sudo docker run --gpus all -p 80:80 -e PYANNOTE_AUTH_TOKEN='VAD_TOKEN_HERE' voicestreamai
```

## Normal, Manual Installation

To set up the VoiceStreamAI server, you need Python 3.8 or later and the following packages:

1. `transformers`
2. `pyannote.core`
3. `pyannote.audio`
4. `websockets`
5. `asyncio`
6. `sentence-transformers`
7. `faster-whisper`

Install these packages using pip:

```bash
pip install -r requirements
```

For the client-side, you need a modern web browser with JavaScript support.

## Configuration and Usage

### Server Configuration

The VoiceStreamAI server can be customized through command line arguments, allowing you to specify components, host, and port settings according to your needs.

- `--vad-type`: Specifies the type of Voice Activity Detection (VAD) pipeline to use (default: `pyannote`) .
- `--vad-args`: A JSON string containing additional arguments for the VAD pipeline. (required for `pyannote`: `'{"auth_token": "VAD_AUTH_HERE"}'`)
- `--asr-type`: Specifies the type of Automatic Speech Recognition (ASR) pipeline to use (default: `faster_whisper`).
- `--asr-args`: A JSON string containing additional arguments for the ASR pipeline (one can for example change `model_name` for whisper)
- `--host`: Sets the host address for the WebSocket server (default: `127.0.0.1`).
- `--port`: Sets the port on which the server listens (default: `80`).

For running the server with the standard configuration:

1. Obtain the key to the Voice-Activity-Detection model at [https://huggingface.co/pyannote/segmentation](https://huggingface.co/pyannote/segmentation)
2. Run the server using Python 3.x, please add the VAD key in the command line:

```bash
python3 -m src.main --vad-args '{"auth_token": "vad token here"}'
```

You can see all the command line options with the command:

```bash
python3 -m src.main --help
```

## Client Usage

1. Open the `client/VoiceStreamAI_Client.html` file in a web browser.
2. Enter the WebSocket address (default is `ws://localhost/ws`).
3. Configure the audio chunk length and offset. See below.
4. Select the language for transcription.
5. Click 'Connect' to establish a WebSocket connection.
6. Use 'Start Streaming' and 'Stop Streaming' to control audio capture.

## Technology Overview

- **Python Server**: Manages WebSocket connections, processes audio streams, and handles voice activity detection and transcription.
- **WebSockets**: Used for real-time communication between the server and client.
- **Voice Activity Detection**: Detects voice activity in the audio stream to optimize processing.
- **Speech-to-Text**: Utilizes [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) or OpenAI's Whisper model (openai/whisper-large-v3) for accurate transcription. Faster Whisper is the default as it is much faster

## Technical Overview

### Settings

### Factory and Strategy patterns

Both the VAD and the ASR components can be easily extended to integrate new techniques and use models with an different interface than HuggingFace pipelines. New processing/chunking strategies can be added in server.py, and used by the specific clients setting the "processing_strategy" key in the config.

### Voice Activity Detection (VAD)

Voice Activity Detection (VAD) in VoiceStreamAI enables the system to distinguish between speech and non-speech segments within an audio stream. The primary purpose of implementing VAD is to enhance the efficiency and accuracy of the speech-to-text process:

- **Reduces Computational Load**: By identifying and processing only those segments that contain speech, VAD significantly reduces the computational resources required for transcription. This is important considering that the speech recognition pipeline takes 7 seconds on a Tesla T4 (16Gb) - take this into consideration when setting the chunk length.
- **Improves Transcription Accuracy**: Processing only the voice segments minimizes the chances of non-speech noises being misinterpreted as speech, thus improving the overall accuracy of the transcription.
- **Optimizes Network Utilization**: In a streaming context, sending only voice segments over the network, as opposed to the entire audio stream, optimizes bandwidth usage.

VoiceStreamAI uses a Huggingface VAD model to ensure reliable detection of speech in diverse audio conditions.

### Processing Strategy "SilenceAtEndOfChunk"

The buffering strategy is designed to balance between near-real-time processing and ensuring complete and accurate capture of speech segments. Here’s how buffering is managed:

- **Chunk-Based Processing**: The audio stream is processed into chunks of a per-client customizable length (defaults to 5 seconds)
- **Silence Handling**: A minimum silence offset is defined to allow for continuous listening and capturing audio beyond the end of a single chunk. This ensures that words at the boundary of chunks are not cut off, thereby maintaining the context and completeness of speech. This introduces extra latency for very dense parts of speech, as the transciprion will not take place until a pause is identified.
- **Dynamic Buffer Management**: The system dynamically manages buffers for each client. When new audio data arrives, it is appended to the client's temporary buffer. Once a buffer reaches the chunk length, it is processed, and the buffer is cleared, ready for new data.

![Buffering Mechanism](/img/vad.png "Chunking and Silence Handling")

### Client-Specific Configuration Messaging

In VoiceStreamAI, each client can have a unique configuration that tailors the transcription process to their specific needs. This personalized setup is achieved through a messaging system where the JavaScript client sends configuration details to the Python server. This section explains how these configurations are structured and transmitted.

The client configuration can include various parameters such as language preference, chunk length, and chunk offset. For instance:

- `language`: Specifies the language for transcription. If set to anything other than "multilanguage" it will force the Whisper inference to be in that language
- `processing_strategy`: Specifies the type of processing for this client, a sort of strategy pattern. Strategy for now aren't using OOP but they are implemented in an if/else in server.py
- `chunk_length_seconds`: Defines the length of each audio chunk to be processed
- `chunk_offset_seconds`: Determines the silence time at the end of each chunk needed to process audio (used by processing_strategy nr 1).

### Transmitting Configuration

1. **Initialization**: When a client initializes a connection with the server, it can optionally send a configuration message. This message is a JSON object containing key-value pairs representing the client's preferred settings.

2. **JavaScript Client Setup**: On the demo client, the configuration is gathered from the user interface elements (like dropdowns and input fields). Once the Audio starts flowing, a JSON object is created and sent to the server via WebSocket. For example:

```javascript
function sendAudioConfig() {
    const audioConfig = {
        type: 'config',
        data: {
            chunk_length_seconds: 5, 
            chunk_offset_seconds: 1,
            processing_strategy: 1,
            language: language
        }
    };
    websocket.send(JSON.stringify(audioConfig));
}
```

## Testing

When implementing a new ASR, Vad or Buffering Strategy you can test it with:

```bash

ASR_TYPE=faster_whisper ASR_TYPE=faster_whisper  python3 -m unittest test.server.test_server

```

Please make sure that the end variables are in place for example for the VAD auth token. Several other tests are in place, for example for the standalone ASR.

## Areas for Improvement

### Challenges with Small Audio Chunks in Whisper

- **Context Loss**: Shorter audio segments may lack sufficient context, leading Whisper to misinterpret the speech or fail to capture the nuances of the dialogue.
- **Accuracy Variability**: The accuracy of transcription can vary with the length of the audio chunk. Smaller chunks might result in less reliable transcriptions compared to longer segments.

### Dependence on Audio Files

Currently, VoiceStreamAI processes audio by saving chunks to files and then running these files through the models.

## Contributors

This project is open for contributions. Feel free to fork the repository and submit pull requests.
