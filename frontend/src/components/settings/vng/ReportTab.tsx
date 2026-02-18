import React from 'react';
import { FileText, Layout, Image, GitCompare, PieChart, BarChart3 } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { SettingsToggle } from '../shared/SettingsToggle';
import { AppConfig, ReportSection } from '../../../types/config';
import { ReportSectionEditor } from './ReportSectionEditor';

interface ReportTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

const TEMPLATE_PRESETS: Record<string, ReportSection[]> = {
    standard: [
        { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
        { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
        { id: 'saccades', label: 'Sacadas', enabled: true, order: 2 },
        { id: 'pursuit', label: 'Rastreo', enabled: true, order: 3 },
        { id: 'okn', label: 'OKN', enabled: false, order: 4 },
        { id: 'positional', label: 'Posicional', enabled: true, order: 5 },
        { id: 'caloric', label: 'Calóricas', enabled: true, order: 6 },
        { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 7 },
        { id: 'signature', label: 'Firma', enabled: true, order: 8 },
    ],
    detailed: [
        { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
        { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
        { id: 'saccades', label: 'Sacadas', enabled: true, order: 2 },
        { id: 'pursuit', label: 'Rastreo', enabled: true, order: 3 },
        { id: 'okn', label: 'OKN', enabled: true, order: 4 },
        { id: 'positional', label: 'Posicional', enabled: true, order: 5 },
        { id: 'caloric', label: 'Calóricas', enabled: true, order: 6 },
        { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 7 },
        { id: 'signature', label: 'Firma', enabled: true, order: 8 },
    ],
    minimal: [
        { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
        { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
        { id: 'saccades', label: 'Sacadas', enabled: false, order: 2 },
        { id: 'pursuit', label: 'Rastreo', enabled: false, order: 3 },
        { id: 'okn', label: 'OKN', enabled: false, order: 4 },
        { id: 'positional', label: 'Posicional', enabled: false, order: 5 },
        { id: 'caloric', label: 'Calóricas', enabled: true, order: 6 },
        { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 7 },
        { id: 'signature', label: 'Firma', enabled: true, order: 8 },
    ],
};

export const ReportTab: React.FC<ReportTabProps> = ({ config, updateConfig }) => {
    const report = config.vng.report;

    const handleTemplateChange = (template: string) => {
        updateConfig('vng.report.template', template);
        if (template !== 'custom' && TEMPLATE_PRESETS[template]) {
            updateConfig('vng.report.sections', TEMPLATE_PRESETS[template]);
        }
    };

    const handleSectionsChange = (newSections: ReportSection[]) => {
        // When manually changing sections, switch to custom template
        const currentPreset = TEMPLATE_PRESETS[report.template];
        if (currentPreset) {
            const isSame = JSON.stringify(currentPreset) === JSON.stringify(newSections);
            if (!isSame) {
                updateConfig('vng.report.template', 'custom');
            }
        }
        updateConfig('vng.report.sections', newSections);
    };

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Template Selection */}
            <SettingsSection
                title="Plantilla de Informe"
                description="Seleccione una plantilla predefinida o personalice las secciones del informe."
                icon={<Layout className="w-4 h-4 text-siev-500" />}
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
                    {report.template === 'standard' && 'Incluye todas las pruebas principales excepto OKN.'}
                    {report.template === 'detailed' && 'Incluye todas las pruebas disponibles con datos completos.'}
                    {report.template === 'minimal' && 'Solo calóricas y resumen clínico.'}
                    {report.template === 'custom' && 'Configure manualmente las secciones a incluir.'}
                </div>
            </SettingsSection>

            {/* Section Editor */}
            <SettingsSection
                title="Secciones del Informe"
                description="Arrastre para reordenar y active/desactive las secciones que desea incluir."
                icon={<FileText className="w-4 h-4 text-cyan-500" />}
            >
                <ReportSectionEditor
                    sections={report.sections}
                    onChange={handleSectionsChange}
                />
            </SettingsSection>

            {/* Visual Options */}
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
                            onChange={v => updateConfig('vng.report.include_logo', v)}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm text-dark-200">Incluir Gráficos</div>
                            <div className="text-xs text-dark-500">Mostrar gráficos y diagramas en el informe</div>
                        </div>
                        <SettingsToggle
                            checked={report.include_graphs}
                            onChange={v => updateConfig('vng.report.include_graphs', v)}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-sm text-dark-200">Incluir Datos Crudos</div>
                            <div className="text-xs text-dark-500">Anexar datos numéricos detallados al final</div>
                        </div>
                        <SettingsToggle
                            checked={report.include_raw_data}
                            onChange={v => updateConfig('vng.report.include_raw_data', v)}
                        />
                    </div>
                </div>
            </SettingsSection>

            {/* Caloric Diagram Style */}
            <SettingsSection
                title="Diagrama Calórico"
                description="Seleccione el estilo de visualización para las pruebas calóricas."
                icon={<PieChart className="w-4 h-4 text-orange-500" />}
            >
                <SettingsField label="Estilo de Diagrama">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={report.diagram_style}
                        onChange={e => updateConfig('vng.report.diagram_style', e.target.value)}
                    >
                        <option value="claussen">Claussen (Tradicional)</option>
                        <option value="freyss">Freyss (Vectorial)</option>
                        <option value="butterfly">Mariposa (Timeline)</option>
                    </select>
                </SettingsField>

                {/* Diagram Preview */}
                <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700 mt-3">
                    <DiagramPreview style={report.diagram_style} />
                </div>
            </SettingsSection>

            {/* Analysis Method */}
            <SettingsSection
                title="Método de Análisis"
                description="Seleccione qué tipo de análisis incluir en el informe de sacadas/nistagmo."
                icon={<BarChart3 className="w-4 h-4 text-teal-500" />}
            >
                <SettingsField label="Método">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={report.analysis_method || 'both'}
                        onChange={e => updateConfig('vng.report.analysis_method', e.target.value)}
                    >
                        <option value="saccades">Solo Sacadas</option>
                        <option value="spv">Solo VCL (Velocidad de Componente Lento)</option>
                        <option value="both">Ambos (Sacadas + VCL)</option>
                    </select>
                </SettingsField>
                <div className="text-xs text-dark-400 mt-2">
                    {report.analysis_method === 'saccades' && 'El informe mostrará solo resultados basados en sacadas detectadas.'}
                    {report.analysis_method === 'spv' && 'El informe mostrará solo resultados basados en velocidad de componente lento (SPV/nistagmo).'}
                    {(!report.analysis_method || report.analysis_method === 'both') && 'El informe incluirá ambos análisis: sacadas detectadas y velocidad de componente lento.'}
                </div>
            </SettingsSection>

            {/* Comparison Options */}
            <SettingsSection
                title="Comparación Histórica"
                description="Configure opciones para comparar con sesiones anteriores."
                icon={<GitCompare className="w-4 h-4 text-green-500" />}
            >
                <div className="flex items-center justify-between">
                    <div>
                        <div className="text-sm text-dark-200">Comparar con Sesión Anterior</div>
                        <div className="text-xs text-dark-500">Incluir comparación con la última sesión del paciente</div>
                    </div>
                    <SettingsToggle
                        checked={report.compare_with_previous}
                        onChange={v => updateConfig('vng.report.compare_with_previous', v)}
                    />
                </div>
            </SettingsSection>

            {/* Export Format */}
            <SettingsSection
                title="Formato de Exportación"
                description="Seleccione el formato de archivo para los informes generados."
                icon={<FileText className="w-4 h-4 text-red-500" />}
            >
                <SettingsField label="Formato">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={report.export_format}
                        onChange={e => updateConfig('vng.report.export_format', e.target.value)}
                    >
                        <option value="pdf">PDF</option>
                        <option value="docx">Word (DOCX)</option>
                    </select>
                </SettingsField>
            </SettingsSection>
        </div>
    );
};

// Simple diagram style preview
const DiagramPreview: React.FC<{ style: string }> = ({ style }) => {
    if (style === 'claussen') {
        return (
            <svg viewBox="0 0 100 100" className="w-full h-24">
                <line x1="50" y1="5" x2="50" y2="95" stroke="#475569" strokeWidth="0.5" />
                <line x1="5" y1="50" x2="95" y2="50" stroke="#475569" strokeWidth="0.5" />
                <text x="25" y="25" fill="#64748b" fontSize="6">RC</text>
                <text x="70" y="25" fill="#64748b" fontSize="6">LC</text>
                <text x="25" y="80" fill="#64748b" fontSize="6">RW</text>
                <text x="70" y="80" fill="#64748b" fontSize="6">LW</text>
                <rect x="20" y="30" width="15" height="15" fill="#3b82f6" opacity="0.7" />
                <rect x="65" y="30" width="12" height="12" fill="#3b82f6" opacity="0.7" />
                <rect x="20" y="55" width="18" height="18" fill="#ef4444" opacity="0.7" />
                <rect x="65" y="55" width="14" height="14" fill="#ef4444" opacity="0.7" />
            </svg>
        );
    }

    if (style === 'freyss') {
        return (
            <svg viewBox="0 0 100 100" className="w-full h-24">
                <circle cx="50" cy="50" r="35" fill="none" stroke="#475569" strokeWidth="0.5" />
                <circle cx="50" cy="50" r="20" fill="none" stroke="#475569" strokeWidth="0.5" strokeDasharray="2,2" />
                <line x1="50" y1="50" x2="75" y2="35" stroke="#3b82f6" strokeWidth="2" />
                <line x1="50" y1="50" x2="30" y2="70" stroke="#ef4444" strokeWidth="2" />
                <circle cx="75" cy="35" r="2" fill="#3b82f6" />
                <circle cx="30" cy="70" r="2" fill="#ef4444" />
            </svg>
        );
    }

    // Butterfly
    return (
        <svg viewBox="0 0 100 60" className="w-full h-24">
            <line x1="10" y1="30" x2="90" y2="30" stroke="#475569" strokeWidth="0.5" />
            <line x1="10" y1="10" x2="10" y2="50" stroke="#475569" strokeWidth="0.5" />
            <polyline
                points="10,30 20,20 30,35 40,15 50,25 60,30"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="1.5"
            />
            <polyline
                points="10,30 20,40 30,25 40,45 50,35 60,30"
                fill="none"
                stroke="#ef4444"
                strokeWidth="1.5"
            />
            <text x="5" y="58" fill="#64748b" fontSize="5">0s</text>
            <text x="55" y="58" fill="#64748b" fontSize="5">180s</text>
        </svg>
    );
};
