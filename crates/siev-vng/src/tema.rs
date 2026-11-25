//! Tema visual claro de SIEV: fondo gris azulado suave, tarjetas blancas,
//! acento turquesa. Colores clinicos de ojos: OD rojo, OI azul.

use eframe::egui::{self, Color32, CornerRadius, FontFamily, FontId, Margin, Shadow, Stroke, TextStyle};

pub const FONDO: Color32 = Color32::from_rgb(0xEE, 0xF2, 0xF7);
pub const TARJETA: Color32 = Color32::WHITE;
pub const BORDE: Color32 = Color32::from_rgb(0xDA, 0xE2, 0xEC);
pub const TEXTO: Color32 = Color32::from_rgb(0x1F, 0x29, 0x37);
pub const TEXTO_SUAVE: Color32 = Color32::from_rgb(0x6B, 0x77, 0x88);
pub const ACENTO: Color32 = Color32::from_rgb(0x0E, 0x9F, 0x9A);
pub const ACENTO_SUAVE: Color32 = Color32::from_rgb(0xD5, 0xF2, 0xF0);
pub const GRILLA: Color32 = Color32::from_rgb(0xB8, 0xC4, 0xD2);
pub const LIENZO_VIDEO: Color32 = Color32::from_rgb(0xDF, 0xE6, 0xEF);

pub const OD: Color32 = Color32::from_rgb(0xE0, 0x47, 0x5B);
pub const OI: Color32 = Color32::from_rgb(0x2F, 0x7D, 0xE1);
pub const VERDE: Color32 = Color32::from_rgb(0x22, 0xA0, 0x6B);
pub const AMBAR: Color32 = Color32::from_rgb(0xD9, 0x8A, 0x0B);
pub const ROJO: Color32 = Color32::from_rgb(0xD6, 0x3C, 0x3C);

pub fn aplicar(ctx: &egui::Context) {
    ctx.set_theme(egui::Theme::Light);
    ctx.style_mut_of(egui::Theme::Light, |s| {
        s.text_styles = [
            (TextStyle::Small, FontId::new(12.0, FontFamily::Proportional)),
            (TextStyle::Body, FontId::new(15.0, FontFamily::Proportional)),
            (TextStyle::Button, FontId::new(15.0, FontFamily::Proportional)),
            (TextStyle::Heading, FontId::new(20.0, FontFamily::Proportional)),
            (TextStyle::Monospace, FontId::new(14.0, FontFamily::Monospace)),
        ]
        .into();

        s.spacing.item_spacing = egui::vec2(10.0, 8.0);
        s.spacing.button_padding = egui::vec2(14.0, 7.0);
        s.spacing.interact_size.y = 30.0;
        s.spacing.slider_width = 200.0;
        s.spacing.window_margin = Margin::same(16);

        let v = &mut s.visuals;
        v.panel_fill = FONDO;
        v.window_fill = TARJETA;
        v.window_stroke = Stroke::new(1.0, BORDE);
        v.window_corner_radius = CornerRadius::same(14);
        v.window_shadow = Shadow { offset: [0, 6], blur: 24, spread: 0, color: Color32::from_black_alpha(28) };
        v.popup_shadow = Shadow { offset: [0, 4], blur: 14, spread: 0, color: Color32::from_black_alpha(22) };
        v.menu_corner_radius = CornerRadius::same(10);
        v.extreme_bg_color = Color32::WHITE;
        v.faint_bg_color = Color32::from_rgb(0xF5, 0xF8, 0xFB);
        v.override_text_color = Some(TEXTO);
        v.hyperlink_color = ACENTO;
        v.selection.bg_fill = ACENTO_SUAVE;
        v.selection.stroke = Stroke::new(1.5, ACENTO);
        v.slider_trailing_fill = true;
        v.striped = true;

        let r = CornerRadius::same(8);
        let w = &mut v.widgets;
        w.noninteractive.bg_stroke = Stroke::new(1.0, BORDE);
        w.noninteractive.fg_stroke = Stroke::new(1.0, TEXTO);
        w.noninteractive.corner_radius = r;

        w.inactive.bg_fill = Color32::from_rgb(0xE6, 0xEC, 0xF3);
        w.inactive.weak_bg_fill = Color32::from_rgb(0xE6, 0xEC, 0xF3);
        w.inactive.bg_stroke = Stroke::NONE;
        w.inactive.fg_stroke = Stroke::new(1.0, TEXTO);
        w.inactive.corner_radius = r;

        w.hovered.bg_fill = Color32::from_rgb(0xD5, 0xEE, 0xEC);
        w.hovered.weak_bg_fill = Color32::from_rgb(0xD5, 0xEE, 0xEC);
        w.hovered.bg_stroke = Stroke::new(1.0, ACENTO);
        w.hovered.fg_stroke = Stroke::new(1.5, TEXTO);
        w.hovered.corner_radius = r;

        w.active.bg_fill = ACENTO;
        w.active.weak_bg_fill = Color32::from_rgb(0xBF, 0xE8, 0xE5);
        w.active.bg_stroke = Stroke::new(1.0, ACENTO);
        w.active.fg_stroke = Stroke::new(1.5, TEXTO);
        w.active.corner_radius = r;

        w.open.bg_fill = Color32::from_rgb(0xE6, 0xEC, 0xF3);
        w.open.weak_bg_fill = Color32::from_rgb(0xE6, 0xEC, 0xF3);
        w.open.corner_radius = r;
    });
}

/// Marco de tarjeta blanca con sombra suave.
pub fn tarjeta() -> egui::Frame {
    egui::Frame::new()
        .fill(TARJETA)
        .stroke(Stroke::new(1.0, BORDE))
        .corner_radius(CornerRadius::same(14))
        .inner_margin(Margin::same(14))
        .shadow(Shadow { offset: [0, 2], blur: 10, spread: 0, color: Color32::from_black_alpha(14) })
}
