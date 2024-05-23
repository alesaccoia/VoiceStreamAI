/**
 * VoiceStreamAI Client - WebSocket-based real-time transcription
 *
 * Contributor:
 * - Alessandro Saccoia - alessandro.saccoia@gmail.com
 */

let websocket;
let context;
let processor;
let globalStream;
let language;

const bufferSize = 4096;
let isRecording = false;

function initWebSocket() {
    const websocketAddress = document.getElementById('websocketAddress');
    const selectedLanguage = document.getElementById('languageSelect');
    const websocketStatus = document.getElementById('webSocketStatus');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');

    language = selectedLanguage.value !== 'multilingual' ? selectedLanguage.value : null;

    if (!websocketAddress.value) {
        console.log("WebSocket address is required.");
        return;
    }

    websocket = new WebSocket(websocketAddress.value);
    websocket.onopen = () => {
        console.log("WebSocket connection established");
        websocketStatus.textContent = 'Connected';
        startButton.disabled = false;
    };
    websocket.onclose = event => {
        console.log("WebSocket connection closed", event);
        websocketStatus.textContent = 'Not Connected';
        startButton.disabled = true;
        stopButton.disabled = true;
    };
    websocket.onmessage = event => {
        console.log("Message from server:", event.data);
        const transcript_data = JSON.parse(event.data);
        updateTranscription(transcript_data);
    };
}

function updateTranscription(transcript_data) {
    const transcriptionDiv = document.getElementById('transcription');
    const languageDiv = document.getElementById('detected_language');

    if (transcript_data.words && transcript_data.words.length > 0) {
        // Append words with color based on their probability
        transcript_data.words.forEach(wordData => {
            const span = document.createElement('span');
            const probability = wordData.probability;
            span.textContent = wordData.word + ' ';

            // Set the color based on the probability
            if (probability > 0.9) {
                span.style.color = 'green';
            } else if (probability > 0.6) {
                span.style.color = 'orange';
            } else {
                span.style.color = 'red';
            }

            transcriptionDiv.appendChild(span);
        });

        // Add a new line at the end
        transcriptionDiv.appendChild(document.createElement('br'));
    } else {
        // Fallback to plain text
        transcriptionDiv.textContent += transcript_data.text + '\n';
    }

    // Update the language information
    if (transcript_data.language && transcript_data.language_probability) {
        languageDiv.textContent = transcript_data.language + ' (' + transcript_data.language_probability.toFixed(2) + ')';
    }

    // Update the processing time, if available
    const processingTimeDiv = document.getElementById('processing_time');
    if (transcript_data.processing_time) {
        processingTimeDiv.textContent = 'Processing time: ' + transcript_data.processing_time.toFixed(2) + ' seconds';
    }
}


function startRecording() {
    if (isRecording) return;
    isRecording = true;

    const AudioContext = window.AudioContext || window.webkitAudioContext;
    context = new AudioContext();

    navigator.mediaDevices.getUserMedia({audio: true}).then(stream => {
        globalStream = stream;
        const input = context.createMediaStreamSource(stream);
        processor = context.createScriptProcessor(bufferSize, 1, 1);
        processor.onaudioprocess = e => processAudio(e);

        // chain up the audio graph
        input.connect(processor).connect(context.destination);

        sendAudioConfig();
    }).catch(error => console.error('Error accessing microphone', error));

    // Disable start button and enable stop button
    document.getElementById('startButton').disabled = true;
    document.getElementById('stopButton').disabled = false;
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;

    if (globalStream) {
        globalStream.getTracks().forEach(track => track.stop());
    }
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (context) {
        context.close().then(() => context = null);
    }
    document.getElementById('startButton').disabled = false;
    document.getElementById('stopButton').disabled = true;
}

function sendAudioConfig() {
    let selectedStrategy = document.getElementById('bufferingStrategySelect').value;
    let processingArgs = {};

    if (selectedStrategy === 'silence_at_end_of_chunk') {
        processingArgs = {
            chunk_length_seconds: parseFloat(document.getElementById('chunk_length_seconds').value),
            chunk_offset_seconds: parseFloat(document.getElementById('chunk_offset_seconds').value)
        };
    }

    const audioConfig = {
        type: 'config',
        data: {
            sampleRate: context.sampleRate,
            bufferSize: bufferSize,
            channels: 1, // Assuming mono channel
            language: language,
            processing_strategy: selectedStrategy,
            processing_args: processingArgs
        }
    };

    websocket.send(JSON.stringify(audioConfig));
}

function downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
    if (inputSampleRate === outputSampleRate) {
        return buffer;
    }
    let sampleRateRatio = inputSampleRate / outputSampleRate;
    let newLength = Math.round(buffer.length / sampleRateRatio);
    let result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        let nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
        let accum = 0, count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        result[offsetResult] = accum / count;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

function processAudio(e) {
    const inputSampleRate = context.sampleRate;
    const outputSampleRate = 16000; // Target sample rate

    const left = e.inputBuffer.getChannelData(0);
    const downsampledBuffer = downsampleBuffer(left, inputSampleRate, outputSampleRate);
    const audioData = convertFloat32ToInt16(downsampledBuffer);

    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(audioData);
    }
}

function convertFloat32ToInt16(buffer) {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
        buf[l] = Math.min(1, buffer[l]) * 0x7FFF;
    }
    return buf.buffer;
}

// Initialize WebSocket on page load
//  window.onload = initWebSocket;

function toggleBufferingStrategyPanel() {
    let selectedStrategy = document.getElementById('bufferingStrategySelect').value;
    let panel = document.getElementById('silence_at_end_of_chunk_options_panel');
    if (selectedStrategy === 'silence_at_end_of_chunk') {
        panel.classList.remove('hidden');
    } else {
        panel.classList.add('hidden');
    }
}
