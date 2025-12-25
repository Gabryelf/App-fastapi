from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum, Table
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

# Таблица связей многие-ко-многим для участников поездки
trip_participants = Table(
    'trip_participants',
    Base.metadata,
    Column('trip_id', Integer, ForeignKey('trips.id', ondelete='CASCADE')),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'))
)


class UserRole(str, enum.Enum):
    TRAVELER = "traveler"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    bio = Column(Text)
    rating = Column(Float, default=0.0)
    role = Column(Enum(UserRole), default=UserRole.TRAVELER)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    organized_trips = relationship("Trip", back_populates="organizer", foreign_keys="Trip.organizer_id")
    trip_messages = relationship("TripMessage", back_populates="author")
    trip_applications = relationship("TripApplication", back_populates="applicant")
    participated_trips = relationship("Trip", secondary=trip_participants, back_populates="participants")


class TripStatus(str, enum.Enum):
    PLANNING = "planning"
    RECRUITING = "recruiting"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    destination = Column(String(200), index=True)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    max_participants = Column(Integer, default=4)
    cost_per_person = Column(Float)
    status = Column(Enum(TripStatus), default=TripStatus.PLANNING)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    organizer = relationship("User", back_populates="organized_trips", foreign_keys=[organizer_id])
    participants = relationship("User", secondary=trip_participants, back_populates="participated_trips")
    messages = relationship("TripMessage", back_populates="trip", cascade="all, delete-orphan")
    applications = relationship("TripApplication", back_populates="trip", cascade="all, delete-orphan")


class TripMessage(Base):
    __tablename__ = "trip_messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    trip = relationship("Trip", back_populates="messages")
    author = relationship("User", back_populates="trip_messages")


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TripApplication(Base):
    __tablename__ = "trip_applications"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    trip = relationship("Trip", back_populates="applications")
    applicant = relationship("User", back_populates="trip_applications")

    # Уникальный ключ, чтобы пользователь не мог подать две заявки на одну поездку

    __table_args__ = (UniqueConstraint('trip_id', 'applicant_id', name='_trip_applicant_uc'),)
