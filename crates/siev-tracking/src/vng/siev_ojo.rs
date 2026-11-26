//! Inferencia de siev_ojo escrita a mano: sin ONNX Runtime ni dependencias.
//!
//! La receta (arquitectura r01, ver `tools/modelo_ojo/kaggle/entrenar.py`) esta
//! en `forward`; del entrenamiento solo se cargan los numeros: el `.bin` de
//! `tools/modelo_ojo/exportar_pesos.py` (BatchNorm ya fusionada en cada Conv).
//!
//! Tensores en formato CHW, un plano por canal con paso (`stride`) multiplo de
//! 16. Las conv 1x1 y la conv 3x3 de la cabeza usan el mismo micro-kernel
//! (4 canales de salida x 16 pixeles en registros); la 3x3 se reduce a 9
//! desplazamientos sobre una copia con borde. Con AVX2+FMA (detectado al
//! arrancar) el compilador lo vectoriza a 8 floats por instruccion.

const MAGIA: &[u8; 4] = b"SOJO";

/// Forma de cada Conv en el orden del `.bin`: (tipo, canales entrada, salida).
#[derive(Clone, Copy)]
enum Tipo {
    /// 3x3 completa
    Full,
    /// 3x3 depthwise (ci = co)
    Dw,
    /// 1x1
    Pw,
}

/// Version 1 del .bin: arquitectura r01/r02 (cabeza 3x3 completa 48->32).
const CAPAS_V1: [(Tipo, usize, usize); 23] = [
    (Tipo::Full, 1, 16),
    (Tipo::Dw, 16, 16),
    (Tipo::Pw, 16, 32),
    (Tipo::Dw, 32, 32),
    (Tipo::Pw, 32, 32),
    (Tipo::Dw, 32, 32),
    (Tipo::Pw, 32, 64),
    (Tipo::Dw, 64, 64),
    (Tipo::Pw, 64, 64),
    (Tipo::Dw, 64, 64),
    (Tipo::Pw, 64, 64),
    (Tipo::Dw, 64, 64),
    (Tipo::Pw, 64, 96),
    (Tipo::Dw, 96, 96),
    (Tipo::Pw, 96, 96),
    (Tipo::Dw, 96, 96),
    (Tipo::Pw, 96, 96),
    (Tipo::Dw, 160, 160),
    (Tipo::Pw, 160, 64),
    (Tipo::Dw, 96, 96),
    (Tipo::Pw, 96, 48),
    (Tipo::Full, 48, 32),
    (Tipo::Pw, 32, 4),
];

/// Version 2 del .bin: arquitectura r03 (cabeza depthwise 3x3 + 1x1 48->32).
const CAPAS_V2: [(Tipo, usize, usize); 24] = {
    let mut c = [(Tipo::Pw, 0, 0); 24];
    let mut i = 0;
    while i < 21 {
        c[i] = CAPAS_V1[i];
        i += 1;
    }
    c[21] = (Tipo::Dw, 48, 48);
    c[22] = (Tipo::Pw, 48, 32);
    c[23] = (Tipo::Pw, 32, 4);
    c
};

fn tam_pesos(t: Tipo, ci: usize, co: usize) -> usize {
    match t {
        Tipo::Full => co * ci * 9,
        Tipo::Dw => co * 9,
        Tipo::Pw => co * ci,
    }
}

#[inline(always)]
fn redondear16(n: usize) -> usize {
    n.div_ceil(16) * 16
}

/// Tensor CHW reutilizable (no reserva memoria si el tamaño no cambia).
#[derive(Default)]
struct T {
    c: usize,
    h: usize,
    w: usize,
    s: usize,
    d: Vec<f32>,
}

impl T {
    /// Ajusta forma; `extra` floats de holgura por plano (lecturas desplazadas).
    fn forma(&mut self, c: usize, h: usize, w: usize, extra: usize) {
        self.c = c;
        self.h = h;
        self.w = w;
        self.s = redondear16(h * w + extra);
        let n = c * self.s;
        if self.d.len() < n {
            self.d.resize(n, 0.0);
        }
    }
}

/// Resultado: mapa [4][alto/4][ancho/4] = logit de centro, dx, dy, r/16.
pub struct Mapa<'a> {
    pub alto: usize,
    pub ancho: usize,
    datos: &'a [f32],
    paso_fila: usize,
    paso_plano: usize,
}

impl Mapa<'_> {
    #[inline]
    pub fn get(&self, canal: usize, y: usize, x: usize) -> f32 {
        self.datos[canal * self.paso_plano + y * self.paso_fila + x]
    }

    /// Pico del mapa: (confianza 0..1, cx, cy, r) en px de la entrada.
    pub fn pico(&self) -> (f32, f32, f32, f32) {
        let (mut mejor, mut iy, mut ix) = (f32::MIN, 0, 0);
        for y in 0..self.alto {
            for x in 0..self.ancho {
                let v = self.get(0, y, x);
                if v > mejor {
                    (mejor, iy, ix) = (v, y, x);
                }
            }
        }
        let conf = 1.0 / (1.0 + (-mejor).exp());
        let cx = (ix as f32 + self.get(1, iy, ix)) * 4.0;
        let cy = (iy as f32 + self.get(2, iy, ix)) * 4.0;
        (conf, cx, cy, self.get(3, iy, ix) * 16.0)
    }
}

pub struct SievOjo {
    p: Vec<f32>,
    /// (offset pesos, offset bias) por capa
    off: Vec<(usize, usize)>,
    version: u32,
    capas: &'static [(Tipo, usize, usize)],
    m: Vec<T>,
    /// Segundos acumulados por etapa (para perfilar).
    pub perfil: [f64; 20],
    esc: Vec<f32>,
}

impl SievOjo {
    pub fn cargar(ruta: &std::path::Path) -> Result<Self, String> {
        let b = std::fs::read(ruta).map_err(|e| format!("{}: {e}", ruta.display()))?;
        Self::desde_bytes(&b)
    }

    pub fn desde_bytes(b: &[u8]) -> Result<Self, String> {
        if b.len() < 12 || &b[0..4] != MAGIA {
            return Err("no es un .bin de siev_ojo".into());
        }
        let ver = u32::from_le_bytes(b[4..8].try_into().unwrap());
        let n = u32::from_le_bytes(b[8..12].try_into().unwrap()) as usize;
        let capas: &'static [(Tipo, usize, usize)] = match ver {
            1 => &CAPAS_V1,
            2 => &CAPAS_V2,
            _ => return Err(format!("version {ver} no soportada")),
        };
        let mut off = Vec::with_capacity(capas.len());
        let mut k = 0;
        for &(t, ci, co) in capas {
            let wn = tam_pesos(t, ci, co);
            off.push((k, k + wn));
            k += wn + co;
        }
        if n != k || b.len() != 12 + 4 * n {
            return Err(format!("el .bin trae {n} parametros, la version {ver} espera {k}"));
        }
        let p = b[12..].chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect();
        Ok(Self { p, off, version: ver, capas, m: (0..24).map(|_| T::default()).collect(), perfil: [0.0; 20], esc: Vec::new() })
    }

    /// Corre la red sobre una imagen gris 0..255 de `alto` x `ancho`
    /// (multiplos de 16). Sin reservas de memoria si el tamaño se repite.
    pub fn inferir(&mut self, img: &[f32], alto: usize, ancho: usize) -> Mapa<'_> {
        assert!(alto % 16 == 0 && ancho % 16 == 0 && alto > 0 && ancho > 0, "alto y ancho multiplos de 16");
        assert_eq!(img.len(), alto * ancho);
        #[cfg(target_arch = "x86_64")]
        {
            // SIEV_OJO_SIN_AVX=1 fuerza la ruta generica (para medir PCs sin AVX2).
            static SIN_AVX: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
            let sin_avx = *SIN_AVX.get_or_init(|| std::env::var("SIEV_OJO_SIN_AVX").is_ok_and(|v| v == "1"));
            if !sin_avx && std::arch::is_x86_feature_detected!("avx2") && std::arch::is_x86_feature_detected!("fma") {
                // SAFETY: se acaba de comprobar que la CPU tiene AVX2 y FMA.
                unsafe { self.forward_avx2(img, alto, ancho) };
                return self.mapa();
            }
        }
        self.forward::<false>(img, alto, ancho);
        self.mapa()
    }

    fn mapa(&self) -> Mapa<'_> {
        let o = &self.m[23];
        // v1: la salida conserva el ancho con borde (w + 2) de la conv 3x3
        let borde = if self.version == 1 { 2 } else { 0 };
        Mapa { alto: o.h, ancho: o.w - borde, datos: &o.d, paso_fila: o.w, paso_plano: o.s }
    }

    #[cfg(target_arch = "x86_64")]
    #[target_feature(enable = "avx2,fma")]
    unsafe fn forward_avx2(&mut self, img: &[f32], alto: usize, ancho: usize) {
        self.forward::<true>(img, alto, ancho);
    }

    #[inline(always)]
    fn forward<const FMA: bool>(&mut self, img: &[f32], h: usize, w: usize) {
        let mut m = std::mem::take(&mut self.m);
        let mut esc = std::mem::take(&mut self.esc);
        let mut perfil = self.perfil;
        let mut t0 = std::time::Instant::now();
        let mut marca = |k: usize| {
            let t = std::time::Instant::now();
            perfil[k] += (t - t0).as_secs_f64();
            t0 = t;
        };
        let p = &self.p;
        let capas = self.capas;
        let pw = |i: usize| -> (&[f32], &[f32]) {
            let (a, b) = self.off[i];
            let co = capas[i].2;
            (&p[a..b], &p[b..b + co])
        };

        // entrada normalizada
        m[0].forma(1, h, w, 0);
        for (d, &v) in m[0].d.iter_mut().zip(img) {
            *d = v / 255.0 - 0.5;
        }

        let (wt, b) = pw(0);
        let (mut o, mut cols) = (std::mem::take(&mut m[1]), std::mem::take(&mut m[22]));
        conv_stem::<FMA>(&m[0], wt, b, &mut cols, &mut o);
        m[1] = o;
        m[22] = cols;
        marca(0);

        // (capa dw, entrada, salida dw, stride, dilatacion) seguido de su pw
        let bloques: [(usize, usize, usize, usize, usize, usize); 8] = [
            // dw, pw, entrada, salida, stride, dilatacion
            (1, 2, 1, 3, 2, 1),
            (3, 4, 3, 5, 1, 1), // m[5] = skip /4
            (5, 6, 5, 7, 2, 1),
            (7, 8, 7, 9, 1, 1),
            (9, 10, 9, 11, 1, 2), // m[11] = skip /8
            (11, 12, 11, 13, 2, 1),
            (13, 14, 13, 15, 1, 2),
            (15, 16, 15, 17, 1, 4),
        ];
        for (nb, &(ldw, lpw, ent, sal, s, d)) in bloques.iter().enumerate() {
            let (wd, bd) = pw(ldw);
            let (a, mut tmp) = (std::mem::take(&mut m[ent]), std::mem::take(&mut m[22]));
            depthwise(&a, wd, bd, s, d, &mut tmp, &mut esc);
            m[ent] = a;
            let (wp, bp) = pw(lpw);
            pointwise::<FMA>(&tmp, wp, bp, capas[lpw].2, &mut m[sal], true);
            m[22] = tmp;
            marca(1 + nb);
        }

        // decodificador: subir x2 + concatenar con el atajo
        let mut tmp = std::mem::take(&mut m[22]);
        let mut cat = std::mem::take(&mut m[18]);
        ampliar_concat(&m[17], &m[11], &mut cat);
        let (wd, bd) = pw(17);
        depthwise(&cat, wd, bd, 1, 1, &mut tmp, &mut esc);
        m[18] = cat;
        let (wp, bp) = pw(18);
        pointwise::<FMA>(&tmp, wp, bp, 64, &mut m[19], true);
        marca(9);

        let mut cat = std::mem::take(&mut m[20]);
        ampliar_concat(&m[19], &m[5], &mut cat);
        marca(13);
        let (wd, bd) = pw(19);
        depthwise(&cat, wd, bd, 1, 1, &mut tmp, &mut esc);
        m[20] = cat;
        marca(14);
        let (wp, bp) = pw(20);
        pointwise::<FMA>(&tmp, wp, bp, 48, &mut m[21], true);
        marca(10);

        let mut sal = std::mem::take(&mut m[16]);
        if self.version == 1 {
            // cabeza r01/r02: 3x3 completa 48->32 sobre copia con borde (tmp), y 1x1 32->4
            let (wt, b) = pw(21);
            conv3_cabeza::<FMA>(&m[21], wt, b, &mut tmp, &mut sal);
            marca(11);
            let (wp, bp) = pw(22);
            pointwise::<FMA>(&sal, wp, bp, 4, &mut m[23], false);
        } else {
            // cabeza r03: depthwise 3x3 + 1x1 48->32, y 1x1 32->4
            let (wd, bd) = pw(21);
            depthwise(&m[21], wd, bd, 1, 1, &mut tmp, &mut esc);
            let (wp, bp) = pw(22);
            pointwise::<FMA>(&tmp, wp, bp, 32, &mut sal, true);
            marca(11);
            let (wp, bp) = pw(23);
            pointwise::<FMA>(&sal, wp, bp, 4, &mut m[23], false);
        }
        marca(12);
        self.perfil = perfil;
        self.esc = esc;
        m[22] = tmp;
        m[16] = sal;
        self.m = m;
    }
}

/// Conv 3x3 completa, stride 2, padding 1, 1 -> 16 canales, ReLU.
/// im2col (9 planos, uno por posicion del kernel) + micro-kernel.
#[inline(always)]
fn conv_stem<const FMA: bool>(a: &T, wt: &[f32], b: &[f32], cols: &mut T, o: &mut T) {
    let (ho, wo) = (a.h / 2, a.w / 2);
    cols.forma(9, ho, wo, 0);
    let x0 = &a.d[..a.h * a.w];
    for t in 0..9 {
        let (ky, kx) = (t / 3, t % 3);
        let pl = &mut cols.d[t * cols.s..t * cols.s + ho * wo];
        for y in 0..ho {
            let fila = &mut pl[y * wo..(y + 1) * wo];
            let iy = (2 * y + ky) as isize - 1;
            if iy < 0 || iy >= a.h as isize {
                fila.fill(0.0);
                continue;
            }
            let fe = &x0[iy as usize * a.w..(iy as usize + 1) * a.w];
            for (x, v) in fila.iter_mut().enumerate() {
                let ix = (2 * x + kx) as isize - 1;
                *v = if ix < 0 || ix >= a.w as isize { 0.0 } else { fe[ix as usize] };
            }
        }
    }
    o.forma(16, ho, wo, 0);
    gemm::<FMA>(&cols.d, cols.s, 9, &[0], wt, b, 16, &mut o.d, o.s, ho * wo, true);
}

/// Depthwise 3x3 con stride `s` (1 o 2), dilatacion y padding `d`, ReLU.
/// Se arma un plano con borde (y para s=2 se separa en 4 fases par/impar) de
/// modo que cada posicion del kernel sea un desplazamiento contiguo; luego un
/// solo kernel acumula las 9 posiciones en registros, 8 pixeles a la vez.
#[inline(always)]
fn depthwise(a: &T, wt: &[f32], b: &[f32], s: usize, d: usize, o: &mut T, esc: &mut Vec<f32>) {
    let (h, w) = (a.h, a.w);
    let (ho, wo) = ((h - 1) / s + 1, (w - 1) / s + 1);
    o.forma(a.c, ho, wo, 0);
    let (hp, wp) = (h + 2 * d, w + 2 * d);
    // geometria de la fuente: s=1 -> un plano wp; s=2 -> 4 fases de hq x wq
    let (wq, hq) = if s == 1 { (wp, hp) } else { (wp.div_ceil(2), hp.div_ceil(2)) };
    let n_fase = hq * wq;
    let n_fuente = if s == 1 { n_fase } else { 4 * n_fase };
    let offs: [usize; 9] = std::array::from_fn(|t| {
        let (ky, kx) = ((t / 3) * d, (t % 3) * d);
        if s == 1 {
            ky * wq + kx
        } else {
            ((ky % 2) * 2 + kx % 2) * n_fase + (ky / 2) * wq + kx / 2
        }
    });
    let n = ho * wq; // salidas calculadas (con columnas de borde)
    let n8 = n.div_ceil(8) * 8;
    let holgura = offs.iter().max().unwrap() + n8 - n + 8;
    let tam_pad = hp * wp;
    let total = tam_pad + n_fuente + holgura + n8;
    if esc.len() < total {
        esc.resize(total, 0.0);
    }
    let (pad, resto) = esc.split_at_mut(tam_pad);
    let (fuente, acc) = resto.split_at_mut(n_fuente + holgura);
    let acc = &mut acc[..n8];
    pad.fill(0.0);
    fuente.fill(0.0);
    for c in 0..a.c {
        let ent = &a.d[c * a.s..c * a.s + h * w];
        if s == 1 {
            for y in 0..h {
                fuente[(y + d) * wp + d..(y + d) * wp + d + w].copy_from_slice(&ent[y * w..(y + 1) * w]);
            }
        } else {
            for y in 0..h {
                pad[(y + d) * wp + d..(y + d) * wp + d + w].copy_from_slice(&ent[y * w..(y + 1) * w]);
            }
            for py in 0..2 {
                for px in 0..2 {
                    let f = &mut fuente[(py * 2 + px) * n_fase..(py * 2 + px + 1) * n_fase];
                    for i in 0..hq {
                        let yy = 2 * i + py;
                        if yy >= hp {
                            break;
                        }
                        let fila = &pad[yy * wp..(yy + 1) * wp];
                        for j in 0..wq {
                            let xx = 2 * j + px;
                            if xx < wp {
                                f[i * wq + j] = fila[xx];
                            }
                        }
                    }
                }
            }
        }
        let k: [f32; 9] = wt[c * 9..c * 9 + 9].try_into().unwrap();
        dw_kernel(fuente, &offs, &k, b[c], n8, acc);
        let sal = &mut o.d[c * o.s..c * o.s + ho * wo];
        for y in 0..ho {
            for (o, &v) in sal[y * wo..(y + 1) * wo].iter_mut().zip(&acc[y * wq..y * wq + wo]) {
                *o = v.max(0.0);
            }
        }
    }
}

/// acc[q] = b + sum_t k[t] * src[q + offs[t]], q en 0..n8 (multiplo de 8).
#[inline(always)]
fn dw_kernel(src: &[f32], offs: &[usize; 9], k: &[f32; 9], b: f32, n8: usize, acc: &mut [f32]) {
    let max_off = *offs.iter().max().unwrap();
    assert!(n8 % 8 == 0 && n8 + max_off <= src.len() && acc.len() >= n8);
    let ps = src.as_ptr();
    for q0 in (0..n8).step_by(8) {
        let mut v = [b; 8];
        for t in 0..9 {
            // SAFETY: q0 + offs[t] + 8 <= n8 + max_off <= src.len() (comprobado arriba).
            let e = unsafe { &*(ps.add(q0 + offs[t]) as *const [f32; 8]) };
            for j in 0..8 {
                v[j] += k[t] * e[j];
            }
        }
        acc[q0..q0 + 8].copy_from_slice(&v);
    }
}

/// Micro-kernel: out[o][p] = b[o] + sum_{i,t} w[o][i][t] * in[i][p + offs[t]],
/// p en 0..n (se calcula hasta redondear16(n); los planos tienen holgura).
/// Bloque de 4 canales x 16 pixeles en registros (8 ymm con AVX2).
#[inline(always)]
fn gemm<const FMA: bool>(
    ent: &[f32],
    ent_s: usize,
    ci: usize,
    offs: &[usize],
    w: &[f32],
    b: &[f32],
    co: usize,
    sal: &mut [f32],
    sal_s: usize,
    n: usize,
    relu: bool,
) {
    let nt = offs.len();
    let n16 = redondear16(n);
    assert!(co % 4 == 0 && b.len() >= co && w.len() >= co * ci * nt);
    // Limites comprobados una vez aqui; el bucle interno va sin chequeos.
    let max_off = offs.iter().copied().max().unwrap_or(0);
    assert!(ci == 0 || (ci - 1) * ent_s + n16 + max_off <= ent.len());
    assert!((co - 1) * sal_s + n16 <= sal.len());
    let (pe, pw, ps) = (ent.as_ptr(), w.as_ptr(), sal.as_mut_ptr());
    for o0 in (0..co).step_by(4) {
        for p0 in (0..n16).step_by(16) {
            let mut acc = [[0f32; 16]; 4];
            for k in 0..4 {
                acc[k] = [b[o0 + k]; 16];
            }
            for i in 0..ci {
                for (t, &off) in offs.iter().enumerate() {
                    // SAFETY: indices dentro de los limites comprobados arriba.
                    unsafe {
                        let v = &*(pe.add(i * ent_s + p0 + off) as *const [f32; 16]);
                        for k in 0..4 {
                            let wk = *pw.add(((o0 + k) * ci + i) * nt + t);
                            for j in 0..16 {
                                acc[k][j] = if FMA { wk.mul_add(v[j], acc[k][j]) } else { wk * v[j] + acc[k][j] };
                            }
                        }
                    }
                }
            }
            for k in 0..4 {
                // SAFETY: (o0+k)*sal_s + p0 + 16 <= sal.len() comprobado arriba.
                let dst = unsafe { &mut *(ps.add((o0 + k) * sal_s + p0) as *mut [f32; 16]) };
                if relu {
                    for j in 0..16 {
                        dst[j] = acc[k][j].max(0.0);
                    }
                } else {
                    *dst = acc[k];
                }
            }
        }
    }
}

#[inline(always)]
fn pointwise<const FMA: bool>(a: &T, wt: &[f32], b: &[f32], co: usize, o: &mut T, relu: bool) {
    o.forma(co, a.h, a.w, 0);
    gemm::<FMA>(&a.d, a.s, a.c, &[0], wt, b, co, &mut o.d, o.s, a.h * a.w, relu);
}

/// Conv 3x3 completa (padding 1) via 9 desplazamientos sobre copia con borde.
/// La salida queda con ancho w + 2 (2 columnas basura a la derecha).
#[inline(always)]
fn conv3_cabeza<const FMA: bool>(a: &T, wt: &[f32], b: &[f32], borde: &mut T, o: &mut T) {
    let (h, w) = (a.h, a.w);
    let wp = w + 2;
    let max_off = 2 * wp + 2;
    borde.forma(a.c, h + 2, wp, max_off + 16);
    for c in 0..a.c {
        let pl = &mut borde.d[c * borde.s..(c + 1) * borde.s];
        pl.fill(0.0);
        for y in 0..h {
            pl[(y + 1) * wp + 1..(y + 1) * wp + 1 + w].copy_from_slice(&a.d[c * a.s + y * w..c * a.s + (y + 1) * w]);
        }
    }
    let offs: [usize; 9] = std::array::from_fn(|t| (t / 3) * wp + t % 3);
    let co = b.len();
    o.forma(co, h, wp, 0);
    gemm::<FMA>(&borde.d, borde.s, a.c, &offs, wt, b, co, &mut o.d, o.s, h * wp, true);
}

/// Sube `a` x2 (vecino mas cercano) y concatena `atajo` detras.
#[inline(always)]
fn ampliar_concat(a: &T, atajo: &T, o: &mut T) {
    let (h, w) = (atajo.h, atajo.w);
    o.forma(a.c + atajo.c, h, w, 0);
    for c in 0..a.c {
        let ent = &a.d[c * a.s..];
        let sal = &mut o.d[c * o.s..c * o.s + h * w];
        for y in 0..h {
            let fe = &ent[(y / 2) * a.w..];
            for x in 0..w {
                sal[y * w + x] = fe[x / 2];
            }
        }
    }
    for c in 0..atajo.c {
        let k = a.c + c;
        o.d[k * o.s..k * o.s + h * w].copy_from_slice(&atajo.d[c * atajo.s..c * atajo.s + h * w]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ruta_pesos() -> std::path::PathBuf {
        std::env::var("SIEV_OJO_PESOS")
            .map(Into::into)
            .unwrap_or_else(|_| "/home/nick/Escritorio/Proyectos/siev_vng_models/siev_ojo_r01.bin".into())
    }

    /// Igualdad contra onnxruntime (archivo .ref de exportar_pesos.py).
    #[test]
    fn igual_a_onnxruntime() {
        let ruta = ruta_pesos();
        let Ok(refb) = std::fs::read(ruta.with_extension("bin.ref")) else {
            eprintln!("sin pesos/referencia en {}: test omitido", ruta.display());
            return;
        };
        let mut red = SievOjo::cargar(&ruta).unwrap();
        let u = |i: usize| u32::from_le_bytes(refb[i..i + 4].try_into().unwrap()) as usize;
        let f = |i: usize, n: usize| -> Vec<f32> {
            refb[i..i + 4 * n].chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect()
        };
        let (h, w) = (u(0), u(4));
        let img = f(8, h * w);
        let k = 8 + 4 * h * w;
        let esperado = f(k + 4, u(k));
        let m = red.inferir(&img, h, w);
        let (ho, wo) = (h / 4, w / 4);
        assert_eq!((m.alto, m.ancho), (ho, wo));
        let mut dif = 0f32;
        for c in 0..4 {
            for y in 0..ho {
                for x in 0..wo {
                    dif = dif.max((m.get(c, y, x) - esperado[(c * ho + y) * wo + x]).abs());
                }
            }
        }
        assert!(dif < 1e-3, "diferencia maxima {dif}");
        // segunda pasada con los buffers reutilizados: mismo resultado
        let p1 = red.inferir(&img, h, w).pico();
        let p2 = red.inferir(&img, h, w).pico();
        assert_eq!(p1, p2);
    }

    #[test]
    fn rechaza_bin_ajeno() {
        assert!(SievOjo::desde_bytes(b"XXXX\x01\0\0\0\0\0\0\0").is_err());
    }
}

#[cfg(test)]
mod bench_capas {
    use super::*;

    #[cfg(target_arch = "x86_64")]
    #[target_feature(enable = "avx2,fma")]
    unsafe fn dw_avx(a: &T, w: &[f32], b: &[f32], s: usize, d: usize, o: &mut T, esc: &mut Vec<f32>) {
        depthwise(a, w, b, s, d, o, esc);
    }

    /// Prototipo (hipotesis 2): depthwise 3x3 en formato canales-ultimo (HWC,
    /// C multiplo de 8). Vectoriza sobre 8 canales con los 9 pesos del bloque
    /// en registros; sin copias con borde (los bordes se saltan por rango).
    #[inline(always)]
    fn dw_hwc(ent: &[f32], h: usize, w: usize, c: usize, k: &[f32], b: &[f32], s: usize, d: usize, sal: &mut [f32]) {
        let (ho, wo) = ((h - 1) / s + 1, (w - 1) / s + 1);
        for c0 in (0..c).step_by(8) {
            let kk: [[f32; 8]; 9] = std::array::from_fn(|t| std::array::from_fn(|j| k[(c0 + j) * 9 + t]));
            let bb: [f32; 8] = std::array::from_fn(|j| b[c0 + j]);
            for y in 0..ho {
                for x in 0..wo {
                    let mut v = bb;
                    for ky in 0..3 {
                        let iy = (y * s + ky * d) as isize - d as isize;
                        if iy < 0 || iy >= h as isize {
                            continue;
                        }
                        for kx in 0..3 {
                            let ix = (x * s + kx * d) as isize - d as isize;
                            if ix < 0 || ix >= w as isize {
                                continue;
                            }
                            let base = (iy as usize * w + ix as usize) * c + c0;
                            let e: &[f32; 8] = ent[base..base + 8].try_into().unwrap();
                            let kt = &kk[ky * 3 + kx];
                            for j in 0..8 {
                                v[j] += kt[j] * e[j];
                            }
                        }
                    }
                    let o = (y * wo + x) * c + c0;
                    for j in 0..8 {
                        sal[o + j] = v[j].max(0.0);
                    }
                }
            }
        }
    }

    #[cfg(target_arch = "x86_64")]
    #[target_feature(enable = "avx2,fma")]
    unsafe fn dw_hwc_avx(ent: &[f32], h: usize, w: usize, c: usize, k: &[f32], b: &[f32], s: usize, d: usize, sal: &mut [f32]) {
        dw_hwc(ent, h, w, c, k, b, s, d, sal);
    }

    #[test]
    #[ignore]
    fn tiempo_depthwise_hwc() {
        for (c, h, w, s) in [(96usize, 24usize, 32usize, 1usize), (16, 48, 64, 2), (160, 12, 16, 1)] {
            let ent: Vec<f32> = (0..h * w * c).map(|i| (i % 13) as f32 * 0.1).collect();
            let (wt, b) = (vec![0.1f32; c * 9], vec![0.0f32; c]);
            let (ho, wo) = ((h - 1) / s + 1, (w - 1) / s + 1);
            let mut sal = vec![0f32; ho * wo * c];
            let n = 2000;
            let t = std::time::Instant::now();
            for _ in 0..n {
                unsafe { dw_hwc_avx(&ent, h, w, c, &wt, &b, s, 1, &mut sal) };
            }
            let us = t.elapsed().as_secs_f64() * 1e6 / n as f64;
            let mac = (c * 9 * ho * wo) as f64;
            println!("dw HWC c={c} {h}x{w} s={s}: {us:.1} us  ({:.2} GMAC/s)", mac / us / 1e3);
        }
    }

    /// cargo test --release -p siev-tracking --lib bench_capas -- --ignored --nocapture
    #[test]
    #[ignore]
    fn tiempo_depthwise() {
        for (c, h, w, s) in [(96usize, 24usize, 32usize, 1usize), (16, 48, 64, 2), (160, 12, 16, 1)] {
            let mut a = T::default();
            a.forma(c, h, w, 0);
            for (i, v) in a.d.iter_mut().enumerate() {
                *v = (i % 13) as f32 * 0.1;
            }
            let wt = vec![0.1f32; c * 9];
            let b = vec![0.0f32; c];
            let (mut o, mut esc) = (T::default(), Vec::new());
            let n = 2000;
            let t = std::time::Instant::now();
            for _ in 0..n {
                unsafe { dw_avx(&a, &wt, &b, s, 1, &mut o, &mut esc) };
            }
            let us = t.elapsed().as_secs_f64() * 1e6 / n as f64;
            let mac = (c * 9 * o.h * o.w) as f64;
            println!("dw c={c} {h}x{w} s={s}: {us:.1} us  ({:.2} GMAC/s)", mac / us / 1e3);
        }
    }
}
