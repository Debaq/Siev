import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { listen, emit } from '@tauri-apps/api/event';
import { Maximize2, X, Move, Monitor, AlertTriangle, Minimize2 } from 'lucide-react';

// Sub-components
import { CalibrationStimulus } from '../components/stimulus/CalibrationStimulus';
import { SaccadeStimulus } from '../components/stimulus/SaccadeStimulus';
import { PursuitStimulus } from '../components/stimulus/PursuitStimulus';
import { OPKStimulus } from '../components/stimulus/OPKStimulus';
import { GazeStimulus } from '../components/stimulus/GazeStimulus';
import { CalibrationPage } from './CalibrationPage';
import { ManualCalibration, CalibrationResult } from '../components/stimulus/ManualCalibration';

// Types
import { VNGTestConfig, StimulusTargetConfig } from '../types/vng';

type DisplayMode = 'idle' | 'stimulus' | 'calibration_wizard' | 'manual_calibration';

interface ManualCalibrationConfig {
    patternType: '3_points' | '5_points' | '9_points';
    horizontalAngle: number;
    verticalAngle: number;
    patientDistance: number;
}

interface StimulusState {
    config: VNGTestConfig | null;
    targetConfig: StimulusTargetConfig;
    screenConfig: {
        distance_cm: number;
        pixel_density: number;
        resolution_width: number;
        resolution_height: number;
    };
}

export const ExternalDisplayPage: React.FC = () => {
    const [mode, setMode] = useState<DisplayMode>('idle');
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [stimulusState, setStimulusState] = useState<StimulusState>({
        config: null,
        targetConfig: { size_degrees: 1.0, color: 'red', shape: 'circle', brightness: 100 },
        screenConfig: { distance_cm: 100, pixel_density: 0, resolution_width: 0, resolution_height: 0 }
    });
    const [manualCalibConfig, setManualCalibConfig] = useState<ManualCalibrationConfig>({
        patternType: '5_points',
        horizontalAngle: 15,
        verticalAngle: 10,
        patientDistance: 150
    });

    useEffect(() => {
        const win = getCurrentWindow();
        
        // Check initial state
        win.isFullscreen().then(setIsFullscreen);

        const setupListeners = async () => {
            const unlistenStart = await listen('start_stimulus', async (event: any) => {
                const payload = event.payload;

                // Auto-fullscreen for calibration stimuli
                if (payload.testConfig?.test === 'calibration') {
                    const currentFullscreen = await win.isFullscreen();
                    if (!currentFullscreen) {
                        await win.setFullscreen(true);
                        setIsFullscreen(true);
                    }
                }

                setStimulusState(prev => ({
                    ...prev,
                    config: payload.testConfig,
                    targetConfig: payload.targetConfig || prev.targetConfig,
                    screenConfig: payload.screenConfig || prev.screenConfig
                }));
                setMode('stimulus');
            });

            const unlistenStop = await listen('stop_stimulus', () => {
                setMode('idle');
                setStimulusState(prev => ({ ...prev, config: null }));
            });

            const unlistenCalib = await listen('start_calibration_wizard', async () => {
                setMode('calibration_wizard');
                await win.setFullscreen(false); // Force windowed for wizard logic if needed, or handle inside
            });

            const unlistenCalibDone = await listen('calibration_complete', (event: any) => {
                const { ppi } = event.payload;
                setStimulusState(prev => ({
                    ...prev,
                    screenConfig: { ...prev.screenConfig, pixel_density: ppi }
                }));
                setMode('idle');
            });

            // Manual calibration for VNG (ocular tracking calibration)
            const unlistenManualCalib = await listen('start_manual_calibration', async (event: any) => {
                const payload = event.payload as ManualCalibrationConfig;

                setManualCalibConfig({
                    patternType: payload.patternType || '5_points',
                    horizontalAngle: payload.horizontalAngle || 15,
                    verticalAngle: payload.verticalAngle || 10,
                    patientDistance: payload.patientDistance || 150
                });

                // Auto-fullscreen
                const currentFullscreen = await win.isFullscreen();
                if (!currentFullscreen) {
                    await win.setFullscreen(true);
                    setIsFullscreen(true);
                }

                setMode('manual_calibration');
            });

            return () => {
                unlistenStart();
                unlistenStop();
                unlistenCalib();
                unlistenCalibDone();
                unlistenManualCalib();
            };
        };

        setupListeners();
    }, []);

    const handleToggleFullscreen = async () => {
        const win = getCurrentWindow();
        const newState = !isFullscreen;
        await win.setFullscreen(newState);
        setIsFullscreen(newState);
    };

    const handleClose = async () => {
        await getCurrentWindow().close();
    };

    // Helper: Deg to Px (memoized to prevent animation restarts)
    const degToPx = useCallback((degrees: number) => {
        const { distance_cm, pixel_density } = stimulusState.screenConfig;
        
        // If not calibrated, use a sensible default (approx 96 PPI at 60cm)
        const effectivePPI = pixel_density || 96;
        const effectiveDist = distance_cm || 60;
        
        const radians = degrees * (Math.PI / 180);
        const size_cm = effectiveDist * Math.tan(radians);
        const size_inches = size_cm / 2.54;
        return size_inches * effectivePPI;
    }, [stimulusState.screenConfig.distance_cm, stimulusState.screenConfig.pixel_density]);

    // Calcular el ángulo máximo representable por la pantalla actual
    const screenLimitInfo = useMemo(() => {
        const { distance_cm, pixel_density } = stimulusState.screenConfig;
        const ppi = pixel_density || 96;
        const dist = distance_cm || 60;
        const sw = window.innerWidth;
        const sh = window.innerHeight;

        // Inversa de degToPx: halfPx → grados
        const pxToDeg = (halfPx: number) => {
            const inches = halfPx / ppi;
            const cm = inches * 2.54;
            return Math.atan(cm / dist) * (180 / Math.PI);
        };

        const maxH = pxToDeg(sw / 2);
        const maxV = pxToDeg(sh / 2);

        // Ángulos requeridos por el estímulo activo
        let requiredH = 0;
        let requiredV = 0;
        const cfg = stimulusState.config;
        if (cfg) {
            const p = cfg.params as any;
            switch (cfg.test) {
                case 'saccades':
                    requiredH = p.max_amplitude || 30;
                    break;
                case 'pursuit':
                    requiredH = p.amplitudes?.[0] || 20;
                    break;
                case 'calibration':
                    requiredH = p.horizontal_fov || 20;
                    requiredV = p.vertical_fov || 10;
                    break;
                case 'gaze': {
                    const pts = p.points || [];
                    requiredH = Math.max(...pts.map((pt: any) => Math.abs(pt.x)), 0);
                    requiredV = Math.max(...pts.map((pt: any) => Math.abs(pt.y)), 0);
                    break;
                }
            }
        }

        const exceedsH = requiredH > maxH;
        const exceedsV = requiredV > maxV;

        return { maxH, maxV, requiredH, requiredV, exceedsH, exceedsV, exceeds: exceedsH || exceedsV };
    }, [stimulusState.config, stimulusState.screenConfig.distance_cm, stimulusState.screenConfig.pixel_density]);

    // --- RENDERERS ---

    // 1. WINDOWED MODE (The "Original" Look)
    // Used when not fullscreen and idle/setup
    if (!isFullscreen && mode !== 'calibration_wizard') {
        return (
            <div 
                data-tauri-drag-region
                className="h-screen w-screen bg-dark-950 text-white flex flex-col p-8 border-4 border-purple-500/30 relative select-none cursor-move overflow-hidden"
            >
                {/* Custom Window Controls */}
                <div className="absolute top-2 right-2 flex gap-2 z-50">
                    <button 
                        onClick={handleClose}
                        className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors cursor-pointer"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center text-center gap-6 pointer-events-none">
                    <div className="p-6 bg-purple-500/10 rounded-full animate-pulse">
                        <Move className="w-12 h-12 text-purple-400" />
                    </div>
                    
                    <div className="max-w-md space-y-2">
                        <h1 className="text-2xl font-bold">Pantalla Externa SIEV</h1>
                        <p className="text-gray-400">
                            Arrastra esta ventana hacia el <strong>Monitor Externo</strong> (Proyector/TV).
                        </p>
                    </div>

                    <div className="p-4 bg-dark-900 rounded-lg border border-dark-800 text-sm text-yellow-500/80 flex items-start gap-3 max-w-sm text-left">
                        <Monitor className="w-5 h-5 shrink-0 mt-0.5" />
                        <p>
                            Una vez ubicada, pulse el botón inferior para maximizar y activar el modo de proyección.
                        </p>
                    </div>
                </div>

                <button 
                    onClick={handleToggleFullscreen}
                    className="w-full py-4 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-purple-500/25 z-50 cursor-pointer pointer-events-auto"
                >
                    <Maximize2 className="w-5 h-5" />
                    ACTIVAR PANTALLA COMPLETA
                </button>
            </div>
        );
    }

    // 2. FULLSCREEN IDLE (Ready State)
    if (isFullscreen && mode === 'idle') {
        return (
            <div className="h-screen w-screen bg-black flex items-center justify-center relative group">
                <img src="/logo-large.png" alt="SIEV" className="w-64 opacity-20 grayscale" />
                
                {/* Hidden controls appearing on hover at top */}
                <div className="absolute top-0 left-0 w-full h-16 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-b from-black/80 to-transparent flex justify-end p-4 pointer-events-none">
                    <button 
                        onClick={handleToggleFullscreen}
                        className="pointer-events-auto bg-white/10 hover:bg-white/20 text-white px-3 py-1 rounded backdrop-blur border border-white/10 flex items-center gap-2 text-xs"
                    >
                        <Minimize2 className="w-4 h-4" />
                        Salir
                    </button>
                </div>
            </div>
        );
    }

    // 3. CALIBRATION WIZARD (Screen PPI calibration)
    if (mode === 'calibration_wizard') {
        return <CalibrationPage />;
    }

    // 4. MANUAL CALIBRATION (VNG ocular tracking calibration)
    if (mode === 'manual_calibration') {
        const handleCalibrationComplete = async (result: CalibrationResult) => {
            // Emit result to main app
            await emit('manual_calibration_complete', result);
            setMode('idle');
        };

        const handleCalibrationCancel = () => {
            setMode('idle');
        };

        return (
            <ManualCalibration
                patternType={manualCalibConfig.patternType}
                horizontalAngle={manualCalibConfig.horizontalAngle}
                verticalAngle={manualCalibConfig.verticalAngle}
                patientDistance={manualCalibConfig.patientDistance}
                onComplete={handleCalibrationComplete}
                onCancel={handleCalibrationCancel}
            />
        );
    }

    // 5. STIMULUS RUNNING
    const commonProps = {
        degToPx,
        targetConfig: stimulusState.targetConfig,
        screenResolution: { 
            width: window.screen.width, 
            height: window.screen.height 
        },
        onComplete: () => setMode('idle')
    };

    return (
        <div className="h-screen w-screen bg-black overflow-hidden relative">
            {/* Safety Warning - not fullscreen */}
            {!isFullscreen && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-red-500/90 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-3 backdrop-blur pointer-events-auto cursor-pointer" onClick={handleToggleFullscreen}>
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-sm font-bold">Haga clic aquí para Pantalla Completa</span>
                </div>
            )}

            {/* Advertencia: estímulo excede pantalla */}
            {screenLimitInfo.exceeds && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-50 bg-amber-600/90 text-white px-5 py-2.5 rounded-xl shadow-lg flex items-center gap-3 backdrop-blur max-w-lg">
                    <AlertTriangle className="w-5 h-5 shrink-0" />
                    <div className="text-xs leading-snug">
                        <span className="font-bold">Pantalla insuficiente:</span>{' '}
                        {screenLimitInfo.exceedsH && (
                            <span>Horizontal requiere {screenLimitInfo.requiredH.toFixed(0)}° pero máximo representable es {screenLimitInfo.maxH.toFixed(1)}°. </span>
                        )}
                        {screenLimitInfo.exceedsV && (
                            <span>Vertical requiere {screenLimitInfo.requiredV.toFixed(0)}° pero máximo representable es {screenLimitInfo.maxV.toFixed(1)}°. </span>
                        )}
                        <span className="opacity-80">Reduzca los ángulos o aumente la distancia al paciente.</span>
                    </div>
                </div>
            )}

            {stimulusState.config?.test === 'calibration' && (
                <CalibrationStimulus config={stimulusState.config.params} {...commonProps} />
            )}
            {stimulusState.config?.test === 'saccades' && (
                <SaccadeStimulus config={stimulusState.config.params} {...commonProps} />
            )}
            {stimulusState.config?.test === 'pursuit' && (
                <PursuitStimulus config={stimulusState.config.params} {...commonProps} />
            )}
            {stimulusState.config?.test === 'gaze' && (
                <GazeStimulus config={stimulusState.config.params} {...commonProps} />
            )}
            {stimulusState.config?.test === 'opk' && (
                <OPKStimulus config={stimulusState.config.params} {...commonProps} />
            )}
        </div>
    );
};