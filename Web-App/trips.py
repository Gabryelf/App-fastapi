from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_session
from auth import get_current_user, require_role
from models import Trip, User, TripStatus, TripMessage, TripApplication, ApplicationStatus
import schemas

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/", response_model=schemas.TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
        trip: schemas.TripCreate,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """Создание новой поездки"""
    if trip.start_date < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be in the past"
        )

    db_trip = Trip(
        **trip.dict(),
        organizer_id=current_user.id,
        status=TripStatus.RECRUITING
    )

    # Организатор автоматически становится участником
    db_trip.participants.append(current_user)

    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)

    # Системное сообщение о создании поездки
    system_message = TripMessage(
        content=f"Поездка '{trip.title}' создана. Начало набора участников!",
        trip_id=db_trip.id,
        author_id=current_user.id,
        is_system=True
    )
    db.add(system_message)
    db.commit()

    return db_trip


@router.get("/", response_model=List[schemas.TripResponse])
def list_trips(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        destination: Optional[str] = None,
        status: Optional[TripStatus] = None,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        db: Session = Depends(get_session)
):
    """Список поездок с фильтрацией"""
    query = db.query(Trip)

    if destination:
        query = query.filter(Trip.destination.ilike(f"%{destination}%"))

    if status:
        query = query.filter(Trip.status == status)

    if min_date:
        query = query.filter(Trip.start_date >= min_date)

    if max_date:
        query = query.filter(Trip.start_date <= max_date)

    return query.order_by(Trip.start_date).offset(skip).limit(limit).all()


@router.get("/{trip_id}", response_model=schemas.TripWithParticipants)
def get_trip(trip_id: int, db: Session = Depends(get_session)):
    """Получить информацию о поездке"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    return trip


@router.put("/{trip_id}", response_model=schemas.TripResponse)
def update_trip(
        trip_id: int,
        trip_update: schemas.TripUpdate,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """Обновить информацию о поездке (только организатор)"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    if trip.organizer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trip organizer can update trip"
        )

    for key, value in trip_update.dict(exclude_unset=True).items():
        setattr(trip, key, value)

    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/apply", response_model=schemas.TripApplicationResponse)
def apply_for_trip(
        trip_id: int,
        application: schemas.TripApplicationCreate,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """Подать заявку на участие в поездке"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    # Проверка статуса поездки
    if trip.status != TripStatus.RECRUITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trip is not recruiting participants"
        )

    # Проверка, что пользователь не организатор
    if trip.organizer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organizer cannot apply for their own trip"
        )

    # Проверка, что пользователь уже не участвует
    if current_user in trip.participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a participant"
        )

    # Проверка существующей заявки
    existing_application = db.query(TripApplication).filter(
        TripApplication.trip_id == trip_id,
        TripApplication.applicant_id == current_user.id
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied for this trip"
        )

    # Создание заявки
    db_application = TripApplication(
        trip_id=trip_id,
        applicant_id=current_user.id,
        message=application.message
    )

    db.add(db_application)
    db.commit()
    db.refresh(db_application)

    # Системное сообщение
    system_message = TripMessage(
        content=f"Пользователь {current_user.username} подал заявку на участие",
        trip_id=trip_id,
        author_id=current_user.id,
        is_system=True
    )
    db.add(system_message)
    db.commit()

    return db_application


@router.get("/{trip_id}/participants", response_model=List[schemas.UserResponse])
def get_trip_participants(trip_id: int, db: Session = Depends(get_session)):
    """Получить список участников поездки"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    return trip.participants


@router.post("/{trip_id}/start")
def start_trip(
        trip_id: int,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """Начать поездку (только организатор)"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    if trip.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trip organizer can start the trip"
        )

    if trip.status != TripStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trip must be confirmed before starting"
        )

    trip.status = TripStatus.IN_PROGRESS
    db.commit()

    return {"message": "Trip started successfully"}