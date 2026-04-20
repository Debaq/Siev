import React, { useCallback, useEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { VNGTestConfig, StimulusTargetConfig } from '../types/vng';
import { CalibrationStimulus } from '../components/stimulus/CalibrationStimulus';
import { SaccadeStimulus } from '../components/stimulus/SaccadeStimulus';
import { PursuitStimulus } from '../components/stimulus/PursuitStimulus';
import { OPKStimulus } from '../components/stimulus/OPKStimulus';
import { GazeStimulus } from '../components/stimulus/GazeStimulus';

interface StimulusState {
    isPlaying: boolean;
    config: VNGTestConfig | null;
    targetConfig: StimulusTargetConfig;
    screenConfig: {
        distance_cm: number;
        pixel_density: number; // PPI
        resolution_width: number;
        resolution_height: number;
    };
}

export const StimulusPlayerPage: React.FC = () => {
    const [state, setState] = useState<StimulusState>({
        isPlaying: false,
        config: null,
        targetConfig: {
            size_degrees: 1.0,
            color: 'red',
            shape: 'circle',
            brightness: 100
        },
        screenConfig: {
            distance_cm: 100,
            pixel_density: 96, // Fallback
            resolution_width: window.screen.width,
            resolution_height: window.screen.height
        }
    });

    useEffect(() => {
        const setup = async () => {
            // Start in fullscreen usually
            // await getCurrentWindow().setFullscreen(true);

            const unlistenStart = await listen('start_stimulus', (event: any) => {
                const payload = event.payload; 
                console.log("Starting stimulus:", payload);
                setState(prev => ({
                    ...prev,
                    isPlaying: true,
                    config: payload.testConfig,
                    targetConfig: payload.targetConfig || prev.targetConfig,
                    screenConfig: payload.screenConfig || prev.screenConfig
                }));
            });

            const unlistenStop = await listen('stop_stimulus', () => {
                console.log("Stopping stimulus");
                setState(prev => ({ ...prev, isPlaying: false, config: null }));
            });

            return () => {
                unlistenStart();
                unlistenStop();
            };
        };

        setup();
    }, []);

    // Helper to convert visual degrees to pixels (memoized to prevent animation restarts)
    const degToPx = useCallback((degrees: number) => {
        const { distance_cm, pixel_density } = state.screenConfig;
        // size_cm = distance_cm * tan(radians)
        const radians = degrees * (Math.PI / 180);
        const size_cm = distance_cm * Math.tan(radians);
        const size_inches = size_cm / 2.54;
        return size_inches * pixel_density;
    }, [state.screenConfig.distance_cm, state.screenConfig.pixel_density]);

    if (!state.isPlaying || !state.config) {
        return (
            <div className="h-screen w-screen bg-black flex items-center justify-center">
                <div className="w-2 h-2 bg-dark-800 rounded-full" /> {/* Fixation point for idle? Or just black */}
            </div>
        );
    }

    const commonProps = {
        degToPx,
        targetConfig: state.targetConfig,
        screenResolution: { 
            width: state.screenConfig.resolution_width, 
            height: state.screenConfig.resolution_height 
        },
        onComplete: () => setState(prev => ({ ...prev, isPlaying: false }))
    };

    return (
        <div className="h-screen w-screen bg-black overflow-hidden relative">
            {state.config.test === 'calibration' && (
                <CalibrationStimulus config={state.config.params} {...commonProps} />
            )}
            {state.config.test === 'saccades' && (
                <SaccadeStimulus config={state.config.params} {...commonProps} />
            )}
            {state.config.test === 'pursuit' && (
                <PursuitStimulus config={state.config.params} {...commonProps} />
            )}
            {state.config.test === 'gaze' && (
                <GazeStimulus config={state.config.params} {...commonProps} />
            )}
            {state.config.test === 'opk' && (
                <OPKStimulus config={state.config.params} {...commonProps} />
            )}
        </div>
    );
};
