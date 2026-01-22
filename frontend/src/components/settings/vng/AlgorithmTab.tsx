import React from 'react';
import { Cpu, Target, Zap, Eye, Settings2 } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig } from '../../../types/config';

interface AlgorithmTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
    apiUrl: string;
}

export const AlgorithmTab: React.FC<AlgorithmTabProps> = ({ config, updateConfig, apiUrl }) => {
    const pupilConfig = config.vng.pupil_detection;
    const legacyConfig = pupilConfig.legacy;

    // Send debug toggle to backend
    const handleDebugToggle = async (enabled: boolean) => {
        try {
            await fetch(`${apiUrl}/video/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ show_debug: enabled })
            });
        } catch (e) {
            console.error('Failed to toggle debug:', e);
        }
    };

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Main Algorithm Selection */}
            <SettingsSection
                title="Algoritmos de Rastreo"
                description="Seleccione el motor de procesamiento para la detección de la pupila."
            >
                <SettingsField label="Motor Principal">
                    <select
                        className="select"
                        value={config.vng.algorithm.primary}
                        onChange={e => updateConfig('vng.algorithm.primary', e.target.value)}
                    >
                        <option value="yolo">Deep Learning (YOLOv8) - Recomendado</option>
                        <option value="hough">Hough Circle Transform</option>
                        <option value="threshold">Dark Threshold (Pupil only)</option>
                    </select>
                </SettingsField>

                <div className="grid grid-cols-2 gap-4">
                    <SettingsField label="Umbral de Binarización">
                        <input
                            type="number" className="input"
                            value={config.vng.algorithm.threshold}
                            onChange={e => updateConfig('vng.algorithm.threshold', Number(e.target.value))}
                        />
                    </SettingsField>
                    <SettingsField label="Tamaño Mín. Pupila (px)">
                        <input
                            type="number" className="input"
                            value={config.vng.algorithm.min_pupil_size}
                            onChange={e => updateConfig('vng.algorithm.min_pupil_size', Number(e.target.value))}
                        />
                    </SettingsField>
                </div>

                {/* Debug Toggle */}
                <div className="flex items-center justify-between p-2.5 bg-dark-800/50 rounded-lg border border-dark-700">
                    <div className="flex items-center gap-2">
                        <Eye className="w-4 h-4 text-siev-400" />
                        <span className="text-xs font-medium text-dark-200">Mostrar Debug en Video</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                        <input
                            type="checkbox"
                            className="sr-only peer"
                            onChange={e => handleDebugToggle(e.target.checked)}
                        />
                        <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-dark-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-siev-500"></div>
                    </label>
                </div>
            </SettingsSection>

            {/* Pupil Detection Mode */}
            <SettingsSection
                title="Detección de Pupila"
                description="Configuración del modo y parámetros de detección."
                icon={<Target className="w-4 h-4 text-siev-500" />}
            >
                <SettingsField label="Modo de Detección">
                    <select
                        className="select"
                        value={pupilConfig.mode}
                        onChange={e => updateConfig('vng.pupil_detection.mode', e.target.value)}
                    >
                        <option value="hybrid">Híbrido (Recomendado) - Fast + Fallback Legacy</option>
                        <option value="fast">Fast - Ventana Local + Starburst</option>
                        <option value="legacy">Legacy - Threshold + CLAHE + Contornos</option>
                    </select>
                </SettingsField>
                <p className="text-[10px] text-dark-500 -mt-1.5 leading-tight">
                    {pupilConfig.mode === 'fast' && 'Máximo rendimiento, puede perder tracking en movimientos rápidos.'}
                    {pupilConfig.mode === 'legacy' && 'Método tradicional, procesa toda la ROI en cada frame.'}
                    {pupilConfig.mode === 'hybrid' && 'Combina velocidad del Fast con robustez del Legacy como respaldo.'}
                </p>
            </SettingsSection>

            {/* Fast/Hybrid Parameters */}
            {(pupilConfig.mode === 'fast' || pupilConfig.mode === 'hybrid') && (
                <SettingsSection
                    title="Parámetros Avanzados (Fast/Hybrid)"
                    description="Ajustes del algoritmo de detección rápida."
                    icon={<Zap className="w-4 h-4 text-yellow-500" />}
                >
                    <div className="grid grid-cols-2 gap-4">
                        <SettingsField label="Multiplicador Ventana" description="Ventana = radio × N">
                            <input
                                type="number"
                                step="0.5"
                                min="1.5"
                                max="5"
                                className="input"
                                value={pupilConfig.search_window_multiplier}
                                onChange={e => updateConfig('vng.pupil_detection.search_window_multiplier', Number(e.target.value))}
                            />
                        </SettingsField>

                        <SettingsField label="Offset Umbral Oscuro (%)" description="% sobre punto más oscuro">
                            <input
                                type="number"
                                min="5"
                                max="50"
                                className="input"
                                value={pupilConfig.dark_threshold_percent}
                                onChange={e => updateConfig('vng.pupil_detection.dark_threshold_percent', Number(e.target.value))}
                            />
                        </SettingsField>

                        <SettingsField label="Rayos Starburst" description="Más rayos = más precisión">
                            <select
                                className="select"
                                value={pupilConfig.starburst_rays}
                                onChange={e => updateConfig('vng.pupil_detection.starburst_rays', Number(e.target.value))}
                            >
                                <option value={8}>8 rayos (45°)</option>
                                <option value={12}>12 rayos (30°)</option>
                                <option value={16}>16 rayos (22.5°)</option>
                                <option value={24}>24 rayos (15°)</option>
                            </select>
                        </SettingsField>

                        <SettingsField label="Gradiente Mín. Borde" description="Sensibilidad del borde">
                            <input
                                type="number"
                                min="10"
                                max="80"
                                className="input"
                                value={pupilConfig.starburst_min_gradient}
                                onChange={e => updateConfig('vng.pupil_detection.starburst_min_gradient', Number(e.target.value))}
                            />
                        </SettingsField>

                        {pupilConfig.mode === 'hybrid' && (
                            <>
                                <SettingsField label="Umbral Fallback (frames)" description="Frames sin detección antes de activar Legacy">
                                    <input
                                        type="number"
                                        min="1"
                                        max="30"
                                        className="input"
                                        value={pupilConfig.fallback_threshold}
                                        onChange={e => updateConfig('vng.pupil_detection.fallback_threshold', Number(e.target.value))}
                                    />
                                </SettingsField>

                                <SettingsField label="Confianza Mín. Lock" description="Circularidad mínima (0-1) para aceptar detección inicial">
                                    <input
                                        type="number"
                                        step="0.1"
                                        min="0.1"
                                        max="1.0"
                                        className="input"
                                        value={pupilConfig.min_confidence_for_lock}
                                        onChange={e => updateConfig('vng.pupil_detection.min_confidence_for_lock', Number(e.target.value))}
                                    />
                                </SettingsField>

                                <SettingsField label="Intervalo Re-validación" description="Cada N frames, verificar con Legacy">
                                    <input
                                        type="number"
                                        min="10"
                                        max="120"
                                        className="input"
                                        value={pupilConfig.revalidation_interval}
                                        onChange={e => updateConfig('vng.pupil_detection.revalidation_interval', Number(e.target.value))}
                                    />
                                </SettingsField>
                            </>
                        )}
                    </div>
                </SettingsSection>
            )}

            {/* Legacy Parameters */}
            {(pupilConfig.mode === 'legacy' || pupilConfig.mode === 'hybrid') && (
                <SettingsSection
                    title={`Parámetros Legacy ${pupilConfig.mode === 'hybrid' ? '(usado en fallback)' : ''}`}
                    description="Pipeline de procesamiento tradicional con filtros configurables."
                    icon={<Settings2 className="w-4 h-4 text-purple-500" />}
                >
                    {/* Stage 1: GaussianBlur */}
                    <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-[10px] font-bold">1</span>
                                <span className="text-xs font-medium text-dark-200">GaussianBlur</span>
                                <span className="text-[10px] text-dark-500">Reducción de ruido</span>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="sr-only peer"
                                    checked={legacyConfig.blur_enabled}
                                    onChange={e => updateConfig('vng.pupil_detection.legacy.blur_enabled', e.target.checked)}
                                />
                                <div className="w-9 h-5 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-dark-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-500"></div>
                            </label>
                        </div>
                        {legacyConfig.blur_enabled && (
                            <div className="ml-7">
                                <label className="block text-[10px] text-dark-400 mb-1">Tamaño Kernel</label>
                                <select
                                    className="select text-xs w-28 h-8 py-0"
                                    value={legacyConfig.blur_kernel}
                                    onChange={e => updateConfig('vng.pupil_detection.legacy.blur_kernel', Number(e.target.value))}
                                >
                                    <option value={3}>3×3</option>
                                    <option value={5}>5×5</option>
                                    <option value={7}>7×7</option>
                                    <option value={9}>9×9</option>
                                </select>
                            </div>
                        )}
                    </div>

                    {/* Stage 2: CLAHE */}
                    <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full bg-green-600/20 text-green-400 flex items-center justify-center text-[10px] font-bold">2</span>
                                <span className="text-xs font-medium text-dark-200">CLAHE</span>
                                <span className="text-[10px] text-dark-500">Mejora de contraste</span>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="sr-only peer"
                                    checked={legacyConfig.clahe_enabled}
                                    onChange={e => updateConfig('vng.pupil_detection.legacy.clahe_enabled', e.target.checked)}
                                />
                                <div className="w-9 h-5 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-dark-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-green-500"></div>
                            </label>
                        </div>
                        {legacyConfig.clahe_enabled && (
                            <div className="ml-7 grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-[10px] text-dark-400 mb-1">Clip Limit</label>
                                    <input
                                        type="number"
                                        step="0.5"
                                        min="1"
                                        max="5"
                                        className="input text-xs h-8"
                                        value={legacyConfig.clahe_clip_limit}
                                        onChange={e => updateConfig('vng.pupil_detection.legacy.clahe_clip_limit', Number(e.target.value))}
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] text-dark-400 mb-1">Grid Size</label>
                                    <select
                                        className="select text-xs h-8 py-0"
                                        value={legacyConfig.clahe_grid_size}
                                        onChange={e => updateConfig('vng.pupil_detection.legacy.clahe_grid_size', Number(e.target.value))}
                                    >
                                        <option value={4}>4×4</option>
                                        <option value={8}>8×8</option>
                                        <option value={16}>16×16</option>
                                    </select>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Stage 3: Morphology */}
                    <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full bg-purple-600/20 text-purple-400 flex items-center justify-center text-[10px] font-bold">3</span>
                                <span className="text-xs font-medium text-dark-200">Morfología</span>
                                <span className="text-[10px] text-dark-500">Close + Dilate</span>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="sr-only peer"
                                    checked={legacyConfig.morph_enabled}
                                    onChange={e => updateConfig('vng.pupil_detection.legacy.morph_enabled', e.target.checked)}
                                />
                                <div className="w-9 h-5 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-dark-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-500"></div>
                            </label>
                        </div>
                        {legacyConfig.morph_enabled && (
                            <div className="ml-7 grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-[10px] text-dark-400 mb-1">Close Iters</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="5"
                                        className="input text-xs h-8"
                                        value={legacyConfig.morph_close_iterations}
                                        onChange={e => updateConfig('vng.pupil_detection.legacy.morph_close_iterations', Number(e.target.value))}
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] text-dark-400 mb-1">Dilate Iters</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="5"
                                        className="input text-xs h-8"
                                        value={legacyConfig.morph_dilate_iterations}
                                        onChange={e => updateConfig('vng.pupil_detection.legacy.morph_dilate_iterations', Number(e.target.value))}
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                </SettingsSection>
            )}
        </div>
    );
};
