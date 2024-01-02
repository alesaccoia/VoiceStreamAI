from .whisper_asr import WhisperASR

class ASRFactory:
    @staticmethod
    def create_asr_pipeline(type, **kwargs):
        if type == "whisper":
            return WhisperASR(**kwargs)
        else:
            raise ValueError(f"Unknown ASR pipeline type: {type}")
