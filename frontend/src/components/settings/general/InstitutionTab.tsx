import React from 'react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { open } from '@tauri-apps/plugin-dialog';

interface InstitutionTabProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

export const InstitutionTab: React.FC<InstitutionTabProps> = ({ config, updateConfig }) => {
    const handleBrowseLogo = async () => {
        try {
            const selected = await open({
                multiple: false,
                filters: [{
                    name: 'Image',
                    extensions: ['png', 'jpg', 'jpeg']
                }]
            });
            
            if (selected && typeof selected === 'string') {
                updateConfig('general.institution.logo_path', selected);
            }
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="space-y-8 animate-fade-in">
            <SettingsSection 
                title="Información de la Clínica" 
                description="Estos datos aparecerán en el encabezado de los reportes PDF generados por el sistema."
            >
                <SettingsField label="Nombre de la Institución">
                    <input 
                        className="input" 
                        value={config.general.institution.name}
                        onChange={e => updateConfig('general.institution.name', e.target.value)}
                        placeholder="Ej. Clínica Santa Lucía"
                    />
                </SettingsField>

                <SettingsField label="Nombre del Profesional (Opcional)">
                    <input 
                        className="input" 
                        value={config.general.institution.doctor_name || ''}
                        onChange={e => updateConfig('general.institution.doctor_name', e.target.value)}
                        placeholder="Ej. Dr. Juan Pérez"
                    />
                </SettingsField>

                <SettingsField label="Logo de la Institución">
                    <div className="flex gap-2">
                        <input 
                            className="input flex-1" 
                            value={config.general.institution.logo_path}
                            onChange={e => updateConfig('general.institution.logo_path', e.target.value)}
                            placeholder="/ruta/a/logo.png"
                        />
                        <button className="btn btn-secondary px-4" onClick={handleBrowseLogo}>
                            Examinar
                        </button>
                    </div>
                </SettingsField>
            </SettingsSection>
        </div>
    );
};
