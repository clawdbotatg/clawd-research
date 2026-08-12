# Let's Encrypt TLS certs for bare IP addresses

**Status: tested live on zkllmapi (2026-08-12). `https://174.129.67.164` serves a
publicly-trusted cert — `curl` verifies with no `-k`.**

## The feature

- Let's Encrypt issues certs with an **IP address SAN** (IPv4 or IPv6, no domain
  needed). First cert July 2025, **generally available since 2026-01-15**.
- IP certs **require the `shortlived` ACME profile**: 160-hour (~6.6 day)
  validity, non-negotiable. Rationale: IPs change hands fast (DHCP, cloud
  reassignment), so long-lived certs are too risky. Short-lived certs also ship
  with no OCSP/CRL revocation — they just expire.
- Challenges: **http-01 or tls-alpn-01 only**. There is no dns-01 for an IP.
- The cert's subject is empty (no CN); the identity lives entirely in the
  `IP Address:` SAN.

## Tooling requirements

- **certbot ≥ 5.3** for the `--ip-address` flag (≥ 5.4 for webroot with IPs);
  `--preferred-profile` landed in 4.0. Ubuntu 24.04 apt ships 2.9.0 — too old.
- The nginx and apache certbot plugins do **not** support IP certs yet; use
  `--webroot`, `--standalone`, or `--manual`.

## What's deployed on zkllmapi (174.129.67.164)

Isolated from the apt certbot that renews the box's 9 production domain certs —
separate binary, separate config dir, separate cron. The two never interact.

| piece | where |
|---|---|
| certbot 5.7.0 venv | `/opt/certbot-ip/bin/certbot` |
| config/live certs | `/etc/letsencrypt-ip/live/174.129.67.164/` |
| nginx vhost | `/etc/nginx/sites-enabled/ip-cert` |
| renewal cron (6h) | `/etc/cron.d/certbot-ip` |
| reload on renew | `renew_hook = systemctl reload nginx` (in the renewal conf) |

Issuance command:

```bash
/opt/certbot-ip/bin/certbot certonly --webroot -w /var/www/html \
  --ip-address 174.129.67.164 --preferred-profile shortlived \
  --config-dir /etc/letsencrypt-ip --work-dir /var/lib/letsencrypt-ip \
  --logs-dir /var/log/letsencrypt-ip \
  --non-interactive --agree-tos --register-unsafely-without-email \
  --deploy-hook "systemctl reload nginx"
```

## The two gotchas

1. **No SNI for IP literals.** Clients connecting to `https://<ip>` send no SNI
   (RFC 6066 forbids IPs there), so nginx can't route by `server_name` — the
   IP-cert vhost must be `listen 443 ssl default_server`. Before this, a no-SNI
   connection got whichever 443 vhost loaded first (agent.denar.ai's cert →
   browser warning). Domain vhosts are unaffected; they still match by SNI.
2. **Renewal cadence is real.** A 160h cert means certbot renews roughly every
   4.5 days (at ~1/3 lifetime left). The apt certbot timer can't see the
   isolated config dir, so the dedicated `/etc/cron.d/certbot-ip` (every 6h,
   idempotent `renew`) is load-bearing — remove it and the IP cert dies within
   a week. `renew --dry-run` verified green.

## When this is useful

Homelabs, ephemeral boxes, DoH/DoT endpoints, bootstrapping (serve HTTPS before
DNS exists), API backends addressed by IP. Not a replacement for domain certs —
the 6-day treadmill means automation isn't optional.

Sources: [GA announcement](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability) ·
[certbot support](https://letsencrypt.org/2026/03/11/shorter-certs-certbot) ·
[EFF writeup](https://www.eff.org/deeplinks/2026/03/certbot-and-lets-encrypt-now-support-ip-address-certificates) ·
[first IP cert](https://letsencrypt.org/2025/07/01/issuing-our-first-ip-address-certificate)
