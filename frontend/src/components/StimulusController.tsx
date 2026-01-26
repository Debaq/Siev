import React, { useState } from 'react';
import { Play, Square, Settings } from 'lucide-react';
import { emit } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';
import { 
    VNGTestConfig, 
    CalibrationConfig, 
    SaccadeConfig, 
    PursuitConfig, 
    OPKConfig, 
    GazeConfig,
    StimulusTargetConfig
} from '../types/vng';
import { AppConfig } from '../types/config';

interface Props {
    testType: string;
    appConfig?: AppConfig;
}

export const StimulusController: React.FC<Props> = ({ testType, appConfig }) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const [showConfig, setShowConfig] = useState(false);

    // Default Configs
    const [targetConfig, setTargetConfig] = useState<StimulusTargetConfig>({
        size_degrees: 1.0,
        color: 'red',
        shape: 'circle',
        brightness: 100
    });

    const [calibrationConfig, setCalibrationConfig] = useState<CalibrationConfig>({
        type: 'points_7',
        horizontal_fov: 20,
        vertical_fov: 10,
        duration_per_point: 2,
        auto_advance: true
    });

    const [saccadeConfig, setSaccadeConfig] = useState<SaccadeConfig>({
        type: 'random',
        min_amplitude: 5,
        max_amplitude: 30,
        min_interval: 1.5,
        max_interval: 2.5,
        direction: 'horizontal',
        count: 20
    });

    const [pursuitConfig, _setPursuitConfig] = useState<PursuitConfig>({
        type: 'sinusoidal',
        frequencies: [0.2, 0.4],
        amplitudes: [20],
        direction: 'horizontal',
        cycles_per_frequency: 3
    });

    const [opkConfig, setOpkConfig] = useState<OPKConfig>({
        pattern: 'bars',
        velocities: [20, 40],
        velocity: 20,
        direction: 'left',
        contrast: 100,
        stripe_width: 5
    });

    const [gazeConfig, _setGazeConfig] = useState<GazeConfig>({
        points: [
            { x: 0, y: 0, duration: 10 },
            { x: 30, y: 0, duration: 10 },
            { x: -30, y: 0, duration: 10 }
        ],
        randomize_order: false
    });

    const handleStart = async () => {
        let testConfig: VNGTestConfig | null = null;

        if (testType === 'calibration' || testType === 'calibration_gaze') {
            testConfig = { test: 'calibration', params: calibrationConfig };
        } else if (testType === 'saccades') {
            testConfig = { test: 'saccades', params: saccadeConfig };
        } else if (testType === 'pursuit') {
            testConfig = { test: 'pursuit', params: pursuitConfig };
        } else if (testType === 'optokinetic') {
            testConfig = { test: 'opk', params: opkConfig };
        } else if (testType === 'gaze' || testType === 'positional') { // Gaze is often part of positional
             testConfig = { test: 'gaze', params: gazeConfig };
        }

        if (testConfig) {
            try {
                // Ensure external display is open
                const wasCreated = await invoke<boolean>('open_external_display');
                
                if (wasCreated) {
                   // Wait for window to load (React hydration)
                   await new Promise(resolve => setTimeout(resolve, 1500));
                }

                // Determine screen config from appConfig
                const screenConfig = appConfig?.stimulus_screen?.display;

                await emit('start_stimulus', {
                    testConfig,
                    targetConfig,
                    screenConfig
                });
                setIsPlaying(true);
            } catch (e) {
                console.error("Failed to start stimulus", e);
            }
        }
    };

    const handleStop = async () => {
        try {
            await emit('stop_stimulus');
            setIsPlaying(false);
        } catch (e) {
            console.error("Failed to emit stop_stimulus", e);
        }
    };

    const ConfigField = ({ label, children }: { label: string, children: React.ReactNode }) => (
        <div className="mb-2">
            <label className="block text-[10px] text-dark-400 mb-1">{label}</label>
            {children}
        </div>
    );

    return (
        <div className="bg-dark-900 border-t border-dark-800 p-3 flex flex-col gap-3">
             <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase text-siev-400">Estímulo Visual</span>
                <button 
                    onClick={() => setShowConfig(!showConfig)}
                    className={`p-1 rounded hover:bg-dark-800 ${showConfig ? 'text-white' : 'text-dark-400'}`}
                >
                    <Settings className="w-3 h-3" />
                </button>
             </div>

             {showConfig && (
                 <div className="bg-dark-800 rounded p-2 text-[10px] max-h-40 overflow-y-auto custom-scrollbar border border-dark-700">
                    <h4 className="font-bold text-white mb-2">Configuración Target</h4>
                    <ConfigField label="Color">
                        <select 
                            value={targetConfig.color}
                            onChange={(e) => setTargetConfig({...targetConfig, color: e.target.value as any})}
                            className="w-full bg-dark-900 border border-dark-600 rounded px-1 py-0.5"
                        >
                            <option value="red">Rojo</option>
                            <option value="green">Verde</option>
                            <option value="blue">Azul</option>
                            <option value="white">Blanco</option>
                        </select>
                    </ConfigField>
                    <ConfigField label="Tamaño (grados)">
                        <input 
                            type="number" step="0.1"
                            value={targetConfig.size_degrees}
                            onChange={(e) => setTargetConfig({...targetConfig, size_degrees: parseFloat(e.target.value)})}
                            className="w-full bg-dark-900 border border-dark-600 rounded px-1 py-0.5"
                        />
                    </ConfigField>
                    
                    {(testType === 'calibration' || testType === 'calibration_gaze') && (
                        <>
                            <h4 className="font-bold text-white mb-2 mt-3">Config Calibración</h4>
                            <ConfigField label="Patrón de Puntos">
                                <select 
                                    value={calibrationConfig.type}
                                    onChange={(e) => setCalibrationConfig({...calibrationConfig, type: e.target.value as any})}
                                    className="w-full bg-dark-900 border border-dark-600 rounded px-1 py-0.5"
                                >
                                    <option value="points_5">5 Puntos (Cruz)</option>
                                    <option value="points_7">7 Puntos (+H)</option>
                                    <option value="points_9">9 Puntos (Completo)</option>
                                </select>
                            </ConfigField>
                        </>
                    )}

                    {testType === 'saccades' && (
                        <>
                            <h4 className="font-bold text-white mb-2 mt-3">Config Sacadas</h4>
                            <ConfigField label="Tipo">
                                <select 
                                    value={saccadeConfig.type}
                                    onChange={(e) => setSaccadeConfig({...saccadeConfig, type: e.target.value as any})}
                                    className="w-full bg-dark-900 border border-dark-600 rounded px-1 py-0.5"
                                >
                                    <option value="random">Aleatorias</option>
                                    <option value="fixed">Fijas</option>
                                    <option value="anti">Anti-Sacadas</option>
                                </select>
                            </ConfigField>
                        </>
                    )}

                    {testType === 'optokinetic' && (
                        <>
                             <h4 className="font-bold text-white mb-2 mt-3">Config OKN</h4>
                             <ConfigField label="Dirección">
                                <select 
                                    value={opkConfig.direction}
                                    onChange={(e) => setOpkConfig({...opkConfig, direction: e.target.value as any})}
                                    className="w-full bg-dark-900 border border-dark-600 rounded px-1 py-0.5"
                                >
                                    <option value="left">Izquierda</option>
                                    <option value="right">Derecha</option>
                                    <option value="up">Arriba</option>
                                    <option value="down">Abajo</option>
                                </select>
                            </ConfigField>
                        </>
                    )}
                 </div>
             )}

             <button
                className={`btn w-full ${isPlaying ? 'btn-danger' : 'btn-success'} h-8`}
                onClick={isPlaying ? handleStop : handleStart}
            >
                {isPlaying ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                <span className="ml-1">{isPlaying ? 'DETENER ESTÍMULO' : 'INICIAR ESTÍMULO'}</span>
            </button>
        </div>
    );
};
