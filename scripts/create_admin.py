#!/usr/bin/env python3
"""CLI utility to create an initial organization and Admin user in production."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.core.database import AsyncSessionLocal
from backend.src.domain.users.service import UserService


async def create_admin(org_name: str, email: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        try:
            tenant, user = await UserService.register_organization(
                db=session,
                organization_name=org_name,
                email=email,
                password=password,
            )
            print(f"[SUCCESS] Created Organization: '{tenant.name}' (ID: {tenant.id})")
            print(f"[SUCCESS] Created Admin User: '{user.email}' (Role: {user.role})")
        except Exception as e:
            print(f"[ERROR] Failed to create admin: {e}")
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create production organization and initial Admin user.")
    parser.add_argument("--org", required=True, help="Organization / Company Name")
    parser.add_argument("--email", required=True, help="Admin Email Address")
    parser.add_argument("--password", required=True, help="Admin Password (minimum 8 characters)")

    args = parser.parse_args()
    if len(args.password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        sys.exit(1)

    asyncio.run(create_admin(args.org, args.email, args.password))


if __name__ == "__main__":
    main()

