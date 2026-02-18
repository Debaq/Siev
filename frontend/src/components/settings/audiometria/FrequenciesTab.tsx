import React from 'react';
import { Music } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { AppConfig } from '../../../types/config';

interface FrequenciesTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

const RANGE_DESCRIPTIONS: Record<string, string> = {
    standard: 'Frecuencias estándar (250–8000 Hz): evaluación audiológica convencional.',
    extended: 'Rango extendido (125–8000 Hz): incluye frecuencias intermedias para mayor resolución.',
    high_frequency: 'Altas frecuencias (8000–16000 Hz): detección temprana de daño coclear.',
};

const formatFrequency = (hz: number): string => {
    if (hz >= 1000) {
        const khz = hz / 1000;
        return Number.isInteger(khz) ? `${khz} kHz` : `${khz.toFixed(1)} kHz`;
    }
    return `${hz} Hz`;
};

export const FrequenciesTab: React.FC<FrequenciesTabProps> = ({ config, updateConfig }) => {
    const frequencies = config.audiometria.frequencies;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Rango de Frecuencias por Defecto"
                description="Seleccione el rango de frecuencias que se utilizará por defecto en nuevos estudios."
                icon={<Music className="w-4 h-4 text-teal-500" />}
            >
                <SettingsField label="Rango predeterminado">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={frequencies.default_range}
                        onChange={e => updateConfig('audiometria.frequencies.default_range', e.target.value)}
                    >
                        <option value="standard">Estándar (250–8000 Hz)</option>
                        <option value="extended">Extendido (125–8000 Hz)</option>
                        <option value="high_frequency">Altas Frecuencias (8–16 kHz)</option>
                    </select>
                </SettingsField>

                <div className="text-xs text-dark-400 mt-2">
                    {RANGE_DESCRIPTIONS[frequencies.default_range]}
                </div>
            </SettingsSection>

            <SettingsSection
                title="Frecuencias Configuradas"
                description="Frecuencias incluidas en cada rango de evaluación."
                icon={<Music className="w-4 h-4 text-purple-500" />}
            >
                <div className="space-y-4">
                    {(['standard', 'extended', 'high_frequency'] as const).map(rangeKey => {
                        const label = rangeKey === 'standard' ? 'Estándar' : rangeKey === 'extended' ? 'Extendido' : 'Altas Frecuencias';
                        const isDefault = frequencies.default_range === rangeKey;
                        return (
                            <div
                                key={rangeKey}
                                className={`p-3 rounded-lg border transition-all ${
                                    isDefault ? 'border-teal-500/30 bg-teal-500/5' : 'border-dark-800 bg-dark-900'
                                }`}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <h4 className={`text-sm font-medium ${isDefault ? 'text-teal-400' : 'text-dark-300'}`}>
                                        {label}
                                    </h4>
                                    {isDefault && (
                                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-400 border border-teal-500/30">
                                            DEFAULT
                                        </span>
                                    )}
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                    {frequencies[rangeKey].map((freq: number) => (
                                        <span
                                            key={freq}
                                            className={`text-[10px] font-mono px-2 py-1 rounded ${
                                                isDefault
                                                    ? 'bg-teal-500/10 text-teal-300 border border-teal-500/20'
                                                    : 'bg-dark-800 text-dark-400 border border-dark-700'
                                            }`}
                                        >
                                            {formatFrequency(freq)}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </SettingsSection>
        </div>
    );
};
