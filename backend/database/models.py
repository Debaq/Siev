from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Patient(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    dni = Column(String(20), unique=True, nullable=True)  # Document ID
    birth_date = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sessions = relationship("Session", back_populates="patient", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    description = Column(String(200), nullable=True)
    duration_seconds = Column(Integer, default=0)
    
    # Paths to stored files
    video_path = Column(String(500), nullable=True)
    data_path = Column(String(500), nullable=True)  # JSON/CSV path
    
    # Relationships
    patient = relationship("Patient", back_populates="sessions")
