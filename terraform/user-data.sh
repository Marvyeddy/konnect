#!/bin/bash

set -euxo pipefail

dnf update -y

dnf install -y docker

systemctl enable docker
systemctl start docker

usermod -aG docker ec2-user

mkdir -p /opt/konnect

chown -R ec2-user:ec2-user /opt/konnect

echo "${docker_image}" > /opt/konnect/docker-image.txt