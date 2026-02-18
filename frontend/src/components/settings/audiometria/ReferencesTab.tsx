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
    const references = config.audiometria.references;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Normativas de Referencia"
                description="Seleccione el estándar normativo para la clasificación de umbrales auditivos."
                icon={<BookOpen className="w-4 h-4 text-teal-500" />}
            >
                <SettingsField label="Normativa">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={references.normative}
                        onChange={e => updateConfig('audiometria.references.normative', e.target.value)}
                    >
                        <option value="iso_7029">ISO 7029 — Umbrales relacionados con edad</option>
                        <option value="ansi_s3_6">ANSI S3.6 — Audiómetros estándar</option>
                    </select>
                </SettingsField>

                <div className="text-xs text-dark-400 mt-2">
                    {references.normative === 'iso_7029' && 'Define umbrales de audición esperados según edad y sexo (ISO 7029:2017).'}
                    {references.normative === 'ansi_s3_6' && 'Especificaciones para audiómetros con valores de referencia ANSI (ANSI S3.6-2018).'}
                </div>
            </SettingsSection>

            <SettingsSection
                title="Umbral Normal"
                description="Defina el límite en dB HL por debajo del cual se considera audición normal."
                icon={<BookOpen className="w-4 h-4 text-green-500" />}
            >
                <SettingsField label="Umbral normal (dB HL)">
                    <div className="flex items-center gap-3">
                        <input
                            type="range"
                            min={10}
                            max={40}
                            step={5}
                            value={references.normal_threshold_db}
                            onChange={e => updateConfig('audiometria.references.normal_threshold_db', Number(e.target.value))}
                            className="flex-1 accent-teal-500"
                        />
                        <span className="text-sm font-mono text-white w-14 text-right">
                            {references.normal_threshold_db} dB
                        </span>
                    </div>
                </SettingsField>

                <div className="text-xs text-dark-500 mt-1">
                    Valores comunes: 20 dB (niños), 25 dB (adultos), 30 dB (criterio relajado).
                </div>
            </SettingsSection>
        </div>
    );
};
