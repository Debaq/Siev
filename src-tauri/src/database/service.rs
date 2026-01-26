use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use std::fs;
use tauri::AppHandle;
use tauri::Manager;
use chrono::NaiveDateTime;
use std::path::Path;
use crate::storage::bundle::SievBundle;
use super::models::{Patient, Session, CreatePatientDto, UpdatePatientDto, Specialist};

pub struct DatabaseService {
    pool: Pool<Sqlite>,
}

impl DatabaseService {
    pub async fn new(app_handle: &AppHandle) -> Result<Self, String> {
        let app_dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
        
        if !app_dir.exists() {
            fs::create_dir_all(&app_dir).map_err(|e| e.to_string())?;
        }

        let db_path = app_dir.join("siev.db");
        let db_url = format!("sqlite://{}", db_path.to_string_lossy());

        // Create file if not exists (sqlx requires it)
        if !db_path.exists() {
            fs::File::create(&db_path).map_err(|e| e.to_string())?;
        }

        let pool = SqlitePoolOptions::new()
            .max_connections(5)
            .connect(&db_url)
            .await
            .map_err(|e| e.to_string())?;

        let service = Self { pool };
        service.init_schema().await?;
        
        Ok(service)
    }

    async fn init_schema(&self) -> Result<(), String> {
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                dni TEXT UNIQUE,
                birth_date DATETIME,
                gender TEXT,
                phone TEXT,
                email TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                specialist_id INTEGER,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                duration_seconds INTEGER DEFAULT 0,
                video_path TEXT,
                data_path TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(specialist_id) REFERENCES specialists(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS specialists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            "#
        )
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?;

        Ok(())
    }

    // --- Settings ---

    pub async fn get_setting(&self, key: &str) -> Result<Option<String>, String> {
        let result: Option<(String,)> = sqlx::query_as("SELECT value FROM settings WHERE key = ?")
            .bind(key)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| e.to_string())?;
        
        Ok(result.map(|r| r.0))
    }

    pub async fn set_setting(&self, key: &str, value: &str) -> Result<(), String> {
        sqlx::query(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )
        .bind(key)
        .bind(value)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?;
        Ok(())
    }

    // --- Specialists ---

    pub async fn get_specialists(&self) -> Result<Vec<Specialist>, String> {
        sqlx::query_as::<_, Specialist>("SELECT * FROM specialists ORDER BY name")
            .fetch_all(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn create_specialist(&self, name: String) -> Result<Specialist, String> {
        let id = sqlx::query("INSERT INTO specialists (name) VALUES (?)")
            .bind(&name)
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?
            .last_insert_rowid();

        sqlx::query_as::<_, Specialist>("SELECT * FROM specialists WHERE id = ?")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn delete_specialist(&self, id: i64) -> Result<(), String> {
        sqlx::query("DELETE FROM specialists WHERE id = ?")
            .bind(id)
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    // --- Patients ---

    pub async fn get_patients(&self, search: Option<String>) -> Result<Vec<Patient>, String> {
        let query_str = if let Some(s) = search {
            let pattern = format!("%{}%", s);
            format!("SELECT * FROM patients WHERE first_name LIKE '{}' OR last_name LIKE '{}' OR dni LIKE '{}' ORDER BY last_name", pattern, pattern, pattern)
        } else {
            "SELECT * FROM patients ORDER BY last_name".to_string()
        };

        sqlx::query_as::<_, Patient>(&query_str)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn create_patient(&self, data: CreatePatientDto) -> Result<Patient, String> {
        // Parse date if present
        let birth_date = if let Some(d) = data.birth_date {
            NaiveDateTime::parse_from_str(&format!("{} 00:00:00", d), "%Y-%m-%d %H:%M:%S")
                .ok() // If fail, store null
        } else {
            None
        };

        let id = sqlx::query(
            r#"
            INSERT INTO patients (first_name, last_name, dni, birth_date, email, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            "#
        )
        .bind(&data.first_name)
        .bind(&data.last_name)
        .bind(&data.dni)
        .bind(birth_date)
        .bind(&data.email)
        .bind(&data.phone)
        .execute(&self.pool)
        .await
        .map_err(|e| {
            if e.to_string().contains("UNIQUE constraint failed") {
                "El DNI ya está registrado.".to_string()
            } else {
                e.to_string()
            }
        })?
        .last_insert_rowid();

        // Return the created patient
        sqlx::query_as::<_, Patient>("SELECT * FROM patients WHERE id = ?")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn update_patient(&self, id: i64, data: UpdatePatientDto) -> Result<Patient, String> {
        let mut patient = sqlx::query_as::<_, Patient>("SELECT * FROM patients WHERE id = ?")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .map_err(|_| "Patient not found".to_string())?;

        // Update fields if provided
        if let Some(v) = data.first_name { patient.first_name = v; }
        if let Some(v) = data.last_name { patient.last_name = v; }
        if let Some(v) = data.dni { patient.dni = Some(v); }
        if let Some(v) = data.email { patient.email = Some(v); }
        if let Some(v) = data.phone { patient.phone = Some(v); }
        
        if let Some(d) = data.birth_date {
             if let Ok(dt) = NaiveDateTime::parse_from_str(&format!("{} 00:00:00", d), "%Y-%m-%d %H:%M:%S") {
                 patient.birth_date = Some(dt);
             }
        }

        // Save back
        sqlx::query(
            r#"
            UPDATE patients SET first_name=?, last_name=?, dni=?, email=?, phone=?, birth_date=?
            WHERE id=?
            "#
        )
        .bind(&patient.first_name)
        .bind(&patient.last_name)
        .bind(&patient.dni)
        .bind(&patient.email)
        .bind(&patient.phone)
        .bind(patient.birth_date)
        .bind(id)
        .execute(&self.pool)
        .await
        .map_err(|e| {
             if e.to_string().contains("UNIQUE constraint failed") {
                "El DNI ya está registrado.".to_string()
            } else {
                e.to_string()
            }
        })?;

        Ok(patient)
    }

    pub async fn delete_patient(&self, id: i64) -> Result<(), String> {
        sqlx::query("DELETE FROM patients WHERE id = ?")
            .bind(id)
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    // --- Sessions ---

    pub async fn create_session(&self, patient_id: i64, specialist_id: Option<i64>, description: Option<String>) -> Result<Session, String> {
        let id = sqlx::query(
            "INSERT INTO sessions (patient_id, specialist_id, description, date) VALUES (?, ?, ?, datetime('now'))"
        )
        .bind(patient_id)
        .bind(specialist_id)
        .bind(description)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?
        .last_insert_rowid();

        sqlx::query_as::<_, Session>("SELECT * FROM sessions WHERE id = ?")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn get_sessions(&self, patient_id: i64) -> Result<Vec<Session>, String> {
        sqlx::query_as::<_, Session>("SELECT * FROM sessions WHERE patient_id = ? ORDER BY date DESC")
            .bind(patient_id)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn get_session_by_id(&self, id: i64) -> Result<Option<Session>, String> {
        sqlx::query_as::<_, Session>("SELECT * FROM sessions WHERE id = ?")
            .bind(id)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn update_session_paths(&self, id: i64, video_path: Option<String>, data_path: Option<String>) -> Result<(), String> {
        sqlx::query(
            "UPDATE sessions SET video_path = ?, data_path = ? WHERE id = ?"
        )
        .bind(video_path)
        .bind(data_path)
        .bind(id)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub async fn get_patient_by_id(&self, id: i64) -> Result<Patient, String> {
        sqlx::query_as::<_, Patient>("SELECT * FROM patients WHERE id = ?")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn sync_storage(&self, root_path: &Path) -> Result<(), String> {
        if !root_path.exists() {
            return Ok(());
        }

        // Walk through patient folders
        let entries = fs::read_dir(root_path).map_err(|e| e.to_string())?;
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let _ = self.sync_patient_folder(&path).await;
            }
        }
        Ok(())
    }

    async fn sync_patient_folder(&self, patient_path: &Path) -> Result<(), String> {
        let entries = fs::read_dir(patient_path).map_err(|e| e.to_string())?;
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() && path.extension().and_then(|s| s.to_str()) == Some("siev") {
                if let Ok(manifest) = SievBundle::load_manifest(&path) {
                    let _ = self.sync_session_bundle(&path, manifest).await;
                }
            }
        }
        Ok(())
    }

    async fn sync_session_bundle(&self, bundle_path: &Path, manifest: crate::storage::bundle::SessionManifest) -> Result<(), String> {
        // 1. Find or create patient
        let patient_id = if let Some(dni) = &manifest.patient.dni {
            // Try to find by DNI
            let p: Option<(i64,)> = sqlx::query_as("SELECT id FROM patients WHERE dni = ?")
                .bind(dni)
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| e.to_string())?;
            
            if let Some((id,)) = p {
                id
            } else {
                self.create_patient_from_snapshot(&manifest.patient).await?
            }
        } else {
            // Try to find by name
            let p: Option<(i64,)> = sqlx::query_as("SELECT id FROM patients WHERE first_name = ? AND last_name = ?")
                .bind(&manifest.patient.first_name)
                .bind(&manifest.patient.last_name)
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| e.to_string())?;

            if let Some((id,)) = p {
                id
            } else {
                self.create_patient_from_snapshot(&manifest.patient).await?
            }
        };

        // 2. Check if session exists (by data_path)
        let data_path = bundle_path.join("data.bin").to_string_lossy().to_string();
        let session_exists: Option<(i64,)> = sqlx::query_as("SELECT id FROM sessions WHERE data_path = ?")
            .bind(&data_path)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        if session_exists.is_none() {
            // Create session
            let video_path = bundle_path.join("video").join("raw_capture.mp4").to_string_lossy().to_string();
            let date = chrono::DateTime::parse_from_rfc3339(&manifest.created_at)
                .map(|dt| dt.naive_local())
                .unwrap_or_else(|_| chrono::Utc::now().naive_utc());

            sqlx::query(
                "INSERT INTO sessions (patient_id, specialist_id, description, date, video_path, data_path) VALUES (?, ?, ?, ?, ?, ?)"
            )
            .bind(patient_id)
            .bind(manifest.specialist_id)
            .bind(&manifest.description)
            .bind(date)
            .bind(video_path)
            .bind(data_path)
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;
        }

        Ok(())
    }

    async fn create_patient_from_snapshot(&self, p: &crate::storage::bundle::PatientSnapshot) -> Result<i64, String> {
        let birth_date = p.birth_date.as_ref().and_then(|d| {
            NaiveDateTime::parse_from_str(&format!("{} 00:00:00", d), "%Y-%m-%d %H:%M:%S").ok()
        });

        let id = sqlx::query(
            "INSERT INTO patients (first_name, last_name, dni, birth_date, gender, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))"
        )
        .bind(&p.first_name)
        .bind(&p.last_name)
        .bind(&p.dni)
        .bind(birth_date)
        .bind(&p.gender)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?
        .last_insert_rowid();

        Ok(id)
    }
}
