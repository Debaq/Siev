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
        id: 'timpanograma',
        label: 'Timpanograma',
        description: 'Medición de la compliance del oído medio en función de la presión. Curva de admitancia.',
    },
    {
        id: 'reflejo_ipsilateral',
        label: 'Reflejo Estapedial Ipsilateral',
        description: 'Respuesta refleja del músculo estapedio estimulando y midiendo en el mismo oído.',
    },
    {
        id: 'reflejo_contralateral',
        label: 'Reflejo Estapedial Contralateral',
        description: 'Respuesta refleja estimulando en un oído y midiendo en el contralateral.',
    },
    {
        id: 'decay',
        label: 'Decay del Reflejo (Fatiga)',
        description: 'Evaluación de la adaptación del reflejo estapedial ante estímulo sostenido.',
    },
    {
        id: 'funcion_tubarica',
        label: 'Función Tubárica',
        description: 'Evaluación de la función de la trompa de Eustaquio mediante cambios de presión.',
    },
];

export const TestsTab: React.FC<TestsTabProps> = ({ config, updateConfig }) => {
    const tests = config.impedanciometria.tests;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Tipos de Prueba"
                description="Active o desactive las pruebas de impedanciometría disponibles para los informes."
                icon={<ClipboardList className="w-4 h-4 text-rose-500" />}
            >
                <div className="space-y-3">
                    {TEST_DEFINITIONS.map(test => (
                        <div
                            key={test.id}
                            className={`p-4 rounded-lg border transition-all ${
                                tests[test.id as keyof typeof tests]
                                    ? 'border-rose-500/30 bg-rose-500/5'
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
                                    onChange={v => updateConfig(`impedanciometria.tests.${test.id}`, v)}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </SettingsSection>
        </div>
    );
};
