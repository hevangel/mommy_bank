# Mommy Bank plugin for ZCode (and Claude-compatible clients)

Gives your AI agent everything it needs to run the family bank:

- **Skill `mommy-bank-control`** — an operator manual that teaches the agent the
  bank's model (cents/seconds units, permissions, peak/off-peak rates) with
  ready-to-use recipes for deposits, screen-time grants, conversions, rule
  changes, loans and family admin.
- **MCP server `mommybank`** — 23 tools covering every GUI capability, running
  over the bank's REST API (so permissions and audit are identical to the app).

## Requirements

1. A running Mommy Bank instance (default `http://127.0.0.1:8971` —
   `docker compose up -d` in the [repo](https://github.com/hevangel/mommy_bank)).
2. The `mommybank` Python package importable by the `python` on your PATH:
   ```bash
   git clone https://github.com/hevangel/mommy_bank && cd mommy_bank/backend
   pip install .
   ```
3. Credentials via environment (never chat): `MOMMYBANK_URL` if not default,
   plus either `MOMMYBANK_TOKEN` or `MOMMYBANK_USERNAME`/`MOMMYBANK_PASSWORD`.

## Install

**ZCode**: Settings → Plugin Management → Discover → **+** → add the marketplace
`https://github.com/hevangel/mommy_bank` (this repo is the marketplace), then
**Get** on the *mommy-bank* card. Works with any Claude-compatible client that
reads `.claude-plugin/` plugin manifests the same way.

**Local directory install**: add the marketplace from the repo checkout path
instead of the GitHub URL.

## Use

Just talk to your agent: *"deposit $20 allowance to teen"*, *"how many minutes
would $5 buy right now?"*, *"double the bedtime exchange cost"*, *"enable
borrowing for big bro"* — the skill routes it to the right MCP tool (or CLI/REST
fallback) and handles units, confirmation for spendy actions, and re-login on
expired tokens.
