class VADFactory:
    """
    Factory for creating instances of VAD systems.
    """

    @staticmethod
    def create_vad_pipeline(type, **kwargs):
        """
        Creates a VAD pipeline based on the specified type.

        Args:
            type (str): The type of VAD pipeline to create (e.g., 'pyannote').
            kwargs: Additional arguments for the VAD pipeline creation.

        Returns:
            VADInterface: An instance of a class that implements VADInterface.
        """
        if type == "pyannote":
            from .pyannote_vad import PyannoteVAD

            return PyannoteVAD(**kwargs)
        if type == "silero":
            from .silero_vad import SileroVAD

            return SileroVAD(**kwargs)
        if type in (None, "none"):
            return None
        else:
            raise ValueError(f"Unknown VAD pipeline type: {type}")
