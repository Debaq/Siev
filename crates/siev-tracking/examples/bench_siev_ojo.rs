//! Velocidad de siev_ojo: version escrita a mano vs ONNX Runtime, 1 hilo.
//!
//!   cargo run --release -p siev-tracking --example bench_siev_ojo -- <modelo.bin> <modelo.onnx>

use std::time::Instant;

use ndarray::Array4;
use ort::session::Session;
use siev_tracking::vng::siev_ojo::SievOjo;

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let mut red = SievOjo::cargar(a[0].as_ref()).expect("pesos");
    let mut ses = Session::builder()
        .and_then(|b| b.with_intra_threads(1))
        .and_then(|b| b.commit_from_file(&a[1]))
        .expect("onnx");

    // (alto, ancho): ROI alrededor del iris, mitad de la combinada, mitad del cuadro crudo
    for (h, w, nombre) in [(64, 64, "ROI 64x64"), (96, 128, "mitad combinada 96x128"), (192, 160, "mitad cruda 192x160")] {
        let img: Vec<f32> = (0..h * w).map(|i| (i * 37 % 251) as f32).collect();
        let n = if h * w > 10000 { 300 } else { 1000 };

        for _ in 0..20 {
            red.inferir(&img, h, w);
        }
        red.perfil = [0.0; 20];
        let t = Instant::now();
        let mut acc = 0.0;
        for _ in 0..n {
            acc += red.inferir(&img, h, w).pico().0;
        }
        let ms_rust = t.elapsed().as_secs_f64() * 1000.0 / n as f64;
        let tot: f64 = red.perfil.iter().sum();
        println!("  perfil %: {:?}", red.perfil.iter().map(|v| (v / tot * 100.0).round() as i32).collect::<Vec<_>>());
        red.perfil = [0.0; 20];

        let arr = Array4::from_shape_vec((1, 1, h, w), img.clone()).unwrap();
        let correr = |ses: &mut Session| {
            let v = ort::value::Value::from_array(arr.clone()).unwrap();
            let o = ses.run(ort::inputs![v]).unwrap();
            o.get("mapa").unwrap().try_extract_array::<f32>().unwrap()[[0, 0, 0, 0]]
        };
        for _ in 0..20 {
            correr(&mut ses);
        }
        let t = Instant::now();
        for _ in 0..n {
            acc += correr(&mut ses);
        }
        let ms_ort = t.elapsed().as_secs_f64() * 1000.0 / n as f64;
        println!("{nombre:>24}: a mano {ms_rust:6.3} ms | ort {ms_ort:6.3} ms | x{:.2}  ({acc:.0})", ms_ort / ms_rust);
    }
}
