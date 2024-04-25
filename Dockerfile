# Use an NVIDIA CUDA base image with Python 3
FROM nvidia/cuda:11.6.2-cudnn8-runtime-ubuntu20.04

# Set the working directory in the container
WORKDIR /usr/src/app

# Avoid interactive prompts from apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install any needed packages
RUN apt-get update && \
  apt-get install -y python3-pip libsndfile1 ffmpeg && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt file
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code
COPY . .

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME VoiceStreamAI

# Set the entrypoint to your application
ENTRYPOINT ["python3", "-m", "src.main"]

# Provide a default command (can be overridden at runtime)
CMD ["--host", "0.0.0.0", "--port", "80", "--static-path", "./src/static"]
