#!/usr/bin/env python3
"""Ensure fallback self-signed SSL certificates exist in ssl/live to prevent Nginx boot crashes."""

import os
from datetime import datetime, timedelta, UTC
from pathlib import Path


def ensure_fallback_ssl() -> None:
    ssl_dir = Path("ssl/live")
    cert_path = ssl_dir / "fullchain.pem"
    key_path = ssl_dir / "privkey.pem"

    if cert_path.exists() and key_path.exists():
        print(f"[OK] SSL certificates exist at {ssl_dir}")
        return

    ssl_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating fallback self-signed SSL certificates in {ssl_dir}...")

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SmartInventory"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC))
            .not_valid_after(datetime.now(UTC) + timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName("localhost")]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with open(key_path, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[OK] Fallback certificates created: {cert_path}, {key_path}")
    except Exception as e:
        print(f"[ERROR] Failed to generate fallback SSL certificates: {e}")
        raise


if __name__ == "__main__":
    ensure_fallback_ssl()

