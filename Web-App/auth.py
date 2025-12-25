from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_session
from auth import get_current_user, get_password_hash, require_role
from models import User, UserRole
import schemas

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_session)):
    """Регистрация нового пользователя"""
    # Проверка существующего email
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Проверка существующего username
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Создание пользователя
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        bio=user.bio,
        hashed_password=hashed_password,
        role=UserRole.TRAVELER
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
def update_current_user(
        user_update: schemas.UserUpdate,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """Обновить информацию о текущем пользователе"""
    update_data = user_update.dict(exclude_unset=True)

    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_session)):
    """Получить информацию о пользователе по ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/", response_model=List[schemas.UserResponse])
def list_users(
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        db: Session = Depends(get_session)
):
    """Список пользователей с фильтрацией"""
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    return query.offset(skip).limit(limit).all()


@router.patch("/{user_id}/verify")
def verify_user(
        user_id: int,
        db: Session = Depends(get_session),
        admin: User = Depends(require_role("admin"))
):
    """Верификация пользователя (только для админа)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_verified = True
    db.commit()
    return {"message": "User verified successfully"}