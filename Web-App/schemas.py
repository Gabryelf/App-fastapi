from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


# Enums для Pydantic
class UserRole(str, Enum):
    TRAVELER = "traveler"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class TripStatus(str, Enum):
    PLANNING = "planning"
    RECRUITING = "recruiting"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# ========== USER SCHEMAS ==========
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    password: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    rating: float
    role: UserRole
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ========== TOKEN SCHEMAS ==========
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ========== TRIP SCHEMAS ==========
class TripBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20)
    destination: str = Field(..., min_length=2)
    start_date: datetime
    end_date: datetime
    max_participants: int = Field(2, ge=2, le=20)
    cost_per_person: Optional[float] = Field(None, ge=0)

    @validator('end_date')
    def validate_dates(cls, end_date, values):
        if 'start_date' in values and end_date <= values['start_date']:
            raise ValueError('End date must be after start date')
        return end_date


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TripStatus] = None


class TripResponse(TripBase):
    id: int
    status: TripStatus
    organizer_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TripWithParticipants(TripResponse):
    organizer: UserResponse
    participants: List[UserResponse]


# ========== MESSAGE SCHEMAS ==========
class TripMessageBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class TripMessageCreate(TripMessageBase):
    pass


class TripMessageResponse(TripMessageBase):
    id: int
    trip_id: int
    author_id: int
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TripMessageWithAuthor(TripMessageResponse):
    author: UserResponse


# ========== APPLICATION SCHEMAS ==========
class TripApplicationBase(BaseModel):
    message: Optional[str] = Field(None, max_length=500)


class TripApplicationCreate(TripApplicationBase):
    pass


class TripApplicationUpdate(BaseModel):
    status: ApplicationStatus


class TripApplicationResponse(TripApplicationBase):
    id: int
    trip_id: int
    applicant_id: int
    status: ApplicationStatus
    created_at: datetime

    class Config:
        from_attributes = True


class TripApplicationWithUser(TripApplicationResponse):
    applicant: UserResponse


class TripApplicationWithTrip(TripApplicationResponse):
    trip: TripResponse