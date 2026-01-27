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
 * Now uses WebSocket for syncing.
 */
export function useSessionConfig(sendToWs?: (msg: any) => void) {
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

        const vng = persistentConfig.vng;
        const newBase: VideoSessionConfig = {
            brightness: vng.camera?.exposure ?? DEFAULT_SESSION_CONFIG.brightness,
            contrast: vng.camera?.contrast ?? DEFAULT_SESSION_CONFIG.contrast,
            threshold: [
                vng.algorithm?.threshold ?? 40,
                vng.algorithm?.threshold ?? 40
            ],
            erode: [0, 0],
            nose_width: 0.25,
            eye_height: 0.25,
            use_yolo: false, // YOLO desactivado por defecto
            show_debug: false,
            smooth: 2.5,
            manual_roi_right: { top: 0.1, bottom: 0.9, nasal: 0.9, temporal: 0.1 },
            manual_roi_left: { top: 0.1, bottom: 0.9, nasal: 0.1, temporal: 0.9 },
        };

        setBaseConfig(newBase);
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
        setOverrides(prev => ({ ...prev, [key]: value }));
        
        if (syncTimeoutRef.current) clearTimeout(syncTimeoutRef.current);
        syncTimeoutRef.current = setTimeout(() => {
            syncToBackend({ [key]: value } as Partial<VideoSessionConfig>);
        }, 50);
    }, [syncToBackend]);

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