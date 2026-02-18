import React from 'react';
import { FileText, Layout, Image } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig, ReportSection } from '../../../types/config';
import { ReportSectionEditor } from '../vng/ReportSectionEditor';

interface ReportTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

const TEMPLATE_PRESETS: Record<string, ReportSection[]> = {
    standard: [
        { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
        { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
        { id: 'tonal', label: 'Audiometría Tonal', enabled: true, order: 2 },
        { id: 'vocal', label: 'Audiometría Vocal', enabled: true, order: 3 },
        { id: 'supraliminar', label: 'Pruebas Supraliminares', enabled: false, order: 4 },
        { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 5 },
        { id: 'signature', label: 'Firma', enabled: true, order: 6 },
    ],
    detailed: [
        { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
        { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
        { id: 'tonal', label: 'Audiometría Tonal', enabled: true, order: 2 },
        { id: 'vocal', label: 'Audiometría Vocal', enabled: true, order: 3 },
        { id: 'supraliminar', label: 'Pruebas Supraliminares', enabled: true, order: 4 },
        { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 5 },
        { id: 'signature', label: 'Firma', enabled: true, order: 6 },
    ],
    minimal: [
        { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
        { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
        { id: 'tonal', label: 'Audiometría Tonal', enabled: true, order: 2 },
        { id: 'vocal', label: 'Audiometría Vocal', enabled: false, order: 3 },
        { id: 'supraliminar', label: 'Pruebas Supraliminares', enabled: false, order: 4 },
        { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 5 },
        { id: 'signature', label: 'Firma', enabled: true, order: 6 },
    ],
};

export const ReportTab: React.FC<ReportTabProps> = ({ config, updateConfig }) => {
    const report = config.audiometria.report;

    const handleTemplateChange = (template: string) => {
        updateConfig('audiometria.report.template', template);
        if (template !== 'custom' && TEMPLATE_PRESETS[template]) {
            updateConfig('audiometria.report.sections', TEMPLATE_PRESETS[template]);
        }
    };

    const handleSectionsChange = (newSections: ReportSection[]) => {
        const currentPreset = TEMPLATE_PRESETS[report.template];
        if (currentPreset) {
            const isSame = JSON.stringify(currentPreset) === JSON.stringify(newSections);
            if (!isSame) {
                updateConfig('audiometria.report.template', 'custom');
            }
        }
        updateConfig('audiometria.report.sections', newSections);
    };

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Plantilla de Informe"
                description="Seleccione una plantilla predefinida o personalice las secciones del informe de audiometría."
                icon={<Layout className="w-4 h-4 text-teal-500" />}
            >
                <SettingsField label="Plantilla Base">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={report.template}
                        onChange={e => handleTemplateChange(e.target.value)}
                    >
                        <option value="standard">Estándar</option>
                        <option value="detailed">Detallado</option>
                        <option value="minimal">Mínimo</option>
                        <option value="custom">Personalizado</option>
                    </select>
                </SettingsField>

                <div className="text-xs text-dark-400 mt-2">
                    {report.template === 'standard' && 'Incluye audiometría tonal y vocal.'}
                    {report.template === 'detailed' && 'Incluye todas las pruebas audiométricas disponibles.'}
                    {report.template === 'minimal' && 'Solo audiometría tonal y resumen.'}
                    {report.template === 'custom' && 'Configure manualmente las secciones a incluir.'}
                </div>
            </SettingsSection>

            <SettingsSection
                title="Secciones del Informe"
                description="Arrastre para reordenar y active/desactive las secciones que desea incluir."
                icon={<FileText className="w-4 h-4 text-teal-500" />}
            >
                <ReportSectionEditor
                    sections={report.sections}
                    onChange={handleSectionsChange}
                />
            </SettingsSection>

            <SettingsSection
                title="Opciones Visuales"
                description="Configure elementos gráficos y de presentación del informe."
                icon={<Image className="w-4 h-4 text-purple-500" />}
            >
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm text-dark-200">Incluir Logo</div>
                            <div className="text-xs text-dark-500">Mostrar el logo de la institución en el encabezado</div>
                        </div>
                        <SettingsToggle
                            checked={report.include_logo}
                            onChange={v => updateConfig('audiometria.report.include_logo', v)}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm text-dark-200">Incluir Audiograma</div>
                            <div className="text-xs text-dark-500">Mostrar el gráfico de audiograma en el informe</div>
                        </div>
                        <SettingsToggle
                            checked={report.include_audiogram}
                            onChange={v => updateConfig('audiometria.report.include_audiogram', v)}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm text-dark-200">Incluir Curva Vocal</div>
                            <div className="text-xs text-dark-500">Mostrar la curva de logoaudiometría</div>
                        </div>
                        <SettingsToggle
                            checked={report.include_speech_curve}
                            onChange={v => updateConfig('audiometria.report.include_speech_curve', v)}
                        />
                    </div>
                </div>
            </SettingsSection>

            <SettingsSection
                title="Formato de Exportación"
                description="Seleccione el formato de archivo para los informes generados."
                icon={<FileText className="w-4 h-4 text-red-500" />}
            >
                <SettingsField label="Formato">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={report.export_format}
                        onChange={e => updateConfig('audiometria.report.export_format', e.target.value)}
                    >
                        <option value="pdf">PDF</option>
                        <option value="docx">Word (DOCX)</option>
                    </select>
                </SettingsField>
            </SettingsSection>
        </div>
    );
};
