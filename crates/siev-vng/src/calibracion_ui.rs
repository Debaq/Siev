//! Asistente de calibracion (ventana del operador) y pantalla de estimulos
//! (ventana a pantalla completa en el monitor del paciente).

use eframe::egui::{self, Color32, RichText, Stroke};

use crate::calibracion::{self, AjusteOjo, Fase, Fuente, LARGO_REGLA_CM};
use crate::tema::{ACENTO, AMBAR, OD, OI, ROJO, TEXTO_SUAVE, VERDE};
use crate::VngApp;

/// Radio del punto de fijacion y del anillo que lo anuncia, en cm reales.
const RADIO_PUNTO_CM: f64 = 0.35;
const RADIO_ANILLO_CM: f64 = 3.0;

enum Accion {
    Abrir,
    Cerrar,
    PantallaCompleta,
    GuardarRegla,
    Comenzar,
    Cancelar,
    Aceptar,
    Repetir,
    Descartar,
    PorDefecto,
    SinEscala,
}

fn id_estimulos() -> egui::ViewportId {
    egui::ViewportId::from_hash_of("siev_estimulos")
}

impl VngApp {
    pub(crate) fn ventana_calibracion(&mut self, ctx: &egui::Context) {
        let mut abierta = self.ver_calib;
        let mut accion: Option<Accion> = None;
        let mut cambio = false;

        egui::Window::new(RichText::new("Calibracion").size(18.0).strong())
            .open(&mut abierta)
            .default_width(440.0)
            .default_pos([ctx.content_rect().right() - 900.0, 70.0])
            .resizable(true)
            .show(ctx, |ui| {
                if let Some(t) = &self.toma {
                    progreso(ui, t);
                    ui.add_space(8.0);
                    if ui.button("Cancelar").clicked() {
                        accion = Some(Accion::Cancelar);
                    }
                    return;
                }
                if let Some(r) = &self.resultado {
                    resultado(ui, r, &mut accion);
                    return;
                }

                let est = &mut self.cfg.estacion;
                ui.label(RichText::new("La pantalla y la distancia se miden una vez por sala. Calibrar al paciente es opcional: sin hacerlo se usa la escala tipica de esta mascara. El cero se toma solo al iniciar cada prueba.").small().color(TEXTO_SUAVE));
                ui.add_space(6.0);

                // 1. Pantalla del paciente
                ui.label(RichText::new("1. Pantalla del paciente").strong());
                ui.horizontal(|ui| {
                    egui::ComboBox::from_id_salt("monitor_paciente")
                        .selected_text(format!("Monitor {}", est.monitor + 1))
                        .show_ui(ui, |ui| {
                            for i in 0..4 {
                                cambio |= ui.selectable_value(&mut est.monitor, i, format!("Monitor {}", i + 1)).changed();
                            }
                        });
                    if self.estimulos {
                        if ui.button("Pantalla completa").clicked() {
                            accion = Some(Accion::PantallaCompleta);
                        }
                        if ui.button("Cerrar").clicked() {
                            accion = Some(Accion::Cerrar);
                        }
                    } else if ui.button("Abrir pantalla de estimulos").clicked() {
                        accion = Some(Accion::Abrir);
                    }
                });
                if self.estimulos && self.tam_estimulos_px[0] > 0.0 {
                    let [w, h] = self.tam_estimulos_px;
                    ui.label(RichText::new(format!("Ventana de estimulos: {w:.0} × {h:.0} px")).small().color(TEXTO_SUAVE));
                }
                ui.add_space(8.0);

                // 2. Medida de la pantalla
                ui.label(RichText::new("2. Medir la pantalla (una vez)").strong());
                if est.cm_por_px > 0.0 {
                    let [w, h] = self.tam_estimulos_px;
                    let tam = if w > 0.0 {
                        format!(" · pantalla de {:.1} × {:.1} cm", w * est.cm_por_px, h * est.cm_por_px)
                    } else {
                        String::new()
                    };
                    ui.label(RichText::new(format!("1 px = {:.4} cm{tam}", est.cm_por_px)).color(VERDE));
                } else {
                    ui.label(RichText::new("Sin medir").color(AMBAR));
                }
                ui.add_enabled_ui(self.estimulos, |ui| {
                    ui.toggle_value(&mut self.regla, "Mostrar regla en la pantalla del paciente");
                    if self.regla {
                        ui.label(format!("Ajustar hasta que la barra blanca mida {LARGO_REGLA_CM:.0} cm con una regla o huincha."));
                        let max = (self.tam_estimulos_px[0] * 0.95).max(400.0);
                        ui.add(egui::Slider::new(&mut self.largo_regla_px, 100.0..=max).step_by(1.0).text("px"));
                        ui.horizontal(|ui| {
                            for (txt, d) in [("−10", -10.0), ("−1", -1.0), ("+1", 1.0), ("+10", 10.0)] {
                                if ui.small_button(txt).clicked() {
                                    self.largo_regla_px = (self.largo_regla_px + d).clamp(100.0, max);
                                }
                            }
                            if ui.button(RichText::new("Guardar medida").strong()).clicked() {
                                accion = Some(Accion::GuardarRegla);
                            }
                        });
                    }
                });
                ui.add_space(8.0);

                // 3. Distancia y angulos
                ui.label(RichText::new("3. Distancia y puntos").strong());
                egui::Grid::new("estacion").num_columns(2).spacing([12.0, 6.0]).show(ui, |ui| {
                    ui.label("Ojos del paciente a la pantalla");
                    cambio |= ui.add(egui::DragValue::new(&mut est.distancia_cm).range(30.0..=400.0).speed(1.0).suffix(" cm")).changed();
                    ui.end_row();
                    ui.label("Puntos horizontales");
                    cambio |= ui.add(egui::DragValue::new(&mut est.amplitud_h).range(3.0..=30.0).speed(0.5).prefix("±").suffix("°")).changed();
                    ui.end_row();
                    ui.label("Puntos verticales");
                    cambio |= ui.add(egui::DragValue::new(&mut est.amplitud_v).range(3.0..=25.0).speed(0.5).prefix("±").suffix("°")).changed();
                    ui.end_row();
                });
                if est.medida() && self.tam_estimulos_px[0] > 0.0 {
                    let max = est.angulo_max(self.tam_estimulos_px);
                    if est.amplitud_h > max[0] || est.amplitud_v > max[1] {
                        ui.label(
                            RichText::new(format!("La pantalla solo alcanza ±{:.1}° × ±{:.1}°: se usara eso.", max[0], max[1]))
                                .small()
                                .color(AMBAR),
                        );
                    }
                }
                ui.label(RichText::new("Medir con huincha desde los ojos hasta la pantalla. Cabeza a la altura del centro de la pantalla y sin la tapa de la mascara.").small().color(TEXTO_SUAVE));
                ui.add_space(10.0);

                // Calibrar
                let listo = self.estimulos && est.medida() && self.manager.is_running() && self.tam_estimulos_px[0] > 0.0;
                let b = egui::Button::new(RichText::new("▶  Calibrar al paciente").strong().color(Color32::WHITE))
                    .fill(ACENTO)
                    .min_size(egui::vec2(220.0, 38.0));
                let falta = if !self.manager.is_running() {
                    "Esperando la camara"
                } else if !self.estimulos {
                    "Abrir la pantalla de estimulos"
                } else {
                    "Medir la pantalla primero"
                };
                if ui.add_enabled(listo, b).on_disabled_hover_text(falta).clicked() {
                    accion = Some(Accion::Comenzar);
                }
                ui.label(RichText::new("El paciente sigue con la mirada un punto rojo: centro, derecha, izquierda, arriba, abajo y centro (~15 s).").small().color(TEXTO_SUAVE));

                ui.add_space(8.0);
                ui.separator();
                ui.horizontal(|ui| {
                    let hay_defecto = self.historial.defecto(&self.cfg.camara.nombre).is_some();
                    if ui.add_enabled(hay_defecto, egui::Button::new("Usar escala por defecto")).clicked() {
                        accion = Some(Accion::PorDefecto);
                    }
                    if ui.button("Quitar escala (px)").clicked() {
                        accion = Some(Accion::SinEscala);
                    }
                });
            });

        self.ver_calib = abierta;
        if cambio {
            self.cfg_sucia = Some(std::time::Instant::now());
        }
        match accion {
            Some(Accion::Abrir) => {
                self.estimulos = true;
                self.tam_estimulos_px = [0.0, 0.0];
            }
            Some(Accion::Cerrar) => {
                self.estimulos = false;
                self.regla = false;
            }
            Some(Accion::PantallaCompleta) => {
                ctx.send_viewport_cmd_to(id_estimulos(), egui::ViewportCommand::Fullscreen(true));
            }
            Some(Accion::GuardarRegla) => {
                self.cfg.estacion.cm_por_px = LARGO_REGLA_CM / self.largo_regla_px;
                self.regla = false;
                self.cfg_sucia = Some(std::time::Instant::now());
            }
            Some(Accion::Comenzar) => self.comenzar_calibracion(),
            Some(Accion::Cancelar) => self.toma = None,
            Some(Accion::Aceptar) => self.aceptar_calibracion(),
            Some(Accion::Repetir) => self.comenzar_calibracion(),
            Some(Accion::Descartar) => self.resultado = None,
            Some(Accion::PorDefecto) => self.usar_escala_por_defecto(),
            Some(Accion::SinEscala) => self.aplicar_escala(None, None, Fuente::Ninguna),
            None => {}
        }
    }

    /// Ventana negra en el monitor del paciente con el estimulo del momento.
    pub(crate) fn pantalla_estimulos(&mut self, ctx: &egui::Context) {
        if !self.estimulos {
            return;
        }
        let builder = egui::ViewportBuilder::default()
            .with_title("SIEV — Estimulos")
            .with_inner_size([960.0, 540.0])
            .with_monitor(self.cfg.estacion.monitor);
        let mut cerrar = false;
        let mut tam = self.tam_estimulos_px;
        ctx.show_viewport_immediate(id_estimulos(), builder, |ui, _| {
            if ui.ctx().input(|i| i.viewport().close_requested()) {
                cerrar = true;
            }
            let ppp = ui.ctx().pixels_per_point() as f64;
            egui::CentralPanel::default().frame(egui::Frame::new().fill(Color32::BLACK)).show(ui, |ui| {
                let r = ui.max_rect();
                tam = [r.width() as f64 * ppp, r.height() as f64 * ppp];
                self.dibujar_estimulo(ui.painter(), r, ppp);
            });
        });
        self.tam_estimulos_px = tam;
        if cerrar {
            self.estimulos = false;
            self.regla = false;
            self.toma = None;
        }
    }

    fn dibujar_estimulo(&self, p: &egui::Painter, r: egui::Rect, ppp: f64) {
        let est = &self.cfg.estacion;
        let c = r.center();
        let pt = |px: f64| (px / ppp) as f32;
        // Sin medida no hay cm: tamaños fijos en px.
        let cm = |v: f64| if est.cm_por_px > 0.0 { pt(v / est.cm_por_px) } else { pt(v * 40.0) };

        if self.regla {
            let medio = pt(self.largo_regla_px) / 2.0;
            let trazo = Stroke::new(4.0, Color32::WHITE);
            p.line_segment([c - egui::vec2(medio, 0.0), c + egui::vec2(medio, 0.0)], trazo);
            for x in [-medio, medio] {
                p.line_segment([c + egui::vec2(x, -40.0), c + egui::vec2(x, 40.0)], trazo);
            }
            p.text(
                c - egui::vec2(0.0, 70.0),
                egui::Align2::CENTER_BOTTOM,
                format!("Esta barra debe medir {LARGO_REGLA_CM:.0} cm"),
                egui::FontId::proportional(28.0),
                Color32::from_gray(200),
            );
            return;
        }

        let pos = |ang: [f64; 2]| {
            if est.medida() {
                let q = est.a_px(ang);
                c + egui::vec2(pt(q[0]), pt(q[1]))
            } else {
                c
            }
        };
        let punto = |en: egui::Pos2, anillo: f32| {
            if anillo > 0.0 {
                let r_anillo = cm(RADIO_PUNTO_CM) + (cm(RADIO_ANILLO_CM) - cm(RADIO_PUNTO_CM)) * anillo;
                p.circle_stroke(en, r_anillo, Stroke::new(3.0, Color32::from_gray(160)));
            }
            p.circle_filled(en, cm(RADIO_PUNTO_CM), Color32::from_rgb(0xE5, 0x2B, 0x2B));
            p.circle_filled(en, cm(RADIO_PUNTO_CM) * 0.3, Color32::WHITE);
        };

        if let Some(t) = &self.toma {
            if let Some(o) = t.actual() {
                // El anillo se cierra sobre el punto mientras el paciente lo busca.
                let anillo = match t.fase {
                    Fase::Fijar => 1.0 - t.avance_fase(),
                    Fase::Muestreo => 0.0,
                };
                punto(pos(o.ang), anillo);
            }
        } else if let Some(z) = &self.cero {
            let anillo = 1.0 - (z.inicio.elapsed().as_secs_f32() / (calibracion::DURACION_CERO.as_secs_f32() / 3.0)).min(1.0);
            punto(c, anillo);
        } else {
            // En reposo: punto central tenue para que el paciente mire al frente.
            p.circle_filled(c, cm(RADIO_PUNTO_CM) * 0.6, Color32::from_gray(90));
        }
    }
}

fn progreso(ui: &mut egui::Ui, t: &calibracion::Toma) {
    let n = t.objetivos.len();
    let nombre = t.actual().map(|o| o.nombre).unwrap_or("—");
    ui.label(RichText::new(format!("Punto {} de {n}: {nombre}", (t.i + 1).min(n))).size(17.0).strong());
    let estado = match t.fase {
        Fase::Fijar => "El paciente lleva la mirada al punto…",
        Fase::Muestreo => "Midiendo…",
    };
    ui.label(RichText::new(estado).color(TEXTO_SUAVE));
    ui.add(egui::ProgressBar::new((t.i as f32 + 0.5 * t.avance_fase()) / n as f32).show_percentage());
    if matches!(t.fase, Fase::Muestreo) {
        let (od, oi) = t.muestras();
        ui.horizontal(|ui| {
            for (nombre, color, k) in [("OD", OD, od), ("OI", OI, oi)] {
                let estado = if k >= 40 { VERDE } else { AMBAR };
                ui.label(RichText::new(format!("{nombre}: {k} muestras")).color(color));
                ui.label(RichText::new("●").color(estado));
            }
        });
    }
    ui.label(RichText::new("Si un ojo parpadea, el punto se alarga hasta 3 s.").small().color(TEXTO_SUAVE));
}

fn resultado(ui: &mut egui::Ui, r: &calibracion::Resultado, accion: &mut Option<Accion>) {
    ui.label(RichText::new("Resultado").size(17.0).strong());
    egui::Grid::new("resultado_calib").num_columns(4).spacing([14.0, 6.0]).striped(true).show(ui, |ui| {
        ui.label("");
        ui.label(RichText::new("H (°/px)").color(TEXTO_SUAVE));
        ui.label(RichText::new("V (°/px)").color(TEXTO_SUAVE));
        ui.label(RichText::new("Error").color(TEXTO_SUAVE));
        ui.end_row();
        for (nombre, color, a) in [("OD", OD, &r.od), ("OI", OI, &r.oi)] {
            ui.label(RichText::new(nombre).color(color).strong());
            match a {
                Some(AjusteOjo { escala, error_deg, .. }) => {
                    ui.label(format!("{:.3}", escala[0]));
                    ui.label(format!("{:.3}", escala[1]));
                    let c = if *error_deg <= 1.0 { VERDE } else if *error_deg <= 1.5 { AMBAR } else { ROJO };
                    if r.copiado == Some(nombre) {
                        ui.label(RichText::new("copiada").color(AMBAR));
                    } else {
                        ui.label(RichText::new(format!("{error_deg:.2}°")).color(c));
                    }
                }
                None => {
                    ui.label("—");
                    ui.label("—");
                    ui.label(RichText::new("sin datos").color(ROJO));
                }
            }
            ui.end_row();
        }
    });
    if r.avisos.is_empty() {
        ui.label(RichText::new("✔ Calibracion consistente").color(VERDE));
    } else {
        for a in &r.avisos {
            ui.label(RichText::new(format!("⚠ {a}")).color(AMBAR));
        }
        ui.label(RichText::new("Con avisos no se usa para la escala por defecto.").small().color(TEXTO_SUAVE));
    }
    ui.add_space(8.0);
    ui.horizontal(|ui| {
        let b = egui::Button::new(RichText::new("✔  Usar esta calibracion").strong().color(Color32::WHITE)).fill(ACENTO);
        if ui.add_enabled(r.usable(), b).clicked() {
            *accion = Some(Accion::Aceptar);
        }
        if ui.button("↻  Repetir").clicked() {
            *accion = Some(Accion::Repetir);
        }
        if ui.button("Descartar").clicked() {
            *accion = Some(Accion::Descartar);
        }
    });
}
