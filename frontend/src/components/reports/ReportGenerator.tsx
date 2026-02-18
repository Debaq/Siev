import React, { useRef, useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { FileDown, Printer, Loader2, AlertCircle, X, Plus, ChevronUp, ChevronDown } from 'lucide-react';
import { VNGReportData, ReportSection as ReportSectionType } from '../../types/vng';
import { VNGReportConfig } from '../../types/config';
import { usePDFGeneration } from './usePDFGeneration';
import { useReportEdits } from '../../hooks/useReportEdits';
import { HeaderSection } from './sections/HeaderSection';
import { PatientInfoSection } from './sections/PatientInfoSection';
import { SaccadeSection } from './sections/SaccadeSection';
import { PursuitSection } from './sections/PursuitSection';
import { PositionalSection } from './sections/PositionalSection';
import { CaloricSection } from './sections/CaloricSection';
import { SignatureSection } from './sections/SignatureSection';
import { SummarySection } from './sections/SummarySection';
import { SaccadeScatterDiagram } from './charts/SaccadeScatterDiagram';
import { SPVTimelineDiagram } from './charts/SPVTimelineDiagram';
import { PursuitGainDiagram } from './charts/PursuitGainDiagram';
import { NystagmusSummaryDiagram } from './charts/NystagmusSummaryDiagram';
import { CaloricDiagram } from './charts/CaloricDiagram';

// --- Types ---
type BlockItem =
    | { type: 'section'; id: string }
    | { type: 'chart'; id: string; chartId: string };

// --- Catálogo de gráficos insertables ---
const INSERTABLE_CHARTS: { id: string; label: string }[] = [
    { id: 'chart:saccade_scatter', label: 'Scatter de Sacadas' },
    { id: 'chart:spv_timeline', label: 'Timeline SPV' },
    { id: 'chart:pursuit_gain', label: 'Ganancia de Rastreo' },
    { id: 'chart:nystagmus_summary', label: 'Resumen de Nistagmo' },
    { id: 'chart:caloric_diagram', label: 'Diagrama Calórico' },
];

// --- BlockWrapper: envuelve cada bloque con X, ↑, ↓ al hover ---
const BlockWrapper: React.FC<{
    isFirst: boolean;
    isLast: boolean;
    onRemove: () => void;
    onMoveUp: () => void;
    onMoveDown: () => void;
    children: React.ReactNode;
}> = ({ isFirst, isLast, onRemove, onMoveUp, onMoveDown, children }) => {
    const [hovered, setHovered] = useState(false);

    return (
        <div
            className="relative"
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
        >
            {hovered && (
                <div className="report-controls absolute top-1 right-1 z-10 flex items-center gap-1">
                    {!isFirst && (
                        <button
                            className="w-6 h-6 flex items-center justify-center rounded-full bg-gray-200/80 hover:bg-blue-100 text-gray-500 hover:text-blue-600 transition-colors"
                            onClick={onMoveUp}
                            title="Mover arriba"
                        >
                            <ChevronUp className="w-3.5 h-3.5" />
                        </button>
                    )}
                    {!isLast && (
                        <button
                            className="w-6 h-6 flex items-center justify-center rounded-full bg-gray-200/80 hover:bg-blue-100 text-gray-500 hover:text-blue-600 transition-colors"
                            onClick={onMoveDown}
                            title="Mover abajo"
                        >
                            <ChevronDown className="w-3.5 h-3.5" />
                        </button>
                    )}
                    <button
                        className="w-6 h-6 flex items-center justify-center rounded-full bg-red-500/80 hover:bg-red-600 text-white transition-colors"
                        onClick={onRemove}
                        title="Eliminar"
                    >
                        <X className="w-3.5 h-3.5" />
                    </button>
                </div>
            )}
            {children}
        </div>
    );
};

// --- InsertButton: línea sutil entre bloques con botón + ---
const InsertButton: React.FC<{
    afterId: string;
    charts: { id: string; label: string }[];
    removedSections: { id: string; label: string }[];
    onInsertChart: (afterId: string, chartId: string) => void;
    onRestoreSection: (afterId: string, sectionId: string) => void;
}> = ({ afterId, charts, removedSections, onInsertChart, onRestoreSection }) => {
    const [hovered, setHovered] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!menuOpen) return;
        const handleClick = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [menuOpen]);

    const hasRemovedSections = removedSections.length > 0;

    return (
        <div
            ref={containerRef}
            className="report-controls relative flex items-center justify-center"
            style={{ height: '20px' }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => { if (!menuOpen) setHovered(false); }}
        >
            <div
                className="absolute inset-x-4 top-1/2 border-t border-dashed border-gray-300 transition-opacity"
                style={{ opacity: hovered || menuOpen ? 0.6 : 0 }}
            />
            <button
                className="relative z-10 w-6 h-6 flex items-center justify-center rounded-full border border-gray-300 bg-white text-gray-400 hover:bg-blue-50 hover:border-blue-400 hover:text-blue-500 transition-all"
                style={{ opacity: hovered || menuOpen ? 1 : 0, pointerEvents: hovered || menuOpen ? 'auto' : 'none' }}
                onClick={() => setMenuOpen(prev => !prev)}
                title="Insertar sección o gráfico"
            >
                <Plus className="w-3.5 h-3.5" />
            </button>
            {menuOpen && (
                <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 z-50 bg-white border border-gray-200 rounded-lg shadow-xl py-1 min-w-[220px] text-sm">
                    <div className="px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wide">Gráficos</div>
                    {charts.map(chart => (
                        <button
                            key={chart.id}
                            className="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-gray-700"
                            onClick={() => { onInsertChart(afterId, chart.id); setMenuOpen(false); setHovered(false); }}
                        >
                            {chart.label}
                        </button>
                    ))}
                    {hasRemovedSections && (
                        <>
                            <div className="border-t border-gray-100 my-1" />
                            <div className="px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wide">Secciones eliminadas</div>
                            {removedSections.map(s => (
                                <button
                                    key={s.id}
                                    className="w-full text-left px-3 py-1.5 hover:bg-green-50 text-gray-700"
                                    onClick={() => { onRestoreSection(afterId, s.id); setMenuOpen(false); setHovered(false); }}
                                >
                                    Restaurar: {s.label}
                                </button>
                            ))}
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

interface ReportGeneratorProps {
    sessionId: number; // Actually recordingId now, kept as prop name for compatibility
    config: VNGReportConfig;
    institutionName: string;
    institutionLogo?: string;
    onClose?: () => void;
}

export const ReportGenerator: React.FC<ReportGeneratorProps> = ({
    sessionId: recordingId,
    config,
    institutionName,
    institutionLogo,
    onClose
}) => {
    const [reportData, setReportData] = useState<VNGReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [blocks, setBlocks] = useState<BlockItem[] | null>(null);
    const chartIdCounter = useRef(0);
    const reportRef = useRef<HTMLDivElement>(null);
    const { generateFromSections, printReport, isGenerating, progress } = usePDFGeneration();
    const {
        edits,
        setSectionComment,
        setConclusion,
        setRecommendations,
        setFindings,
    } = useReportEdits(recordingId);

    const analysisMethod = config.analysis_method || 'both';

    const configSections = config.sections
        .filter(s => s.enabled)
        .sort((a, b) => a.order - b.order);

    // blocks=null → usar orden del config; una vez que el usuario modifica, se guarda en state
    const effectiveBlocks: BlockItem[] = blocks ?? configSections.map(s => ({ type: 'section' as const, id: s.id }));

    // Secciones eliminadas = habilitadas en config pero ausentes del array de bloques
    const removedSections = configSections
        .filter(s => !effectiveBlocks.some(b => b.type === 'section' && b.id === s.id))
        .map(s => ({ id: s.id, label: s.label }));

    useEffect(() => {
        loadReportData();
    }, [recordingId]);

    const loadReportData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await invoke<VNGReportData>('get_vng_report_data', {
                recordingId,
                includeHistorical: config.compare_with_previous
            });
            setReportData(data);
        } catch (e) {
            const msg = typeof e === 'string' ? e : e instanceof Error ? e.message : 'Error desconocido al cargar datos del informe';
            console.error('[ReportGenerator] Error:', e);
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleGeneratePDF = async () => {
        if (!reportRef.current) return;

        // Ocultar controles de edición antes de capturar
        const controls = reportRef.current.querySelectorAll<HTMLElement>('.report-controls');
        controls.forEach(el => el.style.display = 'none');

        const result = await generateFromSections(reportRef as React.RefObject<HTMLElement>, {
            filename: `informe-vng-${reportData?.patient.full_name.replace(/\s+/g, '-')}-${reportData?.session.date.split(' ')[0]}.pdf`,
            quality: 0.95,
            scale: 2
        });

        // Restaurar controles
        controls.forEach(el => el.style.display = '');

        if (!result.success && result.error) {
            setError(result.error);
        }
    };

    const handlePrint = () => {
        if (!reportRef.current) return;
        printReport(reportRef.current);
    };

    const handleRemoveBlock = (blockId: string) => {
        setBlocks(prev => (prev ?? effectiveBlocks).filter(b => b.id !== blockId));
    };

    const handleMoveBlock = (blockId: string, direction: 'up' | 'down') => {
        setBlocks(prev => {
            const arr = [...(prev ?? effectiveBlocks)];
            const idx = arr.findIndex(b => b.id === blockId);
            if (idx === -1) return arr;
            const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
            if (targetIdx < 0 || targetIdx >= arr.length) return arr;
            [arr[idx], arr[targetIdx]] = [arr[targetIdx], arr[idx]];
            return arr;
        });
    };

    const handleInsertChart = (afterId: string, chartId: string) => {
        const newBlock: BlockItem = { type: 'chart', id: `chart-${chartIdCounter.current++}`, chartId };
        setBlocks(prev => {
            const arr = [...(prev ?? effectiveBlocks)];
            if (afterId === '__start__') {
                arr.unshift(newBlock);
            } else {
                const idx = arr.findIndex(b => b.id === afterId);
                arr.splice(idx + 1, 0, newBlock);
            }
            return arr;
        });
    };

    const handleRestoreSection = (afterId: string, sectionId: string) => {
        const restoredBlock: BlockItem = { type: 'section', id: sectionId };
        setBlocks(prev => {
            const arr = [...(prev ?? effectiveBlocks)];
            if (afterId === '__start__') {
                arr.unshift(restoredBlock);
            } else {
                const idx = arr.findIndex(b => b.id === afterId);
                arr.splice(idx + 1, 0, restoredBlock);
            }
            return arr;
        });
    };

    const renderSection = (section: ReportSectionType) => {
        if (!reportData) return null;

        switch (section.id) {
            case 'header':
                return (
                    <HeaderSection
                        institutionName={institutionName}
                        logoPath={config.include_logo ? institutionLogo : undefined}
                        date={reportData.session.date}
                    />
                );
            case 'patient':
                return (
                    <PatientInfoSection
                        patient={reportData.patient}
                        session={reportData.session}
                    />
                );
            case 'saccades':
                return reportData.saccades ? (
                    <SaccadeSection
                        data={reportData.saccades}
                        showGraphs={config.include_graphs}
                        analysisMethod={analysisMethod}
                        spvData={reportData.spv_data}
                        rawSaccades={reportData.raw_saccades}
                        comment={edits.sectionComments['saccades'] || ''}
                        onCommentChange={(v) => setSectionComment('saccades', v)}
                    />
                ) : null;
            case 'pursuit':
                return reportData.pursuit ? (
                    <PursuitSection
                        data={reportData.pursuit}
                        showGraphs={config.include_graphs}
                        comment={edits.sectionComments['pursuit'] || ''}
                        onCommentChange={(v) => setSectionComment('pursuit', v)}
                    />
                ) : null;
            case 'positional':
                return reportData.positional ? (
                    <PositionalSection
                        data={reportData.positional}
                        showGraphs={config.include_graphs}
                        comment={edits.sectionComments['positional'] || ''}
                        onCommentChange={(v) => setSectionComment('positional', v)}
                    />
                ) : null;
            case 'caloric':
                return reportData.caloric ? (
                    <CaloricSection
                        data={reportData.caloric}
                        diagramStyle={config.diagram_style}
                        showGraphs={config.include_graphs}
                        previousData={reportData.previous_session?.caloric}
                        comment={edits.sectionComments['caloric'] || ''}
                        onCommentChange={(v) => setSectionComment('caloric', v)}
                    />
                ) : null;
            case 'summary':
                return (
                    <SummarySection
                        reportData={reportData}
                        findings={edits.findings}
                        conclusion={edits.conclusion}
                        recommendations={edits.recommendations}
                        onFindingsChange={setFindings}
                        onConclusionChange={setConclusion}
                        onRecommendationsChange={setRecommendations}
                    />
                );
            case 'signature':
                return (
                    <SignatureSection
                        specialistName={reportData.session.specialist_name}
                    />
                );
            default:
                return null;
        }
    };

    const renderChartBlock = (chartId: string) => {
        const chartLabel = INSERTABLE_CHARTS.find(c => c.id === chartId)?.label || chartId;
        const placeholder = (
            <div className="py-6 text-center text-gray-400 text-sm italic border border-dashed border-gray-200 rounded mx-4">
                {chartLabel} — sin datos para esta prueba
            </div>
        );

        if (!reportData) return placeholder;

        switch (chartId) {
            case 'chart:saccade_scatter':
                return reportData.raw_saccades?.length
                    ? <div className="py-4 flex justify-center"><SaccadeScatterDiagram saccades={reportData.raw_saccades} /></div>
                    : placeholder;
            case 'chart:spv_timeline':
                return reportData.spv_data?.timeline?.length
                    ? <div className="py-4 flex justify-center"><SPVTimelineDiagram timeline={reportData.spv_data.timeline} overallSPV={reportData.spv_data.overall_spv} /></div>
                    : placeholder;
            case 'chart:pursuit_gain':
                return reportData.pursuit
                    ? <div className="py-4 flex justify-center"><PursuitGainDiagram data={reportData.pursuit} /></div>
                    : placeholder;
            case 'chart:nystagmus_summary':
                return reportData.positional
                    ? <div className="py-4 flex justify-center"><NystagmusSummaryDiagram data={reportData.positional} /></div>
                    : placeholder;
            case 'chart:caloric_diagram':
                return reportData.caloric
                    ? <div className="py-4 flex justify-center"><CaloricDiagram data={reportData.caloric} style={config.diagram_style} /></div>
                    : placeholder;
            default:
                return null;
        }
    };

    // Bloques con contenido renderizable (secciones sin datos se omiten)
    const renderableBlocks = effectiveBlocks
        .map(block => {
            let content: React.ReactNode = null;
            if (block.type === 'section') {
                const section = configSections.find(s => s.id === block.id);
                if (section) content = renderSection(section);
            } else {
                content = renderChartBlock(block.chartId);
            }
            return { block, content };
        })
        .filter(item => item.content !== null);

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
                <div className="flex items-center gap-3 mt-4">
                    <button
                        onClick={loadReportData}
                        className="px-4 py-2 bg-siev-600 hover:bg-siev-700 rounded-lg transition-colors"
                    >
                        Reintentar
                    </button>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                        >
                            Volver
                        </button>
                    )}
                </div>
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
                        onClick={handlePrint}
                        disabled={isGenerating}
                        className="flex items-center gap-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 disabled:opacity-50 rounded-lg transition-colors"
                    >
                        <Printer className="w-4 h-4" />
                        <span>Imprimir</span>
                    </button>
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
                                <span>Guardar PDF</span>
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
                    {renderableBlocks.map(({ block, content }, idx) => {
                        const prevId = idx === 0 ? '__start__' : renderableBlocks[idx - 1].block.id;

                        return (
                            <React.Fragment key={block.id}>
                                <InsertButton
                                    afterId={prevId}
                                    charts={INSERTABLE_CHARTS}
                                    removedSections={removedSections}
                                    onInsertChart={handleInsertChart}
                                    onRestoreSection={handleRestoreSection}
                                />
                                <BlockWrapper
                                    isFirst={idx === 0}
                                    isLast={idx === renderableBlocks.length - 1}
                                    onRemove={() => handleRemoveBlock(block.id)}
                                    onMoveUp={() => handleMoveBlock(block.id, 'up')}
                                    onMoveDown={() => handleMoveBlock(block.id, 'down')}
                                >
                                    {content}
                                </BlockWrapper>
                                {idx === renderableBlocks.length - 1 && (
                                    <InsertButton
                                        afterId={block.id}
                                        charts={INSERTABLE_CHARTS}
                                        removedSections={removedSections}
                                        onInsertChart={handleInsertChart}
                                        onRestoreSection={handleRestoreSection}
                                    />
                                )}
                            </React.Fragment>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};
