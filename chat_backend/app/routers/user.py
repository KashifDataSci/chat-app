from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import UserModel
from typing import Dict, Any

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/search")
def search_users(payload: dict, db: Session = Depends(get_db)):
    """
    Search for users by email (partial match).
    Expects payload: {"email": "search_query"}
    """
    email = payload.get("email", "").strip()
    if not email:
        return []
    
    # Partial case-insensitive search, limit to 20 results
    users = db.query(UserModel).filter(UserModel.email.ilike(f"%{email}%")).limit(20).all()
    
    return [
        {
            "id": str(user.uuid), # Using uuid as ID to match conversation participants
            "email": user.email,
            "data": user.data,
            "iv": user.iv,
            "authtag": user.authtag,
            "created_at": str(user.created_at)
        } for user in users
    ]