use std::fs::File;
use std::io::BufWriter;
use std::path::PathBuf;
use std::sync::mpsc::{self, SyncSender};
use std::thread::{self, JoinHandle};
use image::GrayImage;
use openh264::encoder::{Encoder, EncoderConfig};
use openh264::formats::YUVSlices;

enum VideoCommand {
    Frame(GrayImage),
    Stop,
}

pub struct VideoRecorder {
    sender: SyncSender<VideoCommand>,
    handle: Option<JoinHandle<()>>,
}

impl VideoRecorder {
    pub fn start(path: PathBuf, width: u32, height: u32, fps: u32) -> Result<Self, String> {
        // Ensure dimensions are even (required by H.264)
        let enc_w = (width & !1) as usize;
        let enc_h = (height & !1) as usize;

        let (tx, rx) = mpsc::sync_channel::<VideoCommand>(4);

        let handle = thread::spawn(move || {
            let config = EncoderConfig::new()
                .max_frame_rate(fps as f32)
                .rate_control_mode(openh264::encoder::RateControlMode::Quality);

            let mut encoder = match Encoder::with_api_config(openh264::OpenH264API::from_source(), config) {
                Ok(e) => e,
                Err(e) => {
                    eprintln!("[VideoRecorder] Failed to create encoder: {:?}", e);
                    return;
                }
            };

            let file = match File::create(&path) {
                Ok(f) => f,
                Err(e) => {
                    eprintln!("[VideoRecorder] Failed to create file: {}", e);
                    return;
                }
            };
            let mut writer = BufWriter::new(file);

            // Pre-allocate U/V planes filled with 128 (neutral chroma for grayscale)
            let uv_plane_size = (enc_w / 2) * (enc_h / 2);
            let u_plane = vec![128u8; uv_plane_size];
            let v_plane = vec![128u8; uv_plane_size];

            // Y plane buffer (reused per frame)
            let mut y_plane = vec![0u8; enc_w * enc_h];

            println!("[VideoRecorder] Started recording {}x{}@{} -> {:?}", enc_w, enc_h, fps, path);

            while let Ok(cmd) = rx.recv() {
                match cmd {
                    VideoCommand::Frame(gray) => {
                        // Copy gray pixels into Y plane, handling possible dimension mismatch
                        let gray_raw = gray.as_raw();
                        let gray_w = gray.width() as usize;
                        let gray_h = gray.height() as usize;

                        for row in 0..enc_h.min(gray_h) {
                            let src_start = row * gray_w;
                            let src_end = src_start + enc_w.min(gray_w);
                            let dst_start = row * enc_w;
                            let dst_end = dst_start + enc_w.min(gray_w);
                            if src_end <= gray_raw.len() && dst_end <= y_plane.len() {
                                y_plane[dst_start..dst_end].copy_from_slice(&gray_raw[src_start..src_end]);
                            }
                        }

                        let yuv = YUVSlices::new(
                            (&y_plane, &u_plane, &v_plane),
                            (enc_w, enc_h),
                            (enc_w, enc_w / 2, enc_w / 2),
                        );

                        match encoder.encode(&yuv) {
                            Ok(bitstream) => {
                                if let Err(e) = bitstream.write(&mut writer) {
                                    eprintln!("[VideoRecorder] Write error: {:?}", e);
                                }
                            }
                            Err(e) => {
                                eprintln!("[VideoRecorder] Encode error: {:?}", e);
                            }
                        }
                    }
                    VideoCommand::Stop => {
                        break;
                    }
                }
            }
            println!("[VideoRecorder] Stopped, file saved to {:?}", path);
        });

        Ok(Self {
            sender: tx,
            handle: Some(handle),
        })
    }

    /// Send a frame for encoding. Non-blocking: drops frame if buffer is full.
    pub fn send_frame(&self, frame: GrayImage) {
        let _ = self.sender.try_send(VideoCommand::Frame(frame));
    }

    /// Stop recording and wait for the encoder thread to finish.
    pub fn stop(mut self) {
        let _ = self.sender.send(VideoCommand::Stop);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}
