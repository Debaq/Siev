import { useState, useCallback, useRef, useEffect } from 'react';

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
    threshold: [0, 0],
    erode: [0, 0],
    nose_width: 0.25,
    eye_height: 0.25,
    use_yolo: true,
    show_debug: false,
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
                vng.algorithm?.threshold ?? 0,
                vng.algorithm?.threshold ?? 0
            ],
            erode: [0, 0],
            nose_width: 0.25,
            eye_height: 0.25,
            use_yolo: vng.algorithm?.primary === 'yolo',
            show_debug: false,
        };

        setBaseConfig(newBase);
    }, []);

    const syncToBackend = useCallback(async (valuesToSync?: Partial<VideoSessionConfig>) => {
        if (!sendToWs) return;
        
        const config = valuesToSync ? { ...effectiveValues, ...valuesToSync } : effectiveValues;

        sendToWs({
            type: 'set_config',
            key: 'session_update', // Rust/Python can handle keys or just the object
            value: {
                brightness: config.brightness,
                contrast: config.contrast,
                threshold: config.threshold,
                erode: config.erode,
                nose_width: config.nose_width,
                eye_height: config.eye_height,
                use_yolo: config.use_yolo,
                show_debug: config.show_debug,
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