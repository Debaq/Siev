use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use chrono::NaiveDateTime;

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Patient {
    pub id: i64,
    pub first_name: String,
    pub last_name: String,
    pub dni: Option<String>,
    pub birth_date: Option<NaiveDateTime>,
    pub gender: Option<String>,
    pub phone: Option<String>,
    pub email: Option<String>,
    pub notes: Option<String>,
    pub created_at: NaiveDateTime,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreatePatientDto {
    pub first_name: String,
    pub last_name: String,
    pub dni: Option<String>,
    pub birth_date: Option<String>, // Frontend sends ISO string
    pub email: Option<String>,
    pub phone: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdatePatientDto {
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub dni: Option<String>,
    pub birth_date: Option<String>,
    pub email: Option<String>,
    pub phone: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Session {
    pub id: i64,
    pub patient_id: i64,
    pub specialist_id: Option<i64>,
    pub date: NaiveDateTime,
    pub description: Option<String>,
    pub duration_seconds: i64,
    pub video_path: Option<String>,
    pub data_path: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Specialist {
    pub id: i64,
    pub name: String,
    pub created_at: NaiveDateTime,
}