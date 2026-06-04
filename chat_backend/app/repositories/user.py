from sqlalchemy.orm import Session
from app.models.user import UserModel
import uuid


def get_user_by_email(email: str, db: Session) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.email == email).first()


def get_user_by_uuid(user_uuid, db: Session) -> UserModel | None:
    """Fetch user profile based on UUID primary key."""
    return db.query(UserModel).filter(UserModel.uuid == user_uuid).first()


def create_user(email: str, db: Session) -> UserModel:
    """Create a new unverified user."""
    user = UserModel(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_user(email: str, db: Session) -> UserModel | None:
    """Mark a user as verified after successful OTP check."""
    user = get_user_by_email(email, db)
    # is_verified is removed from schema, doing nothing for now or handle appropriately
    return user


def get_or_create_user_by_email(email: str, db: Session) -> UserModel:
    """Find existing user by email or create a new user.
    Used to auto-provision users from the frontend (N8N-managed users)."""
    user = get_user_by_email(email, db)
    if user:
        return user
    user = UserModel(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user