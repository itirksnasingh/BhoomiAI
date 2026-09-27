from getpass import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.auth import User, UserRole
from app.services.auth import hash_password


def main() -> None:
    print("=== BhoomiAI Admin Bootstrap ===")
    print()

    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()

    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")

    if not email:
        raise SystemExit("Email cannot be empty.")

    if not full_name:
        raise SystemExit("Full name cannot be empty.")

    if len(password) < 12:
        raise SystemExit(
            "Password must contain at least 12 characters."
        )

    if password != confirm_password:
        raise SystemExit("Passwords do not match.")

    db = SessionLocal()

    try:
        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user is not None:
            raise SystemExit(
                f"A user with email '{email}' already exists."
            )

        admin = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print()
        print("Admin account created successfully.")
        print(f"ID: {admin.id}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role.value}")

    finally:
        db.close()


if __name__ == "__main__":
    main()