import React from 'react';
import { ClipboardList } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig } from '../../../types/config';

interface TestsTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

const TEST_DEFINITIONS = [
    {
        id: 'tonal_liminar',
        label: 'Audiometría Tonal Liminar',
        description: 'Determinación de umbrales auditivos por vía aérea y ósea en frecuencias estándar.',
    },
    {
        id: 'vocal',
        label: 'Audiometría Vocal (Logoaudiometría)',
        description: 'Evaluación de la discriminación del habla mediante listas de palabras.',
    },
    {
        id: 'supraliminar',
        label: 'Pruebas Supraliminares',
        description: 'Tests como SISI, Fowler y Tone Decay para evaluar reclutamiento y adaptación.',
    },
    {
        id: 'altas_frecuencias',
        label: 'Audiometría de Altas Frecuencias',
        description: 'Evaluación de umbrales en frecuencias superiores a 8000 Hz (hasta 16000 Hz).',
    },
];

export const TestsTab: React.FC<TestsTabProps> = ({ config, updateConfig }) => {
    const tests = config.audiometria.tests;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Tipos de Prueba"
                description="Active o desactive los tipos de audiometría disponibles para los informes."
                icon={<ClipboardList className="w-4 h-4 text-teal-500" />}
            >
                <div className="space-y-3">
                    {TEST_DEFINITIONS.map(test => (
                        <div
                            key={test.id}
                            className={`p-4 rounded-lg border transition-all ${
                                tests[test.id as keyof typeof tests]
                                    ? 'border-teal-500/30 bg-teal-500/5'
                                    : 'border-dark-800 bg-dark-900 opacity-70'
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex-1">
                                    <h4 className={`text-sm font-medium ${
                                        tests[test.id as keyof typeof tests] ? 'text-white' : 'text-dark-400'
                                    }`}>
                                        {test.label}
                                    </h4>
                                    <p className="text-xs text-dark-500 mt-0.5">{test.description}</p>
                                </div>
                                <SettingsToggle
                                    checked={tests[test.id as keyof typeof tests]}
                                    onChange={v => updateConfig(`audiometria.tests.${test.id}`, v)}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </SettingsSection>
        </div>
    );
};
