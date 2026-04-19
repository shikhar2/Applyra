#!/bin/bash
set -e

# One-shot setup script for Oracle Cloud Free Tier (Ubuntu 22.04 ARM)
# Run as: curl -fsSL <raw-github-url>/scripts/setup_oracle.sh | bash
# Or: bash scripts/setup_oracle.sh

REPO_URL="https://github.com/shikhar2/Applyra.git"
APP_DIR="/opt/applyra"

echo "==> Installing Docker..."
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker

echo "==> Installing Docker Compose plugin..."
sudo apt-get install -y docker-compose-plugin

echo "==> Cloning Applyra..."
sudo git clone "$REPO_URL" "$APP_DIR" || (cd "$APP_DIR" && sudo git pull)
sudo chown -R "$USER:$USER" "$APP_DIR"
cd "$APP_DIR"

echo "==> Creating .env file..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "*** Edit $APP_DIR/.env and add your API keys, then re-run: ***"
  echo "    cd $APP_DIR && docker compose up -d"
  echo ""
  echo "Required keys to set in .env:"
  echo "  GEMINI_API_KEY=...   (free at aistudio.google.com)"
  echo "  SECRET_KEY=$(openssl rand -hex 32)"
  echo ""
else
  echo ".env already exists, skipping."
fi

echo "==> Opening firewall port 80..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || true

echo ""
echo "==> Done! Next steps:"
echo "  1. Edit /opt/applyra/.env with your API keys"
echo "  2. Run: cd /opt/applyra && docker compose up -d"
echo "  3. Also open port 80 in Oracle Cloud Security List (see README)"
echo ""
