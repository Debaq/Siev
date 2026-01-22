import React from 'react';
import { Cpu, Target, Zap } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { SettingsToggle } from '../shared/SettingsToggle';

interface AlgorithmTabProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

export const AlgorithmTab: React.FC<AlgorithmTabProps> = ({ config, updateConfig }) => {
    return (
        <div className="space-y-8 animate-fade-in">
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

                <div className="grid grid-cols-2 gap-6">
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
            </SettingsSection>

            <SettingsSection 
                title="Detección de Pupila Avanzada"
                description="Ajustes específicos para el motor de detección híbrido."
            >
                <SettingsField label="Modo de Funcionamiento">
                    <select
                        className="select"
                        value={config.vng.pupil_detection.mode}
                        onChange={e => updateConfig('vng.pupil_detection.mode', e.target.value)}
                    >
                        <option value="hybrid">Híbrido (Recomendado)</option>
                        <option value="fast">Fast (Local Window)</option>
                        <option value="legacy">Legacy (Full ROI)</option>
                    </select>
                </SettingsField>

                {config.vng.pupil_detection.mode !== 'legacy' && (
                    <div className="grid grid-cols-2 gap-6 p-4 bg-dark-800/50 rounded-lg border border-dark-700">
                        <SettingsField label="Ventana de Búsqueda" description="Multiplicador del radio.">
                            <input
                                type="number" step="0.5" className="input"
                                value={config.vng.pupil_detection.search_window_multiplier}
                                onChange={e => updateConfig('vng.pupil_detection.search_window_multiplier', Number(e.target.value))}
                            />
                        </SettingsField>
                        <SettingsField label="Rayos Starburst" description="Número de vectores.">
                            <select
                                className="select"
                                value={config.vng.pupil_detection.starburst_rays}
                                onChange={e => updateConfig('vng.pupil_detection.starburst_rays', Number(e.target.value))}
                            >
                                <option value={8}>8 rayos</option>
                                <option value={16}>16 rayos</option>
                                <option value={24}>24 rayos</option>
                            </select>
                        </SettingsField>
                    </div>
                )}
            </SettingsSection>
        </div>
    );
};
