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
        <div className="space-y-6 animate-fade-in">
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

                <div className="grid grid-cols-2 gap-4">
                    <SettingsField label="Teléfono de Contacto">
                        <input 
                            className="input" 
                            value={config.general.institution.phone || ''}
                            onChange={e => updateConfig('general.institution.phone', e.target.value)}
                            placeholder="+56 9 ..."
                        />
                    </SettingsField>

                    <SettingsField label="Correo Electrónico">
                        <input 
                            className="input" 
                            value={config.general.institution.email || ''}
                            onChange={e => updateConfig('general.institution.email', e.target.value)}
                            placeholder="contacto@clinica.com"
                        />
                    </SettingsField>
                </div>

                <SettingsField label="Dirección">
                    <input 
                        className="input" 
                        value={config.general.institution.address || ''}
                        onChange={e => updateConfig('general.institution.address', e.target.value)}
                        placeholder="Av. Principal 123, Ciudad"
                    />
                </SettingsField>

                <SettingsField label="Otros Antecedentes (Opcional)" description="Información adicional para el pie de página o encabezado.">
                    <textarea 
                        className="input min-h-[80px] py-2" 
                        value={config.general.institution.extra_info || ''}
                        onChange={e => updateConfig('general.institution.extra_info', e.target.value)}
                        placeholder="Ej. Registro Sanitario Nº 12345"
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
