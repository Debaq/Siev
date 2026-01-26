import React from 'react';
import { VNGReportData } from '../../../types/vng';

interface SummarySectionProps {
    reportData: VNGReportData;
}

export const SummarySection: React.FC<SummarySectionProps> = ({ reportData }) => {
    const { saccades, pursuit, positional, caloric } = reportData;

    // Collect findings
    const findings: string[] = [];
    const abnormalFindings: string[] = [];

    // Saccades
    if (saccades) {
        if (saccades.is_normal) {
            findings.push('Sacadas dentro de límites normales');
        } else {
            abnormalFindings.push('Alteraciones en sacadas');
            if (saccades.abnormality_notes) {
                abnormalFindings.push(saccades.abnormality_notes);
            }
        }
    }

    // Pursuit
    if (pursuit) {
        if (pursuit.is_normal) {
            findings.push(`Rastreo normal (Patrón ${pursuit.pattern})`);
        } else {
            abnormalFindings.push(`Rastreo alterado (Patrón ${pursuit.pattern})`);
        }
    }

    // Positional
    if (positional) {
        if (positional.spontaneous_dark || positional.spontaneous_fixation) {
            const spv = positional.spontaneous_dark?.spv || positional.spontaneous_fixation?.spv || 0;
            if (spv > 3) {
                abnormalFindings.push(`Nistagmo espontáneo presente (${spv.toFixed(1)}°/s)`);
            }
        }

        if (positional.dix_hallpike) {
            if (positional.dix_hallpike.left.bppv_suspected || positional.dix_hallpike.right.bppv_suspected) {
                const side = positional.dix_hallpike.left.bppv_suspected ? 'izquierdo' : 'derecho';
                const canal = positional.dix_hallpike.left.bppv_suspected
                    ? positional.dix_hallpike.left.affected_canal
                    : positional.dix_hallpike.right.affected_canal;
                abnormalFindings.push(`VPPB sospechado (lado ${side}, canal ${canal})`);
            } else {
                findings.push('Dix-Hallpike negativo bilateral');
            }
        }

        if (positional.fixation_index !== undefined) {
            if (positional.fixation_index < 60) {
                abnormalFindings.push(`Índice de fijación disminuido (${positional.fixation_index.toFixed(1)}%)`);
            }
        }
    }

    // Caloric
    if (caloric) {
        const { jongkees, interpretation } = caloric;

        if (interpretation.vestibular_function === 'normal') {
            findings.push('Función vestibular calórica bilateral normal');
        } else {
            if (jongkees.uw_significant) {
                const side = jongkees.unilateral_weakness_percent > 0 ? 'derecha' : 'izquierda';
                abnormalFindings.push(`Paresia canalicular ${side} (UW ${Math.abs(jongkees.unilateral_weakness_percent).toFixed(1)}%)`);
            }
            if (jongkees.dp_significant) {
                const dir = jongkees.directional_preponderance_percent > 0 ? 'derecha' : 'izquierda';
                abnormalFindings.push(`Preponderancia direccional ${dir} (DP ${Math.abs(jongkees.directional_preponderance_percent).toFixed(1)}%)`);
            }
            if (interpretation.vestibular_function === 'bilateral_weakness') {
                abnormalFindings.push('Hipofunción vestibular bilateral');
            }
        }
    }

    // Determine overall conclusion
    const hasAbnormalities = abnormalFindings.length > 0;

    return (
        <div className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 border-b border-gray-300 pb-2 mb-3">
                Resumen Clínico
            </h2>

            {/* Normal Findings */}
            {findings.length > 0 && (
                <div className="mb-4">
                    <h3 className="text-sm font-medium text-green-700 mb-2">Hallazgos Normales</h3>
                    <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {findings.map((finding, idx) => (
                            <li key={idx}>{finding}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Abnormal Findings */}
            {abnormalFindings.length > 0 && (
                <div className="mb-4">
                    <h3 className="text-sm font-medium text-red-700 mb-2">Hallazgos Anormales</h3>
                    <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {abnormalFindings.map((finding, idx) => (
                            <li key={idx} className="text-red-800">{finding}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Conclusion */}
            <div className={`p-4 rounded-lg ${hasAbnormalities ? 'bg-amber-50 border border-amber-200' : 'bg-green-50 border border-green-200'}`}>
                <h3 className="text-sm font-semibold text-gray-800 mb-2">Conclusión</h3>
                <p className="text-sm text-gray-700">
                    {hasAbnormalities ? (
                        <>
                            El estudio VNG revela <span className="font-medium">alteraciones</span> que sugieren
                            {caloric?.interpretation.vestibular_function === 'unilateral_weakness' && (
                                ` patología vestibular periférica ${caloric.interpretation.affected_side === 'left' ? 'izquierda' : 'derecha'}`
                            )}
                            {caloric?.interpretation.vestibular_function === 'bilateral_weakness' && (
                                ' afectación vestibular bilateral'
                            )}
                            {positional?.dix_hallpike?.left.bppv_suspected || positional?.dix_hallpike?.right.bppv_suspected ? (
                                ' vértigo posicional paroxístico benigno (VPPB)'
                            ) : ''}
                            . Se recomienda correlación clínica y seguimiento.
                        </>
                    ) : (
                        <>
                            El estudio VNG se encuentra <span className="font-medium">dentro de límites normales</span>.
                            No se evidencian signos de patología vestibular periférica ni central en el momento del estudio.
                        </>
                    )}
                </p>
            </div>

            {/* Recommendations */}
            {hasAbnormalities && (
                <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <h3 className="text-sm font-medium text-blue-800 mb-2">Recomendaciones</h3>
                    <ul className="list-disc list-inside text-sm text-blue-700 space-y-1">
                        {caloric?.interpretation.vestibular_function !== 'normal' && (
                            <li>Considerar estudio audiológico completo</li>
                        )}
                        {positional?.dix_hallpike?.left.bppv_suspected || positional?.dix_hallpike?.right.bppv_suspected ? (
                            <li>Maniobras de reposicionamiento canalicular (Epley/Semont)</li>
                        ) : null}
                        <li>Control evolutivo según evolución clínica</li>
                    </ul>
                </div>
            )}
        </div>
    );
};
