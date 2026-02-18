import { useState, useEffect, useCallback, useRef } from 'react';
import { useTauriDb } from './useTauriDb';
import { AppConfig } from '../types/config';

export const DEFAULT_APP_CONFIG: AppConfig = {
    modules: {
        vng: false,
        stimulus_screen: false,
        vhit: false,
        static_posturography: false,
        imu_posturography: false,
        vemp: false,
        point_projector: false,
        audiometria: false,
        otoscopia: false,
        impedanciometria: false
    },
    general: {
        institution: {
            name: "Centro de Diagnóstico VNG",
            logo_path: "",
            address: "",
            phone: "",
            email: "",
            extra_info: ""
        },
        storage: {
            data_path: "",
            backup_enabled: true
        }
    },
    vng: {
        camera: {
            camera_id: 0,
            resolution_width: 960,
            resolution_height: 540,
            fps: 60,
        },
        algorithm: {
            primary: 'yolo26',
            yolo_frequency: 4,
            yolo_confidence: 0.5,
            yolo_pupil_confidence: 0.3,
        },
        hardware: {
            serial_port: "/dev/ttyUSB0",
            baudrate: 115200,
            ir_led_intensity: 2,
        },
        calibration: {
            pattern_type: '5_points',
            horizontal_angle: 30,
            vertical_angle: 20,
            point_duration: 2.0,
            patient_distance_cm: 60
        },
        report: {
            template: 'standard',
            sections: [
                { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
                { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
                { id: 'saccades', label: 'Sacadas', enabled: true, order: 2 },
                { id: 'pursuit', label: 'Rastreo', enabled: true, order: 3 },
                { id: 'okn', label: 'OKN', enabled: false, order: 4 },
                { id: 'positional', label: 'Posicional', enabled: true, order: 5 },
                { id: 'caloric', label: 'Calóricas', enabled: true, order: 6 },
                { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 7 },
                { id: 'signature', label: 'Firma', enabled: true, order: 8 },
            ],
            export_format: 'pdf',
            include_logo: true,
            include_raw_data: false,
            include_graphs: true,
            compare_with_previous: false,
            diagram_style: 'claussen',
            analysis_method: 'both'
        },
        tests: {
            caloric: {
                protocols: [
                    {
                        id: 'bitermal-alternada',
                        name: 'Bitérmal Alternada',
                        comment: '',
                        is_base: true,
                        irrigations: [
                            { label: '44°C OD', temperature: 44, ear: 'od' },
                            { label: '44°C OI', temperature: 44, ear: 'oi' },
                            { label: '30°C OD', temperature: 30, ear: 'od' },
                            { label: '30°C OI', temperature: 30, ear: 'oi' },
                        ],
                        timing: {
                            delay: 0,
                            irrigation_duration: 30,
                            rest_time: 300,
                            total_duration: 180,
                            torok: { start_time: 90, duration: 30 },
                            ofi: { start_time: 130, duration: 10, fixation_led: 'both' },
                        },
                    },
                    {
                        id: 'monotermal-caliente',
                        name: 'Monotérmal Caliente',
                        comment: '',
                        is_base: true,
                        irrigations: [
                            { label: '44°C OD', temperature: 44, ear: 'od' },
                            { label: '44°C OI', temperature: 44, ear: 'oi' },
                        ],
                        timing: {
                            delay: 0,
                            irrigation_duration: 30,
                            rest_time: 300,
                            total_duration: 180,
                            torok: { start_time: 90, duration: 30 },
                            ofi: { start_time: 130, duration: 10, fixation_led: 'both' },
                        },
                    },
                ],
            },
        }
    },
    stimulus_screen: {
        display: {
            monitor_name: "",
            monitor_index: -1,
            scale_factor: 1,
            resolution_width: 0,
            resolution_height: 0,
            physical_width_mm: 0,
            physical_height_mm: 0,
            distance_cm: 100,
            is_calibrated: false,
            pixel_density: 0
        }
    },
    audiometria: {
        report: {
            template: 'standard',
            sections: [
                { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
                { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
                { id: 'tonal', label: 'Audiometría Tonal', enabled: true, order: 2 },
                { id: 'vocal', label: 'Audiometría Vocal', enabled: true, order: 3 },
                { id: 'supraliminar', label: 'Pruebas Supraliminares', enabled: false, order: 4 },
                { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 5 },
                { id: 'signature', label: 'Firma', enabled: true, order: 6 },
            ],
            export_format: 'pdf',
            include_logo: true,
            include_audiogram: true,
            include_speech_curve: true,
        },
        tests: {
            tonal_liminar: true,
            vocal: true,
            supraliminar: false,
            altas_frecuencias: false,
        },
        references: {
            normative: 'iso_7029',
            normal_threshold_db: 25,
        },
        frequencies: {
            standard: [250, 500, 1000, 2000, 4000, 8000],
            extended: [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000],
            high_frequency: [8000, 9000, 10000, 11200, 12500, 14000, 16000],
            default_range: 'standard',
        },
    },
    otoscopia: {
        report: {
            template: 'standard',
            sections: [
                { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
                { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
                { id: 'od', label: 'Oído Derecho', enabled: true, order: 2 },
                { id: 'oi', label: 'Oído Izquierdo', enabled: true, order: 3 },
                { id: 'images', label: 'Imágenes', enabled: true, order: 4 },
                { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 5 },
                { id: 'signature', label: 'Firma', enabled: true, order: 6 },
            ],
            export_format: 'pdf',
            include_logo: true,
            include_images: true,
        },
        findings: {
            findings: [
                { id: 'normal', label: 'Membrana timpánica normal', category: 'normal', enabled: true },
                { id: 'translucida', label: 'Membrana translúcida', category: 'normal', enabled: true },
                { id: 'opaca', label: 'Membrana opaca', category: 'patologico', enabled: true },
                { id: 'retraccion', label: 'Retracción timpánica', category: 'patologico', enabled: true },
                { id: 'perforacion', label: 'Perforación', category: 'patologico', enabled: true },
                { id: 'otorrea', label: 'Otorrea', category: 'patologico', enabled: true },
                { id: 'miringoesclerosis', label: 'Miringoesclerosis', category: 'patologico', enabled: true },
                { id: 'colesteatoma', label: 'Colesteatoma', category: 'patologico', enabled: true },
                { id: 'cerumen', label: 'Tapón de cerumen', category: 'patologico', enabled: true },
                { id: 'exostosis', label: 'Exostosis', category: 'patologico', enabled: true },
            ],
        },
        regions: {
            regions: [
                { id: 'pars_tensa', label: 'Pars tensa', enabled: true },
                { id: 'pars_flaccida', label: 'Pars flácida', enabled: true },
                { id: 'umbo', label: 'Umbo', enabled: true },
                { id: 'mango_martillo', label: 'Mango del martillo', enabled: true },
                { id: 'triangulo_luminoso', label: 'Triángulo luminoso', enabled: true },
                { id: 'annulus', label: 'Annulus', enabled: true },
                { id: 'cuadrante_anterosuperior', label: 'Cuadrante anterosuperior', enabled: true },
                { id: 'cuadrante_anteroinferior', label: 'Cuadrante anteroinferior', enabled: true },
                { id: 'cuadrante_posterosuperior', label: 'Cuadrante posterosuperior', enabled: true },
                { id: 'cuadrante_posteroinferior', label: 'Cuadrante posteroinferior', enabled: true },
            ],
        },
        images: {
            capture_enabled: false,
            reference_images_enabled: true,
        },
    },
    postural: {
        timing: {
            auto_advance: false,
            countdown_sound: true,
        },
        visualization: {
            show_3d_head: true,
            show_target_orientation: true,
            head_model: 'ellipsoid',
        },
        symptoms: {
            scale: { type: 'vas_0_10' },
            symptoms: [
                { id: 'vertigo', label: 'Vértigo', enabled: true },
                { id: 'nausea', label: 'Náusea', enabled: true },
                { id: 'vomito', label: 'Vómito', enabled: true },
                { id: 'inestabilidad', label: 'Inestabilidad', enabled: false },
                { id: 'cefalea', label: 'Cefalea', enabled: false },
            ],
        },
        enabled_tests: [
            'vppb_dix_hallpike_right', 'vppb_dix_hallpike_left',
            'vppb_supine_roll_right', 'vppb_supine_roll_left',
            'vppb_bow_lean',
            'vppb_epley_right', 'vppb_epley_left',
            'vppb_semont_right', 'vppb_semont_left',
            'vppb_bbq_right', 'vppb_bbq_left',
            'vppb_gufoni_right', 'vppb_gufoni_left',
        ],
        custom_tests: [],
    },
    impedanciometria: {
        report: {
            template: 'standard',
            sections: [
                { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
                { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
                { id: 'timpanograma', label: 'Timpanograma', enabled: true, order: 2 },
                { id: 'reflejos', label: 'Reflejos Estapediales', enabled: true, order: 3 },
                { id: 'clasificacion', label: 'Clasificación', enabled: true, order: 4 },
                { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 5 },
                { id: 'signature', label: 'Firma', enabled: true, order: 6 },
            ],
            export_format: 'pdf',
            include_logo: true,
            include_tympanogram: true,
            include_reflex_table: true,
        },
        tests: {
            timpanograma: true,
            reflejo_ipsilateral: true,
            reflejo_contralateral: true,
            decay: false,
            funcion_tubarica: false,
        },
        references: {
            normative: 'jerger_1970',
        },
        classification: {
            jerger_types: [
                { id: 'A', label: 'Tipo A', description: 'Normal', compliance_min: 0.3, compliance_max: 1.75, pressure_min: -100, pressure_max: 50, enabled: true },
                { id: 'As', label: 'Tipo As', description: 'Rigidez (otoesclerosis)', compliance_min: 0.0, compliance_max: 0.3, pressure_min: -100, pressure_max: 50, enabled: true },
                { id: 'Ad', label: 'Tipo Ad', description: 'Hipercompliance (disrupción osicular)', compliance_min: 1.75, compliance_max: 5.0, pressure_min: -100, pressure_max: 50, enabled: true },
                { id: 'B', label: 'Tipo B', description: 'Plano (efusión del oído medio)', compliance_min: 0.0, compliance_max: 0.2, pressure_min: -400, pressure_max: 400, enabled: true },
                { id: 'C', label: 'Tipo C', description: 'Presión negativa (disfunción tubárica)', compliance_min: 0.3, compliance_max: 1.75, pressure_min: -400, pressure_max: -100, enabled: true },
            ],
        },
    },
};

export function useSettingsConfig(sendToWs?: (msg: any) => void) {
    const [config, setConfig] = useState<AppConfig | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const { getSetting, setSetting } = useTauriDb();
    
    // Store original config in a ref to compare without triggering re-renders
    const originalConfigRef = useRef<AppConfig | null>(null);
    // Use a ref to store the timeout for debounced auto-save
    const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        loadConfig();
        return () => {
            if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
        };
    }, []);

    const loadConfig = async () => {
        setIsLoading(true);
        console.log("[Config] Starting loadConfig...");
        try {
            const stored = await getSetting('app_config');
            let finalConfig = JSON.parse(JSON.stringify(DEFAULT_APP_CONFIG));

            if (stored) {
                try {
                    const parsed = JSON.parse(stored);
                    console.log("[Config] raw stored string found, parsing...");
                    // Use a more robust merge that prefers stored values
                    finalConfig = deepMerge(finalConfig, parsed);
                    console.log("[Config] Merged config:", finalConfig);
                } catch (e) {
                    console.error("[Config] Failed to parse stored config:", e);
                }
            } else {
                console.log("[Config] No config in DB, using defaults");
            }

            // Migration/Sync from legacy settings if they exist
            const wizardClinic = await getSetting('clinic_name');
            const wizardStorage = await getSetting('storage_path');

            if (wizardClinic && finalConfig.general.institution.name === DEFAULT_APP_CONFIG.general.institution.name) {
                finalConfig.general.institution.name = wizardClinic;
            }
            if (wizardStorage && !finalConfig.general.storage.data_path) {
                finalConfig.general.storage.data_path = wizardStorage;
            }

            console.log("[Config] Final config state to be set:", finalConfig);
            setConfig(finalConfig);
            originalConfigRef.current = JSON.parse(JSON.stringify(finalConfig));
            setIsDirty(false);
        } catch (e) {
            console.error("[Config] Fatal error in loadConfig:", e);
            setConfig(DEFAULT_APP_CONFIG);
            originalConfigRef.current = JSON.parse(JSON.stringify(DEFAULT_APP_CONFIG));
        } finally {
            setIsLoading(false);
        }
    };

    const saveConfig = async (configToSave: AppConfig) => {
        if (!configToSave) return false;
        setIsSaving(true);
        try {
            console.log("[Config] Saving to DB...");
            // 1. Save to Tauri DB (SQLite)
            const configStr = JSON.stringify(configToSave);
            await setSetting('app_config', configStr);
            
            // 2. Sync with Backend via WebSocket (if function provided)
            if (sendToWs) {
                await syncWithWebSocket(configToSave, sendToWs);
            }
            
            originalConfigRef.current = JSON.parse(configStr);
            setIsDirty(false);
            console.log("[Config] Saved successfully");
            return true;
        } catch (e) {
            console.error("[Config] Failed to save config:", e);
            return false;
        } finally {
            setIsSaving(false);
        }
    };

    const updateConfig = useCallback((path: string, value: any) => {
        console.log(`[Config] Updating path: ${path} with value:`, value);
        setConfig(prev => {
            if (!prev) return null;
            
            // Check if value actually changed
            const keys = path.split('.');
            let current: any = prev;
            for (const key of keys) {
                if (current === undefined || current === null) break;
                current = current[key];
            }
            if (JSON.stringify(current) === JSON.stringify(value)) {
                console.log(`[Config] No change detected for ${path}`);
                return prev;
            }

            const newConfig = JSON.parse(JSON.stringify(prev));
            setDeepValue(newConfig, path, value);
            console.log(`[Config] New state generated for ${path}`);
            return newConfig;
        });
    }, []);

    // Effect for auto-saving and dirty state calculation
    useEffect(() => {
        if (!config || !originalConfigRef.current) return;

        const configStr = JSON.stringify(config);
        const originalStr = JSON.stringify(originalConfigRef.current);
        const dirty = configStr !== originalStr;
        
        setIsDirty(dirty);

        if (dirty) {
            if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
            autoSaveTimerRef.current = setTimeout(() => {
                saveConfig(config);
            }, 1000); // 1 second debounce
        }
    }, [config]);

    return {
        config,
        isLoading,
        isSaving,
        isDirty,
        updateConfig,
        saveConfig: () => config && saveConfig(config),
        resetConfig: () => {
            if (originalConfigRef.current) {
                const reset = JSON.parse(JSON.stringify(originalConfigRef.current));
                setConfig(reset);
                setIsDirty(false);
            }
        },
        refresh: loadConfig
    };
}

// Helper: Sync via WebSocket
// No envía camera_setup aquí — la cámara solo se inicia
// explícitamente al entrar a una prueba (start_capture en App.tsx).
export async function syncWithWebSocket(
    _config: AppConfig,
    _send: (msg: any) => void
) {
    // Reservado para futuras sincronizaciones que no involucren hardware.
    // camera_setup se eliminó porque reiniciaba la cámara en cada guardado de config.
}

// Helper: Deep merge
export function deepMerge(target: any, source: any): any {
    const output = { ...target };
    if (isObject(target) && isObject(source)) {
        Object.keys(source).forEach(key => {
            if (isObject(source[key])) {
                if (!(key in target)) {
                    Object.assign(output, { [key]: source[key] });
                } else {
                    output[key] = deepMerge(target[key], source[key]);
                }
            } else {
                Object.assign(output, { [key]: source[key] });
            }
        });
    }
    return output;
}

function isObject(item: any) {
    return (item && typeof item === 'object' && !Array.isArray(item));
}

function setDeepValue(obj: any, path: string, value: any) {
    const keys = path.split('.');
    let current = obj;
    for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        if (!(key in current)) current[key] = {};
        current = current[key];
    }
    current[keys[keys.length - 1]] = value;
}