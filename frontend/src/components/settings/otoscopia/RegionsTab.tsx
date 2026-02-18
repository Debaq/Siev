import React from 'react';
import { MapPin } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig, OtoscopiaRegion } from '../../../types/config';

interface RegionsTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

export const RegionsTab: React.FC<RegionsTabProps> = ({ config, updateConfig }) => {
    const regions = config.otoscopia.regions.regions;

    const handleToggle = (id: string) => {
        const updated = regions.map((r: OtoscopiaRegion) =>
            r.id === id ? { ...r, enabled: !r.enabled } : r
        );
        updateConfig('otoscopia.regions.regions', updated);
    };

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Regiones Anatómicas"
                description="Regiones de la membrana timpánica disponibles para registro de hallazgos."
                icon={<MapPin className="w-4 h-4 text-amber-500" />}
            >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {regions.map((region: OtoscopiaRegion) => (
                        <div
                            key={region.id}
                            className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                                region.enabled
                                    ? 'border-amber-500/30 bg-amber-500/5'
                                    : 'border-dark-800 bg-dark-900 opacity-70'
                            }`}
                        >
                            <span className={`text-sm ${region.enabled ? 'text-white' : 'text-dark-400'}`}>
                                {region.label}
                            </span>
                            <SettingsToggle
                                checked={region.enabled}
                                onChange={() => handleToggle(region.id)}
                            />
                        </div>
                    ))}
                </div>
            </SettingsSection>

            {/* Diagrama SVG de membrana timpánica */}
            <SettingsSection
                title="Diagrama de Referencia"
                description="Esquema de la membrana timpánica con las regiones anatómicas principales."
                icon={<MapPin className="w-4 h-4 text-purple-500" />}
            >
                <div className="p-4 bg-dark-800/50 rounded-lg border border-dark-700 flex justify-center">
                    <TympanicMembraneDiagram regions={regions} />
                </div>
            </SettingsSection>

            <div className="text-xs text-dark-500 border-t border-dark-700 pt-3">
                {regions.filter((r: OtoscopiaRegion) => r.enabled).length} de {regions.length} regiones habilitadas
            </div>
        </div>
    );
};

const TympanicMembraneDiagram: React.FC<{ regions: OtoscopiaRegion[] }> = ({ regions }) => {
    const isEnabled = (id: string) => regions.find((r: OtoscopiaRegion) => r.id === id)?.enabled ?? false;
    const fillColor = (id: string) => isEnabled(id) ? 'rgba(251, 191, 36, 0.15)' : 'rgba(100, 116, 139, 0.05)';
    const strokeColor = (id: string) => isEnabled(id) ? '#f59e0b' : '#475569';
    const textColor = (id: string) => isEnabled(id) ? '#fbbf24' : '#64748b';

    return (
        <svg viewBox="0 0 200 200" className="w-48 h-48">
            {/* Annulus (borde exterior) */}
            <circle
                cx="100" cy="100" r="85"
                fill={fillColor('annulus')}
                stroke={strokeColor('annulus')}
                strokeWidth="2"
            />

            {/* Líneas de cuadrantes */}
            <line x1="100" y1="15" x2="100" y2="185" stroke="#475569" strokeWidth="0.5" strokeDasharray="3,3" />
            <line x1="15" y1="100" x2="185" y2="100" stroke="#475569" strokeWidth="0.5" strokeDasharray="3,3" />

            {/* Cuadrante anterosuperior */}
            <path
                d="M 100 100 L 100 15 A 85 85 0 0 0 15 100 Z"
                fill={fillColor('cuadrante_anterosuperior')}
                stroke="none"
            />

            {/* Cuadrante posterosuperior */}
            <path
                d="M 100 100 L 185 100 A 85 85 0 0 0 100 15 Z"
                fill={fillColor('cuadrante_posterosuperior')}
                stroke="none"
            />

            {/* Cuadrante anteroinferior */}
            <path
                d="M 100 100 L 15 100 A 85 85 0 0 0 100 185 Z"
                fill={fillColor('cuadrante_anteroinferior')}
                stroke="none"
            />

            {/* Cuadrante posteroinferior */}
            <path
                d="M 100 100 L 100 185 A 85 85 0 0 0 185 100 Z"
                fill={fillColor('cuadrante_posteroinferior')}
                stroke="none"
            />

            {/* Mango del martillo */}
            <line
                x1="100" y1="40" x2="100" y2="100"
                stroke={strokeColor('mango_martillo')}
                strokeWidth="3"
                strokeLinecap="round"
            />

            {/* Umbo */}
            <circle
                cx="100" cy="100" r="4"
                fill={strokeColor('umbo')}
            />

            {/* Triángulo luminoso */}
            <path
                d="M 100 104 L 65 155 L 85 160 Z"
                fill={fillColor('triangulo_luminoso')}
                stroke={strokeColor('triangulo_luminoso')}
                strokeWidth="1"
            />

            {/* Pars flácida */}
            <ellipse
                cx="100" cy="28" rx="25" ry="12"
                fill={fillColor('pars_flaccida')}
                stroke={strokeColor('pars_flaccida')}
                strokeWidth="1"
                strokeDasharray="2,2"
            />

            {/* Labels */}
            <text x="55" y="65" fill={textColor('cuadrante_anterosuperior')} fontSize="7" textAnchor="middle">AS</text>
            <text x="145" y="65" fill={textColor('cuadrante_posterosuperior')} fontSize="7" textAnchor="middle">PS</text>
            <text x="55" y="150" fill={textColor('cuadrante_anteroinferior')} fontSize="7" textAnchor="middle">AI</text>
            <text x="145" y="150" fill={textColor('cuadrante_posteroinferior')} fontSize="7" textAnchor="middle">PI</text>
            <text x="100" y="22" fill={textColor('pars_flaccida')} fontSize="6" textAnchor="middle">P. flácida</text>
        </svg>
    );
};
