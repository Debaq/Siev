import React from 'react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { AppConfig } from '../../../types/config';
import { useWebSocket } from '../../../contexts/WebSocketContext';

interface AlgorithmTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

export const AlgorithmTab: React.FC<AlgorithmTabProps> = ({ config, updateConfig }) => {
    const { send } = useWebSocket();

    const handleConfigChange = (path: string, value: any, wsKey?: string) => {
        updateConfig(path, value);
        if (wsKey) {
            send({ type: 'set_config', key: wsKey, value: value });
        }
    };

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Algoritmos de Rastreo"
                description="Seleccione el motor de procesamiento para la detección de la pupila."
            >
                <SettingsField label="Motor Principal">
                    <select
                        className="select"
                        value={config.vng.algorithm.primary}
                        onChange={e => handleConfigChange('vng.algorithm.primary', e.target.value, 'primary_algorithm')}
                    >
                        <option value="yolo26">Deep Learning (YOLO26) - Recomendado</option>
                        <option value="hough">Hough Circle Transform</option>
                        <option value="threshold">Dark Threshold (Pupil only)</option>
                    </select>
                </SettingsField>

                {config.vng.algorithm.primary === 'yolo26' && (
                    <div className="grid grid-cols-3 gap-4 p-4 bg-dark-800/30 rounded-lg border border-dark-700/50">
                        <SettingsField label="Frecuencia YOLO (Frames)">
                            <div className="flex flex-col gap-1">
                                <input
                                    type="number" className="input"
                                    min="1" max="60"
                                    value={config.vng.algorithm.yolo_frequency || 4}
                                    onChange={e => handleConfigChange('vng.algorithm.yolo_frequency', Number(e.target.value), 'yolo_frequency')}
                                />
                                <span className="text-[10px] text-dark-500">Ej: 4 = Inferencia cada 4 frames</span>
                            </div>
                        </SettingsField>
                        <SettingsField label="Confianza Ojos">
                            <div className="flex flex-col gap-1">
                                <input
                                    type="number" className="input"
                                    min="0.1" max="1.0" step="0.05"
                                    value={config.vng.algorithm.yolo_confidence || 0.5}
                                    onChange={e => handleConfigChange('vng.algorithm.yolo_confidence', Number(e.target.value), 'yolo_confidence')}
                                />
                                <span className="text-[10px] text-dark-500">Valor entre 0.1 y 1.0 (Def: 0.5)</span>
                            </div>
                        </SettingsField>
                        <SettingsField label="Confianza Pupilas">
                            <div className="flex flex-col gap-1">
                                <input
                                    type="number" className="input"
                                    min="0.1" max="1.0" step="0.05"
                                    value={config.vng.algorithm.yolo_pupil_confidence || 0.3}
                                    onChange={e => handleConfigChange('vng.algorithm.yolo_pupil_confidence', Number(e.target.value), 'yolo_pupil_confidence')}
                                />
                                <span className="text-[10px] text-dark-500">Valor entre 0.1 y 1.0 (Def: 0.3)</span>
                            </div>
                        </SettingsField>
                    </div>
                )}
            </SettingsSection>
        </div>
    );
};
