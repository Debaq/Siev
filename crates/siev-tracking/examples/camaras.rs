//! Lista camaras y formatos tal como los ve la app.
fn main() {
    match siev_tracking::vng::native_video::list_cameras() {
        Ok(cs) => {
            for c in cs {
                println!("[{}] {:?} ({})", c.index, c.name, c.description);
                match siev_tracking::vng::native_video::list_camera_formats(c.index) {
                    Ok(fs) => println!("    {} formatos, ej: {:?}", fs.len(), fs.iter().take(3).map(|f| format!("{}x{}@{} {}", f.width, f.height, f.fps, f.format)).collect::<Vec<_>>()),
                    Err(e) => println!("    formatos: ERROR {e}"),
                }
            }
        }
        Err(e) => println!("ERROR {e}"),
    }
}
