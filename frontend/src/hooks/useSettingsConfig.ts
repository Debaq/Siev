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
            camera_id: 2,
            resolution_width: 960,
            resolution_height: 540,
            fps: 120,
            exposure: -5,
            contrast: 50,
            flip_horizontal: false,
            flip_vertical: false
        },
        algorithm: {
            primary: 'yolo',
            threshold: 40,
            min_pupil_size: 10,
            roi_enabled: true
        },
        pupil_detection: {
            mode: 'hybrid',
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
            include_sections: ['patient', 'summary', 'graphs'],
            export_format: 'pdf',
            include_logo: true,
            include_raw_data: false
        }
    },
    stimulus_screen: {
        display: {
            screen_index: 1,
            resolution: "1920x1080",
            fullscreen: true
        }
    }
};

export function useSettingsConfig(apiUrl: string) {
    const [config, setConfig] = useState<AppConfig | null>(null);
    const [originalConfig, setOriginalConfig] = useState<AppConfig | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const { getSetting, setSetting } = useTauriDb();
    
    // Use a ref to store the timeout for debounced auto-save
    const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

    const isDirty = JSON.stringify(config) !== JSON.stringify(originalConfig);

    useEffect(() => {
        loadConfig();
        return () => {
            if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
        };
    }, []);

    const loadConfig = async () => {
        setIsLoading(true);
        try {
            const stored = await getSetting('app_config');
            let baseConfig = DEFAULT_APP_CONFIG;

            if (stored) {
                const parsed = JSON.parse(stored);
                // Deep merge with default to handle new fields
                baseConfig = deepMerge(DEFAULT_APP_CONFIG, parsed);
            }

            // Migration from Welcome Wizard
            const wizardClinic = await getSetting('clinic_name');
            const wizardDoctor = await getSetting('doctor_name');
            const wizardStorage = await getSetting('storage_path');

            if (wizardClinic && (baseConfig.general.institution.name === DEFAULT_APP_CONFIG.general.institution.name || !baseConfig.general.institution.name)) {
                baseConfig.general.institution.name = wizardClinic;
            }
            if (wizardStorage && !baseConfig.general.storage.data_path) {
                baseConfig.general.storage.data_path = wizardStorage;
            }

            setConfig(baseConfig);
            setOriginalConfig(baseConfig);
        } catch (e) {
            console.error("Failed to load config:", e);
            setConfig(DEFAULT_APP_CONFIG);
            setOriginalConfig(DEFAULT_APP_CONFIG);
        } finally {
            setIsLoading(false);
        }
    };

    const saveConfig = async (configToSave: AppConfig) => {
        if (!configToSave) return false;
        setIsSaving(true);
        try {
            // 1. Save to Tauri DB
            await setSetting('app_config', JSON.stringify(configToSave));
            
            // 2. Sync with Python Backend (Live Updates)
            await syncWithBackend(configToSave, apiUrl);
            
            setOriginalConfig(configToSave);
            return true;
        } catch (e) {
            console.error("Failed to save config:", e);
            return false;
        } finally {
            setIsSaving(false);
        }
    };

    const resetConfig = () => {
        setConfig(originalConfig);
    };

    const updateConfig = useCallback((path: string, value: any) => {
        setConfig(prev => {
            if (!prev) return null;
            
            // Check if value actually changed to avoid unnecessary updates
            const keys = path.split('.');
            let current: any = prev;
            for (const key of keys) {
                if (current === undefined || current === null) break;
                current = current[key];
            }
            if (current === value) return prev;

            const newConfig = { ...prev };
            setDeepValue(newConfig, path, value);
            
            // Debounced auto-save
            if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
            autoSaveTimerRef.current = setTimeout(() => {
                saveConfig(newConfig);
            }, 1000); // Save after 1 second of inactivity

            return newConfig;
        });
    }, []);

    const applyLive = async (path: string, value: any) => {
        // Update local state and trigger auto-save
        updateConfig(path, value);
    };

    return {
        config,
        isLoading,
        isSaving,
        isDirty,
        updateConfig,
        saveConfig: () => config && saveConfig(config),
        resetConfig,
        applyLive,
        refresh: loadConfig
    };
}

// Helper: Deep merge objects (exported for use in App.tsx)
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

// Helper: Set value in nested object by path "a.b.c"
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

/**
 * Session override type for video config values that can be temporarily overridden.
 */
interface VideoSessionOverrides {
    brightness?: number;
    contrast?: number;
    threshold?: [number, number];
    erode?: [number, number];
    nose_width?: number;
    eye_height?: number;
    use_yolo?: boolean;
    show_debug?: boolean;
}

/**
 * Sync persistent config with backend.
 *
 * @param config - The persistent app configuration
 * @param apiUrl - Backend API URL
 * @param sessionOverrides - If provided, skip these fields (they're managed by session config)
 * @param includeSessionFields - If true, include session-controlled fields (brightness, contrast, etc.)
 *                               Default is false to avoid overwriting session adjustments.
 */
export async function syncWithBackend(
    config: AppConfig,
    apiUrl: string,
    sessionOverrides?: Partial<VideoSessionOverrides>,
    includeSessionFields: boolean = false
) {
    const overrideKeys = sessionOverrides ? Object.keys(sessionOverrides) : [];

    // 1. Video Config - only include camera setup fields by default
    // Session-controlled fields (brightness, contrast, threshold, use_yolo, show_debug)
    // are synced separately via sessionConfig to avoid conflicts
    const videoPayload: Record<string, any> = {
        camera_id: config.vng.camera.camera_id,
        width: config.vng.camera.resolution_width,
        height: config.vng.camera.resolution_height,
        fps: config.vng.camera.fps,
        flip_h: config.vng.camera.flip_horizontal,
        flip_v: config.vng.camera.flip_vertical,
    };

    // Only include session-controlled fields if explicitly requested AND not overridden
    if (includeSessionFields) {
        if (!overrideKeys.includes('brightness')) {
            videoPayload.brightness = config.vng.camera.exposure;
        }
        if (!overrideKeys.includes('contrast')) {
            videoPayload.contrast = config.vng.camera.contrast;
        }
        if (!overrideKeys.includes('use_yolo')) {
            videoPayload.use_yolo = config.vng.algorithm.primary === 'yolo';
        }
        if (!overrideKeys.includes('threshold')) {
            videoPayload.threshold = [config.vng.algorithm.threshold, config.vng.algorithm.threshold];
        }
    }

    await fetch(`${apiUrl}/video/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(videoPayload)
    });

    // 2. Full Pupil Detection Config (not affected by session overrides)
    const pupilConfig = config.vng.pupil_detection;
    const pupilPayload = {
        mode: pupilConfig.mode,
        search_window_multiplier: pupilConfig.search_window_multiplier,
        dark_threshold_percent: pupilConfig.dark_threshold_percent,
        starburst_rays: pupilConfig.starburst_rays,
        starburst_min_gradient: pupilConfig.starburst_min_gradient,
        fallback_threshold: pupilConfig.fallback_threshold,
        min_confidence_for_lock: pupilConfig.min_confidence_for_lock,
        revalidation_interval: pupilConfig.revalidation_interval,
        legacy_blur_enabled: pupilConfig.legacy.blur_enabled,
        legacy_blur_kernel: pupilConfig.legacy.blur_kernel,
        legacy_clahe_enabled: pupilConfig.legacy.clahe_enabled,
        legacy_clahe_clip_limit: pupilConfig.legacy.clahe_clip_limit,
        legacy_clahe_grid_size: pupilConfig.legacy.clahe_grid_size,
        legacy_morph_enabled: pupilConfig.legacy.morph_enabled,
        legacy_morph_close_iterations: pupilConfig.legacy.morph_close_iterations,
        legacy_morph_dilate_iterations: pupilConfig.legacy.morph_dilate_iterations
    };

    await fetch(`${apiUrl}/video/pupil/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pupilPayload)
    });
}
