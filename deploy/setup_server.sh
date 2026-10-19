#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 server. Run as root:
#   sudo bash setup_server.sh git@github.com:OWNER/REPO.git [domain.example.com]
# Without a domain the site is served over plain HTTP on the server's IP (fine for a first test).
set -euo pipefail

REPO="${1:?Usage: setup_server.sh <git-ssh-url> [domain]}"
DOMAIN="${2:-}"
APP=/opt/turkiye-discover
RUN="sudo -H -u turkiye"

echo "== 1/8 Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3-venv python3-pip postgresql git caddy

echo "== 2/8 Creating the application user"
id turkiye >/dev/null 2>&1 || adduser --system --group --home "$APP" --shell /bin/bash turkiye

echo "== 3/8 Creating the PostgreSQL database"
runuser -u postgres -- psql -tc "SELECT 1 FROM pg_roles WHERE rolname='turkiye'" | grep -q 1 \
  || runuser -u postgres -- createuser turkiye
runuser -u postgres -- psql -tc "SELECT 1 FROM pg_database WHERE datname='turkiye_discover'" | grep -q 1 \
  || runuser -u postgres -- createdb -O turkiye turkiye_discover

echo "== 4/8 Getting the code from GitHub (read-only deploy key)"
mkdir -p "$APP/.ssh" && chown turkiye:turkiye "$APP/.ssh" && chmod 700 "$APP/.ssh"
if [ ! -f "$APP/.ssh/id_ed25519" ]; then
  $RUN ssh-keygen -t ed25519 -N "" -f "$APP/.ssh/id_ed25519" -C "turkiye-discover-server" >/dev/null
fi
$RUN ssh-keyscan -t ed25519 github.com >> "$APP/.ssh/known_hosts" 2>/dev/null
if ! $RUN git ls-remote "$REPO" >/dev/null 2>&1; then
  echo
  echo "GitHub: repository -> Settings -> Deploy keys -> Add deploy key (leave 'write access' OFF)."
  echo "Paste this key:"
  echo
  cat "$APP/.ssh/id_ed25519.pub"
  echo
  read -r -p "When you have added it, press Enter... " _
fi
if [ ! -d "$APP/.git" ]; then
  $RUN git clone "$REPO" "$APP/.clone"
  $RUN cp -a "$APP/.clone/." "$APP/"
  rm -rf "$APP/.clone"
fi

echo "== 5/8 Python environment"
$RUN python3 -m venv "$APP/.venv"
$RUN "$APP/.venv/bin/pip" install -q -r "$APP/requirements-server.txt"

echo "== 6/8 Settings file (.env)"
if [ ! -f "$APP/.env" ]; then
  SECRET=$($RUN "$APP/.venv/bin/python" -c "import secrets; print(secrets.token_urlsafe(50))")
  if [ -n "$DOMAIN" ]; then
    HOSTS="$DOMAIN"; ORIGINS="https://$DOMAIN"; SSL="True"
  else
    HOSTS="*"; ORIGINS="http://$(hostname -I | awk '{print $1}')"; SSL="False"
  fi
  cat > "$APP/.env" <<ENV
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=$SECRET
DJANGO_ALLOWED_HOSTS=$HOSTS
DJANGO_CSRF_TRUSTED_ORIGINS=$ORIGINS
DJANGO_SSL_REDIRECT=$SSL
DATABASE_URL=postgres:///turkiye_discover
ANTHROPIC_API_KEY=
MONTHLY_API_BUDGET_USD=10
REVIEW_CONFIDENCE_THRESHOLD=0.75
CRAWLER_DELAY_SECONDS=3
WHATSAPP_NUMBER=PHONE_NUMBER
ENV
  chown turkiye:turkiye "$APP/.env" && chmod 600 "$APP/.env"
fi

echo "== 7/8 Database tables and static files"
$RUN "$APP/.venv/bin/python" "$APP/manage.py" migrate --noinput
$RUN "$APP/.venv/bin/python" "$APP/manage.py" collectstatic --noinput -v0

echo "== 8/8 Services (website, daily collection, daily backup, HTTPS)"
chmod +x "$APP"/deploy/*.sh
cp "$APP"/deploy/turkiye-discover*.service "$APP"/deploy/turkiye-discover*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now turkiye-discover.service turkiye-discover-collect.timer turkiye-discover-backup.timer
sed "s/^SITE /${DOMAIN:-:80} /" "$APP/deploy/Caddyfile.template" > /etc/caddy/Caddyfile
systemctl restart caddy

echo
echo "Done. Next steps:"
echo "  1) Create the admin account:  sudo -u turkiye $APP/.venv/bin/python $APP/manage.py createsuperuser"
echo "  2) Put the WhatsApp number and (later) the API key in $APP/.env, then:  sudo systemctl restart turkiye-discover"
echo "  3) Open the site${DOMAIN:+ at https://$DOMAIN} and check /healthz/"
