#!/usr/bin/env bash
# Install apt packages on a hosted runner without hanging on a stuck mirror:
# no prompts, no man-db rebuild, IPv4 only, and bounded retried attempts.
set -u
export DEBIAN_FRONTEND=noninteractive
sudo rm -f /var/lib/man-db/auto-update
opts=(-o Acquire::ForceIPv4=true -o Acquire::Retries=3 -o Acquire::http::Timeout=30
      -o Acquire::https::Timeout=30 -o Dpkg::Use-Pty=0)
for attempt in 1 2 3; do
  echo "apt attempt $attempt: $*"
  if timeout 180 sudo -E apt-get "${opts[@]}" update -q &&
     timeout 480 sudo -E apt-get "${opts[@]}" install -y -q "$@"; then
    exit 0
  fi
  sudo killall -q apt-get dpkg 2>/dev/null; sudo dpkg --configure -a || true
  sleep $((attempt * 10))
done
echo "::error::apt install failed after 3 attempts"
exit 1
