# VoiceStreamAI: near-realtime voice transcription through WebSocket with a self-hosted Whisper model

VoiceStreamAI is a Python 3 -based server and JavaScript client solution that enables near-realtime audio streaming and transcription using WebSocket. The system employs Huggingface's Voice Activity Detection (VAD) and OpenAI's Whisper model for accurate speech recognition and processing.

## Features

- Real-time audio streaming through WebSocket.
- Voice activity detection using Huggingface's VAD.
- Speech transcription using OpenAI's Whisper model.
- Customizable audio chunk processing.
- Support for multilingual transcription.

## Installation

To set up the VoiceStreamAI server, you need Python 3.8 or later and the following packages:

1. `transformers`
2. `pyannote.core`
3. `pyannote.audio`
4. `websockets`

Install these packages using pip:

```bash
pip install transformers pyannote.core pyannote.audio websockets
```

For the client-side, you need a modern web browser with JavaScript support.

## Server Setup

1. Clone the repository.
2. Navigate to the project directory.
3. Obtain the key to the Voice-Activity-Detection model at [https://huggingface.co/pyannote/segmentation](https://huggingface.co/pyannote/segmentation)
4. Replace the placeholder in VAD_AUTH_TOKEN with the key you've obtained
5. Run the server using Python 3.x:

```bash
python server.py
```

## Client Usage

1. Open the `client/VoiceStreamAI_Client.html` file in a web browser.
2. Enter the WebSocket address (default is `ws://localhost:8765`).
3. Configure the audio chunk length and offset. See below.
4. Select the language for transcription.
5. Click 'Connect' to establish a WebSocket connection.
6. Use 'Start Streaming' and 'Stop Streaming' to control audio capture.

![Client Demo](/img/client.png "Client Demo")

## Technology Overview

- **Python Server**: Manages WebSocket connections, processes audio streams, and handles voice activity detection and transcription.
- **WebSockets**: Used for real-time communication between the server and client.
- **Voice Activity Detection**: Detects voice activity in the audio stream to optimize processing.
- **Speech-to-Text**: Utilizes OpenAI's Whisper model (openai/whisper-large-v3) for accurate transcription.

## Technical Overview

### Voice Activity Detection (VAD)

Voice Activity Detection (VAD) in VoiceStreamAI enables the system to distinguish between speech and non-speech segments within an audio stream. The primary purpose of implementing VAD is to enhance the efficiency and accuracy of the speech-to-text process:

- **Reduces Computational Load**: By identifying and processing only those segments that contain speech, VAD significantly reduces the computational resources required for transcription. This is important considering that the speech recognition pipeline takes 7 seconds on a Tesla T4 (16Gb) - take this into consideration when setting the chunk length.
- **Improves Transcription Accuracy**: Processing only the voice segments minimizes the chances of non-speech noises being misinterpreted as speech, thus improving the overall accuracy of the transcription.
- **Optimizes Network Utilization**: In a streaming context, sending only voice segments over the network, as opposed to the entire audio stream, optimizes bandwidth usage.

VoiceStreamAI uses a Huggingface VAD model to ensure reliable detection of speech in diverse audio conditions.

### Buffering Strategy

The buffering strategy is designed to balance between near-real-time processing and ensuring complete and accurate capture of speech segments. Here’s how buffering is managed:

- **Chunk-Based Processing**: The audio stream is processed into chunks of a per-client customizable length (defaults to 5 seconds)
- **Silence Handling**: A minimum silence offset is defined to allow for continuous listening and capturing audio beyond the end of a single chunk. This ensures that words at the boundary of chunks are not cut off, thereby maintaining the context and completeness of speech. This introduces extra latency for very dense parts of speech, as the transciprion will not take place until a pause is identified.
- **Dynamic Buffer Management**: The system dynamically manages buffers for each client. When new audio data arrives, it is appended to the client's temporary buffer. Once a buffer reaches the chunk length, it is processed, and the buffer is cleared, ready for new data.

![Buffering Mechanism](/img/vad.png "Chunking and Silence Handling")

### Client-Specific Configuration Messaging

In VoiceStreamAI, each client can have a unique configuration that tailors the transcription process to their specific needs. This personalized setup is achieved through a messaging system where the JavaScript client sends configuration details to the Python server. This section explains how these configurations are structured and transmitted.

The client configuration can include various parameters such as language preference, chunk length, and chunk offset. For instance:

- `language`: Specifies the language for transcription. If set to anything other than "multilanguage" it will force the Whisper inference to be in that language
- `chunk_length_seconds`: Defines the length of each audio chunk to be processed.
- `chunk_offset_seconds`: Determines the silence time at the end of each chunk needed to process audio

### Transmitting Configuration

1. **Initialization**: When a client initializes a connection with the server, it can optionally send a configuration message. This message is a JSON object containing key-value pairs representing the client's preferred settings.

2. **JavaScript Client Setup**: On the demo client, the configuration is gathered from the user interface elements (like dropdowns and input fields). Once the Audio starts flowing, a JSON object is created and sent to the server via WebSocket. For example:

```javascript
function sendAudioConfig() {
    const audioConfig = {
        type: 'config',
        data: {
            sampleRate: context.sampleRate,
            bufferSize: bufferSize,
            channels: 1, // Assuming mono channel
            chunk_length_seconds: chunk_length_seconds, 
            chunk_offset_seconds: chunk_offset_seconds,
            language: language
        }
    };
    websocket.send(JSON.stringify(audioConfig));
}

## Areas for Improvement

### Challenges with Small Audio Chunks in Whisper

- **Context Loss**: Shorter audio segments may lack sufficient context, leading Whisper to misinterpret the speech or fail to capture the nuances of the dialogue.
- **Accuracy Variability**: The accuracy of transcription can vary with the length of the audio chunk. Smaller chunks might result in less reliable transcriptions compared to longer segments.

### Dependence on Audio Files

Currently, VoiceStreamAI processes audio by saving chunks to files and then running these files through the models. 

## Contributors

This project is open for contributions. Feel free to fork the repository and submit pull requests.

## License

VoiceStreamAI is open-sourced under the MIT License.

