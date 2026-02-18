import { VNGReportData } from '../../../types/vng';

export interface AutoSummary {
    findings: string[];
    abnormalFindings: string[];
    conclusion: string;
    recommendations: string[];
}

export function generateAutoSummary(reportData: VNGReportData): AutoSummary {
    const { saccades, pursuit, positional, caloric } = reportData;

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

    // Conclusion
    const hasAbnormalities = abnormalFindings.length > 0;
    let conclusion: string;
    if (hasAbnormalities) {
        let details = 'El estudio VNG revela alteraciones que sugieren';
        if (caloric?.interpretation.vestibular_function === 'unilateral_weakness') {
            details += ` patología vestibular periférica ${caloric.interpretation.affected_side === 'left' ? 'izquierda' : 'derecha'}`;
        }
        if (caloric?.interpretation.vestibular_function === 'bilateral_weakness') {
            details += ' afectación vestibular bilateral';
        }
        if (positional?.dix_hallpike?.left.bppv_suspected || positional?.dix_hallpike?.right.bppv_suspected) {
            details += ' vértigo posicional paroxístico benigno (VPPB)';
        }
        details += '. Se recomienda correlación clínica y seguimiento.';
        conclusion = details;
    } else {
        conclusion = 'El estudio VNG se encuentra dentro de límites normales. No se evidencian signos de patología vestibular periférica ni central en el momento del estudio.';
    }

    // Recommendations
    const recommendations: string[] = [];
    if (hasAbnormalities) {
        if (caloric?.interpretation.vestibular_function !== 'normal') {
            recommendations.push('Considerar estudio audiológico completo');
        }
        if (positional?.dix_hallpike?.left.bppv_suspected || positional?.dix_hallpike?.right.bppv_suspected) {
            recommendations.push('Maniobras de reposicionamiento canalicular (Epley/Semont)');
        }
        recommendations.push('Control evolutivo según evolución clínica');
    }

    return { findings, abnormalFindings, conclusion, recommendations };
}
