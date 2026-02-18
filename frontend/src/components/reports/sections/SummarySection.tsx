import React, { useEffect, useRef } from 'react';
import { RefreshCw } from 'lucide-react';
import { VNGReportData } from '../../../types/vng';
import { generateAutoSummary } from '../utils/generateSummary';
import { EditableField } from '../shared/EditableField';

interface SummarySectionProps {
    reportData: VNGReportData;
    findings?: string;
    conclusion?: string;
    recommendations?: string;
    onFindingsChange?: (value: string) => void;
    onConclusionChange?: (value: string) => void;
    onRecommendationsChange?: (value: string) => void;
}

export const SummarySection: React.FC<SummarySectionProps> = ({
    reportData,
    findings: findingsOverride,
    conclusion: conclusionOverride,
    recommendations: recommendationsOverride,
    onFindingsChange,
    onConclusionChange,
    onRecommendationsChange,
}) => {
    const auto = useRef(generateAutoSummary(reportData));
    const initialized = useRef(false);

    // Pre-fill empty editable fields with auto-generated text
    useEffect(() => {
        if (initialized.current) return;
        initialized.current = true;
        const a = auto.current;

        if (onFindingsChange && !findingsOverride) {
            const allFindings = [
                ...a.findings.map(f => `[Normal] ${f}`),
                ...a.abnormalFindings.map(f => `[Anormal] ${f}`),
            ];
            if (allFindings.length > 0) {
                onFindingsChange(allFindings.join('\n'));
            }
        }
        if (onConclusionChange && !conclusionOverride) {
            onConclusionChange(a.conclusion);
        }
        if (onRecommendationsChange && !recommendationsOverride) {
            if (a.recommendations.length > 0) {
                onRecommendationsChange(a.recommendations.join('\n'));
            }
        }
    }, [reportData]);

    const handleRegenFindings = () => {
        const a = generateAutoSummary(reportData);
        auto.current = a;
        const allFindings = [
            ...a.findings.map(f => `[Normal] ${f}`),
            ...a.abnormalFindings.map(f => `[Anormal] ${f}`),
        ];
        onFindingsChange?.(allFindings.join('\n'));
    };

    const handleRegenConclusion = () => {
        const a = generateAutoSummary(reportData);
        auto.current = a;
        onConclusionChange?.(a.conclusion);
    };

    const handleRegenRecommendations = () => {
        const a = generateAutoSummary(reportData);
        auto.current = a;
        onRecommendationsChange?.(a.recommendations.join('\n'));
    };

    // Determine display values: editable override > auto-generated
    const a = auto.current;
    const displayFindings = findingsOverride || [
        ...a.findings.map(f => `[Normal] ${f}`),
        ...a.abnormalFindings.map(f => `[Anormal] ${f}`),
    ].join('\n');

    const displayConclusion = conclusionOverride || a.conclusion;
    const displayRecommendations = recommendationsOverride || a.recommendations.join('\n');

    const hasAbnormalities = a.abnormalFindings.length > 0;
    const isEditable = !!onFindingsChange;

    const RegenButton: React.FC<{ onClick: () => void }> = ({ onClick }) => {
        if (!isEditable) return null;
        return (
            <button
                onClick={onClick}
                className="ml-2 p-1 text-gray-400 hover:text-blue-500 transition-colors"
                title="Regenerar sugerencia"
            >
                <RefreshCw className="w-3.5 h-3.5" />
            </button>
        );
    };

    return (
        <div className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 border-b border-gray-300 pb-2 mb-3">
                Resumen Clínico
            </h2>

            {/* Findings */}
            <div className="mb-4">
                <div className="flex items-center">
                    <h3 className="text-sm font-medium text-gray-700">Hallazgos</h3>
                    <RegenButton onClick={handleRegenFindings} />
                </div>
                {isEditable ? (
                    <EditableField
                        value={displayFindings}
                        onChange={onFindingsChange!}
                        placeholder="Describir hallazgos..."
                    />
                ) : (
                    <div className="mt-1">
                        {a.findings.length > 0 && (
                            <div className="mb-2">
                                <span className="text-xs font-medium text-green-700">Normales:</span>
                                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1 mt-1">
                                    {a.findings.map((f, i) => <li key={i}>{f}</li>)}
                                </ul>
                            </div>
                        )}
                        {a.abnormalFindings.length > 0 && (
                            <div>
                                <span className="text-xs font-medium text-red-700">Anormales:</span>
                                <ul className="list-disc list-inside text-sm text-red-800 space-y-1 mt-1">
                                    {a.abnormalFindings.map((f, i) => <li key={i}>{f}</li>)}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Conclusion */}
            <div className={`mb-4 p-4 rounded-lg ${hasAbnormalities ? 'bg-amber-50 border border-amber-200' : 'bg-green-50 border border-green-200'}`}>
                <div className="flex items-center">
                    <h3 className="text-sm font-semibold text-gray-800">Conclusión</h3>
                    <RegenButton onClick={handleRegenConclusion} />
                </div>
                {isEditable ? (
                    <EditableField
                        value={displayConclusion}
                        onChange={onConclusionChange!}
                        placeholder="Escribir conclusión..."
                    />
                ) : (
                    <p className="text-sm text-gray-700 mt-1">{displayConclusion}</p>
                )}
            </div>

            {/* Recommendations */}
            {(hasAbnormalities || displayRecommendations) && (
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center">
                        <h3 className="text-sm font-medium text-blue-800">Recomendaciones</h3>
                        <RegenButton onClick={handleRegenRecommendations} />
                    </div>
                    {isEditable ? (
                        <EditableField
                            value={displayRecommendations}
                            onChange={onRecommendationsChange!}
                            placeholder="Escribir recomendaciones..."
                        />
                    ) : (
                        <ul className="list-disc list-inside text-sm text-blue-700 space-y-1 mt-1">
                            {a.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                        </ul>
                    )}
                </div>
            )}
        </div>
    );
};
