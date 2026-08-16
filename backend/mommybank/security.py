"""Password hashing, JWT, auth dependencies, optional Cloudflare Access identity."""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_config
from .db import get_db
from .models import Setting, User

TOKEN_HOURS = 12

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    rounds = max(4, min(14, get_config().bcrypt_rounds))
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def generate_password(length: int = 16) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------- JWT


def _jwt_secret(db: Session) -> str:
    """Env secret wins; else generate once and persist (hidden key in settings)."""
    cfg = get_config()
    if cfg.jwt_secret_env:
        return cfg.jwt_secret_env
    row = db.get(Setting, "_jwt_secret")
    if row is None:
        row = Setting(key="_jwt_secret", value=json.dumps(secrets.token_urlsafe(48)))
        db.add(row)
        db.flush()
    return json.loads(row.value)


def create_token(db: Session, user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_HOURS)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(db), algorithm="HS256")


def decode_token(db: Session, token: str) -> User | None:
    try:
        payload = jwt.decode(token, _jwt_secret(db), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user


# ------------------------------------------------- Cloudflare Access (optional)

# Only bare team names (e.g. "myfamily") or full <team>.cloudflareaccess.com are
# accepted; everything else is rejected before any network use.
_TEAM_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?(\.cloudflareaccess\.com)?$")

_jwks_client = None


def _normalized_team(domain: str) -> str | None:
    if not domain or not _TEAM_DOMAIN_RE.fullmatch(domain.lower()):
        return None
    return domain.lower().removesuffix(".cloudflareaccess.com")


def _cf_user_from_assertion(db: Session, request: Request) -> User | None:
    """Validate Cf-Access-Jwt-Assertion and map verified email -> local user.

    Enabled only when MOMMYBANK_CF_TEAM_DOMAIN + MOMMYBANK_CF_AUD are set
    (production deployment behind Cloudflare Access with Google login).
    Key fetch/caching/kid-selection is handled by PyJWKClient against the
    regex-validated, pinned *.cloudflareaccess.com host over https.
    """
    global _jwks_client

    cfg = get_config()
    team = _normalized_team(cfg.cf_team_domain)
    if not (team and cfg.cf_aud):
        return None
    token = request.headers.get("Cf-Access-Jwt-Assertion")
    if not token:
        return None
    try:
        if _jwks_client is None:
            from jwt import PyJWKClient

            _jwks_client = PyJWKClient(f"https://{team}.cloudflareaccess.com/cdn-cgi/access/certs")
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=cfg.cf_aud,
            issuer=f"https://{team}.cloudflareaccess.com",
        )
    except Exception:
        return None
    email = (claims.get("email") or "").lower()
    if not email:
        return None
    # ORM query — bound parameters only, never string-assembled SQL
    return db.query(User).filter(User.email == email, User.is_active.is_(True)).one_or_none()


# ---------------------------------------------------------------- deps


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = None
    if credentials is not None:
        user = decode_token(db, credentials.credentials)
    if user is None:
        user = _cf_user_from_assertion(db, request)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user
