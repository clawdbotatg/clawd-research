# Omarchy on the HP Omen 15-dc0045nr — zero-touch install runbook

**Goal:** plug in USB, tap a couple of keys, walk away; come back to an Omarchy
box with sshd up and Claude's key authorized. Researched 2026-08-22 against
**Omarchy 4.0.0 "Quattro"** (tagged 2026-08-14) and the `omarchy-iso` quattro
branch source.

## TLDR

Omarchy's ISO has a built-in **unattended mode**: if it finds any filesystem
labeled `cidata` (or `CIDATA`) carrying the wizard's own output files, it
**skips the wizard, installs, enables sshd + opens ufw 22 (if `authorized_keys`
is present), and reboots itself** — no keypress at all. So the whole job is:

1. **Mac (Claude does it):** write `omarchy-4.0.0.iso` to USB stick A; format
   USB stick B as FAT32 named `CIDATA` and drop `make-cidata.sh`'s output on it.
2. **Laptop (Austin, ~2 min of typing):** plug Ethernet + both sticks →
   `F10` → disable Secure Boot → save → type the 4-digit HP confirmation code →
   `F9` → pick the USB → walk away.
3. **~5–10 min later:** it reboots into Omarchy's login screen. `ssh austin@omen`
   works. Claude takes it from there (WiFi, growing the partition, whatever).

Manual keypresses total: F10, two arrow/enter taps for Secure Boot, F10 to
save, a 4-digit code, F9, one menu pick. That's the floor — Secure Boot can't
be turned off from the outside, and archiso's grub isn't MS-signed.

## The laptop

HP Omen 15-dc0045nr (2018): i7-8750H (Intel UHD 630 iGPU) + **GTX 1070 Max-Q
(Pascal)**, 32 GB, 512 GB NVMe, Intel AC 9560 WiFi (iwlwifi, fine), **gigabit
RJ-45 port** (use it — the unattended install can't carry WiFi creds; DHCP via
NetworkManager is automatic on wired).

### The one real hardware gotcha — and it's already handled in 4.0.0
NVIDIA's 590 driver dropped Pascal; Arch's main `nvidia`/`nvidia-dkms`
packages switched to the open kernel modules, which can't drive a GTX 10xx.
Omarchy issue #3954 was the installer picking an unusable driver for exactly
these cards. **Quattro's `install/hardware/nvidia.sh` fixes it**: it probes
for GSP firmware (`omarchy-hw-nvidia-gsp` / `-without-gsp`), and a Pascal
GPU lands on `nvidia-580xx-dkms` + `nvidia-580xx-utils` (+ lib32), all
**bundled in the ISO's offline mirror** (`install/omarchy-other.packages`),
with the early-KMS modprobe/mkinitcpio drop-ins written for you. The test
file `test/shell.d/hw-nvidia-test.sh` explicitly asserts "GP104 [GTX 1080]
→ without-gsp". Worst case if it ever misfires: the Intel iGPU drives the
panel on this hybrid laptop and Hyprland still comes up — fixable over ssh.

### BIOS (HP)
- `F10` on power-on → BIOS Setup. `System Configuration` → `Boot Options` →
  **Secure Boot: Disabled**. Leave Legacy Support **off** (UEFI boot is what
  we want; archiso boots fine via grub on UEFI). `F10` → Yes to save.
- On the reboot HP shows a blue **"Operating System Boot Mode Change"**
  screen with a random 4-digit code — type it and press Enter, or the change
  is discarded. (The manual's "and/or TPM" note is irrelevant; TPM can stay.)
- `F9` on power-on → Boot Device Options → pick the `UEFI - <stick name>`
  entry. This is a one-time pick; permanent boot order is unchanged, so the
  post-install reboot lands on the new Limine entry, not back on the USB.
- If the NVMe doesn't show up at all in the installer (unlikely on the
  SSD-only 045nr config, but some dc0 SKUs shipped with Intel RST/Optane):
  BIOS → Advanced → System Options → uncheck "Configure Storage Controller for
  Intel Optane" / set SATA to AHCI.

## How the autoinstall works (from source, so it's not a guess)

`configs/airootfs/root/.automated_script.sh` runs on tty1 at boot → calls
`/usr/local/bin/omarchy-cidata-load`, which `udevadm settle`s, looks for
`/dev/disk/by-label/cidata` or `CIDATA`, mounts it read-only, and copies the
files into `/root`. If `user_configuration.json` + `user_credentials.json` are
both there it exits 0 → wizard skipped, `OMARCHY_UI_INTERACTIVE=no` → the
dashboard's `reboot_prompt` returns immediately → **auto-reboot on success**.
Anything less than that pair → the normal wizard runs (safe fallback).

Files it consumes (all in the label root, no subdirectory):

| file | required | what |
|---|---|---|
| `user_configuration.json` | yes | archinstall config: disk layout, hostname, tz, keyboard, packages |
| `user_credentials.json` | yes | username + `$6$` SHA-512 hash (also used for root) |
| `authorized_keys` | no | → `~/.ssh/authorized_keys`, `systemctl enable sshd`, `ufw allow ssh`. **Empty/invalid file fails the install.** |
| `tailscale_authkey` | no | installs tailscale from the bundled mirror, joins on first network |
| `user_full_name.txt` / `user_email_address.txt` | no | git identity |
| `user_encrypt_installation.txt` | no | `true` only if the config has a `disk_encryption` block |

"Any filesystem with the right label works" — so **stick B is just a FAT32
USB drive that macOS named `CIDATA`** (the loader accepts upper-case; FAT
labels are upper-cased anyway). No genisoimage needed.

### Decisions baked into `make-cidata.sh`
- **Unencrypted.** Encrypted autoinstalls still need a human at the LUKS
  prompt on every boot — useless for a box Claude drives remotely. Side effect:
  unencrypted installs get the SDDM login screen instead of autologin (fine;
  ssh doesn't care).
- **Full-disk wipe of `/dev/nvme0n1`**, the wizard's exact layout: 2 GiB
  FAT32 ESP at `/boot` (Limine) + btrfs `@ @home @log @pkg` with `compress=zstd`,
  zram swap. The config carries **absolute byte sizes**, and we can't read the
  drive's true size from here, so the script assumes the IDEMA-standard 512 GB
  (512,110,190,592 B) **minus a 2 GiB margin**. Too small is harmless; too big
  would fail archinstall. Reclaim it afterwards over ssh:
  `sudo growpart /dev/nvme0n1 2 && sudo btrfs filesystem resize max /`
  (or `OMARCHY_DISK_BYTES=<lsblk -bdno SIZE>` and regenerate if you ever know
  the real number).
- **Kernel `linux`** (the wizard only picks `linux-t2` on T2 Macs).
- **user `austin`, host `omen`, tz `America/Denver`, kb `us`** — all
  overridable via `OMARCHY_*` env vars (see script header).
- **SSH key:** `~/.ssh/id_ed25519.pub` from this Mac (the key `ssh` uses by
  default, so Claude's shell sessions connect with no config). Add more with
  `OMARCHY_PUBKEYS="a.pub b.pub"`.
- Password hash via Homebrew OpenSSL 3 (`/opt/homebrew/opt/openssl@3`) —
  macOS's LibreSSL has no `passwd -6`, and Python 3.13 dropped `crypt`.

## Step-by-step

### A. On the Mac (Claude, except the two `sudo`s)
```bash
cd ~/clawd/clawd-harness/projects/clawd-research/omarchy
curl -LO https://iso.omarchy.org/omarchy-4.0.0.iso          # ~5.5 GB

# stick A = the ISO. find it:
diskutil list external                                        # e.g. /dev/disk4
diskutil unmountDisk /dev/disk4
sudo dd if=omarchy-4.0.0.iso of=/dev/rdisk4 bs=4m status=progress   # Austin: `! sudo dd …`
diskutil eject /dev/disk4

# stick B = cidata (any size, even 1 GB). MBR+FAT32, label CIDATA:
diskutil eraseDisk FAT32 CIDATA MBRFormat /dev/disk5
OMARCHY_PASSWORD='…' ./make-cidata.sh /Volumes/CIDATA         # or let it prompt
diskutil eject /dev/disk5
```
(macOS may pop "The disk you attached was not readable" after `dd` — that's
the Linux partitions; click Ignore/Eject.) Omarchy's site publishes no
checksum; if you want one, `shasum -a 256 omarchy-4.0.0.iso` and compare
against the GitHub release notes if they ever add it.

### B. On the laptop (Austin)
1. Ethernet cable in. Both sticks in. Power button.
2. Tap `F10` → BIOS → System Configuration → Boot Options → Secure Boot
   **Disabled** → `F10` save/exit.
3. Blue "Operating System Boot Mode Change" screen → type the 4 digits → Enter.
4. Tap `F9` → pick `UEFI - <stick A>` → Enter.
5. Grub auto-selects Omarchy in ~15 s; the dashboard shows "Autoinstall
   configuration found on cidata drive; skipping the configurator." Walk away.
6. ~5–10 min: black screen → reboot → Omarchy login (SDDM). Pull both sticks
   whenever convenient (the install is done once you see the login screen).

### C. Back on the Mac
```bash
ssh austin@omen.local        # or the DHCP IP from the router; key auth, no password
```
Then, over ssh, Claude can: `nmcli dev wifi connect <ssid> password <pw>`,
`growpart`/`btrfs resize` (above), `omarchy-update`, add the box to the
fleet, etc.

## If something goes sideways
- **Wizard appears instead of auto-install** → cidata wasn't found or a
  required file is missing. Check the label (`lsblk -o NAME,LABEL` from
  ctrl-alt-F2) and that the files sit at the stick's root, not in a folder.
- **Install fails** → the dashboard shows a failure menu with a log tail;
  full log at `/var/log/omarchy-install.log` on the live system (and copied to
  `/mnt/var/log/` on the target if it got that far). Disk-size too large is
  the only config-side failure I'd expect; drop `OMARCHY_DISK_BYTES` and regen.
- **It boots the USB again after install** (wrong permanent boot order) →
  pull stick B first; stick A alone just shows the wizard, which is harmless;
  then F9 → "OS Boot Manager" / the Limine entry, or reorder in F10.
- **Re-running the autoinstall re-wipes the disk** — by design. Don't leave
  stick B plugged into a machine you care about.

## Alternatives considered
- **Single USB stick** (ISO + a trailing `cidata` partition): the archiso
  image is a hybrid MBR/GPT, so it's doable with `sgdisk -e -n 0:0:0 -c
  0:cidata` + `newfs_msdos` on the new slice — but macOS lacks `sgdisk`
  (brew `gptfdisk`) and it's partition surgery on a freshly dd'd image for no
  gain. Two sticks is strictly simpler and what the format was designed for.
- **`genisoimage`/`hdiutil makehybrid` cidata.iso**: what the docs show, for
  VMs (Proxmox/libvirt attach it as a CD). A FAT stick is the same thing to
  the loader.
- **Tailscale** (`OMARCHY_TAILSCALE_AUTHKEY=tskey-auth-…`): worth adding if
  you want the Omen reachable from the fleet/relay box, not just this LAN.
  Needs a reusable pre-authorized key from the tailnet admin console.
- **Deferred provisioning** (`defer-provisioning` marker, no credentials):
  imaging-rig mode, user created at first boot — wrong for us, we want ssh
  from minute one.

## Sources
- omarchy.org (download: https://iso.omarchy.org/omarchy-4.0.0.iso)
- https://omarchy.org/manual/unattended-installs/
- https://github.com/omacom-io/omarchy-iso (quattro) — `README.md`,
  `configs/airootfs/usr/local/bin/omarchy-cidata-load`,
  `configs/airootfs/root/.automated_script.sh`, `configs/airootfs/root/configurator`
  (the JSON template), `orchestrator/phases_impl.py::configure_ssh_access`
- https://github.com/basecamp/omarchy (quattro) — `install/hardware/nvidia.sh`,
  `install/omarchy-other.packages`, `test/shell.d/hw-nvidia-test.sh`
- https://github.com/basecamp/omarchy/issues/3954 (Pascal driver bug)
- https://archlinux.org/news/nvidia-590-driver-drops-pascal-support-main-packages-switch-to-open-kernel-modules/
- HP: https://support.hp.com/us-en/document/ish_6930187-6931079-16 (Secure Boot + 4-digit code),
  https://h30434.www3.hp.com/t5/Unanswered-Topics-Gaming/How-to-boot-from-USB-in-HP-OMEN-15-DC-dc-series-laptop/td-p/6895958 (F9/F10)
- Specs: https://support.hp.com/us-en/product/omen-by-hp-15-dc0000-laptop-pc/20329817/model/24514934/document/c06177240
