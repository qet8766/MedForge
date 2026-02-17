#!/usr/bin/env bash
#
# East–west isolation for MedForge session containers.
#
# Allows only Caddy (CADDY_IP) to reach port 8080 on the external-sessions
# bridge.  All other inter-container traffic to 8080 is dropped, preventing
# one session from reaching another session's code-server directly.
#
# Run once after Docker networks are created (or on boot via systemd).

set -euo pipefail

CADDY_IP="${CADDY_IP:-172.30.0.2}"
SESSIONS_BRIDGE="${SESSIONS_BRIDGE:-br-$(docker network inspect medforge-external-sessions -f '{{.Id}}' | head -c 12)}"

# Ensure bridged container traffic is evaluated by iptables.
modprobe br_netfilter
sysctl -w net.bridge.bridge-nf-call-iptables=1 >/dev/null
sysctl -w net.bridge.bridge-nf-call-ip6tables=1 >/dev/null

# Flush any previous MedForge rules.
iptables -D DOCKER-USER -i "$SESSIONS_BRIDGE" -p tcp --dport 8080 -s "$CADDY_IP" -j ACCEPT 2>/dev/null || true
iptables -D DOCKER-USER -i "$SESSIONS_BRIDGE" -p tcp --dport 8080 -j DROP 2>/dev/null || true

# Allow Caddy → session containers on 8080.
iptables -I DOCKER-USER -i "$SESSIONS_BRIDGE" -p tcp --dport 8080 -s "$CADDY_IP" -j ACCEPT

# Drop everything else → session containers on 8080.
iptables -I DOCKER-USER 2 -i "$SESSIONS_BRIDGE" -p tcp --dport 8080 -j DROP

echo "East–west isolation applied (bridge=$SESSIONS_BRIDGE, caddy=$CADDY_IP)"
