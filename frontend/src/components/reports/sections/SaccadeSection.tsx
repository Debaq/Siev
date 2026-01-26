import React from 'react';
import { SaccadeTestResult } from '../../../types/vng';
import { REFERENCE_RANGES, isNormal, formatValue } from '../usePDFGeneration';

interface SaccadeSectionProps {
    data: SaccadeTestResult;
    showGraphs?: boolean;
}

export const SaccadeSection: React.FC<SaccadeSectionProps> = ({ data, showGraphs: _showGraphs }) => {
    const refs = REFERENCE_RANGES.saccade;

    const MetricCell: React.FC<{ value: number; range: { min: number; max: number }; unit: string }> =
        ({ value, range, unit }) => {
            const normal = isNormal(value, range);
            return (
                <td className={`px-3 py-2 text-center ${normal ? 'text-gray-900' : 'text-red-600 font-semibold'}`}>
                    {formatValue(value, unit)}
                </td>
            );
        };

    return (
        <div className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 border-b border-gray-300 pb-2 mb-3">
                Prueba de Sacadas
            </h2>

            <div className="overflow-hidden rounded-lg border border-gray-200">
                <table className="w-full text-sm">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-3 py-2 text-left text-gray-700">Dirección</th>
                            <th className="px-3 py-2 text-center text-gray-700">Latencia (ms)</th>
                            <th className="px-3 py-2 text-center text-gray-700">Velocidad (°/s)</th>
                            <th className="px-3 py-2 text-center text-gray-700">Precisión (%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr className="border-t border-gray-200">
                            <td className="px-3 py-2 font-medium">Izquierda</td>
                            <MetricCell value={data.left.latency_ms} range={refs.latency} unit="ms" />
                            <MetricCell value={data.left.peak_velocity} range={refs.velocity} unit="°/s" />
                            <MetricCell value={data.left.accuracy_percent} range={refs.accuracy} unit="%" />
                        </tr>
                        <tr className="border-t border-gray-200 bg-gray-50">
                            <td className="px-3 py-2 font-medium">Derecha</td>
                            <MetricCell value={data.right.latency_ms} range={refs.latency} unit="ms" />
                            <MetricCell value={data.right.peak_velocity} range={refs.velocity} unit="°/s" />
                            <MetricCell value={data.right.accuracy_percent} range={refs.accuracy} unit="%" />
                        </tr>
                        {data.up && (
                            <tr className="border-t border-gray-200">
                                <td className="px-3 py-2 font-medium">Arriba</td>
                                <MetricCell value={data.up.latency_ms} range={refs.latency} unit="ms" />
                                <MetricCell value={data.up.peak_velocity} range={refs.velocity} unit="°/s" />
                                <MetricCell value={data.up.accuracy_percent} range={refs.accuracy} unit="%" />
                            </tr>
                        )}
                        {data.down && (
                            <tr className="border-t border-gray-200 bg-gray-50">
                                <td className="px-3 py-2 font-medium">Abajo</td>
                                <MetricCell value={data.down.latency_ms} range={refs.latency} unit="ms" />
                                <MetricCell value={data.down.peak_velocity} range={refs.velocity} unit="°/s" />
                                <MetricCell value={data.down.accuracy_percent} range={refs.accuracy} unit="%" />
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Reference values */}
            <div className="mt-2 text-xs text-gray-500">
                Valores normales: Latencia {refs.latency.min}-{refs.latency.max}ms,
                Velocidad {refs.velocity.min}-{refs.velocity.max}°/s,
                Precisión &gt;{refs.accuracy.min}%
            </div>

            {/* Interpretation */}
            <div className={`mt-3 p-3 rounded ${data.is_normal ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                <span className="font-medium">Interpretación:</span>{' '}
                {data.is_normal ? 'Sacadas dentro de límites normales.' : 'Se observan alteraciones en las sacadas.'}
                {data.abnormality_notes && <span> {data.abnormality_notes}</span>}
            </div>

            {data.clinical_notes && (
                <div className="mt-2 text-sm text-gray-600 italic">
                    Nota: {data.clinical_notes}
                </div>
            )}
        </div>
    );
};
