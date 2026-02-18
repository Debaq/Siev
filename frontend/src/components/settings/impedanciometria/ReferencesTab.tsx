import React from 'react';
import { BookOpen } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { AppConfig } from '../../../types/config';

interface ReferencesTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

export const ReferencesTab: React.FC<ReferencesTabProps> = ({ config, updateConfig }) => {
    const references = config.impedanciometria.references;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Curvas Normativas"
                description="Seleccione el estándar de referencia para la clasificación de timpanogramas."
                icon={<BookOpen className="w-4 h-4 text-rose-500" />}
            >
                <SettingsField label="Normativa">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={references.normative}
                        onChange={e => updateConfig('impedanciometria.references.normative', e.target.value)}
                    >
                        <option value="jerger_1970">Jerger (1970) — Clasificación clásica</option>
                        <option value="asha_1997">ASHA (1997) — Guía actualizada</option>
                    </select>
                </SettingsField>

                <div className="text-xs text-dark-400 mt-2">
                    {references.normative === 'jerger_1970' && 'Clasificación de Jerger (1970): tipos A, As, Ad, B y C. La más utilizada en la práctica clínica.'}
                    {references.normative === 'asha_1997' && 'Guía ASHA (1997): valores normativos actualizados con rangos de compliance y presión revisados.'}
                </div>
            </SettingsSection>

            {/* Curva de referencia visual */}
            <SettingsSection
                title="Curva Normativa de Referencia"
                description="Visualización esquemática de la curva timpanométrica normal según la normativa seleccionada."
                icon={<BookOpen className="w-4 h-4 text-purple-500" />}
            >
                <div className="p-4 bg-dark-800/50 rounded-lg border border-dark-700 flex justify-center">
                    <TympanogramReference />
                </div>
                <div className="text-xs text-dark-500 mt-2 text-center">
                    Curva Tipo A (normal): pico entre -100 y +50 daPa, compliance 0.3–1.75 ml
                </div>
            </SettingsSection>
        </div>
    );
};

const TympanogramReference: React.FC = () => {
    return (
        <svg viewBox="0 0 240 140" className="w-full h-32">
            {/* Ejes */}
            <line x1="40" y1="10" x2="40" y2="120" stroke="#475569" strokeWidth="1" />
            <line x1="40" y1="120" x2="230" y2="120" stroke="#475569" strokeWidth="1" />

            {/* Eje Y - Compliance */}
            <text x="8" y="70" fill="#64748b" fontSize="7" transform="rotate(-90, 8, 70)">Compliance (ml)</text>
            <text x="35" y="25" fill="#64748b" fontSize="6" textAnchor="end">1.5</text>
            <text x="35" y="55" fill="#64748b" fontSize="6" textAnchor="end">1.0</text>
            <text x="35" y="85" fill="#64748b" fontSize="6" textAnchor="end">0.5</text>
            <text x="35" y="118" fill="#64748b" fontSize="6" textAnchor="end">0</text>

            {/* Eje X - Presión */}
            <text x="135" y="136" fill="#64748b" fontSize="7" textAnchor="middle">Presión (daPa)</text>
            <text x="55" y="132" fill="#64748b" fontSize="6" textAnchor="middle">-400</text>
            <text x="95" y="132" fill="#64748b" fontSize="6" textAnchor="middle">-200</text>
            <text x="135" y="132" fill="#64748b" fontSize="6" textAnchor="middle">0</text>
            <text x="175" y="132" fill="#64748b" fontSize="6" textAnchor="middle">+200</text>
            <text x="215" y="132" fill="#64748b" fontSize="6" textAnchor="middle">+400</text>

            {/* Grid lines */}
            {[55, 95, 135, 175, 215].map(x => (
                <line key={x} x1={x} y1="15" x2={x} y2="120" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,3" />
            ))}
            {[25, 55, 85].map(y => (
                <line key={y} x1="40" y1={y} x2="230" y2={y} stroke="#334155" strokeWidth="0.5" strokeDasharray="2,3" />
            ))}

            {/* Zona normal (sombreada) */}
            <rect x="115" y="20" width="40" height="95" fill="rgba(244, 63, 94, 0.08)" stroke="rgba(244, 63, 94, 0.2)" strokeWidth="0.5" strokeDasharray="3,3" rx="2" />

            {/* Curva Tipo A */}
            <path
                d="M 55 115 Q 75 112 95 108 Q 115 95 130 40 Q 140 30 145 40 Q 160 95 180 108 Q 200 112 215 115"
                fill="none"
                stroke="#f43f5e"
                strokeWidth="2"
            />

            {/* Pico */}
            <circle cx="137" cy="32" r="3" fill="#f43f5e" />
            <text x="142" y="28" fill="#f43f5e" fontSize="7" fontWeight="bold">Tipo A</text>
        </svg>
    );
};
