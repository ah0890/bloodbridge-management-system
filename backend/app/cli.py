"""Management commands.

python -m app.cli migrate                 Apply database migrations
python -m app.cli create-user ...         Create a staff account (password prompted or from env)
python -m app.cli seed-demo [--reset]     Generate SYNTHETIC DEMO DATA (never in production)
python -m app.cli validate-data           Run cross-table consistency checks
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


def seed_demo(args: argparse.Namespace) -> None:
    import secrets
    from datetime import date

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.seed import SeedError
    from app.seed import seed_demo as run_seed
    from app.seed.generator import SeedConfig

    password = get_settings().demo_password
    generated = False
    if not password:
        password, generated = secrets.token_urlsafe(14), True
    try:
        validate_password_strength(password)
    except ValueError as exc:
        sys.exit(f"BB_DEMO_PASSWORD: {exc}")
    cfg = SeedConfig(
        seed=args.seed,
        anchor=date.fromisoformat(args.anchor_date) if args.anchor_date else SeedConfig().anchor,
        donors=args.donors,
        requests=args.requests,
        staff_password=password,
    )
    with SessionLocal() as db:
        try:
            summary = run_seed(db, cfg, reset=args.reset, allow_mixed=args.allow_mixed)
        except SeedError as exc:
            sys.exit(str(exc))
    print(f"SYNTHETIC DEMO DATA generated (seed={cfg.seed}, anchor={cfg.anchor.isoformat()}):")
    for key in (
        "blood_banks",
        "donors",
        "donations",
        "inventory_batches",
        "stock_movements",
        "requests",
        "contact_attempts",
        "notifications",
    ):
        print(f"  {key:<18} {getattr(summary, key)}")
    print("Demo staff accounts:")
    for email, role in summary.staff_accounts:
        print(f"  {role:<13} {email}")
    if generated:
        print(f"Generated password for all demo accounts (shown once, not stored): {password}")
    else:
        print("Demo account password: value of BB_DEMO_PASSWORD")


def validate_data() -> None:
    from app.db.session import SessionLocal
    from app.seed.validate import validate_dataset

    with SessionLocal() as db:
        problems = validate_dataset(db)
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("Dataset consistency checks passed.")


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

    sd = sub.add_parser("seed-demo", help="Generate synthetic demonstration data")
    sd.add_argument("--reset", action="store_true", help="Delete existing synthetic data and demo accounts first")
    sd.add_argument("--seed", type=int, default=20261027, help="Random seed (same seed + anchor date = same data)")
    sd.add_argument("--anchor-date", help="Treat this ISO date as 'today' when generating (default: today)")
    sd.add_argument("--donors", type=int, default=1000)
    sd.add_argument("--requests", type=int, default=160)
    sd.add_argument("--allow-mixed", action="store_true", help="Permit seeding alongside imported/verified records")
    sub.add_parser("validate-data", help="Check cross-table consistency")

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        migrate()
    elif args.cmd == "create-user":
        create_user(args)
    elif args.cmd == "seed-demo":
        seed_demo(args)
    elif args.cmd == "validate-data":
        validate_data()


if __name__ == "__main__":
    main()
