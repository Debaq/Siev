use pyo3::prelude::*;
use numpy::{PyReadonlyArray3, PyArray2, ToPyArray};
use ndarray::{Array2, Axis};
use image::GrayImage;
use imageproc::filter::gaussian_blur_f32;
use imageproc::morphology::{erode_mut, dilate_mut};
use imageproc::distance_transform::Norm;
use imageproc::contours::find_contours;
use serde::Serialize;

#[derive(Serialize)]
pub struct RustPupilResult {
    pub center_x: f32,
    pub center_y: f32,
    pub radius: f32,
    pub confidence: f32,
    pub found: bool,
}

#[pyfunction]
fn process_and_detect_bgr(
    input: PyReadonlyArray3<u8>, 
    blur_sigma: f32, 
    threshold: u8, 
    erode_iters: u32,
    dilate_iters: u32,
    min_area: f32,
    max_area: f32,
    return_mask: bool // NUEVO PARÁMETRO
) -> PyResult<(Option<Py<PyArray2<u8>>>, String)> {
    let array = input.as_array();
    let (height, width, _channels) = (array.shape()[0], array.shape()[1], array.shape()[2]);
    
    // 1. Extraer canal azul (ultra rápido)
    let gray_array: Array2<u8> = array.index_axis(Axis(2), 0).to_owned();
    
    // 2. Convertir a GrayImage
    let mut processed = GrayImage::from_raw(width as u32, height as u32, gray_array.clone().into_raw_vec())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid image dimensions"))?;

    // 3. Gaussian Blur
    if blur_sigma > 0.1 {
        processed = gaussian_blur_f32(&processed, blur_sigma);
    }

    // 4. Threshold (Invertido)
    for pixel in processed.pixels_mut() {
        if pixel.0[0] <= threshold {
            pixel.0[0] = 255;
        } else {
            pixel.0[0] = 0;
        }
    }

    // 5. Morfología
    let norm = Norm::LInf;
    for _ in 0..erode_iters { erode_mut(&mut processed, norm, 1); }
    for _ in 0..dilate_iters { dilate_mut(&mut processed, norm, 1); }

    // 6. Encontrar Contornos
    let contours = find_contours::<i32>(&processed);
    let mut best_result = RustPupilResult {
        center_x: 0.0, center_y: 0.0, radius: 0.0, confidence: 0.0, found: false,
    };

    let mut max_found_area = 0.0;
    for contour in contours {
        let points = &contour.points;
        if points.len() < 5 { continue; }

        let mut m00 = 0.0;
        let mut m10 = 0.0;
        let mut m01 = 0.0;
        for p in points {
            m00 += 1.0;
            m10 += p.x as f32;
            m01 += p.y as f32;
        }

        let area = m00;
        if area > min_area && area < max_area {
            if area > max_found_area {
                max_found_area = area;
                let cx = m10 / m00;
                let cy = m01 / m00;
                let mut dist_sum = 0.0;
                for p in points {
                    let dx = p.x as f32 - cx;
                    let dy = p.y as f32 - cy;
                    dist_sum += (dx*dx + dy*dy).sqrt();
                }
                let radius = dist_sum / points.len() as f32;
                best_result = RustPupilResult {
                    center_x: cx, center_y: cy, radius, confidence: 0.8, found: true,
                };
            }
        }
    }

    // 7. Preparar salida (Solo devolver máscara si se pide)
    let mask_py = if return_mask {
        let result_vec = processed.into_raw();
        let result_array = Array2::from_shape_vec((height, width), result_vec)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Array shape error: {}", e)))?;
        
        Python::with_gil(|py| {
            Some(result_array.to_pyarray(py).to_owned().into())
        })
    } else {
        None
    };

    let json_res = serde_json::to_string(&best_result).unwrap_or_default();
    Ok((mask_py, json_res))
}

#[pymodule]
fn siev_vision_py(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_and_detect_bgr, m)?)?;
    Ok(())
}
