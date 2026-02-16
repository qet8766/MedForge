#!/usr/bin/env bash
#
# One-time ZFS pool and dataset setup for MedForge.
#
# Prerequisites:
#   - ZFS kernel module loaded (modprobe zfs)
#   - Target disks/partitions identified
#
# Edit POOL_DISKS before running.

set -euo pipefail

POOL_NAME="${POOL_NAME:-tank}"
POOL_DISKS="${POOL_DISKS:-}"  # e.g. "/dev/sdb /dev/sdc" — set before running.

if [ -z "$POOL_DISKS" ]; then
  echo "ERROR: Set POOL_DISKS before running (e.g. POOL_DISKS='/dev/sdb' $0)"
  exit 1
fi

# ── Create pool (skip if it already exists) ─────────────────
if ! zpool list "$POOL_NAME" &>/dev/null; then
  # shellcheck disable=SC2086
  zpool create \
    -o ashift=12 \
    -o autotrim=on \
    -O compression=lz4 \
    -O atime=off \
    -O xattr=sa \
    -O dnodesize=auto \
    -O normalization=formD \
    -O relatime=on \
    "$POOL_NAME" $POOL_DISKS
  echo "Pool '$POOL_NAME' created."
else
  echo "Pool '$POOL_NAME' already exists, skipping creation."
fi

# ── Datasets ────────────────────────────────────────────────
for ds in \
  "$POOL_NAME/medforge" \
  "$POOL_NAME/medforge/workspaces" \
  "$POOL_NAME/medforge/system" \
  "$POOL_NAME/medforge/system/db"; do

  if ! zfs list "$ds" &>/dev/null; then
    zfs create "$ds"
    echo "Created dataset $ds"
  fi
done

# MariaDB needs its mount owned by the mysql user (UID 999 in the mariadb:11 image).
chown 999:999 "/$POOL_NAME/medforge/system/db"

echo "ZFS setup complete.  Workspace datasets are created per-session at runtime."
echo "  Workspaces: $POOL_NAME/medforge/workspaces/<user_id>/<session_id>"
echo "  DB:         /$POOL_NAME/medforge/system/db"
