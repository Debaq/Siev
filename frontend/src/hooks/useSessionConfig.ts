import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * ROI manual para un ojo (valores relativos 0.0 a 1.0)
 */
export interface ManualEyeRoi {
    top: number;      // Límite superior
    bottom: number;   // Límite inferior
    nasal: number;    // Límite nasal
    temporal: number; // Límite temporal
}

/**
 * Session-level video configuration that can temporarily override persistent settings.
 * These values are used during capture and reset when the app restarts.
 */
export interface VideoSessionConfig {
    brightness: number;
    contrast: number;
    threshold: [number, number];
    erode: [number, number];
    nose_width: number;
    eye_height: number;
    use_yolo: boolean;
    show_debug: boolean;
    smooth: number;
    manual_roi_right: ManualEyeRoi;
    manual_roi_left: ManualEyeRoi;
}

export interface SessionConfigState {
    // Current effective values (base + overrides)
    values: VideoSessionConfig;
    // Which fields have been overridden locally
    overrides: Partial<VideoSessionConfig>;
    // Whether there are any active overrides
    hasOverrides: boolean;
}

const DEFAULT_SESSION_CONFIG: VideoSessionConfig = {
    brightness: -21,
    contrast: 50,
    threshold: [40, 40],
    erode: [0, 0],
    nose_width: 0.25,
    eye_height: 0.25,
    use_yolo: false, // YOLO desactivado por defecto
    show_debug: false,
    smooth: 2.5,
    manual_roi_right: { top: 0.1, bottom: 0.9, nasal: 0.9, temporal: 0.1 },
    manual_roi_left: { top: 0.1, bottom: 0.9, nasal: 0.1, temporal: 0.9 },
};

/**
 * Hook to manage session-level video configuration with temporary overrides.
 * Now uses WebSocket for syncing and can optionally persist changes.
 */
export function useSessionConfig(
    sendToWs?: (msg: any) => void,
    onPersistentUpdate?: (path: string, value: any) => void
) {
    const [baseConfig, setBaseConfig] = useState<VideoSessionConfig>(DEFAULT_SESSION_CONFIG);
    const [overrides, setOverrides] = useState<Partial<VideoSessionConfig>>({});
    const syncTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const effectiveValues: VideoSessionConfig = {
        ...baseConfig,
        ...overrides,
    };

    const hasOverrides = Object.keys(overrides).length > 0;

    const initFromPersistentConfig = useCallback((persistentConfig: any) => {
        if (!persistentConfig?.vng) return;

        console.log("[SessionConfig] Initializing from persistent config");
        const vng = persistentConfig.vng;
        const algo = vng.algorithm || {};
        const cam = vng.camera || {};

        const newBase: VideoSessionConfig = {
            brightness: cam.brightness ?? cam.exposure ?? DEFAULT_SESSION_CONFIG.brightness,
            contrast: cam.contrast ?? DEFAULT_SESSION_CONFIG.contrast,
            threshold: [
                algo.threshold_right ?? algo.threshold ?? 40,
                algo.threshold_left ?? algo.threshold ?? 40
            ],
            erode: [
                algo.erode_right ?? 0,
                algo.erode_left ?? 0
            ],
            nose_width: algo.nose_width ?? 0.25,
            eye_height: algo.eye_height ?? 0.25,
            use_yolo: algo.use_yolo ?? false,
            show_debug: algo.show_debug ?? false,
            smooth: algo.smooth ?? 2.5,
            manual_roi_right: algo.manual_roi_right ?? { top: 0.1, bottom: 0.9, nasal: 0.9, temporal: 0.1 },
            manual_roi_left: algo.manual_roi_left ?? { top: 0.1, bottom: 0.9, nasal: 0.1, temporal: 0.9 },
        };

        setBaseConfig(newBase);
        // DO NOT clear overrides here if we are already in a session
        // Only clear if it's the first initialization
    }, []);

    const syncToBackend = useCallback(async (valuesToSync?: Partial<VideoSessionConfig>) => {
        if (!sendToWs) return;

        const config = valuesToSync ? { ...effectiveValues, ...valuesToSync } : effectiveValues;

        sendToWs({
            type: 'set_config',
            key: 'session_update',
            value: {
                brightness: config.brightness,
                contrast: config.contrast,
                threshold: config.threshold,
                erode: config.erode,
                nose_width: config.nose_width,
                eye_height: config.eye_height,
                use_yolo: config.use_yolo,
                show_debug: config.show_debug,
                smooth: config.smooth,
                manual_roi_right: config.manual_roi_right,
                manual_roi_left: config.manual_roi_left,
            }
        });
    }, [sendToWs, effectiveValues]);

    const updateAndSync = useCallback(<K extends keyof VideoSessionConfig>(
        key: K,
        value: VideoSessionConfig[K]
    ) => {
        setOverrides(prev => {
            const newOverrides = { ...prev, [key]: value };
            return newOverrides;
        });
        
        // Persist to global config if callback provided
        if (onPersistentUpdate) {
            console.log(`[SessionConfig] Persisting change for ${key}:`, value);
            if (key === 'brightness') {
                onPersistentUpdate('vng.camera.brightness', value);
                onPersistentUpdate('vng.camera.exposure', value);
            } else if (key === 'contrast') {
                onPersistentUpdate('vng.camera.contrast', value);
            } else if (key === 'threshold') {
                const val = value as [number, number];
                onPersistentUpdate('vng.algorithm.threshold_right', val[0]);
                onPersistentUpdate('vng.algorithm.threshold_left', val[1]);
                onPersistentUpdate('vng.algorithm.threshold', val[0]); // Legacy compatibility
            } else if (key === 'erode') {
                const val = value as [number, number];
                onPersistentUpdate('vng.algorithm.erode_right', val[0]);
                onPersistentUpdate('vng.algorithm.erode_left', val[1]);
            } else if (key === 'nose_width') {
                onPersistentUpdate('vng.algorithm.nose_width', value);
            } else if (key === 'eye_height') {
                onPersistentUpdate('vng.algorithm.eye_height', value);
            } else if (key === 'use_yolo') {
                onPersistentUpdate('vng.algorithm.use_yolo', value);
            } else if (key === 'show_debug') {
                onPersistentUpdate('vng.algorithm.show_debug', value);
            } else if (key === 'smooth') {
                onPersistentUpdate('vng.algorithm.smooth', value);
            } else if (key === 'manual_roi_right') {
                onPersistentUpdate('vng.algorithm.manual_roi_right', value);
            } else if (key === 'manual_roi_left') {
                onPersistentUpdate('vng.algorithm.manual_roi_left', value);
            }
        }

        if (syncTimeoutRef.current) clearTimeout(syncTimeoutRef.current);
        syncTimeoutRef.current = setTimeout(() => {
            syncToBackend({ [key]: value } as Partial<VideoSessionConfig>);
        }, 50);
    }, [syncToBackend, onPersistentUpdate]);

    const clearAllOverrides = useCallback(() => {
        setOverrides({});
    }, []);

    useEffect(() => {
        return () => {
            if (syncTimeoutRef.current) clearTimeout(syncTimeoutRef.current);
        };
    }, []);

    return {
        values: effectiveValues,
        baseConfig,
        overrides,
        hasOverrides,
        initFromPersistentConfig,
        updateAndSync,
        clearAllOverrides,
        syncToBackend,
        getOverrides: () => overrides,
    };
}

export type UseSessionConfigReturn = ReturnType<typeof useSessionConfig>;