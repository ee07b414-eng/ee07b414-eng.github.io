#!/usr/bin/env bash
set -euxo pipefail

APP_DIR=/opt/citeguard
REPO_DIR="$APP_DIR/repo"
BACKEND_DIR="$REPO_DIR/citeguard-api/backend"
DOMAIN="101-33-75-222.sslip.io"
EMAIL="ee07b414@gmail.com"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  python3-venv \
  python3-pip \
  nginx \
  curl \
  ca-certificates

sudo mkdir -p "$APP_DIR"
sudo chown -R ubuntu:ubuntu "$APP_DIR"

if [ -d "$REPO_DIR/.git" ]; then
  cd "$REPO_DIR"
  git fetch origin main
  git reset --hard origin/main
else
  git clone https://github.com/ee07b414-eng/ee07b414-eng.github.io.git "$REPO_DIR"
fi

cd "$BACKEND_DIR"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "CITEGUARD_MAILTO=$EMAIL" | sudo tee /etc/citeguard.env >/dev/null

sudo tee /etc/systemd/system/citeguard.service >/dev/null <<EOF
[Unit]
Description=CiteGuard FastAPI backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=/etc/citeguard.env
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now citeguard
sleep 3
sudo systemctl --no-pager --full status citeguard || true
curl -fsS http://127.0.0.1:8000/health

sudo tee /etc/nginx/sites-available/citeguard >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 30m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/citeguard /etc/nginx/sites-enabled/citeguard
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
curl -fsS http://127.0.0.1/health

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect || true

printf '\nCITEGUARD_DEPLOY_DONE\n'
curl -i http://127.0.0.1/health || true
curl -i "https://$DOMAIN/health" || true
