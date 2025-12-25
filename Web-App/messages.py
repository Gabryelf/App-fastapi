from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json

from database import get_session
from auth import get_current_user
from models import Trip, TripMessage, TripParticipant
import schemas

router = APIRouter(prefix="/messages", tags=["messages"])

# Хранилище активных WebSocket соединений
active_connections = {}


@router.get("/trip/{trip_id}", response_model=List[schemas.TripMessageWithAuthor])
def get_trip_messages(
        trip_id: int,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_session),
        current_user=Depends(get_current_user)
):
    """Получить сообщения поездки"""
    # Проверка, что пользователь является участником поездки
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    if current_user not in trip.participants and current_user.id != trip.organizer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this trip"
        )

    messages = db.query(TripMessage).filter(
        TripMessage.trip_id == trip_id
    ).order_by(TripMessage.created_at).offset(skip).limit(limit).all()

    return messages


@router.post("/trip/{trip_id}", response_model=schemas.TripMessageResponse)
async def send_trip_message(
        trip_id: int,
        message: schemas.TripMessageCreate,
        db: Session = Depends(get_session),
        current_user=Depends(get_current_user)
):
    """Отправить сообщение в чат поездки"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    if current_user not in trip.participants and current_user.id != trip.organizer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this trip"
        )

    db_message = TripMessage(
        content=message.content,
        trip_id=trip_id,
        author_id=current_user.id
    )

    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    await notify_trip_participants(trip_id, db_message, db)

    return db_message

@router.websocket("/ws/trip/{trip_id}")
async def websocket_trip_chat(
        websocket: WebSocket,
        trip_id: int,
        token: str,
        db: Session = Depends(get_session)
):
    """WebSocket для чата поездки"""
    # Валидация токена и пользователя
    from auth import get_current_user_ws

    try:
        user = await get_current_user_ws(token, db)
        trip = db.query(Trip).filter(Trip.id == trip_id).first()

        if not trip or user not in trip.participants:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()

        # Добавление соединения в активные
        if trip_id not in active_connections:
            active_connections[trip_id] = []
        active_connections[trip_id].append(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Сохранение сообщения в БД
                db_message = TripMessage(
                    content=message_data["content"],
                    trip_id=trip_id,
                    author_id=user.id
                )
                db.add(db_message)
                db.commit()

                # Рассылка сообщения всем участникам
                await broadcast_message(trip_id, {
                    "type": "message",
                    "content": message_data["content"],
                    "author": user.username,
                    "timestamp": db_message.created_at.isoformat()
                })

        except WebSocketDisconnect:
            active_connections[trip_id].remove(websocket)

    except Exception as e:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


async def broadcast_message(trip_id: int, message: dict):
    """Отправка сообщения всем участникам поездки"""
    if trip_id in active_connections:
        for connection in active_connections[trip_id]:
            await connection.send_json(message)


async def notify_trip_participants(trip_id: int, message: TripMessage, db: Session):
    """Уведомление участников о новом сообщении"""
    pass
