#!/usr/bin/env bash
set -euo pipefail

LOCAL_PORT="${LOCAL_PORT:-3307}"
REMOTE_DB_HOST="${REMOTE_DB_HOST:-sdb-j.hosting.stackcp.net}"
REMOTE_DB_PORT="${REMOTE_DB_PORT:-3306}"
SSH_HOST="${SSH_HOST:-ssh.us.stackcp.com}"
SSH_USER="${SSH_USER:-swateck.com}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519_stackcp}"

exec ssh \
  -i "$SSH_KEY" \
  -N \
  -L "127.0.0.1:${LOCAL_PORT}:${REMOTE_DB_HOST}:${REMOTE_DB_PORT}" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o StrictHostKeyChecking=accept-new \
  "${SSH_USER}@${SSH_HOST}"

