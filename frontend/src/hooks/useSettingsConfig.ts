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
        point_projector: false
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
            exposure: -21,
            contrast: 50,
            brightness: -21,
            flip_horizontal: false,
            flip_vertical: false,
            video_quality: 80,
            video_scale: 0.75
        },
        algorithm: {
            primary: 'yolo',
            threshold: 40,
            threshold_left: 40,
            threshold_right: 40,
            erode_left: 0,
            erode_right: 0,
            min_pupil_size: 10,
            roi_enabled: true,
            yolo_frequency: 4,
            yolo_confidence: 0.5,
            nose_width: 0.25,
            eye_height: 0.25,
            smooth: 2.5,
            use_yolo: false,
            show_debug: false,
            manual_roi_right: { top: 0.1, bottom: 0.9, nasal: 0.9, temporal: 0.1 },
            manual_roi_left: { top: 0.1, bottom: 0.9, nasal: 0.1, temporal: 0.9 }
        },
        pupil_detection: {
            mode: 'legacy',
            search_window_multiplier: 3.0,
            dark_threshold_percent: 20,
            starburst_rays: 16,
            starburst_min_gradient: 30,
            fallback_threshold: 5,
            min_confidence_for_lock: 0.5,
            revalidation_interval: 30,
            legacy: {
                blur_enabled: true,
                blur_kernel: 5,
                clahe_enabled: true,
                clahe_clip_limit: 2.0,
                clahe_grid_size: 8,
                morph_enabled: true,
                morph_close_iterations: 1,
                morph_dilate_iterations: 1
            }
        },
        hardware: {
            serial_port: "/dev/ttyUSB0",
            baudrate: 115200,
            ir_led_intensity: 2, // 40%
            fixation_led_enabled: false,
            fixation_led_auto_off: 30
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
            diagram_style: 'claussen'
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
    }
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
            
            // 2. Sync with Python Backend via WebSocket (if function provided)
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
export async function syncWithWebSocket(
    config: AppConfig,
    send: (msg: any) => void
) {
    // 1. Sync Video/Camera Config
    send({
        type: 'set_config',
        key: 'camera_setup',
        value: {
            camera_id: config.vng.camera.camera_id,
            width: config.vng.camera.resolution_width,
            height: config.vng.camera.resolution_height,
            fps: config.vng.camera.fps,
            video_quality: config.vng.camera.video_quality,
            video_scale: config.vng.camera.video_scale
        }
    });

    // 2. Sync Pupil Detection Config
    const pc = config.vng.pupil_detection;
    send({
        type: 'set_pupil_config',
        params: {
            mode: pc.mode,
            search_window_multiplier: pc.search_window_multiplier,
            dark_threshold_percent: pc.dark_threshold_percent,
            starburst_rays: pc.starburst_rays,
            starburst_min_gradient: pc.starburst_min_gradient,
            fallback_threshold: pc.fallback_threshold,
            min_confidence_for_lock: pc.min_confidence_for_lock,
            revalidation_interval: pc.revalidation_interval,
            legacy_blur_enabled: pc.legacy.blur_enabled,
            legacy_blur_kernel: pc.legacy.blur_kernel,
            legacy_clahe_enabled: pc.legacy.clahe_enabled,
            legacy_clahe_clip_limit: pc.legacy.clahe_clip_limit,
            legacy_clahe_grid_size: pc.legacy.clahe_grid_size,
            legacy_morph_enabled: pc.legacy.morph_enabled,
            legacy_morph_close_iterations: pc.legacy.morph_close_iterations,
            legacy_morph_dilate_iterations: pc.legacy.morph_dilate_iterations
        }
    });
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