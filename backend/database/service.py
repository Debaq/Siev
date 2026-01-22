import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession
from .models import Base, Patient, Session
from typing import List, Optional
from datetime import datetime

# Database configuration
# Get absolute path to the 'backend' directory
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FOLDER = BASE_DIR / "data"
DB_FOLDER.mkdir(exist_ok=True)

DB_PATH = f"sqlite:///{DB_FOLDER / 'siev_patients.db'}"

class DatabaseService:
    def __init__(self):
        self.engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    # --- Patient Operations ---

    def create_patient(self, db: DBSession, data: dict) -> Patient:
        # Convert birth_date string to datetime if necessary
        if 'birth_date' in data and isinstance(data['birth_date'], str):
            try:
                data['birth_date'] = datetime.fromisoformat(data['birth_date'].replace('Z', '+00:00'))
            except:
                data['birth_date'] = None

        patient = Patient(**data)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    def get_patients(self, db: DBSession, skip: int = 0, limit: int = 100, search: str = None) -> List[Patient]:
        query = db.query(Patient)
        if search:
            search_fmt = f"%{search}%"
            query = query.filter(
                (Patient.last_name.ilike(search_fmt)) | 
                (Patient.first_name.ilike(search_fmt)) |
                (Patient.dni.ilike(search_fmt))
            )
        return query.order_by(Patient.last_name).offset(skip).limit(limit).all()

    def get_patient(self, db: DBSession, patient_id: int) -> Optional[Patient]:
        return db.query(Patient).filter(Patient.id == patient_id).first()

    def update_patient(self, db: DBSession, patient_id: int, data: dict) -> Optional[Patient]:
        patient = self.get_patient(db, patient_id)
        if not patient:
            return None
        
        for key, value in data.items():
            if hasattr(patient, key):
                if key == 'birth_date' and isinstance(value, str):
                    try:
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        pass
                setattr(patient, key, value)
        
        db.commit()
        db.refresh(patient)
        return patient

    def delete_patient(self, db: DBSession, patient_id: int) -> bool:
        patient = self.get_patient(db, patient_id)
        if not patient:
            return False
        db.delete(patient)
        db.commit()
        return True

    # --- Session Operations ---

    def create_session(self, db: DBSession, patient_id: int, description: str = None) -> Session:
        session = Session(patient_id=patient_id, description=description)
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Create folder structure for session?
        # Maybe handled by file manager, but good to note here.
        return session

    def get_patient_sessions(self, db: DBSession, patient_id: int) -> List[Session]:
        return db.query(Session).filter(Session.patient_id == patient_id).order_by(Session.date.desc()).all()

    def update_session_files(self, db: DBSession, session_id: int, video_path: str = None, data_path: str = None, duration: int = None):
        session = db.query(Session).filter(Session.id == session_id).first()
        if session:
            if video_path: session.video_path = video_path
            if data_path: session.data_path = data_path
            if duration: session.duration_seconds = duration
            db.commit()
            db.refresh(session)
            return session
        return None

# Global instance
db_service = DatabaseService()
