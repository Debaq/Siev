use std::path::{Path, PathBuf};
use std::fs;
use serde::{Serialize, Deserialize};
use chrono::Local;
use crate::database::models::Patient;

/// Represents the metadata stored in session.json
#[derive(Debug, Serialize, Deserialize)]
pub struct SessionManifest {
    pub version: String, // Schema version, e.g., "1.0"
    pub created_at: String,
    pub patient: PatientSnapshot,
    pub test_type: String, // e.g., "VNG", "VHIT"
    pub description: Option<String>,
    pub specialist_id: Option<i64>,
}

/// A snapshot of patient data at the time of the session
#[derive(Debug, Serialize, Deserialize)]
pub struct PatientSnapshot {
    pub id: i64,
    pub first_name: String,
    pub last_name: String,
    pub dni: Option<String>,
    pub birth_date: Option<String>,
    pub gender: Option<String>,
}

impl From<&Patient> for PatientSnapshot {
    fn from(p: &Patient) -> Self {
        Self {
            id: p.id,
            first_name: p.first_name.clone(),
            last_name: p.last_name.clone(),
            dni: p.dni.clone(),
            birth_date: p.birth_date.map(|d| d.to_string()),
            gender: p.gender.clone(),
        }
    }
}

/// Manages the .siev directory bundle
pub struct SievBundle {
    pub root_path: PathBuf,
    pub bundle_path: PathBuf,
}

impl SievBundle {
    /// Creates a new SievBundle instance.
    /// Does not create directories on disk until `init()` is called.
    pub fn new(root_dir: &Path, patient: &Patient, test_type: &str, session_id: i64) -> Self {
        let patient_folder_name = format!("{}_{}_{}", patient.id, patient.first_name, patient.last_name)
            .replace(" ", "_")
            .replace(|c: char| !c.is_alphanumeric() && c != '_', "");

        let date_str = Local::now().format("%Y%m%d_%H%M%S").to_string();
        let bundle_name = format!("{}_{}_{}.siev", date_str, test_type, session_id);

        let patient_path = root_dir.join(patient_folder_name);
        let bundle_path = patient_path.join(bundle_name);

        Self {
            root_path: root_dir.to_path_buf(),
            bundle_path,
        }
    }

    /// Initializes the directory structure and writes session.json
    pub fn init(&self, manifest: &SessionManifest) -> Result<(), std::io::Error> {
        // Create bundle directory (and parents)
        fs::create_dir_all(&self.bundle_path)?;

        // Create 'video' subdirectory
        let video_dir = self.bundle_path.join("video");
        fs::create_dir_all(&video_dir)?;

        // Write session.json
        let manifest_path = self.bundle_path.join("session.json");
        let json = serde_json::to_string_pretty(manifest)?;
        fs::write(manifest_path, json)?;

        Ok(())
    }

    /// Returns the path to the main data file (e.g., data.bin)
    pub fn get_data_path(&self) -> PathBuf {
        self.bundle_path.join("data.bin")
    }

    /// Returns the path to the video capture file
    pub fn get_video_path(&self) -> PathBuf {
        self.bundle_path.join("video").join("raw_capture.mp4")
    }
    
    /// Returns the path to the bundle directory
    pub fn path(&self) -> &Path {
        &self.bundle_path
    }

    /// Tries to load a manifest from an existing .siev directory
    pub fn load_manifest(path: &Path) -> Result<SessionManifest, std::io::Error> {
        let manifest_path = path.join("session.json");
        let content = fs::read_to_string(manifest_path)?;
        let manifest: SessionManifest = serde_json::from_str(&content)?;
        Ok(manifest)
    }
}
