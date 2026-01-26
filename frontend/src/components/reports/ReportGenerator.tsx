import React, { useRef, useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { FileDown, Loader2, AlertCircle } from 'lucide-react';
import { VNGReportData, ReportSection as ReportSectionType } from '../../types/vng';
import { VNGReportConfig } from '../../types/config';
import { usePDFGeneration } from './usePDFGeneration';
import { HeaderSection } from './sections/HeaderSection';
import { PatientInfoSection } from './sections/PatientInfoSection';
import { SaccadeSection } from './sections/SaccadeSection';
import { PursuitSection } from './sections/PursuitSection';
import { PositionalSection } from './sections/PositionalSection';
import { CaloricSection } from './sections/CaloricSection';
import { SignatureSection } from './sections/SignatureSection';
import { SummarySection } from './sections/SummarySection';

interface ReportGeneratorProps {
    sessionId: number;
    config: VNGReportConfig;
    institutionName: string;
    institutionLogo?: string;
    onClose?: () => void;
}

export const ReportGenerator: React.FC<ReportGeneratorProps> = ({
    sessionId,
    config,
    institutionName,
    institutionLogo,
    onClose
}) => {
    const [reportData, setReportData] = useState<VNGReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const reportRef = useRef<HTMLDivElement>(null);
    const { generateFromSections, isGenerating, progress } = usePDFGeneration();

    useEffect(() => {
        loadReportData();
    }, [sessionId]);

    const loadReportData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await invoke<VNGReportData>('get_vng_report_data', {
                sessionId,
                includeHistorical: config.compare_with_previous
            });
            setReportData(data);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Error loading report data');
        } finally {
            setLoading(false);
        }
    };

    const handleGeneratePDF = async () => {
        if (!reportRef.current) return;

        const result = await generateFromSections(reportRef as React.RefObject<HTMLElement>, {
            filename: `informe-vng-${reportData?.patient.full_name.replace(/\s+/g, '-')}-${reportData?.session.date.split(' ')[0]}.pdf`,
            quality: 0.95,
            scale: 2
        });

        if (!result.success) {
            setError(result.error || 'Error generating PDF');
        }
    };

    const enabledSections = config.sections
        .filter(s => s.enabled)
        .sort((a, b) => a.order - b.order);

    const renderSection = (section: ReportSectionType) => {
        if (!reportData) return null;

        switch (section.id) {
            case 'header':
                return (
                    <HeaderSection
                        key={section.id}
                        institutionName={institutionName}
                        logoPath={config.include_logo ? institutionLogo : undefined}
                        date={reportData.session.date}
                    />
                );
            case 'patient':
                return (
                    <PatientInfoSection
                        key={section.id}
                        patient={reportData.patient}
                        session={reportData.session}
                    />
                );
            case 'saccades':
                return reportData.saccades ? (
                    <SaccadeSection
                        key={section.id}
                        data={reportData.saccades}
                        showGraphs={config.include_graphs}
                    />
                ) : null;
            case 'pursuit':
                return reportData.pursuit ? (
                    <PursuitSection
                        key={section.id}
                        data={reportData.pursuit}
                        showGraphs={config.include_graphs}
                    />
                ) : null;
            case 'positional':
                return reportData.positional ? (
                    <PositionalSection
                        key={section.id}
                        data={reportData.positional}
                    />
                ) : null;
            case 'caloric':
                return reportData.caloric ? (
                    <CaloricSection
                        key={section.id}
                        data={reportData.caloric}
                        diagramStyle={config.diagram_style}
                        showGraphs={config.include_graphs}
                        previousData={reportData.previous_session?.caloric}
                    />
                ) : null;
            case 'summary':
                return (
                    <SummarySection
                        key={section.id}
                        reportData={reportData}
                    />
                );
            case 'signature':
                return (
                    <SignatureSection
                        key={section.id}
                        specialistName={reportData.session.specialist_name}
                    />
                );
            default:
                return null;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="w-8 h-8 animate-spin text-siev-500" />
                <span className="ml-3 text-dark-300">Cargando datos del informe...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-96 text-red-400">
                <AlertCircle className="w-12 h-12 mb-4" />
                <p className="text-lg mb-2">Error al cargar el informe</p>
                <p className="text-sm text-dark-400">{error}</p>
                <button
                    onClick={loadReportData}
                    className="mt-4 px-4 py-2 bg-siev-600 hover:bg-siev-700 rounded-lg"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    if (!reportData) {
        return (
            <div className="flex items-center justify-center h-96 text-dark-400">
                No hay datos disponibles para este informe.
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-4 border-b border-dark-700 bg-dark-800">
                <div className="flex items-center gap-4">
                    <h2 className="text-lg font-medium text-dark-100">Vista Previa del Informe</h2>
                    <span className="text-sm text-dark-400">
                        {reportData.patient.full_name} - {reportData.session.date.split(' ')[0]}
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleGeneratePDF}
                        disabled={isGenerating}
                        className="flex items-center gap-2 px-4 py-2 bg-siev-600 hover:bg-siev-700 disabled:opacity-50 rounded-lg transition-colors"
                    >
                        {isGenerating ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Generando... {progress}%</span>
                            </>
                        ) : (
                            <>
                                <FileDown className="w-4 h-4" />
                                <span>Descargar PDF</span>
                            </>
                        )}
                    </button>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                        >
                            Cerrar
                        </button>
                    )}
                </div>
            </div>

            {/* Preview Container */}
            <div className="flex-1 overflow-auto bg-dark-900 p-8">
                <div
                    ref={reportRef}
                    className="max-w-[210mm] mx-auto bg-white text-black p-8 shadow-2xl"
                    style={{ minHeight: '297mm' }}
                >
                    {enabledSections.map(section => renderSection(section))}
                </div>
            </div>
        </div>
    );
};
