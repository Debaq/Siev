import React from 'react';
import { Search } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig, OtoscopiaFinding } from '../../../types/config';

interface FindingsTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

export const FindingsTab: React.FC<FindingsTabProps> = ({ config, updateConfig }) => {
    const findings = config.otoscopia.findings.findings;

    const normalFindings = findings.filter((f: OtoscopiaFinding) => f.category === 'normal');
    const pathologicalFindings = findings.filter((f: OtoscopiaFinding) => f.category === 'patologico');

    const handleToggle = (id: string) => {
        const updated = findings.map((f: OtoscopiaFinding) =>
            f.id === id ? { ...f, enabled: !f.enabled } : f
        );
        updateConfig('otoscopia.findings.findings', updated);
    };

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Hallazgos Normales"
                description="Hallazgos predefinidos que indican un estado normal de la membrana timpánica."
                icon={<Search className="w-4 h-4 text-green-500" />}
            >
                <div className="space-y-2">
                    {normalFindings.map((finding: OtoscopiaFinding) => (
                        <div
                            key={finding.id}
                            className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                                finding.enabled
                                    ? 'border-green-500/30 bg-green-500/5'
                                    : 'border-dark-800 bg-dark-900 opacity-70'
                            }`}
                        >
                            <div className="flex items-center gap-3">
                                <div className={`w-2 h-2 rounded-full ${finding.enabled ? 'bg-green-400' : 'bg-dark-600'}`} />
                                <span className={`text-sm ${finding.enabled ? 'text-white' : 'text-dark-400'}`}>
                                    {finding.label}
                                </span>
                            </div>
                            <SettingsToggle
                                checked={finding.enabled}
                                onChange={() => handleToggle(finding.id)}
                            />
                        </div>
                    ))}
                </div>
            </SettingsSection>

            <SettingsSection
                title="Hallazgos Patológicos"
                description="Hallazgos predefinidos que indican patología. Active los que desea incluir en la lista de selección rápida."
                icon={<Search className="w-4 h-4 text-amber-500" />}
            >
                <div className="space-y-2">
                    {pathologicalFindings.map((finding: OtoscopiaFinding) => (
                        <div
                            key={finding.id}
                            className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                                finding.enabled
                                    ? 'border-amber-500/30 bg-amber-500/5'
                                    : 'border-dark-800 bg-dark-900 opacity-70'
                            }`}
                        >
                            <div className="flex items-center gap-3">
                                <div className={`w-2 h-2 rounded-full ${finding.enabled ? 'bg-amber-400' : 'bg-dark-600'}`} />
                                <span className={`text-sm ${finding.enabled ? 'text-white' : 'text-dark-400'}`}>
                                    {finding.label}
                                </span>
                            </div>
                            <SettingsToggle
                                checked={finding.enabled}
                                onChange={() => handleToggle(finding.id)}
                            />
                        </div>
                    ))}
                </div>
            </SettingsSection>

            <div className="text-xs text-dark-500 border-t border-dark-700 pt-3">
                {findings.filter((f: OtoscopiaFinding) => f.enabled).length} de {findings.length} hallazgos habilitados
            </div>
        </div>
    );
};
