#!/bin/bash

set -euxo pipefail

# Update system
dnf update -y

# Install Docker
dnf install -y docker

# Start Docker
systemctl enable docker
systemctl start docker

# Add ec2-user to docker group
usermod -aG docker ec2-user

# Create application directory
mkdir -p /opt/konnect
chown -R ec2-user:ec2-user /opt/konnect

# Save image name
echo "${docker_image}" > /opt/konnect/docker-image.txt

# Pull the latest application image
docker pull "${docker_image}"

# Remove an old container if one exists
docker rm -f konnect 2>/dev/null || true

# Start Konnect
docker run -d \
  --name konnect \
  --restart unless-stopped \
  -p 8000:80 \
  "${docker_image}"