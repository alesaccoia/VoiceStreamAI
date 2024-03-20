# Use an NVIDIA CUDA base image with Python 3
FROM nvidia/cuda:11.6.2-base-ubuntu20.04

# Set the working directory in the container
WORKDIR /usr/src/app

# Avoid interactive prompts from apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install any needed packages
RUN apt-get update && apt-get install -y python3-pip libsndfile1 ffmpeg wget dpkg
RUN wget https://github.com/TyreseDev/nvidia-cucnn/releases/download/v0.0.1/cudnn-local-repo-ubuntu2004-8.9.7.29_1.0-1_amd64.deb && \
  dpkg -i cudnn-local-repo-ubuntu2004-8.9.7.29_1.0-1_amd64.deb && \
  cp /var/cudnn-local-repo-ubuntu2004-8.9.7.29/cudnn-*-keyring.gpg /usr/share/keyrings/ && \
  apt-get update && apt-get -y install libcudnn8 libcudnn8-dev && \
  rm -f cudnn-local-repo-ubuntu2004-8.9.7.29_1.0-1_amd64.deb && \
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
