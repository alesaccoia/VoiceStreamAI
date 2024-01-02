class ASRInterface:
    async def transcribe(self, client):
        """
        Transcribe the given audio data.

        :param client: The client object with all the member variables including the buffer
        :return: The transcription text.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
