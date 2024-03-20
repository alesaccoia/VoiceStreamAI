#!/bin/bash

# Define variables
# DOCKER_USERNAME="tyrese3915"
read -p "Enter your Docker Hub username: " DOCKER_USERNAME
IMAGE_NAME="voice-stream-ai"
TAG="latest"

# Step 1: Log in to Docker Hub
echo "Logging in to Docker Hub..."
docker login --username "$DOCKER_USERNAME"
if [ $? -ne 0 ]; then
  echo "Docker login failed. Exiting..."
  exit 1
fi

# Step 2: Build your Docker image
echo "Building the Docker image..."
docker build -t "$IMAGE_NAME:$TAG" .
if [ $? -ne 0 ]; then
  echo "Docker build failed. Exiting..."
  exit 1
fi

# Step 3: Tag the image for your Docker Hub repository
echo "Tagging the image..."
docker tag "$IMAGE_NAME:$TAG" "$DOCKER_USERNAME/$IMAGE_NAME:$TAG"
if [ $? -ne 0 ]; then
  echo "Docker tag failed. Exiting..."
  exit 1
fi

# Step 4: Push the image to Docker Hub
echo "Pushing the image to Docker Hub..."
docker push "$DOCKER_USERNAME/$IMAGE_NAME:$TAG"
if [ $? -ne 0 ]; then
  echo "Docker push failed. Exiting..."
  exit 1
fi

echo "Docker image has been successfully pushed to Docker Hub."
