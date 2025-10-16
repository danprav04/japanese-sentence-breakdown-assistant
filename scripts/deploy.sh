#!/bin/bash
# A robust deployment script for the Telegram bot.

# Exit immediately if a command exits with a non-zero status.
# Print each command to the console before it is executed.
set -ex

# --- Configuration Passed as Arguments ---
# These are expected to be passed from the GitHub Actions workflow.
GHCR_USERNAME="$1"
GHCR_PULL_TOKEN="$2"
CONTAINER_NAME="$3"
FULL_IMAGE_URI="$4"
TELEGRAM_BOT_TOKEN="$5"
GEMINI_API_KEY="$6"
GEMINI_VISION_MODEL="$7"
GEMINI_TEXT_MODEL="$8"

# --- Script Logic ---

echo "--- Starting deployment for ${CONTAINER_NAME} ---"

# 1. Log in to GitHub Container Registry
echo "Logging in to GitHub Container Registry..."
echo "${GHCR_PULL_TOKEN}" | sudo docker login ghcr.io -u "${GHCR_USERNAME}" --password-stdin

# 2. Create the systemd service file
# Using a heredoc to write the entire file at once.
# This is clean and prevents quoting issues.
echo "Creating systemd service file at /etc/systemd/system/${CONTAINER_NAME}.service..."
sudo tee "/etc/systemd/system/${CONTAINER_NAME}.service" > /dev/null << EOT
[Unit]
Description=${CONTAINER_NAME} Docker Container
Requires=docker.service
After=docker.service network.target

[Service]
Restart=always
RestartSec=10

# Environment variables for the bot application
Environment="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}"
Environment="GEMINI_API_KEY=${GEMINI_API_KEY}"
Environment="GEMINI_VISION_MODEL=${GEMINI_VISION_MODEL}"
Environment="GEMINI_TEXT_MODEL=${GEMINI_TEXT_MODEL}"

# Service commands
ExecStartPre=-/usr/bin/docker stop ${CONTAINER_NAME}
ExecStartPre=-/usr/bin/docker rm ${CONTAINER_NAME}
ExecStartPre=/usr/bin/docker pull ${FULL_IMAGE_URI}
ExecStart=/usr/bin/docker run --rm --name ${CONTAINER_NAME} \
  -e TELEGRAM_BOT_TOKEN \
  -e GEMINI_API_KEY \
  -e GEMINI_VISION_MODEL \
  -e GEMINI_TEXT_MODEL \
  ${FULL_IMAGE_URI}
ExecStop=/usr/bin/docker stop ${CONTAINER_NAME}

[Install]
WantedBy=multi-user.target
EOT

# 3. Reload systemd and restart the service
echo "Reloading systemd and restarting the service..."
sudo systemctl daemon-reload
sudo systemctl enable "${CONTAINER_NAME}.service"
sudo systemctl restart "${CONTAINER_NAME}.service"

echo "--- Deployment of ${CONTAINER_NAME} finished successfully. ---"