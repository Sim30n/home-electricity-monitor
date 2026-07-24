#!/bin/bash
# Pull-based deploy: fetch origin/master and, when a new commit appears,
# update this clone and run build.sh. Executed periodically by the
# ele_deploy systemd timer (installed by create_service.sh in this
# directory). The last successfully deployed commit is recorded in
# .last_deploy at the repo root; a failed deploy is retried on the next
# timer tick until it succeeds.
set -e

main() {
  REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  STATE_FILE="$REPO_DIR/.last_deploy"
  cd "$REPO_DIR"

  git fetch origin master
  REMOTE=$(git rev-parse origin/master)
  DEPLOYED=$(cat "$STATE_FILE" 2>/dev/null || true)

  if [ "$REMOTE" = "$DEPLOYED" ]; then
    exit 0
  fi

  echo "New commit on origin/master: $REMOTE (last deployed: ${DEPLOYED:-none})"

  # energy_log.txt and price_info.py are tracked in git but written to
  # continuously on this machine (serial logger / daily price cron), so the
  # live copies must survive the reset to origin/master.
  LIVE_BACKUP="$(mktemp -d)"
  cp pulse_sensor/energy_log.txt "$LIVE_BACKUP/" 2>/dev/null || true
  cp web_app/price_info.py "$LIVE_BACKUP/" 2>/dev/null || true

  git checkout -f master
  git reset --hard "$REMOTE"

  if [ -f "$LIVE_BACKUP/energy_log.txt" ]; then
    cp "$LIVE_BACKUP/energy_log.txt" pulse_sensor/energy_log.txt
  fi
  if [ -f "$LIVE_BACKUP/price_info.py" ]; then
    cp "$LIVE_BACKUP/price_info.py" web_app/price_info.py
  fi
  rm -rf "$LIVE_BACKUP"

  if [ -x web_app/venv/bin/pip ]; then
    echo "Updating web app dependencies..."
    web_app/venv/bin/pip install -q -r web_app/requirements.txt
  fi

  ./build.sh

  echo "$REMOTE" > "$STATE_FILE"
  echo "Deployed $REMOTE"
}

# reset --hard rewrites this script on disk mid-run when it changed upstream;
# main is fully parsed before execution starts, and the trailing exit keeps
# bash from reading any further into the (possibly rewritten) file.
main "$@"; exit
