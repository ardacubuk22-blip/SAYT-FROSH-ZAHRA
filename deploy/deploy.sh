#!/usr/bin/env bash
# Update the server to the latest code from GitHub. Run as root:  sudo /opt/turkiye-discover/deploy/deploy.sh
set -euo pipefail

APP=/opt/turkiye-discover
RUN="sudo -H -u turkiye"

cd "$APP"
echo "== Current version: $($RUN git rev-parse --short HEAD)"
$RUN git pull --ff-only
$RUN .venv/bin/pip install -q -r requirements-server.txt
$RUN .venv/bin/python manage.py migrate --noinput
$RUN .venv/bin/python manage.py collectstatic --noinput -v0
$RUN .venv/bin/python manage.py check --deploy || true
systemctl restart turkiye-discover
echo "== New version: $($RUN git rev-parse --short HEAD)"
echo "To go back to the previous version:  cd $APP && sudo -u turkiye git checkout <old-version> && sudo systemctl restart turkiye-discover"
