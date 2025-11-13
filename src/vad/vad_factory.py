class VADFactory:
    """
    Factory for creating instances of VAD systems.
    """

    @staticmethod
    def create_vad_pipeline(type, **kwargs):
        """
        Creates a VAD pipeline based on the specified type.
        """
        if type == "none" or type is None:
            return None
        else:
            raise ValueError(f"VAD type '{type}' not available. Use 'none' to disable VAD.")