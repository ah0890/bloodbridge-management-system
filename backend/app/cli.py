"""Management commands.

    python -m app.cli migrate                 Apply database migrations
    python -m app.cli create-user ...         Create a staff account (password prompted or from env)
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import func, select

BACKEND_DIR = Path(__file__).resolve().parent.parent


def migrate() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


def _read_password(env_var: str | None) -> str:
    if env_var:
        value = os.environ.get(env_var)
        if not value:
            sys.exit(f"Environment variable {env_var} is not set.")
        return value
    first = getpass.getpass("Password: ")
    if first != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    return first


def validate_password_strength(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters.")


def create_user(args: argparse.Namespace) -> None:
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models import BloodBank, User
    from app.models.enums import Role

    password = _read_password(args.password_env)
    try:
        validate_password_strength(password)
    except ValueError as exc:
        sys.exit(str(exc))
    role = Role(args.role)
    with SessionLocal() as db:
        if db.scalar(select(User).where(func.lower(User.email) == args.email.lower())):
            sys.exit("A user with that email already exists.")
        bank_id = None
        if role == Role.BANK_MANAGER:
            if not args.bank_code:
                sys.exit("--bank-code is required for bank managers.")
            bank = db.scalar(select(BloodBank).where(BloodBank.code == args.bank_code))
            if bank is None:
                sys.exit(f"No blood bank with code {args.bank_code}.")
            bank_id = bank.id
        db.add(
            User(
                email=args.email.lower(),
                full_name=args.name,
                password_hash=hash_password(password),
                role=role,
                blood_bank_id=bank_id,
            )
        )
        db.commit()
    print(f"Created {role.value} account {args.email.lower()}.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate", help="Apply database migrations to the latest revision")

    cu = sub.add_parser("create-user", help="Create a staff account")
    cu.add_argument("--email", required=True)
    cu.add_argument("--name", required=True)
    cu.add_argument("--role", required=True, choices=["admin", "bank_manager", "coordinator"])
    cu.add_argument("--bank-code", help="Organisation code (required for bank_manager)")
    cu.add_argument("--password-env", help="Read the password from this environment variable instead of prompting")

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        migrate()
    elif args.cmd == "create-user":
        create_user(args)


if __name__ == "__main__":
    main()
