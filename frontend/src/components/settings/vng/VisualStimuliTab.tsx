import React, { useEffect, useState, useRef } from 'react';
import { Monitor, Move, Target, Eye, Activity, PlayCircle, Play, Square, Save, ExternalLink } from 'lucide-react';
import { VNGConfig, StimulusScreenConfig, StimulusDefaultParams } from '../../../types/config';
import { emit } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';

interface VisualStimuliTabProps {
    config: VNGConfig;
    stimulusConfig: StimulusScreenConfig;
    updateConfig: (section: string, data: any) => void;
}

const DEFAULT_PARAMS: StimulusDefaultParams = {
    calibration: { type: 'points_9', duration: 1.5 },
    saccades: { min_amplitude: 5, max_amplitude: 30, min_interval: 1.5, max_interval: 2.5 },
    pursuit: { frequency: 0.2, amplitudes: [20] },
    opk: { velocity: 20, stripe_width_deg: 5, direction: 'left', fixation_enabled: false },
    target: { size_deg: 1.0, color: 'red', shape: 'circle' }
};

export const VisualStimuliTab: React.FC<VisualStimuliTabProps> = ({ stimulusConfig, updateConfig }) => {
    const isConfigured = stimulusConfig?.display?.monitor_name && stimulusConfig?.display?.is_calibrated;
    
    const [localDefaults, setLocalDefaults] = useState<StimulusDefaultParams>(
        stimulusConfig.defaults || DEFAULT_PARAMS
    );

    const [activeTest, setActiveTest] = useState<string | null>(null);
    const activeTestRef = useRef<string | null>(null);

    useEffect(() => {
        if (stimulusConfig.defaults) {
            setLocalDefaults({
                ...DEFAULT_PARAMS,
                ...stimulusConfig.defaults,
                // Ensure backward compatibility if they had arrays
                pursuit: { 
                    ...DEFAULT_PARAMS.pursuit, 
                    ...stimulusConfig.defaults.pursuit,
                    frequency: (stimulusConfig.defaults.pursuit as any).frequencies?.[0] || stimulusConfig.defaults.pursuit.frequency || 0.2
                },
                opk: { 
                    ...DEFAULT_PARAMS.opk, 
                    ...stimulusConfig.defaults.opk,
                    velocity: (stimulusConfig.defaults.opk as any).velocities?.[0] || stimulusConfig.defaults.opk.velocity || 20
                }
            });
        }
    }, [stimulusConfig.defaults]);

    useEffect(() => {
        activeTestRef.current = activeTest;
    }, [activeTest]);

    useEffect(() => {
        if (activeTestRef.current) {
            runStimulus(activeTestRef.current);
        }
    }, [localDefaults]);

    const handleSave = () => {
        updateConfig('stimulus_screen', {
            ...stimulusConfig,
            defaults: localDefaults
        });
    };

    const handleOpenWindow = async () => {
        try {
            await invoke('open_external_display');
        } catch (e) {
            console.error("Failed to open external display window", e);
        }
    };

    const runStimulus = async (testType: string) => {
        let testConfig: any = null;

        if (testType === 'calibration') {
            testConfig = { 
                test: 'calibration', 
                params: {
                    type: localDefaults.calibration.type,
                    horizontal_fov: 20,
                    vertical_fov: 10,
                    duration_per_point: localDefaults.calibration.duration,
                    auto_advance: true
                }
            };
        } else if (testType === 'saccades') {
            testConfig = {
                test: 'saccades',
                params: {
                    type: 'random',
                    min_amplitude: localDefaults.saccades.min_amplitude,
                    max_amplitude: localDefaults.saccades.max_amplitude,
                    min_interval: localDefaults.saccades.min_interval,
                    max_interval: localDefaults.saccades.max_interval,
                    direction: 'horizontal',
                    count: 99999
                }
            };
        } else if (testType === 'pursuit') {
            testConfig = {
                test: 'pursuit',
                params: {
                    type: 'sinusoidal',
                    frequencies: [localDefaults.pursuit.frequency],
                    amplitudes: localDefaults.pursuit.amplitudes,
                    direction: 'horizontal',
                    cycles_per_frequency: 9999
                }
            };
        } else if (testType === 'opk') {
            testConfig = {
                test: 'opk',
                params: {
                    pattern: 'bars',
                    velocities: [localDefaults.opk.velocity],
                    direction: localDefaults.opk.direction,
                    stripe_width: localDefaults.opk.stripe_width_deg,
                    fixation_enabled: localDefaults.opk.fixation_enabled,
                    loop: true
                }
            };
        } else if (testType === 'target') {
             testConfig = {
                 test: 'gaze',
                 params: { points: [{ x: 0, y: 0, duration: 9999 }], randomize_order: false }
             };
        }

        if (testConfig) {
            try {
                await emit('start_stimulus', {
                    testConfig,
                    targetConfig: {
                        size_degrees: localDefaults.target.size_deg,
                        color: localDefaults.target.color,
                        shape: localDefaults.target.shape,
                        brightness: 100
                    }
                });
            } catch (e) {
                console.error("Failed to emit test stimulus", e);
            }
        }
    };

    const handleToggleTest = async (testType: string) => {
        if (activeTest === testType) {
            try {
                await emit('stop_stimulus');
                setActiveTest(null);
            } catch (e) {
                console.error("Failed to stop stimulus", e);
            }
        } else {
            await handleOpenWindow();
            await new Promise(r => setTimeout(r, 100)); 
            setActiveTest(testType);
            runStimulus(testType);
        }
    };

    const ConfigSection = ({ title, icon: Icon, children, testId }: any) => {
        const isRunning = activeTest === testId;
        
        return (
            <div className={`bg-dark-900/50 p-5 rounded-xl border mb-4 transition-all ${isRunning ? 'border-siev-500 shadow-[0_0_15px_rgba(139,92,246,0.1)]' : 'border-dark-800'}`}>
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg bg-dark-950 border border-dark-800`}>
                            <Icon className={`w-5 h-5 ${isRunning ? 'text-siev-400 animate-pulse' : 'text-siev-400'}`} />
                        </div>
                        <h4 className="text-sm font-bold text-white uppercase tracking-wide">{title}</h4>
                    </div>
                    <button 
                        onClick={() => handleToggleTest(testId)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors text-xs font-bold border ${
                            isRunning 
                            ? 'bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/30' 
                            : 'bg-dark-800 hover:bg-siev-600 text-dark-300 hover:text-white border-dark-700 hover:border-siev-500'
                        }`}
                    >
                        {isRunning ? <Square className="w-3 h-3 fill-current" /> : <Play className="w-3 h-3" />}
                        {isRunning ? 'DETENER' : 'PROBAR'}
                    </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {children}
                </div>
            </div>
        );
    };

    const InputField = ({ label, value, onChange, type = "number", min, max, step = "1", options = null }: any) => (
        <div>
            <label className="block text-[10px] text-dark-500 mb-1 uppercase font-bold">{label}</label>
            {options ? (
                <select
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-full bg-dark-950 border border-dark-700 rounded-lg px-3 py-2 text-sm text-white focus:border-siev-500 outline-none appearance-none"
                >
                    {options.map((opt: any) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>
            ) : (
                <input
                    type={type}
                    step={step}
                    min={min}
                    max={max}
                    value={value}
                    onChange={(e) => {
                        let val = type === 'number' ? parseFloat(e.target.value) : e.target.value;
                        if (type === 'number' && !isNaN(val as number)) {
                            if (min !== undefined) val = Math.max(min, val as number);
                            if (max !== undefined) val = Math.min(max, val as number);
                        }
                        onChange(val);
                    }}
                    className="w-full bg-dark-950 border border-dark-700 rounded-lg px-3 py-2 text-sm text-white focus:border-siev-500 outline-none"
                />
            )}
        </div>
    );

    if (!isConfigured) {
        return (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center">
                <Monitor className="w-16 h-16 text-dark-700 mb-4" />
                <h3 className="text-xl font-bold text-dark-300 mb-2">Pantalla no Configurada</h3>
                <p className="text-dark-500 max-w-md">
                    Configure primero el monitor secundario en la pestaña "Hardware" o "Sistema" para habilitar los estímulos.
                </p>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col p-6 overflow-y-auto custom-scrollbar">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Target className="w-6 h-6 text-cyan-400" />
                    Configuración de Estímulos
                </h3>
                <div className="flex gap-3">
                    <button 
                        onClick={handleOpenWindow}
                        className="flex items-center gap-2 px-3 py-2 bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-white rounded-lg font-bold transition-colors border border-dark-700 hover:border-dark-600 text-xs"
                    >
                        <ExternalLink className="w-4 h-4" />
                        Abrir Pantalla
                    </button>
                    <button 
                        onClick={handleSave}
                        className="flex items-center gap-2 px-4 py-2 bg-siev-600 hover:bg-siev-500 text-white rounded-lg font-bold transition-colors shadow-lg shadow-siev-900/20"
                    >
                        <Save className="w-4 h-4" />
                        Guardar Cambios
                    </button>
                </div>
            </div>

            {/* Target Settings */}
            <ConfigSection title="Objetivo Visual (Target)" icon={Target} testId="target">
                <InputField 
                    label="Color" 
                    value={localDefaults.target.color} 
                    onChange={(v: string) => setLocalDefaults(prev => ({...prev, target: {...prev.target, color: v}}))}
                    options={[
                        { value: 'red', label: 'Rojo' },
                        { value: 'green', label: 'Verde' },
                        { value: 'blue', label: 'Azul' },
                        { value: 'white', label: 'Blanco' }
                    ]}
                />
                <InputField 
                    label="Forma" 
                    value={localDefaults.target.shape} 
                    onChange={(v: string) => setLocalDefaults(prev => ({...prev, target: {...prev.target, shape: v}}))}
                    options={[
                        { value: 'circle', label: 'Círculo' },
                        { value: 'square', label: 'Cuadrado' },
                        { value: 'cross', label: 'Cruz' },
                        { value: 'pediatric_dog', label: 'Pediátrico (Perro)' }
                    ]}
                />
                <InputField 
                    label="Tamaño (Grados)" 
                    type="number" step="0.1" min={0.1} max={5}
                    value={localDefaults.target.size_deg} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, target: {...prev.target, size_deg: v}}))}
                />
            </ConfigSection>

            {/* Calibration Settings */}
            <ConfigSection title="Calibración" icon={Activity} testId="calibration">
                <InputField 
                    label="Patrón" 
                    value={localDefaults.calibration.type} 
                    onChange={(v: any) => setLocalDefaults(prev => ({...prev, calibration: {...prev.calibration, type: v}}))}
                    options={[
                        { value: 'points_5', label: '5 Puntos (Cruz)' },
                        { value: 'points_7', label: '7 Puntos (+H)' },
                        { value: 'points_9', label: '9 Puntos (Completo)' }
                    ]}
                />
                <InputField 
                    label="Duración por Punto (s)" 
                    type="number" step="0.5" min={0.5} max={10}
                    value={localDefaults.calibration.duration} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, calibration: {...prev.calibration, duration: v}}))}
                />
            </ConfigSection>

            {/* Saccades Settings */}
            <ConfigSection title="Sacadas" icon={Move} testId="saccades">
                <InputField 
                    label="Amplitud Mínima (°)" 
                    type="number" min={1} max={40}
                    value={localDefaults.saccades.min_amplitude} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, saccades: {...prev.saccades, min_amplitude: Math.floor(v)}}))}
                />
                <InputField 
                    label="Amplitud Máxima (°)" 
                    type="number" min={1} max={40}
                    value={localDefaults.saccades.max_amplitude} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, saccades: {...prev.saccades, max_amplitude: Math.floor(v)}}))}
                />
                <InputField 
                    label="Intervalo Mínimo (s)" 
                    type="number" step="0.1" min={0.5} max={5}
                    value={localDefaults.saccades.min_interval} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, saccades: {...prev.saccades, min_interval: v}}))}
                />
                <InputField 
                    label="Intervalo Máximo (s)" 
                    type="number" step="0.1" min={0.5} max={5}
                    value={localDefaults.saccades.max_interval} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, saccades: {...prev.saccades, max_interval: v}}))}
                />
            </ConfigSection>

            {/* Pursuit Settings */}
            <ConfigSection title="Rastreo Pendular" icon={Eye} testId="pursuit">
                <InputField 
                    label="Frecuencia (Hz)" 
                    type="number" step="0.1" min={0.1} max={1.0}
                    value={localDefaults.pursuit.frequency} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, pursuit: {...prev.pursuit, frequency: v}}))}
                />
                <InputField 
                    label="Amplitud (°)" 
                    type="number" min={5} max={40}
                    value={localDefaults.pursuit.amplitudes[0]} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, pursuit: {...prev.pursuit, amplitudes: [Math.floor(v)]}}))}
                />
            </ConfigSection>

            {/* OPK Settings */}
            <ConfigSection title="Optocinético" icon={PlayCircle} testId="opk">
                <InputField 
                    label="Velocidad (°/s)" 
                    type="number" step="1" min={10} max={100}
                    value={localDefaults.opk.velocity} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, opk: {...prev.opk, velocity: Math.floor(v)}}))}
                />
                <InputField 
                    label="Ancho de Banda (°)" 
                    type="number" min={1} max={20}
                    value={localDefaults.opk.stripe_width_deg} 
                    onChange={(v: number) => setLocalDefaults(prev => ({...prev, opk: {...prev.opk, stripe_width_deg: Math.floor(v)}}))}
                />
                <InputField 
                    label="Dirección" 
                    value={localDefaults.opk.direction} 
                    onChange={(v: string) => setLocalDefaults(prev => ({...prev, opk: {...prev.opk, direction: v as any}}))}
                    options={[
                        { value: 'left', label: 'Izquierda' },
                        { value: 'right', label: 'Derecha' },
                        { value: 'up', label: 'Arriba' },
                        { value: 'down', label: 'Abajo' }
                    ]}
                />
                
                <div className="flex items-center gap-3 bg-dark-950 p-2 rounded-lg border border-dark-700">
                    <label className="text-[10px] text-dark-500 uppercase font-bold flex-1">Punto Fijación</label>
                    <button 
                        onClick={() => setLocalDefaults(prev => ({...prev, opk: {...prev.opk, fixation_enabled: !prev.opk.fixation_enabled}}))}
                        className={`w-10 h-5 rounded-full relative transition-colors ${localDefaults.opk.fixation_enabled ? 'bg-siev-500' : 'bg-dark-700'}`}
                    >
                        <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform ${localDefaults.opk.fixation_enabled ? 'translate-x-5' : ''}`} />
                    </button>
                </div>
            </ConfigSection>
        </div>
    );
};
