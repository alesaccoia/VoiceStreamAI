class RealtimeAudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
    }

    process(inputs, outputs, params) {
        // ASR and VAD models typically require a mono audio.
        this.port.postMessage(inputs[0][0]);
        return true;
    }
}

registerProcessor('realtime-audio-processor', RealtimeAudioProcessor);
