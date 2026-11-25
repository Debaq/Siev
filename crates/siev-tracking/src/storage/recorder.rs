use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::sync::mpsc::{self, SyncSender};
use crate::math::processor::ProcessedEyeData;

pub enum RecorderCommand {
    Record(ProcessedEyeData),
    Stop,
}

/// Grabador de datos oculares en JSONL, en hilo propio.
pub struct SessionRecorder {
    sender: SyncSender<RecorderCommand>,
}

impl SessionRecorder {
    pub fn start(path: PathBuf) -> Self {
        let (tx, rx) = mpsc::sync_channel::<RecorderCommand>(1000);

        std::thread::spawn(move || {
            let file = match File::create(&path) {
                Ok(f) => f,
                Err(e) => {
                    eprintln!("Failed to create recording file: {}", e);
                    return;
                }
            };
            let mut writer = BufWriter::new(file);

            while let Ok(cmd) = rx.recv() {
                match cmd {
                    RecorderCommand::Record(data) => {
                        if let Ok(json) = serde_json::to_string(&data) {
                            if let Err(e) = writeln!(writer, "{}", json) {
                                eprintln!("Failed to write to recording file: {}", e);
                                break;
                            }
                        }
                    }
                    RecorderCommand::Stop => break,
                }
            }
            let _ = writer.flush();
            println!("Recording stopped and saved to {:?}", path);
        });

        Self { sender: tx }
    }

    pub fn record(&self, data: ProcessedEyeData) {
        let _ = self.sender.try_send(RecorderCommand::Record(data));
    }

    pub fn stop(&self) {
        let _ = self.sender.send(RecorderCommand::Stop);
    }
}
