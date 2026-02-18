import React from 'react';
import { BarChart3 } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig, JergerTypeConfig } from '../../../types/config';

interface ClassificationTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

const TYPE_COLORS: Record<string, { border: string; bg: string; text: string; accent: string }> = {
    'A':  { border: 'border-green-500/30',  bg: 'bg-green-500/5',  text: 'text-green-400',  accent: '#22c55e' },
    'As': { border: 'border-blue-500/30',   bg: 'bg-blue-500/5',   text: 'text-blue-400',   accent: '#3b82f6' },
    'Ad': { border: 'border-purple-500/30', bg: 'bg-purple-500/5', text: 'text-purple-400', accent: '#a855f7' },
    'B':  { border: 'border-rose-500/30',   bg: 'bg-rose-500/5',   text: 'text-rose-400',   accent: '#f43f5e' },
    'C':  { border: 'border-amber-500/30',  bg: 'bg-amber-500/5',  text: 'text-amber-400',  accent: '#f59e0b' },
};

export const ClassificationTab: React.FC<ClassificationTabProps> = ({ config, updateConfig }) => {
    const jergerTypes = config.impedanciometria.classification.jerger_types;

    const handleToggle = (id: string) => {
        const updated = jergerTypes.map((t: JergerTypeConfig) =>
            t.id === id ? { ...t, enabled: !t.enabled } : t
        );
        updateConfig('impedanciometria.classification.jerger_types', updated);
    };

    const handleRangeChange = (id: string, field: string, value: number) => {
        const updated = jergerTypes.map((t: JergerTypeConfig) =>
            t.id === id ? { ...t, [field]: value } : t
        );
        updateConfig('impedanciometria.classification.jerger_types', updated);
    };

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Clasificación de Jerger"
                description="Configure los tipos de timpanograma según la clasificación de Jerger. Ajuste los rangos de compliance y presión."
                icon={<BarChart3 className="w-4 h-4 text-rose-500" />}
            >
                <div className="space-y-4">
                    {jergerTypes.map((type: JergerTypeConfig) => {
                        const colors = TYPE_COLORS[type.id] || TYPE_COLORS['A'];
                        return (
                            <div
                                key={type.id}
                                className={`rounded-xl border transition-all overflow-hidden ${
                                    type.enabled ? colors.border + ' ' + colors.bg : 'border-dark-800 bg-dark-900 opacity-60'
                                }`}
                            >
                                {/* Header */}
                                <div className="flex items-center justify-between p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-dark-950 border border-dark-700 flex items-center justify-center">
                                            <JergerMiniCurve typeId={type.id} color={colors.accent} />
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className={`text-sm font-bold ${type.enabled ? colors.text : 'text-dark-400'}`}>
                                                    {type.label}
                                                </span>
                                                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded bg-dark-950 border border-dark-700 ${colors.text}`}>
                                                    {type.id}
                                                </span>
                                            </div>
                                            <p className="text-xs text-dark-500">{type.description}</p>
                                        </div>
                                    </div>
                                    <SettingsToggle
                                        checked={type.enabled}
                                        onChange={() => handleToggle(type.id)}
                                    />
                                </div>

                                {/* Rangos editables */}
                                {type.enabled && (
                                    <div className="px-4 pb-4 pt-0">
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="space-y-2">
                                                <label className="text-[10px] font-semibold text-dark-400 uppercase tracking-wider">
                                                    Compliance (ml)
                                                </label>
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="number"
                                                        step="0.05"
                                                        min="0"
                                                        max="10"
                                                        value={type.compliance_min}
                                                        onChange={e => handleRangeChange(type.id, 'compliance_min', Number(e.target.value))}
                                                        className="input h-8 text-xs w-20 text-center"
                                                    />
                                                    <span className="text-dark-500 text-xs">—</span>
                                                    <input
                                                        type="number"
                                                        step="0.05"
                                                        min="0"
                                                        max="10"
                                                        value={type.compliance_max}
                                                        onChange={e => handleRangeChange(type.id, 'compliance_max', Number(e.target.value))}
                                                        className="input h-8 text-xs w-20 text-center"
                                                    />
                                                </div>
                                            </div>

                                            <div className="space-y-2">
                                                <label className="text-[10px] font-semibold text-dark-400 uppercase tracking-wider">
                                                    Presión (daPa)
                                                </label>
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="number"
                                                        step="10"
                                                        min="-600"
                                                        max="600"
                                                        value={type.pressure_min}
                                                        onChange={e => handleRangeChange(type.id, 'pressure_min', Number(e.target.value))}
                                                        className="input h-8 text-xs w-20 text-center"
                                                    />
                                                    <span className="text-dark-500 text-xs">—</span>
                                                    <input
                                                        type="number"
                                                        step="10"
                                                        min="-600"
                                                        max="600"
                                                        value={type.pressure_max}
                                                        onChange={e => handleRangeChange(type.id, 'pressure_max', Number(e.target.value))}
                                                        className="input h-8 text-xs w-20 text-center"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </SettingsSection>
        </div>
    );
};

const JergerMiniCurve: React.FC<{ typeId: string; color: string }> = ({ typeId, color }) => {
    const curves: Record<string, string> = {
        'A':  'M 2 28 Q 10 26 15 15 Q 18 8 20 15 Q 25 26 33 28',
        'As': 'M 2 28 Q 10 27 15 22 Q 18 18 20 22 Q 25 27 33 28',
        'Ad': 'M 2 28 Q 10 25 15 8 Q 17 2 20 8 Q 25 25 33 28',
        'B':  'M 2 25 Q 10 24 17 23 Q 20 22 23 23 Q 30 24 33 25',
        'C':  'M 2 28 Q 5 26 8 15 Q 10 8 12 15 Q 15 26 20 28 Q 26 28 33 28',
    };

    return (
        <svg viewBox="0 0 35 30" className="w-8 h-8">
            <path
                d={curves[typeId] || curves['A']}
                fill="none"
                stroke={color}
                strokeWidth="2"
                strokeLinecap="round"
            />
        </svg>
    );
};
