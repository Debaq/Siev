import React from 'react';
import { ImageIcon, Camera } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig } from '../../../types/config';

interface ImagesTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

export const ImagesTab: React.FC<ImagesTabProps> = ({ config, updateConfig }) => {
    const images = config.otoscopia.images;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Captura de Imágenes"
                description="Configure las opciones de captura fotográfica durante la otoscopia."
                icon={<Camera className="w-4 h-4 text-amber-500" />}
            >
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm text-dark-200">Habilitar Captura</div>
                            <div className="text-xs text-dark-500">Permitir capturar imágenes otoscópicas durante el examen</div>
                        </div>
                        <SettingsToggle
                            checked={images.capture_enabled}
                            onChange={v => updateConfig('otoscopia.images.capture_enabled', v)}
                        />
                    </div>

                    {!images.capture_enabled && (
                        <div className="p-3 rounded-lg border border-dark-800 bg-dark-900">
                            <p className="text-xs text-dark-500">
                                La captura de imágenes requiere un otoscopio con cámara digital conectado.
                                Active esta opción cuando disponga del hardware necesario.
                            </p>
                        </div>
                    )}
                </div>
            </SettingsSection>

            <SettingsSection
                title="Imágenes de Referencia"
                description="Mostrar imágenes de referencia de hallazgos otoscópicos para comparación visual."
                icon={<ImageIcon className="w-4 h-4 text-purple-500" />}
            >
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm text-dark-200">Mostrar Imágenes de Referencia</div>
                            <div className="text-xs text-dark-500">Mostrar atlas de referencia durante el registro de hallazgos</div>
                        </div>
                        <SettingsToggle
                            checked={images.reference_images_enabled}
                            onChange={v => updateConfig('otoscopia.images.reference_images_enabled', v)}
                        />
                    </div>

                    {images.reference_images_enabled && (
                        <div className="grid grid-cols-3 gap-2">
                            {['Normal', 'Perforación', 'Retracción', 'Otorrea', 'Colesteatoma', 'Miringoesclerosis'].map(label => (
                                <div
                                    key={label}
                                    className="aspect-square rounded-lg border border-dark-700 bg-dark-800 flex items-center justify-center"
                                >
                                    <div className="text-center">
                                        <ImageIcon className="w-6 h-6 text-dark-600 mx-auto mb-1" />
                                        <span className="text-[9px] text-dark-500">{label}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </SettingsSection>
        </div>
    );
};
