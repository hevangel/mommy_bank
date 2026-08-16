# Deployment

## Local development

```bash
# terminal 1 — backend (http://127.0.0.1:8000, docs at /docs)
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m uvicorn mommybank.main:app --reload
#   first run prints the generated admin password (or set MOMMYBANK_ADMIN_PASSWORD)
#   optional: MOMMYBANK_SEED_DEMO=1 seeds three demo kids (teen/kid/toddler)

# terminal 2 — frontend (http://localhost:5173, proxies /api → 8000)
cd frontend
npm install
npm run dev
```

Data lives in `backend/data/mommybank.db` (gitignored). Delete it for a factory reset.

## Production build & Docker

```bash
docker compose up --build -d        # builds SPA, bundles into python image, runs on :8000
```

- Multi-stage `Dockerfile`: `node:20-alpine` builds the SPA → `python:3.12-slim` installs the
  `mommybank` package and serves **both** API and static SPA via uvicorn (single container, single port).
- SQLite file on a bind/volume: `./data:/app/data` (compose). Set `TZ` for natural logs; exchange
  windows use the app `timezone` setting regardless.
- Healthcheck: `GET /api/health`.
- Scale: it's SQLite + one process — perfect for a family; use `--workers 1` (default) to keep writes serialized.

Environment for the container: see the table in [architecture.md](architecture.md#configuration-env).
Set at minimum `MOMMYBANK_ADMIN_PASSWORD` (first-boot admin), and `MOMMYBANK_SEED_DEMO=0` for real use.

## Production: EC2 + Cloudflare (Gmail login)

Target topology (designed-for, follows the stated plan):

```
family.example.com ── Cloudflare (Access for Teams + WAF/TLS)
        │  verified identity → Cf-Access-Jwt-Assertion header
        ▼
   EC2 (docker compose, port 8000, security group = Cloudflare IP ranges only)
        ▼
   Mommy Bank API+SPA  ── auto-provision/match users by verified email
```

Steps:

1. **EC2**: any small instance (t3.micro is plenty). Install Docker, clone repo, `docker compose up -d --build`. Attach an EBS volume or use the instance's disk for `./data`. Security group: allow 443/80 from Cloudflare published IP ranges only (or no ingress at all if using Cloudflare Tunnel).
2. **Cloudflare DNS**: point `bank.example.com` at the EC2 public IP (proxied 🟠).
3. **Cloudflare Access (Zero Trust → Access → Applications)**: create a self-hosted app for `bank.example.com`; identity providers: **Google (Gmail) login** — allow-list the parents' Gmails as admins and kids' Gmails as users. Policy names map to roles below.
4. **Role mapping**: in Mommy Bank, each family member's user record can carry an email (users table `email` column reserved for this). On a Cloudflare-authenticated request, the app verifies the assertion against your team's JWKS (`MOMMYBANK_CF_TEAM_DOMAIN`, `MOMMYBANK_CF_AUD` env) and matches the verified email to the local user — Google login with zero passwords. Local password login remains as fallback for dev/offline.
5. **Recommended hardening**: Cloudflare Tunnel instead of open ports (`cloudflared` runs on EC2, outbound-only), Let's Encrypt origin certs via Cloudflare, automated EBS snapshots for `data/mommybank.db`.
6. **Backups**: `sqlite3 data/mommybank.db ".backup backup.db"` on a cron; the DB is the entire state.

> Note: the CF-Access verification hook is implemented behind env flags and default-off;
> until you deploy to EC2 behind Access, everything works with password auth. The reserved
> `users.email` column + mapping logic is the seam for Gmail identity.

## Upgrades

`git pull && docker compose up -d --build` — SQLAlchemy `create_all` is additive; new columns
get lightweight `ALTER TABLE` migrations in `seed.py` when needed (no external migration framework
for a family-scale app).
