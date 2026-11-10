#!/usr/bin/env python3
"""Generate cryptographically strong secrets for production deployment (.env.production)."""

import base64
import secrets


def generate_secrets() -> None:
    jwt_secret = secrets.token_hex(32)  # 64-char hex
    encryption_key = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")  # 32-byte base64
    postgres_password = secrets.token_urlsafe(24)
    redis_password = secrets.token_urlsafe(24)

    print("=" * 70)
    print("PRODUCTION SECRETS GENERATOR")
    print("Copy and paste these values into your .env.production file:")
    print("=" * 70)
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print(f"POSTGRES_PASSWORD={postgres_password}")
    print(f"REDIS_PASSWORD={redis_password}")
    print("=" * 70)


if __name__ == "__main__":
    generate_secrets()

