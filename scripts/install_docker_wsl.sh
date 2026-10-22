#!/usr/bin/env bash
# WSL2 Ubuntu에 Docker Engine + compose + NVIDIA Container Toolkit 설치 (Docker Desktop 불필요)
# 사용: WSL Ubuntu 안에서 sudo bash scripts/install_docker_wsl.sh
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
CODENAME=$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $CODENAME stable" \
  > /etc/apt/sources.list.d/docker.list

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor --yes -o /etc/apt/keyrings/nvidia-container-toolkit.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update -q
apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl enable --now docker
systemctl restart docker
[ -n "$SUDO_USER" ] && usermod -aG docker "$SUDO_USER" || true
docker --version && docker compose version
