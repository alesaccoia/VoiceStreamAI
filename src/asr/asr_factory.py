class ASRFactory:
    @staticmethod
    def create_asr_pipeline(asr_type, **kwargs):
        if asr_type == "whisper":
            from .whisper_asr import WhisperASR

            return WhisperASR(**kwargs)
        if asr_type == "faster_whisper":
            from .faster_whisper_asr import FasterWhisperASR

            return FasterWhisperASR(**kwargs)
        else:
            raise ValueError(f"Unknown ASR pipeline type: {asr_type}")
