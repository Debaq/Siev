use std::fs;
use std::path::Path;
use minimp4::Mp4Muxer;

/// Check if the playback MP4 already exists
pub fn playback_mp4_exists(bundle_path: &Path) -> bool {
    bundle_path.join("video").join("playback.mp4").exists()
}

/// Get the path to the raw H.264 file
pub fn raw_h264_path(bundle_path: &Path) -> std::path::PathBuf {
    bundle_path.join("video").join("raw_capture.mp4")
}

/// Get the path to the playback MP4 file
pub fn playback_mp4_path(bundle_path: &Path) -> std::path::PathBuf {
    bundle_path.join("video").join("playback.mp4")
}

/// Convert raw H.264 Annex B stream to a proper MP4 container
/// that can be played by HTML5 <video> element.
///
/// The raw file produced by openh264 encoder is a bare H.264 Annex B bitstream
/// (start codes + NAL units). This function wraps it in an MP4 container.
pub fn convert_h264_to_mp4(
    raw_h264_path: &Path,
    output_mp4_path: &Path,
    width: u32,
    height: u32,
    fps: u32,
) -> Result<(), String> {
    // Read the raw H.264 bitstream
    let h264_data = fs::read(raw_h264_path)
        .map_err(|e| format!("Failed to read H.264 file: {}", e))?;

    if h264_data.is_empty() {
        return Err("H.264 file is empty".to_string());
    }

    // Create output file
    let output_file = fs::File::create(output_mp4_path)
        .map_err(|e| format!("Failed to create MP4 file: {}", e))?;

    let mut muxer = Mp4Muxer::new(output_file);
    muxer.init_video(width as i32, height as i32, false, "Session Recording");

    // minimp4 write_video_with_fps takes the full Annex B bitstream
    // and handles NAL unit parsing internally
    muxer.write_video_with_fps(&h264_data, fps);
    muxer.close();

    let file_size = fs::metadata(output_mp4_path)
        .map(|m| m.len())
        .unwrap_or(0);

    println!(
        "[VideoConvert] Converted H.264 -> MP4: {:?} ({}x{}@{}fps, {} bytes)",
        output_mp4_path,
        width,
        height,
        fps,
        file_size,
    );

    Ok(())
}

/// Count the number of video frames in a raw H.264 Annex B file.
/// Counts NAL units of type 1 (non-IDR slice) and 5 (IDR slice).
pub fn count_h264_frames(raw_path: &Path) -> usize {
    if let Ok(data) = fs::read(raw_path) {
        let nals = parse_annex_b_nals(&data);
        nals.iter().filter(|nal| {
            if !nal.is_empty() {
                let nal_type = nal[0] & 0x1F;
                nal_type == 1 || nal_type == 5 // non-IDR slice or IDR slice
            } else {
                false
            }
        }).count()
    } else {
        0
    }
}

/// Parse Annex B NAL units from H.264 bitstream
/// Finds 00 00 00 01 or 00 00 01 start code patterns
fn parse_annex_b_nals(data: &[u8]) -> Vec<&[u8]> {
    let mut nals = Vec::new();
    let mut i = 0;
    let len = data.len();

    // Find first start code
    let mut nal_start = None;

    while i < len {
        // Check for 4-byte start code: 00 00 00 01
        if i + 3 < len && data[i] == 0 && data[i + 1] == 0 && data[i + 2] == 0 && data[i + 3] == 1 {
            if let Some(start) = nal_start {
                // Save previous NAL
                let end = i;
                if end > start {
                    nals.push(&data[start..end]);
                }
            }
            i += 4;
            nal_start = Some(i);
            continue;
        }
        // Check for 3-byte start code: 00 00 01
        if i + 2 < len && data[i] == 0 && data[i + 1] == 0 && data[i + 2] == 1 {
            if let Some(start) = nal_start {
                let end = i;
                if end > start {
                    nals.push(&data[start..end]);
                }
            }
            i += 3;
            nal_start = Some(i);
            continue;
        }
        i += 1;
    }

    // Last NAL
    if let Some(start) = nal_start {
        if start < len {
            nals.push(&data[start..len]);
        }
    }

    nals
}

/// Auto-detect video dimensions from the raw H.264 file by parsing SPS NAL unit.
/// Falls back to provided defaults if parsing fails.
pub fn detect_video_dimensions(raw_path: &Path, default_w: u32, default_h: u32) -> (u32, u32) {
    if let Ok(data) = fs::read(raw_path) {
        let nals = parse_annex_b_nals(&data);
        for nal in &nals {
            if !nal.is_empty() {
                let nal_type = nal[0] & 0x1F;
                if nal_type == 7 {
                    // SPS NAL - try to parse dimensions
                    if let Some((w, h)) = parse_sps_dimensions(nal) {
                        return (w, h);
                    }
                }
            }
        }
    }
    (default_w, default_h)
}

/// Minimal SPS parser to extract width and height
fn parse_sps_dimensions(sps: &[u8]) -> Option<(u32, u32)> {
    // This is a simplified parser that works for baseline profile
    // SPS structure: nal_header(1) + profile(1) + constraints(1) + level(1) + ...
    if sps.len() < 5 {
        return None;
    }

    // Use a bitstream reader approach
    let mut reader = BitstreamReader::new(&sps[1..]); // Skip NAL header byte

    let _profile_idc = reader.read_bits(8)?;
    let _constraint_flags = reader.read_bits(8)?;
    let _level_idc = reader.read_bits(8)?;
    let _sps_id = reader.read_exp_golomb()?; // seq_parameter_set_id

    if _profile_idc == 100 || _profile_idc == 110 || _profile_idc == 122 ||
       _profile_idc == 244 || _profile_idc == 44 || _profile_idc == 83 ||
       _profile_idc == 86 || _profile_idc == 118 || _profile_idc == 128 {
        let chroma_format = reader.read_exp_golomb()?;
        if chroma_format == 3 {
            reader.read_bits(1)?; // separate_colour_plane_flag
        }
        reader.read_exp_golomb()?; // bit_depth_luma
        reader.read_exp_golomb()?; // bit_depth_chroma
        reader.read_bits(1)?; // qpprime_y_zero_transform_bypass
        let seq_scaling_matrix = reader.read_bits(1)?;
        if seq_scaling_matrix == 1 {
            let limit = if chroma_format != 3 { 8 } else { 12 };
            for _ in 0..limit {
                let present = reader.read_bits(1)?;
                if present == 1 {
                    // Skip scaling list
                    let size = if limit <= 6 { 16 } else { 64 };
                    let mut last_scale = 8i32;
                    let mut next_scale = 8i32;
                    for _ in 0..size {
                        if next_scale != 0 {
                            let delta = reader.read_signed_exp_golomb()?;
                            next_scale = (last_scale + delta + 256) % 256;
                        }
                        last_scale = if next_scale == 0 { last_scale } else { next_scale };
                    }
                }
            }
        }
    }

    let _log2_max_frame_num = reader.read_exp_golomb()?;
    let pic_order_cnt_type = reader.read_exp_golomb()?;

    if pic_order_cnt_type == 0 {
        reader.read_exp_golomb()?; // log2_max_pic_order_cnt_lsb
    } else if pic_order_cnt_type == 1 {
        reader.read_bits(1)?; // delta_pic_order_always_zero
        reader.read_signed_exp_golomb()?; // offset_for_non_ref_pic
        reader.read_signed_exp_golomb()?; // offset_for_top_to_bottom
        let num_ref = reader.read_exp_golomb()?;
        for _ in 0..num_ref {
            reader.read_signed_exp_golomb()?;
        }
    }

    let _max_num_ref_frames = reader.read_exp_golomb()?;
    let _gaps_in_frame_num = reader.read_bits(1)?;
    let pic_width = reader.read_exp_golomb()? + 1;
    let pic_height = reader.read_exp_golomb()? + 1;

    let width = pic_width * 16;
    let height = pic_height * 16;

    Some((width as u32, height as u32))
}

/// Simple bitstream reader for parsing H.264 headers
struct BitstreamReader<'a> {
    data: &'a [u8],
    byte_pos: usize,
    bit_pos: u8,
}

impl<'a> BitstreamReader<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, byte_pos: 0, bit_pos: 0 }
    }

    fn read_bits(&mut self, count: u8) -> Option<u32> {
        let mut value = 0u32;
        for _ in 0..count {
            if self.byte_pos >= self.data.len() {
                return None;
            }
            let bit = (self.data[self.byte_pos] >> (7 - self.bit_pos)) & 1;
            value = (value << 1) | bit as u32;
            self.bit_pos += 1;
            if self.bit_pos >= 8 {
                self.bit_pos = 0;
                self.byte_pos += 1;
            }
        }
        Some(value)
    }

    fn read_exp_golomb(&mut self) -> Option<u32> {
        let mut leading_zeros = 0u32;
        loop {
            let bit = self.read_bits(1)?;
            if bit == 1 {
                break;
            }
            leading_zeros += 1;
            if leading_zeros > 31 {
                return None;
            }
        }
        if leading_zeros == 0 {
            return Some(0);
        }
        let suffix = self.read_bits(leading_zeros as u8)?;
        Some((1 << leading_zeros) - 1 + suffix)
    }

    fn read_signed_exp_golomb(&mut self) -> Option<i32> {
        let val = self.read_exp_golomb()?;
        if val == 0 {
            Some(0)
        } else if val % 2 == 1 {
            Some(((val + 1) / 2) as i32)
        } else {
            Some(-((val / 2) as i32))
        }
    }
}
