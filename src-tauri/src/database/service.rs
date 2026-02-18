use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use std::fs;
use tauri::AppHandle;
use tauri::Manager;
use chrono::NaiveDateTime;
use std::path::Path;
use crate::storage::bundle::SievBundle;
use super::models::{Patient, Session, Recording, CreatePatientDto, UpdatePatientDto, Specialist};

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

        // Enable foreign keys for CASCADE support
        sqlx::query("PRAGMA foreign_keys = ON")
            .execute(&service.pool)
            .await
            .map_err(|e| e.to_string())?;

        service.init_schema().await?;
        service.migrate_v2_recordings().await?;
        service.migrate_vng_test_results_schema().await?;

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
                protocol_type TEXT,
                protocol_config TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(specialist_id) REFERENCES specialists(id)
            );

            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                label TEXT,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                duration_seconds INTEGER DEFAULT 0,
                video_path TEXT,
                data_path TEXT,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
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

            -- VNG Test Results
            CREATE TABLE IF NOT EXISTS vng_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                results_json TEXT,
                clinical_notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(recording_id) REFERENCES recordings(id) ON DELETE CASCADE
            );

            -- VNG Reference Values
            CREATE TABLE IF NOT EXISTS vng_reference_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                min_normal REAL,
                max_normal REAL,
                unit TEXT,
                age_group TEXT,
                UNIQUE(test_type, metric_name, age_group)
            );

            -- VNG Reports
            CREATE TABLE IF NOT EXISTS vng_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                pdf_path TEXT,
                config_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(recording_id) REFERENCES recordings(id) ON DELETE CASCADE
            );
            "#
        )
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?;

        Ok(())
    }

    /// Migrate old sessions (with video_path/data_path) to new session+recording model.
    /// This handles existing databases that still have the old schema.
    async fn migrate_v2_recordings(&self) -> Result<(), String> {
        // Check if old schema exists (sessions table has video_path column)
        let has_video_path: Option<(String,)> = sqlx::query_as(
            "SELECT name FROM pragma_table_info('sessions') WHERE name = 'video_path'"
        )
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| e.to_string())?;

        if has_video_path.is_none() {
            return Ok(()); // Already migrated or fresh DB
        }

        println!("[SIEV-DB] Migrating old sessions to session+recording model...");

        // 1. Migrate old vng_test_results that still have session_id column
        let has_old_fk: Option<(String,)> = sqlx::query_as(
            "SELECT name FROM pragma_table_info('vng_test_results') WHERE name = 'session_id'"
        )
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| e.to_string())?;

        // 2. Create recordings from old sessions that have data
        let old_sessions: Vec<(i64, Option<String>, Option<String>, Option<String>, String, i64)> = sqlx::query_as(
            "SELECT id, description, video_path, data_path, date, duration_seconds FROM sessions WHERE video_path IS NOT NULL OR data_path IS NOT NULL"
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| e.to_string())?;

        for (session_id, description, video_path, data_path, date, duration_seconds) in &old_sessions {
            // Check if recording already exists for this session
            let existing: Option<(i64,)> = sqlx::query_as(
                "SELECT id FROM recordings WHERE session_id = ?"
            )
            .bind(session_id)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

            if existing.is_none() {
                let test_type = description.as_deref().unwrap_or("unknown");
                let recording_id = sqlx::query(
                    "INSERT INTO recordings (session_id, test_type, label, date, duration_seconds, video_path, data_path, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, 0)"
                )
                .bind(session_id)
                .bind(test_type)
                .bind(description)
                .bind(date)
                .bind(duration_seconds)
                .bind(video_path)
                .bind(data_path)
                .execute(&self.pool)
                .await
                .map_err(|e| e.to_string())?
                .last_insert_rowid();

                // Migrate vng_test_results from session_id to recording_id (if old column exists)
                if has_old_fk.is_some() {
                    let _ = sqlx::query(
                        "UPDATE vng_test_results SET recording_id = ? WHERE session_id = ?"
                    )
                    .bind(recording_id)
                    .bind(session_id)
                    .execute(&self.pool)
                    .await;
                }

                println!("[SIEV-DB] Migrated session {} -> recording {}", session_id, recording_id);
            }
        }

        // 3. Remove old columns from sessions table using temp table approach
        // SQLite doesn't support DROP COLUMN in older versions, so we use the temp table method
        let _ = sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS sessions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                specialist_id INTEGER,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                protocol_type TEXT,
                protocol_config TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(specialist_id) REFERENCES specialists(id)
            );
            INSERT OR IGNORE INTO sessions_new (id, patient_id, specialist_id, date, description)
                SELECT id, patient_id, specialist_id, date, description FROM sessions;
            DROP TABLE sessions;
            ALTER TABLE sessions_new RENAME TO sessions;
            "#
        )
        .execute(&self.pool)
        .await
        .map_err(|e| format!("Migration error: {}", e))?;

        println!("[SIEV-DB] Migration to v2 (session+recording) complete.");
        Ok(())
    }

    /// Ensure vng_test_results has recording_id column (old DBs may still have session_id).
    async fn migrate_vng_test_results_schema(&self) -> Result<(), String> {
        let has_recording_id: Option<(String,)> = sqlx::query_as(
            "SELECT name FROM pragma_table_info('vng_test_results') WHERE name = 'recording_id'"
        )
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| e.to_string())?;

        if has_recording_id.is_some() {
            return Ok(()); // Already has the correct schema
        }

        // Check if the table even exists
        let table_exists: Option<(String,)> = sqlx::query_as(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='vng_test_results'"
        )
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| e.to_string())?;

        if table_exists.is_none() {
            return Ok(()); // Table doesn't exist yet, init_schema will create it
        }

        println!("[SIEV-DB] Migrating vng_test_results: session_id -> recording_id...");

        // Recreate with correct schema, mapping session_id -> recording via lookup
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS vng_test_results_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                results_json TEXT,
                clinical_notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(recording_id) REFERENCES recordings(id) ON DELETE CASCADE
            )
            "#
        )
        .execute(&self.pool)
        .await
        .map_err(|e| format!("vng_test_results migration error: {}", e))?;

        // Try to migrate existing data by matching session_id to recordings
        let _ = sqlx::query(
            r#"
            INSERT OR IGNORE INTO vng_test_results_new (id, recording_id, test_type, results_json, clinical_notes, created_at)
            SELECT vtr.id, r.id, vtr.test_type, vtr.results_json, vtr.clinical_notes, vtr.created_at
            FROM vng_test_results vtr
            INNER JOIN recordings r ON r.session_id = vtr.session_id
            "#
        )
        .execute(&self.pool)
        .await;

        sqlx::query("DROP TABLE vng_test_results")
            .execute(&self.pool)
            .await
            .map_err(|e| format!("vng_test_results migration error: {}", e))?;

        sqlx::query("ALTER TABLE vng_test_results_new RENAME TO vng_test_results")
            .execute(&self.pool)
            .await
            .map_err(|e| format!("vng_test_results migration error: {}", e))?;

        println!("[SIEV-DB] vng_test_results migration complete.");
        Ok(())
    }

    pub async fn reset_database(&self) -> Result<(), String> {
        sqlx::query("DROP TABLE IF EXISTS vng_reports")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        sqlx::query("DROP TABLE IF EXISTS vng_test_results")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        sqlx::query("DROP TABLE IF EXISTS vng_reference_values")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        sqlx::query("DROP TABLE IF EXISTS recordings")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        sqlx::query("DROP TABLE IF EXISTS sessions")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        sqlx::query("DROP TABLE IF EXISTS patients")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        sqlx::query("DROP TABLE IF EXISTS settings")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        sqlx::query("DROP TABLE IF EXISTS specialists")
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        self.init_schema().await?;
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
            format!(
                "SELECT p.*, COALESCE(cnt.c, 0) AS session_count \
                 FROM patients p LEFT JOIN (SELECT patient_id, COUNT(*) AS c FROM sessions GROUP BY patient_id) cnt \
                 ON p.id = cnt.patient_id \
                 WHERE p.first_name LIKE '{}' OR p.last_name LIKE '{}' OR p.dni LIKE '{}' \
                 ORDER BY p.last_name",
                pattern, pattern, pattern
            )
        } else {
            "SELECT p.*, COALESCE(cnt.c, 0) AS session_count \
             FROM patients p LEFT JOIN (SELECT patient_id, COUNT(*) AS c FROM sessions GROUP BY patient_id) cnt \
             ON p.id = cnt.patient_id \
             ORDER BY p.last_name".to_string()
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

    pub async fn delete_session(&self, id: i64) -> Result<(), String> {
        // CASCADE will delete recordings, which cascade to vng_test_results and vng_reports
        sqlx::query("DELETE FROM sessions WHERE id = ?")
            .bind(id)
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    // --- Sessions ---

    pub async fn create_session(
        &self,
        patient_id: i64,
        specialist_id: Option<i64>,
        description: Option<String>,
        protocol_type: Option<String>,
        protocol_config: Option<String>,
    ) -> Result<Session, String> {
        let id = sqlx::query(
            "INSERT INTO sessions (patient_id, specialist_id, description, protocol_type, protocol_config, date) VALUES (?, ?, ?, ?, ?, datetime('now'))"
        )
        .bind(patient_id)
        .bind(specialist_id)
        .bind(description)
        .bind(protocol_type)
        .bind(protocol_config)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?
        .last_insert_rowid();

        sqlx::query_as::<_, Session>(
            "SELECT s.*, COALESCE(rc.c, 0) AS recording_count \
             FROM sessions s LEFT JOIN (SELECT session_id, COUNT(*) AS c FROM recordings GROUP BY session_id) rc \
             ON s.id = rc.session_id WHERE s.id = ?"
        )
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn get_sessions(&self, patient_id: i64) -> Result<Vec<Session>, String> {
        sqlx::query_as::<_, Session>(
            "SELECT s.*, COALESCE(rc.c, 0) AS recording_count \
             FROM sessions s LEFT JOIN (SELECT session_id, COUNT(*) AS c FROM recordings GROUP BY session_id) rc \
             ON s.id = rc.session_id WHERE s.patient_id = ? ORDER BY s.date DESC"
        )
            .bind(patient_id)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn get_session_by_id(&self, id: i64) -> Result<Option<Session>, String> {
        sqlx::query_as::<_, Session>(
            "SELECT s.*, COALESCE(rc.c, 0) AS recording_count \
             FROM sessions s LEFT JOIN (SELECT session_id, COUNT(*) AS c FROM recordings GROUP BY session_id) rc \
             ON s.id = rc.session_id WHERE s.id = ?"
        )
            .bind(id)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    // --- Recordings ---

    pub async fn create_recording(
        &self,
        session_id: i64,
        test_type: &str,
        label: Option<&str>,
        sort_order: i64,
    ) -> Result<Recording, String> {
        let id = sqlx::query(
            "INSERT INTO recordings (session_id, test_type, label, sort_order, date) VALUES (?, ?, ?, ?, datetime('now'))"
        )
        .bind(session_id)
        .bind(test_type)
        .bind(label)
        .bind(sort_order)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?
        .last_insert_rowid();

        sqlx::query_as::<_, Recording>("SELECT * FROM recordings WHERE id = ?")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn get_recordings(&self, session_id: i64) -> Result<Vec<Recording>, String> {
        sqlx::query_as::<_, Recording>(
            "SELECT * FROM recordings WHERE session_id = ? ORDER BY sort_order, date"
        )
            .bind(session_id)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn get_recording_by_id(&self, id: i64) -> Result<Option<Recording>, String> {
        sqlx::query_as::<_, Recording>("SELECT * FROM recordings WHERE id = ?")
            .bind(id)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn update_recording_paths(&self, id: i64, video_path: Option<String>, data_path: Option<String>) -> Result<(), String> {
        sqlx::query(
            "UPDATE recordings SET video_path = ?, data_path = ? WHERE id = ?"
        )
        .bind(video_path)
        .bind(data_path)
        .bind(id)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub async fn update_recording_duration(&self, id: i64, duration_seconds: i64) -> Result<(), String> {
        sqlx::query("UPDATE recordings SET duration_seconds = ? WHERE id = ?")
            .bind(duration_seconds)
            .bind(id)
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub async fn delete_recording(&self, id: i64) -> Result<(), String> {
        sqlx::query("DELETE FROM recordings WHERE id = ?")
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

        // 2. Check if recording exists (by data_path)
        let data_path = bundle_path.join("data.bin").to_string_lossy().to_string();
        let recording_exists: Option<(i64,)> = sqlx::query_as("SELECT id FROM recordings WHERE data_path = ?")
            .bind(&data_path)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| e.to_string())?;

        if recording_exists.is_none() {
            let video_path = bundle_path.join("video").join("raw_capture.mp4").to_string_lossy().to_string();
            let date = chrono::DateTime::parse_from_rfc3339(&manifest.created_at)
                .map(|dt| dt.naive_local())
                .unwrap_or_else(|_| chrono::Utc::now().naive_utc());

            // Create session
            let session_id = sqlx::query(
                "INSERT INTO sessions (patient_id, specialist_id, description, protocol_type, date) VALUES (?, ?, ?, ?, ?)"
            )
            .bind(patient_id)
            .bind(manifest.specialist_id)
            .bind(&manifest.description)
            .bind(&manifest.test_type)
            .bind(date)
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?
            .last_insert_rowid();

            // Create recording under session
            sqlx::query(
                "INSERT INTO recordings (session_id, test_type, label, date, video_path, data_path, sort_order) VALUES (?, ?, ?, ?, ?, ?, 0)"
            )
            .bind(session_id)
            .bind(&manifest.test_type)
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

    // --- VNG Test Results ---

    pub async fn save_vng_test_result(
        &self,
        recording_id: i64,
        test_type: &str,
        results_json: &str,
        clinical_notes: Option<&str>,
    ) -> Result<i64, String> {
        let id = sqlx::query(
            "INSERT INTO vng_test_results (recording_id, test_type, results_json, clinical_notes) VALUES (?, ?, ?, ?)"
        )
        .bind(recording_id)
        .bind(test_type)
        .bind(results_json)
        .bind(clinical_notes)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?
        .last_insert_rowid();

        Ok(id)
    }

    pub async fn get_vng_test_results(
        &self,
        recording_id: i64,
        test_type: Option<&str>,
    ) -> Result<Vec<(i64, String, String, Option<String>)>, String> {
        let results: Vec<(i64, String, String, Option<String>)> = if let Some(tt) = test_type {
            sqlx::query_as(
                "SELECT id, test_type, results_json, clinical_notes FROM vng_test_results WHERE recording_id = ? AND test_type = ? ORDER BY created_at DESC"
            )
            .bind(recording_id)
            .bind(tt)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| e.to_string())?
        } else {
            sqlx::query_as(
                "SELECT id, test_type, results_json, clinical_notes FROM vng_test_results WHERE recording_id = ? ORDER BY created_at DESC"
            )
            .bind(recording_id)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| e.to_string())?
        };

        Ok(results)
    }

    pub async fn get_vng_reference_values(
        &self,
        test_type: Option<&str>,
        age_group: Option<&str>,
    ) -> Result<Vec<(String, String, f64, f64, Option<String>)>, String> {
        let results: Vec<(String, String, f64, f64, Option<String>)> = match (test_type, age_group) {
            (Some(tt), Some(ag)) => {
                sqlx::query_as(
                    "SELECT test_type, metric_name, min_normal, max_normal, unit FROM vng_reference_values WHERE test_type = ? AND (age_group = ? OR age_group IS NULL)"
                )
                .bind(tt)
                .bind(ag)
                .fetch_all(&self.pool)
                .await
                .map_err(|e| e.to_string())?
            }
            (Some(tt), None) => {
                sqlx::query_as(
                    "SELECT test_type, metric_name, min_normal, max_normal, unit FROM vng_reference_values WHERE test_type = ?"
                )
                .bind(tt)
                .fetch_all(&self.pool)
                .await
                .map_err(|e| e.to_string())?
            }
            _ => {
                sqlx::query_as(
                    "SELECT test_type, metric_name, min_normal, max_normal, unit FROM vng_reference_values"
                )
                .fetch_all(&self.pool)
                .await
                .map_err(|e| e.to_string())?
            }
        };

        Ok(results)
    }

    pub async fn save_vng_report(
        &self,
        recording_id: i64,
        pdf_path: Option<&str>,
        config_json: &str,
    ) -> Result<i64, String> {
        let id = sqlx::query(
            "INSERT INTO vng_reports (recording_id, pdf_path, config_json) VALUES (?, ?, ?)"
        )
        .bind(recording_id)
        .bind(pdf_path)
        .bind(config_json)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?
        .last_insert_rowid();

        Ok(id)
    }

    /// Get all recordings with their file paths for a session (used when deleting)
    pub async fn get_session_recordings_paths(&self, session_id: i64) -> Result<Vec<(i64, Option<String>, Option<String>)>, String> {
        sqlx::query_as::<_, (i64, Option<String>, Option<String>)>(
            "SELECT id, video_path, data_path FROM recordings WHERE session_id = ?"
        )
        .bind(session_id)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| e.to_string())
    }
}
