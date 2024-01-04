# Use an NVIDIA CUDA base image with Python 3
FROM nvidia/cuda:11.6.2-base-ubuntu20.04 

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements.txt file first to leverage Docker cache
COPY requirements.txt ./

# Avoid interactive prompts from apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y python3-pip libsndfile1 ffmpeg && \
    pip3 install --no-cache-dir -r requirements.txt

# Reset the frontend (not necessary in newer Docker versions)
ENV DEBIAN_FRONTEND=newt

# Copy the rest of your application's code
COPY . .

# Make port 8765 available to the world outside this container
EXPOSE 8765

# Define environment variable
ENV NAME VoiceStreamAI

# Set the entrypoint to your application
ENTRYPOINT ["python3", "-m", "src.main"]

# Provide a default command (can be overridden at runtime)
CMD ["--host", "0.0.0.0", "--port", "8765"]

