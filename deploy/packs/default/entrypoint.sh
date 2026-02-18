#!/bin/bash
set -euo pipefail

# Generate SSH host keys if missing
ssh-keygen -A

# Inject user's public key
CODER_SSH="/home/coder/.ssh"
mkdir -p "$CODER_SSH"
if [ -n "${MEDFORGE_SSH_PUBLIC_KEY:-}" ]; then
    echo "$MEDFORGE_SSH_PUBLIC_KEY" > "$CODER_SSH/authorized_keys"
    chmod 600 "$CODER_SSH/authorized_keys"
fi
chown -R 1000:1000 "$CODER_SSH"

# Ensure /run/sshd exists
mkdir -p /run/sshd

# Start sshd in foreground (logs to stderr)
exec /usr/sbin/sshd -D -e
