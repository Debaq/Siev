import React, { useState, useMemo } from 'react';
import { CaloricTestResult, CaloricIrrigation, CaloricCalculationMethod } from '../../../types/vng';
import { REFERENCE_RANGES, isNormal, formatValue } from '../usePDFGeneration';
import { CaloricDiagram } from '../charts/CaloricDiagram';
import { EditableField } from '../shared/EditableField';

interface CaloricSectionProps {
    data: CaloricTestResult;
    diagramStyle: string;
    showGraphs?: boolean;
    previousData?: CaloricTestResult;
    comment?: string;
    onCommentChange?: (value: string) => void;
}

const METHOD_LABELS: Record<CaloricCalculationMethod, string> = {
    spv: 'VCL (°/s)',
    beat_count: 'Conteo de nistagmos',
    total_duration: 'Duración de respuesta (s)',
};

const PROTOCOL_TITLES: Record<string, string> = {
    bithermal: 'Pruebas Calóricas Bitérmicas',
    monothermal_warm: 'Pruebas Calóricas Monotérmicas (Caliente)',
    monothermal_cool: 'Pruebas Calóricas Monotérmicas (Frías)',
};

function getVal(irr: CaloricIrrigation, method: CaloricCalculationMethod): number {
    switch (method) {
        case 'spv': return irr.spv_max;
        case 'beat_count': return irr.beat_count ?? 0;
        case 'total_duration': return irr.duration_response;
    }
}

function getOfiInterpretation(ofi: number): { label: string; bg: string; text: string } {
    if (ofi >= 60) return { label: 'Normal', bg: 'bg-green-100', text: 'text-green-800' };
    if (ofi >= 40) return { label: 'Limítrofe', bg: 'bg-yellow-100', text: 'text-yellow-800' };
    return { label: 'Anormal', bg: 'bg-red-100', text: 'text-red-800' };
}

export const CaloricSection: React.FC<CaloricSectionProps> = ({
    data,
    diagramStyle,
    showGraphs = true,
    previousData,
    comment,
    onCommentChange,
}) => {
    const refs = REFERENCE_RANGES.caloric;
    const { irrigations, interpretation } = data;
    const protocolType = data.protocol_type ?? 'bithermal';
    const isMonothermal = protocolType !== 'bithermal';

    const [calculationMethod, setCalculationMethod] = useState<CaloricCalculationMethod>(
        data.jongkees.calculation_method ?? 'spv'
    );

    // Determinar irrigaciones activas según protocolo
    const activeIrrigations = useMemo(() => {
        const all: { irrigation: CaloricIrrigation; label: string; key: string }[] = [];
        if (protocolType !== 'monothermal_cool') {
            all.push({ irrigation: irrigations.right_warm, label: 'OD Caliente', key: 'rw' });
        }
        if (protocolType !== 'monothermal_warm') {
            all.push({ irrigation: irrigations.right_cool, label: 'OD Fría', key: 'rc' });
        }
        if (protocolType !== 'monothermal_cool') {
            all.push({ irrigation: irrigations.left_warm, label: 'OI Caliente', key: 'lw' });
        }
        if (protocolType !== 'monothermal_warm') {
            all.push({ irrigation: irrigations.left_cool, label: 'OI Fría', key: 'lc' });
        }
        return all;
    }, [irrigations, protocolType]);

    // Verificar si hay datos de beat_count en al menos una irrigación
    const hasBeatData = activeIrrigations.some(
        ({ irrigation }) => irrigation.beat_count != null || irrigation.nystagmus_frequency != null
    );

    // Verificar si hay datos de OFI en al menos una irrigación
    const hasFixationData = activeIrrigations.some(
        ({ irrigation }) => irrigation.fixation_index != null
    );

    // Recálculo dinámico de UW/DP según método seleccionado
    const dynamicJongkees = useMemo(() => {
        const rw = getVal(irrigations.right_warm, calculationMethod);
        const rc = getVal(irrigations.right_cool, calculationMethod);
        const lw = getVal(irrigations.left_warm, calculationMethod);
        const lc = getVal(irrigations.left_cool, calculationMethod);
        const total = rw + rc + lw + lc;
        const uw = total > 0 ? ((rw + rc) - (lw + lc)) / total * 100 : 0;
        const dp = total > 0 ? ((rw + lc) - (lw + rc)) / total * 100 : 0;
        return {
            uw,
            dp,
            uw_significant: Math.abs(uw) > 22,
            dp_significant: Math.abs(dp) > 28,
            rw, rc, lw, lc,
        };
    }, [irrigations, calculationMethod]);

    const isActiveMethodCol = (col: 'spv' | 'beat_count' | 'total_duration') => col === calculationMethod;

    return (
        <div className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 border-b border-gray-300 pb-2 mb-3">
                {PROTOCOL_TITLES[protocolType] ?? PROTOCOL_TITLES.bithermal}
            </h2>

            {/* Selector de método de cálculo — se oculta en PDF */}
            <div className="report-controls flex gap-2 mb-4">
                {(['spv', 'beat_count', 'total_duration'] as CaloricCalculationMethod[]).map((m) => (
                    <button
                        key={m}
                        onClick={() => setCalculationMethod(m)}
                        className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                            calculationMethod === m
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                        }`}
                    >
                        {METHOD_LABELS[m]}
                    </button>
                ))}
            </div>

            {/* Irrigations Table */}
            <div className="overflow-hidden rounded-lg border border-gray-200 mb-4">
                <table className="w-full text-sm">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-3 py-2 text-left text-gray-700">Irrigación</th>
                            <th className="px-3 py-2 text-center text-gray-700">Temp.</th>
                            <th className={`px-3 py-2 text-center text-gray-700 ${isActiveMethodCol('spv') ? 'bg-blue-50' : ''}`}>
                                VCL Máx
                            </th>
                            <th className="px-3 py-2 text-center text-gray-700">Latencia</th>
                            <th className={`px-3 py-2 text-center text-gray-700 ${isActiveMethodCol('total_duration') ? 'bg-blue-50' : ''}`}>
                                Duración Resp.
                            </th>
                            {hasBeatData && (
                                <>
                                    <th className={`px-3 py-2 text-center text-gray-700 ${isActiveMethodCol('beat_count') ? 'bg-blue-50' : ''}`}>
                                        Nistagmos
                                    </th>
                                    <th className="px-3 py-2 text-center text-gray-700">Frec. Nist.</th>
                                </>
                            )}
                            {hasFixationData && (
                                <th className="px-3 py-2 text-center text-gray-700">OFI%</th>
                            )}
                        </tr>
                    </thead>
                    <tbody>
                        {activeIrrigations.map(({ irrigation, label, key }, i) => (
                            <tr key={key} className={`border-t border-gray-200 ${i % 2 === 1 ? 'bg-gray-50' : ''}`}>
                                <td className="px-3 py-2 font-medium">{label}</td>
                                <td className="px-3 py-2 text-center">{irrigation.temperature_celsius}°C</td>
                                <td className={`px-3 py-2 text-center ${isActiveMethodCol('spv') ? 'bg-blue-50' : ''} ${
                                    isNormal(irrigation.spv_max, refs.spv) ? 'text-gray-900' : 'text-red-600 font-semibold'
                                }`}>
                                    {formatValue(irrigation.spv_max, '°/s')}
                                </td>
                                <td className="px-3 py-2 text-center">{formatValue(irrigation.latency_seconds, 's')}</td>
                                <td className={`px-3 py-2 text-center ${isActiveMethodCol('total_duration') ? 'bg-blue-50' : ''}`}>
                                    {formatValue(irrigation.duration_response, 's')}
                                </td>
                                {hasBeatData && (
                                    <>
                                        <td className={`px-3 py-2 text-center ${isActiveMethodCol('beat_count') ? 'bg-blue-50' : ''}`}>
                                            {irrigation.beat_count != null ? irrigation.beat_count : '—'}
                                        </td>
                                        <td className="px-3 py-2 text-center">
                                            {irrigation.nystagmus_frequency != null
                                                ? formatValue(irrigation.nystagmus_frequency, 'Hz')
                                                : '—'}
                                        </td>
                                    </>
                                )}
                                {hasFixationData && (
                                    <td className={`px-3 py-2 text-center ${
                                        irrigation.fixation_index != null
                                            ? (isNormal(irrigation.fixation_index, refs.fixation) ? 'text-gray-900' : 'text-red-600 font-semibold')
                                            : ''
                                    }`}>
                                        {irrigation.fixation_index != null ? formatValue(irrigation.fixation_index, '%') : '—'}
                                    </td>
                                )}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Jongkees Analysis - dinámico según método */}
            <div className="text-xs text-gray-500 mb-2">
                Calculado por {METHOD_LABELS[calculationMethod]}
            </div>
            <div className={`grid ${isMonothermal ? 'grid-cols-1' : 'grid-cols-2'} gap-4 mb-4`}>
                <div className={`p-4 rounded-lg ${dynamicJongkees.uw_significant ? 'bg-red-50' : 'bg-green-50'}`}>
                    <div className="text-sm text-gray-600 mb-1">Paresia Unilateral (UW%)</div>
                    <div className={`text-2xl font-bold ${dynamicJongkees.uw_significant ? 'text-red-600' : 'text-green-600'}`}>
                        {dynamicJongkees.uw > 0 ? '+' : ''}{dynamicJongkees.uw.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                        {dynamicJongkees.uw_significant
                            ? dynamicJongkees.uw > 0 ? 'Hipoexcitabilidad derecha' : 'Hipoexcitabilidad izquierda'
                            : 'Dentro de límites normales (±22%)'}
                    </div>
                </div>

                {!isMonothermal && (
                    <div className={`p-4 rounded-lg ${dynamicJongkees.dp_significant ? 'bg-red-50' : 'bg-green-50'}`}>
                        <div className="text-sm text-gray-600 mb-1">Preponderancia Direccional (DP%)</div>
                        <div className={`text-2xl font-bold ${dynamicJongkees.dp_significant ? 'text-red-600' : 'text-green-600'}`}>
                            {dynamicJongkees.dp > 0 ? '+' : ''}{dynamicJongkees.dp.toFixed(1)}%
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                            {dynamicJongkees.dp_significant
                                ? dynamicJongkees.dp > 0 ? 'Preponderancia derecha' : 'Preponderancia izquierda'
                                : 'Dentro de límites normales (±28%)'}
                        </div>
                    </div>
                )}
            </div>

            {/* Sección OFI dedicada */}
            {hasFixationData && (
                <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-2">Índice de Fijación Ocular (OFI)</h3>
                    <div className="overflow-hidden rounded-lg border border-gray-200 mb-2">
                        <table className="w-full text-sm">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="px-3 py-2 text-left text-gray-700">Irrigación</th>
                                    <th className="px-3 py-2 text-center text-gray-700">VCL Török (°/s)</th>
                                    <th className="px-3 py-2 text-center text-gray-700">VCL con Fijación (°/s)</th>
                                    <th className="px-3 py-2 text-center text-gray-700">OFI (%)</th>
                                    <th className="px-3 py-2 text-center text-gray-700">Interpretación</th>
                                </tr>
                            </thead>
                            <tbody>
                                {activeIrrigations
                                    .filter(({ irrigation }) => irrigation.fixation_index != null)
                                    .map(({ irrigation, label, key }, i) => {
                                        const interp = getOfiInterpretation(irrigation.fixation_index!);
                                        return (
                                            <tr key={key} className={`border-t border-gray-200 ${i % 2 === 1 ? 'bg-gray-50' : ''}`}>
                                                <td className="px-3 py-2 font-medium">{label}</td>
                                                <td className="px-3 py-2 text-center">{formatValue(irrigation.spv_max, '°/s')}</td>
                                                <td className="px-3 py-2 text-center">
                                                    {irrigation.spv_with_fixation != null
                                                        ? formatValue(irrigation.spv_with_fixation, '°/s')
                                                        : '—'}
                                                </td>
                                                <td className="px-3 py-2 text-center font-semibold">{formatValue(irrigation.fixation_index!, '%')}</td>
                                                <td className={`px-3 py-2 text-center font-medium ${interp.text}`}>
                                                    <span className={`px-2 py-0.5 rounded ${interp.bg}`}>{interp.label}</span>
                                                </td>
                                            </tr>
                                        );
                                    })}
                            </tbody>
                        </table>
                    </div>
                    <p className="text-xs text-gray-500 italic">
                        OFI = (VCL Török − VCL con fijación) / VCL Török × 100. Normal ≥ 60%.
                    </p>
                    {activeIrrigations.some(({ irrigation }) =>
                        irrigation.fixation_index != null && irrigation.fixation_index < 40
                    ) && (
                        <p className="text-xs text-red-600 mt-1 font-medium">
                            Alteración del OFI sugiere compromiso de vías centrales de fijación visual.
                        </p>
                    )}
                </div>
            )}

            {/* Caloric Diagram */}
            {showGraphs && (
                <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    <div className="text-sm text-gray-600 mb-2">Diagrama Calórico ({
                        diagramStyle === 'claussen' ? 'Claussen' :
                        diagramStyle === 'freyss' ? 'Freyss' : 'Mariposa'
                    })</div>
                    <CaloricDiagram
                        data={data}
                        style={diagramStyle as 'claussen' | 'freyss' | 'butterfly'}
                    />
                </div>
            )}

            {/* Historical Comparison */}
            {previousData && (
                <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                    <div className="text-sm font-medium text-blue-800 mb-2">Comparación con sesión anterior</div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="text-gray-600">UW% anterior: </span>
                            <span className="font-medium">{previousData.jongkees.unilateral_weakness_percent.toFixed(1)}%</span>
                            <span className="ml-2 text-xs">
                                {Math.abs(dynamicJongkees.uw) < Math.abs(previousData.jongkees.unilateral_weakness_percent)
                                    ? '↓ Mejoría'
                                    : Math.abs(dynamicJongkees.uw) > Math.abs(previousData.jongkees.unilateral_weakness_percent)
                                        ? '↑ Empeoramiento'
                                        : '→ Sin cambios'}
                            </span>
                        </div>
                        <div>
                            <span className="text-gray-600">DP% anterior: </span>
                            <span className="font-medium">{previousData.jongkees.directional_preponderance_percent.toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Interpretation */}
            <div className={`p-3 rounded ${
                interpretation.vestibular_function === 'normal' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
            }`}>
                <span className="font-medium">Interpretación:</span>{' '}
                {interpretation.vestibular_function === 'normal' && 'Función vestibular bilateral normal.'}
                {interpretation.vestibular_function === 'unilateral_weakness' && (
                    `Hipofunción vestibular ${interpretation.affected_side === 'left' ? 'izquierda' : 'derecha'}.`
                )}
                {interpretation.vestibular_function === 'bilateral_weakness' && 'Hipofunción vestibular bilateral.'}
                {interpretation.vestibular_function === 'hyperactive' && 'Hiperexcitabilidad vestibular.'}
                {interpretation.central_signs && interpretation.central_signs.length > 0 && (
                    <span className="ml-2">Signos centrales: {interpretation.central_signs.join(', ')}.</span>
                )}
            </div>

            {data.clinical_notes && (
                <div className="mt-3 text-sm text-gray-600 italic">
                    Nota: {data.clinical_notes}
                </div>
            )}

            {/* Evaluator comment */}
            {onCommentChange && (
                <EditableField
                    value={comment || ''}
                    onChange={onCommentChange}
                    label="Observaciones del evaluador"
                    placeholder="Escribir observaciones sobre pruebas calóricas..."
                />
            )}
        </div>
    );
};
