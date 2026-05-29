import argparse
import os
import secrets

from sqlalchemy import select

from app.companies.models import Company
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.users.models import User


def create_superuser(args: argparse.Namespace) -> None:
    password = args.password or os.getenv("SUPERUSER_PASSWORD")
    generated_password = False
    if not password:
        password = secrets.token_urlsafe(24)
        generated_password = True

    with SessionLocal() as db:
        company = db.scalar(select(Company).where(Company.name == args.company_name))
        if company is None:
            company = Company(name=args.company_name, status="active")
            db.add(company)
            db.flush()

        email = args.email.lower()
        user = db.scalar(
            select(User).where(
                User.company_id == company.id,
                User.email == email,
            )
        )
        if user is None:
            user = User(
                company_id=company.id,
                name=args.name,
                email=email,
                password_hash=hash_password(password),
                role="superadmin",
                status="active",
            )
            db.add(user)
        else:
            user.name = args.name
            user.password_hash = hash_password(password)
            user.role = "superadmin"
            user.status = "active"

        db.commit()

    print(f"Superuser ready: {email}")
    if generated_password:
        print(f"Generated password: {password}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SwaFlow management commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    superuser_parser = subparsers.add_parser("create-superuser")
    superuser_parser.add_argument("--email", default="admin@swateck.com")
    superuser_parser.add_argument("--name", default="Superusuario Swateck")
    superuser_parser.add_argument("--company-name", default="Swateck")
    superuser_parser.add_argument("--password")
    superuser_parser.set_defaults(func=create_superuser)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
