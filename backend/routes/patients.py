from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from database.service import db_service
from models.api_schemas import PatientCreate, PatientUpdate, PatientResponse, SessionResponse

router = APIRouter(tags=["Patients"])

# Helper to get DB session
def get_db():
    db = next(db_service.get_db())
    try:
        yield db
    finally:
        db.close()

@router.post("/patients", response_model=PatientResponse)
async def create_patient(patient: PatientCreate, db: DBSession = Depends(get_db)):
    """Create a new patient"""
    new_patient = db_service.create_patient(db, patient.model_dump())
    return new_patient

@router.get("/patients", response_model=List[PatientResponse])
async def get_patients(skip: int = 0, limit: int = 100, search: Optional[str] = None, db: DBSession = Depends(get_db)):
    """Get list of patients with optional search"""
    patients = db_service.get_patients(db, skip, limit, search)
    return patients

@router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: DBSession = Depends(get_db)):
    """Get a specific patient"""
    patient = db_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@router.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: int, patient: PatientUpdate, db: DBSession = Depends(get_db)):
    """Update a patient"""
    updated = db_service.update_patient(db, patient_id, patient.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Patient not found")
    return updated

@router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: int, db: DBSession = Depends(get_db)):
    """Delete a patient"""
    success = db_service.delete_patient(db, patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"status": "deleted", "id": patient_id}

@router.get("/patients/{patient_id}/sessions", response_model=List[SessionResponse])
async def get_patient_sessions(patient_id: int, db: DBSession = Depends(get_db)):
    """Get all sessions for a patient"""
    sessions = db_service.get_patient_sessions(db, patient_id)
    return sessions
