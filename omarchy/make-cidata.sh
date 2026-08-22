#!/usr/bin/env bash
# Build the Omarchy autoinstall ("cidata") payload for the HP Omen 15-dc0045nr.
#
# Omarchy's ISO skips its wizard entirely when it finds a filesystem labeled
# `cidata`/`CIDATA` carrying user_configuration.json + user_credentials.json
# (verified in omarchy-iso: configs/airootfs/usr/local/bin/omarchy-cidata-load).
# With authorized_keys present it also enables sshd + opens ufw port 22.
#
# Usage (macOS):
#   OMARCHY_PASSWORD='...' ./make-cidata.sh [OUT_DIR]
#   # then copy OUT_DIR/* to the root of a FAT32 USB stick named CIDATA
#
# Nothing here is committed: OUT_DIR defaults to ./out (gitignored).
set -euo pipefail

OUT=${1:-"$(cd "$(dirname "$0")" && pwd)/out"}
USERNAME=${OMARCHY_USERNAME:-austin}
HOSTNAME=${OMARCHY_HOSTNAME:-omen}
TIMEZONE=${OMARCHY_TIMEZONE:-America/Denver}
KEYBOARD=${OMARCHY_KEYBOARD:-us}
FULL_NAME=${OMARCHY_FULL_NAME:-"Austin Griffith"}
EMAIL=${OMARCHY_EMAIL:-austin@ethereum.org}
DISK=${OMARCHY_DISK:-/dev/nvme0n1}
# IDEMA-standard 512 GB drive = 1,000,215,216 sectors × 512. We can't read the
# real size without touching the laptop, so leave a 2 GiB margin under it; the
# btrfs partition can be grown over ssh afterwards (see README).
DISK_BYTES=${OMARCHY_DISK_BYTES:-512110190592}
MARGIN_BYTES=$((2 * 1024 * 1024 * 1024))
PUBKEYS=${OMARCHY_PUBKEYS:-"$HOME/.ssh/id_ed25519.pub"}
TAILSCALE_AUTHKEY=${OMARCHY_TAILSCALE_AUTHKEY:-}

if [[ -z ${OMARCHY_PASSWORD:-} ]]; then
  read -r -s -p "Password for user '$USERNAME' (also root + sudo): " OMARCHY_PASSWORD; echo
fi

OPENSSL=$(command -v openssl)
# macOS LibreSSL lacks `passwd -6`; prefer Homebrew OpenSSL 3.
for cand in /opt/homebrew/opt/openssl@3/bin/openssl /opt/homebrew/bin/openssl; do
  [[ -x $cand ]] && { OPENSSL=$cand; break; }
done
HASH=$("$OPENSSL" passwd -6 "$OMARCHY_PASSWORD")
[[ $HASH == '$6$'* ]] || { echo "openssl passwd -6 failed (need OpenSSL 3: brew install openssl)" >&2; exit 1; }

mib=$((1024 * 1024)); gib=$((mib * 1024))
disk_size_in_mib=$(( (DISK_BYTES - MARGIN_BYTES) / mib * mib ))
boot_start=$mib
boot_size=$((2 * gib))
main_start=$((boot_start + boot_size))
main_size=$((disk_size_in_mib - main_start - mib))

mkdir -p "$OUT"
chmod 700 "$OUT"

# ---- user_configuration.json: exactly what the wizard writes for a full-disk,
# unencrypted install (omarchy-iso configs/airootfs/root/configurator, quattro).
cat >"$OUT/user_configuration.json" <<JSON
{
    "app_config": null,
    "archinstall-language": "English",
    "auth_config": {},
    "audio_config": { "audio": "pipewire" },
    "bootloader_config": { "bootloader": "Limine", "uki": false, "removable": false },
    "custom_commands": [],
    "omarchy_install": {
        "mode": "full_disk",
        "defer_provisioning": false,
        "target_mount": "/mnt",
        "boot": {
            "esp_mount": "/boot",
            "esp_path": "/EFI/limine",
            "efi_binary": "limine_x64.efi",
            "enable_fallback": true
        },
        "storage": { "kernel": "linux" }
    },
    "disk_config": {
        "config_type": "default_layout",
        "device_modifications": [
            {
                "device": "$DISK",
                "partitions": [
                    {
                        "btrfs": [],
                        "dev_path": null,
                        "flags": [ "boot", "esp" ],
                        "fs_type": "fat32",
                        "mount_options": [],
                        "mountpoint": "/boot",
                        "obj_id": "ea21d3f2-82bb-49cc-ab5d-6f81ae94e18d",
                        "size":  { "sector_size": { "unit": "B", "value": 512 }, "unit": "B", "value": $boot_size },
                        "start": { "sector_size": { "unit": "B", "value": 512 }, "unit": "B", "value": $boot_start },
                        "status": "create",
                        "type": "primary"
                    },
                    {
                        "btrfs": [
                            { "mountpoint": "/", "name": "@" },
                            { "mountpoint": "/home", "name": "@home" },
                            { "mountpoint": "/var/log", "name": "@log" },
                            { "mountpoint": "/var/cache/pacman/pkg", "name": "@pkg" }
                        ],
                        "dev_path": null,
                        "flags": [],
                        "fs_type": "btrfs",
                        "mount_options": [ "compress=zstd" ],
                        "mountpoint": null,
                        "obj_id": "8c2c2b92-1070-455d-b76a-56263bab24aa",
                        "size":  { "sector_size": { "unit": "B", "value": 512 }, "unit": "B", "value": $main_size },
                        "start": { "sector_size": { "unit": "B", "value": 512 }, "unit": "B", "value": $main_start },
                        "status": "create",
                        "type": "primary"
                    }
                ],
                "wipe": true
            }
        ]
    },
    "hostname": "$HOSTNAME",
    "kernels": [ "linux" ],
    "network_config": { "type": "iso" },
    "ntp": true,
    "parallel_downloads": 8,
    "script": null,
    "services": [],
    "swap": true,
    "timezone": "$TIMEZONE",
    "locale_config": { "kb_layout": "$KEYBOARD", "sys_enc": "UTF-8", "sys_lang": "en_US.UTF-8" },
    "mirror_config": {
        "custom_repositories": [],
        "custom_servers": [
            {"url": "https://mirror.omarchy.org/\$repo/os/\$arch"},
            {"url": "https://mirror.rackspace.com/archlinux/\$repo/os/\$arch"},
            {"url": "https://geo.mirror.pkgbuild.com/\$repo/os/\$arch"}
        ],
        "mirror_regions": {},
        "optional_repositories": []
    },
    "packages": [ "base-devel", "git", "omarchy-keyring", "omarchy-settings", "omarchy" ],
    "profile_config": { "gfx_driver": null, "greeter": null, "profile": {} },
    "version": "3.0.9"
}
JSON

# ---- user_credentials.json (no encryption_password: unencrypted install)
jq -n --arg h "$HASH" --arg u "$USERNAME" '{
  root_enc_password: $h,
  users: [ { enc_password: $h, groups: [], sudo: true, username: $u } ]
}' >"$OUT/user_credentials.json"

printf '%s\n' "$FULL_NAME" >"$OUT/user_full_name.txt"
printf '%s\n' "$EMAIL"     >"$OUT/user_email_address.txt"
printf 'false\n'           >"$OUT/user_encrypt_installation.txt"

: >"$OUT/authorized_keys"
for k in $PUBKEYS; do cat "$k" >>"$OUT/authorized_keys"; done
[[ -s $OUT/authorized_keys ]] || { echo "no public keys found in: $PUBKEYS" >&2; exit 1; }

if [[ -n $TAILSCALE_AUTHKEY ]]; then
  printf '%s\n' "$TAILSCALE_AUTHKEY" >"$OUT/tailscale_authkey"
else
  rm -f "$OUT/tailscale_authkey"
fi

chmod 600 "$OUT"/*
echo "wrote $(ls "$OUT" | tr '\n' ' ')-> $OUT"
echo "boot=${boot_size}B main=${main_size}B on $DISK (margin $((MARGIN_BYTES/gib)) GiB)"
echo "next: copy these to the root of a FAT32 stick labeled CIDATA (see README.md)"
