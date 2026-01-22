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
 *
 * - Initializes from persistent config when provided
 * - Tracks which values have been locally overridden
 * - Provides methods to update values and sync with backend
 * - Allows resetting overrides to return to persistent config values
 */
export function useSessionConfig(apiUrl: string) {
    const [baseConfig, setBaseConfig] = useState<VideoSessionConfig>(DEFAULT_SESSION_CONFIG);
    const [overrides, setOverrides] = useState<Partial<VideoSessionConfig>>({});
    const syncTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Compute effective values (base merged with overrides)
    const effectiveValues: VideoSessionConfig = {
        ...baseConfig,
        ...overrides,
    };

    const hasOverrides = Object.keys(overrides).length > 0;

    /**
     * Initialize base config from persistent settings.
     * Called when persistent config is loaded or updated.
     */
    const initFromPersistentConfig = useCallback((persistentConfig: {
        vng?: {
            camera?: { exposure?: number; contrast?: number };
            algorithm?: { primary?: string; threshold?: number };
        };
    }) => {
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

    /**
     * Update a single config value. This creates an override.
     */
    const updateValue = useCallback(<K extends keyof VideoSessionConfig>(
        key: K,
        value: VideoSessionConfig[K]
    ) => {
        setOverrides(prev => ({
            ...prev,
            [key]: value,
        }));
    }, []);

    /**
     * Update multiple values at once.
     */
    const updateValues = useCallback((updates: Partial<VideoSessionConfig>) => {
        setOverrides(prev => ({
            ...prev,
            ...updates,
        }));
    }, []);

    /**
     * Clear a specific override, reverting to base config value.
     */
    const clearOverride = useCallback(<K extends keyof VideoSessionConfig>(key: K) => {
        setOverrides(prev => {
            const next = { ...prev };
            delete next[key];
            return next;
        });
    }, []);

    /**
     * Clear all overrides, reverting to base config.
     */
    const clearAllOverrides = useCallback(() => {
        setOverrides({});
    }, []);

    /**
     * Sync current effective values to backend.
     */
    const syncToBackend = useCallback(async (valuesToSync?: Partial<VideoSessionConfig>) => {
        const config = valuesToSync ? { ...effectiveValues, ...valuesToSync } : effectiveValues;

        try {
            await fetch(`${apiUrl}/video/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    brightness: config.brightness,
                    contrast: config.contrast,
                    threshold: config.threshold,
                    erode: config.erode,
                    nose_width: config.nose_width,
                    eye_height: config.eye_height,
                    use_yolo: config.use_yolo,
                    show_debug: config.show_debug,
                }),
            });
        } catch (error) {
            console.error('Error syncing session config to backend:', error);
        }
    }, [apiUrl, effectiveValues]);

    /**
     * Debounced sync - useful for slider changes.
     */
    const debouncedSync = useCallback((valuesToSync?: Partial<VideoSessionConfig>) => {
        if (syncTimeoutRef.current) {
            clearTimeout(syncTimeoutRef.current);
        }
        syncTimeoutRef.current = setTimeout(() => {
            syncToBackend(valuesToSync);
        }, 50); // Fast debounce for responsive feel
    }, [syncToBackend]);

    /**
     * Update a value and immediately sync to backend.
     */
    const updateAndSync = useCallback(<K extends keyof VideoSessionConfig>(
        key: K,
        value: VideoSessionConfig[K]
    ) => {
        updateValue(key, value);
        debouncedSync({ [key]: value } as Partial<VideoSessionConfig>);
    }, [updateValue, debouncedSync]);

    // Cleanup timeout on unmount
    useEffect(() => {
        return () => {
            if (syncTimeoutRef.current) {
                clearTimeout(syncTimeoutRef.current);
            }
        };
    }, []);

    /**
     * Get current state for external use.
     */
    const getState = useCallback((): SessionConfigState => ({
        values: effectiveValues,
        overrides,
        hasOverrides,
    }), [effectiveValues, overrides, hasOverrides]);

    /**
     * Get only the overridden values (for merging with persistent sync).
     */
    const getOverrides = useCallback(() => overrides, [overrides]);

    return {
        // Current effective values
        values: effectiveValues,
        // Base config (from persistent settings)
        baseConfig,
        // Active overrides
        overrides,
        hasOverrides,

        // Actions
        initFromPersistentConfig,
        updateValue,
        updateValues,
        updateAndSync,
        clearOverride,
        clearAllOverrides,
        syncToBackend,

        // State getters
        getState,
        getOverrides,
    };
}

export type UseSessionConfigReturn = ReturnType<typeof useSessionConfig>;
