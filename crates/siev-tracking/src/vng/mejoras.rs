//! Mejoras opcionales del detector de pupila para imagen de baja calidad.
//! Apagadas, el detector es identico al de referencia (prueba de regresion).
//!
//! - `quitar_reflejos`: los reflejos corneales del LED IR son puntos casi
//!   blancos que cortan el contorno de la pupila al umbralizar. Se rellenan
//!   desde su borde hacia adentro con el promedio de sus vecinos no saturados.
//! - `umbral_por_valle`: en la ventana de busqueda la pupila es el primer modo
//!   oscuro del histograma. El umbral se pone en el valle entre ese modo y el
//!   siguiente (iris). A diferencia de un percentil fijo, no depende de que
//!   fraccion de la ventana ocupa la pupila.

use image::{GrayImage, Luma};
use imageproc::distance_transform::Norm;
use imageproc::morphology::dilate_mut;

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct OpcionesDetector {
    pub quitar_reflejos: bool,
    pub umbral_valle: bool,
    pub umbral_semilla: bool,
}

/// Rellena los reflejos especulares en el lugar.
///
/// Solo actua si lo brillante es poco (reflejos puntuales). Si una fraccion
/// grande de la ventana esta saturada no son reflejos sino piel o el
/// acolchado de la mascara, y rellenarlo seria caro e inutil.
pub fn quitar_reflejos(img: &mut GrayImage) {
    const FRACCION_MAX: f32 = 0.04;
    const CAPAS_MAX: usize = 8;

    let (w, h) = img.dimensions();
    if w < 3 || h < 3 {
        return;
    }
    let wu = w as usize;
    let n = (w * h) as f32;
    let media = img.as_raw().iter().map(|&v| v as f32).sum::<f32>() / n;
    // Reflejo = casi saturado y muy por encima del nivel de la ventana.
    let umbral = (media + 60.0).clamp(170.0, 250.0) as u8;

    let brillantes = img.as_raw().iter().filter(|&&v| v >= umbral).count();
    if brillantes == 0 || brillantes as f32 > n * FRACCION_MAX {
        return;
    }

    let mut mascara = GrayImage::new(w, h);
    for (x, y, p) in img.enumerate_pixels() {
        if p.0[0] >= umbral {
            mascara.put_pixel(x, y, Luma([255]));
        }
    }
    // El halo del reflejo tambien esta aclarado: ampliar 2 px.
    dilate_mut(&mut mascara, Norm::LInf, 2);

    let mut pendientes: Vec<usize> =
        mascara.as_raw().iter().enumerate().filter(|(_, &m)| m != 0).map(|(i, _)| i).collect();
    let mut cambios: Vec<(usize, u8)> = Vec::new();

    // Relleno por capas, de afuera hacia adentro, solo sobre los marcados.
    for _ in 0..CAPAS_MAX {
        if pendientes.is_empty() {
            break;
        }
        cambios.clear();
        {
            let (raw, m) = (img.as_raw(), mascara.as_raw());
            for &i in &pendientes {
                let (x, y) = ((i % wu) as i32, (i / wu) as i32);
                let (mut suma, mut cuenta) = (0u32, 0u32);
                for dy in -1i32..=1 {
                    for dx in -1i32..=1 {
                        let (nx, ny) = (x + dx, y + dy);
                        if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                            continue;
                        }
                        let j = ny as usize * wu + nx as usize;
                        if m[j] == 0 {
                            suma += raw[j] as u32;
                            cuenta += 1;
                        }
                    }
                }
                if let Some(v) = suma.checked_div(cuenta) {
                    cambios.push((i, v as u8));
                }
            }
        }
        if cambios.is_empty() {
            break;
        }
        let (raw, m) = (img.as_mut(), &mut mascara);
        for &(i, v) in &cambios {
            raw[i] = v;
            m.as_mut()[i] = 0;
        }
        pendientes.retain(|&i| mascara.as_raw()[i] != 0);
    }
}

/// Umbral en el valle tras el primer modo oscuro del histograma, o `None` si
/// el histograma no muestra un modo oscuro separado.
pub fn umbral_por_valle(img: &GrayImage) -> Option<u8> {
    let mut hist = [0f32; 256];
    for p in img.pixels() {
        hist[p.0[0] as usize] += 1.0;
    }
    let n: f32 = hist.iter().sum();
    if n < 64.0 {
        return None;
    }

    // Suavizado (ventana 9) para que el ruido no fabrique picos.
    let mut hs = [0f32; 256];
    for (i, v) in hs.iter_mut().enumerate() {
        let (a, b) = (i.saturating_sub(4), (i + 4).min(255));
        *v = hist[a..=b].iter().sum::<f32>() / (b - a + 1) as f32;
    }

    // Nivel mas oscuro con presencia real (0.5 % acumulado).
    let mut acc = 0.0;
    let mut inicio = 0usize;
    for (i, &c) in hist.iter().enumerate() {
        acc += c;
        if acc >= n * 0.005 {
            inicio = i;
            break;
        }
    }

    // Primer maximo local desde ahi: el modo de la pupila.
    let mut pico = None;
    for i in inicio.max(1)..255 {
        if hs[i] > 0.0 && hs[i] >= hs[i - 1] && hs[i] > hs[i + 1] {
            pico = Some(i);
            break;
        }
    }
    let pico = pico?;

    // Primer minimo despues del pico, seguido de una subida clara (modo del iris).
    let mut valle = None;
    for i in (pico + 1)..255 {
        if hs[i] <= hs[i - 1] && hs[i] < hs[i + 1] {
            let sube = hs[i + 1..(i + 40).min(256)].iter().cloned().fold(0.0, f32::max);
            if sube > hs[i] * 1.25 + 0.5 {
                valle = Some(i);
                break;
            }
        }
    }
    let valle = valle?;

    // La pupila no puede ser ni una mota ni casi toda la ventana.
    let fraccion = hist[..=valle].iter().sum::<f32>() / n;
    if !(0.01..=0.45).contains(&fraccion) {
        return None;
    }
    Some(valle as u8)
}

/// Umbral por crecimiento desde el punto mas oscuro: se sube el umbral desde
/// el minimo y se mide la region conexa que contiene ese punto. Mientras es
/// la pupila crece redonda; al derramarse hacia iris o pestañas pierde
/// circularidad o toca el borde. Se elige el umbral de mejor forma.
/// Pensado para pupila de bajo contraste frente al iris (sin valle claro).
pub fn umbral_por_semilla(img: &GrayImage, area_min: u32) -> Option<u8> {
    let (w, h) = img.dimensions();
    if w < 8 || h < 8 {
        return None;
    }
    let raw = img.as_raw();
    let (wu, hu) = (w as usize, h as usize);

    // Semilla: minimo lejos del borde.
    let mut semilla = None;
    let mut minimo = u8::MAX;
    for y in 2..hu - 2 {
        for x in 2..wu - 2 {
            let v = raw[y * wu + x];
            if v < minimo {
                minimo = v;
                semilla = Some(y * wu + x);
            }
        }
    }
    let semilla = semilla?;

    let total = wu * hu;
    let mut visitado = vec![0u16; total]; // marca = numero de iteracion
    let mut pila = Vec::with_capacity(1024);
    let mut mejor: Option<(f32, u8)> = None;

    for (iter, delta) in (2u16..=60).step_by(2).enumerate() {
        let t = (minimo as u16 + delta).min(254) as u8;
        let marca = iter as u16 + 1;
        pila.clear();
        pila.push(semilla);
        visitado[semilla] = marca;
        let (mut area, mut borde, mut toca) = (0usize, 0usize, false);
        while let Some(i) = pila.pop() {
            area += 1;
            let (x, y) = (i % wu, i / wu);
            if x == 0 || y == 0 || x == wu - 1 || y == hu - 1 {
                toca = true;
            }
            let mut es_borde = false;
            for (dx, dy) in [(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
                let (nx, ny) = (x as i32 + dx, y as i32 + dy);
                if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                    es_borde = true;
                    continue;
                }
                let j = ny as usize * wu + nx as usize;
                if raw[j] <= t {
                    if visitado[j] != marca {
                        visitado[j] = marca;
                        pila.push(j);
                    }
                } else {
                    es_borde = true;
                }
            }
            if es_borde {
                borde += 1;
            }
        }
        if toca || area * 2 > total {
            break; // se derramo: los umbrales mayores solo empeoran
        }
        if area < area_min.max(12) as usize || borde == 0 {
            continue;
        }
        // Circularidad con perimetro en pixeles de borde (aprox. 2*pi*r).
        let circ = (4.0 * std::f32::consts::PI * area as f32) / (borde as f32 * borde as f32);
        // A igual forma, preferir la region mas grande (pupila completa).
        let puntaje = circ.min(1.2) * (area as f32).powf(0.25);
        if mejor.is_none_or(|(p, _)| puntaje > p) {
            mejor = Some((puntaje, t));
        }
    }
    mejor.map(|(_, t)| t)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Ojo sintetico: fondo (piel) 170, iris 90 radio 30, pupila 25 radio 10,
    /// reflejo 255 radio 3 en el borde de la pupila. Ruido +-6.
    fn ojo() -> GrayImage {
        let (w, h) = (100u32, 80u32);
        let (cx, cy) = (50.0f32, 40.0f32);
        GrayImage::from_fn(w, h, |x, y| {
            let d = ((x as f32 - cx).powi(2) + (y as f32 - cy).powi(2)).sqrt();
            let dr = ((x as f32 - (cx + 8.0)).powi(2) + (y as f32 - (cy - 4.0)).powi(2)).sqrt();
            let ruido = (((x * 7 + y * 13) % 13) as i32 - 6) as f32;
            let base = if dr <= 3.0 {
                255.0
            } else if d <= 10.0 {
                25.0
            } else if d <= 30.0 {
                90.0
            } else {
                170.0
            };
            Luma([(base + if base < 255.0 { ruido } else { 0.0 }).clamp(0.0, 255.0) as u8])
        })
    }

    #[test]
    fn reflejo_se_rellena_con_tono_oscuro() {
        let mut img = ojo();
        quitar_reflejos(&mut img);
        assert!(img.pixels().all(|p| p.0[0] < 200), "quedo un reflejo");
        // El centro del reflejo cae dentro de la pupila: debe quedar oscuro.
        assert!(img.get_pixel(57, 36).0[0] < 80, "valor {}", img.get_pixel(57, 36).0[0]);
    }

    #[test]
    fn sin_reflejos_no_toca_la_imagen() {
        let img = GrayImage::from_fn(40, 40, |x, y| Luma([(60 + (x + y) % 40) as u8]));
        let mut copia = img.clone();
        quitar_reflejos(&mut copia);
        assert_eq!(img, copia);
    }

    #[test]
    fn valle_separa_pupila_de_iris() {
        let mut img = ojo();
        quitar_reflejos(&mut img);
        let u = umbral_por_valle(&img).expect("sin valle");
        assert!(u > 32 && u < 84, "umbral {u} fuera del hueco pupila(25)-iris(90)");
        let bajo = img.pixels().filter(|p| p.0[0] <= u).count() as f32;
        let pupila = std::f32::consts::PI * 100.0;
        assert!((bajo - pupila).abs() / pupila < 0.35, "{bajo} px bajo umbral, pupila ~{pupila}");
    }

    #[test]
    fn semilla_encuentra_pupila_de_bajo_contraste() {
        // Pupila 8, iris 20 (solo 12 niveles de diferencia), pestañas 15 en
        // una franja que toca el borde.
        let img = GrayImage::from_fn(100, 80, |x, y| {
            let d = ((x as f32 - 50.0).powi(2) + (y as f32 - 45.0).powi(2)).sqrt();
            let ruido = (((x * 7 + y * 13) % 5) as i32 - 2) as f32;
            let base = if d <= 9.0 { 8.0 } else if y < 18 { 15.0 } else if d <= 28.0 { 20.0 } else { 60.0 };
            Luma([(base + ruido).max(0.0) as u8])
        });
        let u = umbral_por_semilla(&img, 30).expect("sin umbral");
        let bajo: Vec<_> = img.enumerate_pixels().filter(|(_, _, p)| p.0[0] <= u).collect();
        let (cx, cy) = bajo.iter().fold((0.0, 0.0), |(a, b), (x, y, _)| (a + *x as f32, b + *y as f32));
        let n = bajo.len() as f32;
        assert!(((cx / n) - 50.0).abs() < 3.0 && ((cy / n) - 45.0).abs() < 3.0, "centro ({}, {}) u={u}", cx / n, cy / n);
    }

    #[test]
    fn imagen_plana_no_da_umbral() {
        let img = GrayImage::from_pixel(50, 50, Luma([120]));
        assert_eq!(umbral_por_valle(&img), None);
    }
}
