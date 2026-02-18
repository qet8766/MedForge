#!/usr/bin/env bash
#
# East–west isolation for MedForge session containers.
#
# Drops inter-container SSH traffic (port 22) on the external-sessions bridge,
# preventing one session from reaching another session's sshd directly.
#
# Run once after Docker networks are created (or on boot via systemd).

set -euo pipefail

SESSIONS_BRIDGE="${SESSIONS_BRIDGE:-br-$(docker network inspect medforge-external-sessions -f '{{.Id}}' | head -c 12)}"

# Ensure bridged container traffic is evaluated by iptables.
modprobe br_netfilter
sysctl -w net.bridge.bridge-nf-call-iptables=1 >/dev/null
sysctl -w net.bridge.bridge-nf-call-ip6tables=1 >/dev/null

# Flush any previous MedForge rules.
iptables -D DOCKER-USER -i "$SESSIONS_BRIDGE" -p tcp --dport 22 -j DROP 2>/dev/null || true

# Drop inter-session traffic to port 22 (SSH).
iptables -I DOCKER-USER -i "$SESSIONS_BRIDGE" -p tcp --dport 22 -j DROP

echo "East–west isolation applied (bridge=$SESSIONS_BRIDGE)"
