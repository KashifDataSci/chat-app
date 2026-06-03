from sqlalchemy.orm import Session
from app.models.user import UserModel


def get_user_by_email(email: str, db: Session) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.email == email).first()


def get_user_by_id(user_id: int, db: Session) -> UserModel | None:
    """Fetch user profile based on the sequential integer primary key."""
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def create_user(username: str, email: str, db: Session) -> UserModel:
    """Create a new unverified user."""
    user = UserModel(username=username, email=email, is_verified=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_user(email: str, db: Session) -> UserModel | None:
    """Mark a user as verified after successful OTP check."""
    user = get_user_by_email(email, db)
    if user:
        user.is_verified = True
        db.commit()
        db.refresh(user)
    return user