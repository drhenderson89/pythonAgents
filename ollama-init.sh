#!/bin/bash

MODEL="${OLLAMA_MODEL:-qwen2.5:7b-instruct}"

# Start Ollama service in the background
ollama serve &

# Wait for Ollama to be ready
echo "Waiting for Ollama service to start..."
sleep 5

# Check if model exists, if not pull it
echo "Checking if ${MODEL} model exists..."
if ! ollama list | grep -q "${MODEL}"; then
    echo "Model not found. Pulling ${MODEL} (this may take several minutes)..."
    ollama pull "${MODEL}"
    echo "Model downloaded successfully!"
else
    echo "Model already exists, skipping download."
fi

# Keep the container running by waiting on the background process
wait
