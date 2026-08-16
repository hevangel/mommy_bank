"""Environment-driven configuration. No credential literals anywhere."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class Config:
    db_path: str = field(default_factory=lambda: _env("MOMMYBANK_DB", "data/mommybank.db"))
    jwt_secret_env: str = field(default_factory=lambda: _env("MOMMYBANK_SECRET"))
    bcrypt_rounds: int = field(default_factory=lambda: int(_env("MOMMYBANK_BCRYPT_ROUNDS", "10")))
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in _env("MOMMYBANK_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            if o.strip()
        ]
    )
    static_dir: str = field(
        default_factory=lambda: _env(
            "MOMMYBANK_STATIC_DIR",
            str(Path(__file__).resolve().parent.parent / "frontend" / "dist"),
        )
    )
    admin_username: str = field(default_factory=lambda: _env("MOMMYBANK_ADMIN_USERNAME", "admin"))
    admin_password_env: str = field(default_factory=lambda: _env("MOMMYBANK_ADMIN_PASSWORD"))
    seed_demo: bool = field(default_factory=lambda: _env("MOMMYBANK_SEED_DEMO", "0") in ("1", "true", "yes"))
    demo_password_env: str = field(default_factory=lambda: _env("MOMMYBANK_DEMO_PASSWORD"))
    # Cloudflare Access (default off; production identity layer)
    cf_team_domain: str = field(default_factory=lambda: _env("MOMMYBANK_CF_TEAM_DOMAIN"))
    cf_aud: str = field(default_factory=lambda: _env("MOMMYBANK_CF_AUD"))


def get_config() -> Config:
    return Config()
