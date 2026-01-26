import React from 'react';
import { CaloricTestResult, CaloricIrrigation } from '../../../types/vng';
import { REFERENCE_RANGES, isNormal, formatValue } from '../usePDFGeneration';
import { CaloricDiagram } from '../charts/CaloricDiagram';

interface CaloricSectionProps {
    data: CaloricTestResult;
    diagramStyle: string;
    showGraphs?: boolean;
    previousData?: CaloricTestResult;
}

export const CaloricSection: React.FC<CaloricSectionProps> = ({
    data,
    diagramStyle,
    showGraphs = true,
    previousData
}) => {
    const refs = REFERENCE_RANGES.caloric;
    const { jongkees, irrigations, interpretation } = data;

    const IrrigationRow: React.FC<{ irrigation: CaloricIrrigation; label: string; bgColor?: string }> = ({
        irrigation,
        label,
        bgColor = ''
    }) => (
        <tr className={`border-t border-gray-200 ${bgColor}`}>
            <td className="px-3 py-2 font-medium">{label}</td>
            <td className="px-3 py-2 text-center">{irrigation.temperature_celsius}°C</td>
            <td className={`px-3 py-2 text-center ${
                isNormal(irrigation.spv_max, refs.spv) ? 'text-gray-900' : 'text-red-600 font-semibold'
            }`}>
                {formatValue(irrigation.spv_max, '°/s')}
            </td>
            <td className="px-3 py-2 text-center">{formatValue(irrigation.latency_seconds, 's')}</td>
            <td className="px-3 py-2 text-center">{formatValue(irrigation.duration_response, 's')}</td>
            {irrigation.fixation_index !== undefined && (
                <td className={`px-3 py-2 text-center ${
                    isNormal(irrigation.fixation_index, refs.fixation) ? 'text-gray-900' : 'text-red-600 font-semibold'
                }`}>
                    {formatValue(irrigation.fixation_index, '%')}
                </td>
            )}
        </tr>
    );

    return (
        <div className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 border-b border-gray-300 pb-2 mb-3">
                Pruebas Calóricas Bitérmicas
            </h2>

            {/* Irrigations Table */}
            <div className="overflow-hidden rounded-lg border border-gray-200 mb-4">
                <table className="w-full text-sm">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-3 py-2 text-left text-gray-700">Irrigación</th>
                            <th className="px-3 py-2 text-center text-gray-700">Temp.</th>
                            <th className="px-3 py-2 text-center text-gray-700">SPV Máx</th>
                            <th className="px-3 py-2 text-center text-gray-700">Latencia</th>
                            <th className="px-3 py-2 text-center text-gray-700">Duración</th>
                            <th className="px-3 py-2 text-center text-gray-700">Índ. Fij.</th>
                        </tr>
                    </thead>
                    <tbody>
                        <IrrigationRow irrigation={irrigations.right_warm} label="OD Caliente" />
                        <IrrigationRow irrigation={irrigations.right_cool} label="OD Fría" bgColor="bg-gray-50" />
                        <IrrigationRow irrigation={irrigations.left_warm} label="OI Caliente" />
                        <IrrigationRow irrigation={irrigations.left_cool} label="OI Fría" bgColor="bg-gray-50" />
                    </tbody>
                </table>
            </div>

            {/* Jongkees Analysis */}
            <div className="grid grid-cols-2 gap-4 mb-4">
                <div className={`p-4 rounded-lg ${jongkees.uw_significant ? 'bg-red-50' : 'bg-green-50'}`}>
                    <div className="text-sm text-gray-600 mb-1">Paresia Unilateral (UW%)</div>
                    <div className={`text-2xl font-bold ${jongkees.uw_significant ? 'text-red-600' : 'text-green-600'}`}>
                        {jongkees.unilateral_weakness_percent > 0 ? '+' : ''}{jongkees.unilateral_weakness_percent.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                        {jongkees.uw_significant
                            ? jongkees.unilateral_weakness_percent > 0 ? 'Hipoexcitabilidad derecha' : 'Hipoexcitabilidad izquierda'
                            : 'Dentro de límites normales (±22%)'}
                    </div>
                </div>

                <div className={`p-4 rounded-lg ${jongkees.dp_significant ? 'bg-red-50' : 'bg-green-50'}`}>
                    <div className="text-sm text-gray-600 mb-1">Preponderancia Direccional (DP%)</div>
                    <div className={`text-2xl font-bold ${jongkees.dp_significant ? 'text-red-600' : 'text-green-600'}`}>
                        {jongkees.directional_preponderance_percent > 0 ? '+' : ''}{jongkees.directional_preponderance_percent.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                        {jongkees.dp_significant
                            ? jongkees.directional_preponderance_percent > 0 ? 'Preponderancia derecha' : 'Preponderancia izquierda'
                            : 'Dentro de límites normales (±28%)'}
                    </div>
                </div>
            </div>

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
                                {Math.abs(jongkees.unilateral_weakness_percent) < Math.abs(previousData.jongkees.unilateral_weakness_percent)
                                    ? '↓ Mejoría'
                                    : Math.abs(jongkees.unilateral_weakness_percent) > Math.abs(previousData.jongkees.unilateral_weakness_percent)
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
        </div>
    );
};
