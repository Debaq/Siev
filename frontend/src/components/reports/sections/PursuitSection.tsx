import React from 'react';
import { SmoothPursuitTestResult, PursuitPattern } from '../../../types/vng';
import { REFERENCE_RANGES, isNormal, formatValue } from '../usePDFGeneration';
import { PursuitGainDiagram } from '../charts/PursuitGainDiagram';
import { EditableField } from '../shared/EditableField';

interface PursuitSectionProps {
    data: SmoothPursuitTestResult;
    showGraphs?: boolean;
    comment?: string;
    onCommentChange?: (value: string) => void;
}

const patternDescriptions: Record<PursuitPattern, string> = {
    'I': 'Normal - Movimiento suave sin sacadas correctivas',
    'II': 'Levemente afectado - Escasas sacadas correctivas',
    'III': 'Moderadamente afectado - Frecuentes sacadas correctivas',
    'IV': 'Severamente afectado - Rastreo sacádico predominante'
};

export const PursuitSection: React.FC<PursuitSectionProps> = ({
    data,
    showGraphs,
    comment,
    onCommentChange,
}) => {
    const refs = REFERENCE_RANGES.pursuit;

    const GainCell: React.FC<{ value: number }> = ({ value }) => {
        const normal = isNormal(value, refs.gain);
        return (
            <td className={`px-3 py-2 text-center ${normal ? 'text-gray-900' : 'text-red-600 font-semibold'}`}>
                {formatValue(value, '', 2)}
            </td>
        );
    };

    return (
        <div className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 border-b border-gray-300 pb-2 mb-3">
                Prueba de Rastreo (Smooth Pursuit)
            </h2>

            {/* Pattern visual indicator */}
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-600">Patrón:</span>
                    <div className="flex gap-1">
                        {(['I', 'II', 'III', 'IV'] as PursuitPattern[]).map((p, i) => (
                            <div
                                key={p}
                                className={`w-8 h-8 flex items-center justify-center rounded text-sm font-medium
                                    ${data.pattern === p
                                        ? i === 0
                                            ? 'bg-green-500 text-white'
                                            : i === 1
                                                ? 'bg-yellow-500 text-white'
                                                : i === 2
                                                    ? 'bg-orange-500 text-white'
                                                    : 'bg-red-500 text-white'
                                        : 'bg-gray-200 text-gray-400'
                                    }`}
                            >
                                {p}
                            </div>
                        ))}
                    </div>
                    <span className="text-sm text-gray-700">{patternDescriptions[data.pattern]}</span>
                </div>
            </div>

            {/* Metrics table */}
            <div className="overflow-hidden rounded-lg border border-gray-200">
                <table className="w-full text-sm">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-3 py-2 text-left text-gray-700">Dirección</th>
                            <th className="px-3 py-2 text-center text-gray-700">Ganancia</th>
                            <th className="px-3 py-2 text-center text-gray-700">Desfase (°)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr className="border-t border-gray-200">
                            <td className="px-3 py-2 font-medium">Izquierda</td>
                            <GainCell value={data.horizontal.left.gain} />
                            <td className="px-3 py-2 text-center">{formatValue(data.horizontal.left.phase_lag, '°')}</td>
                        </tr>
                        <tr className="border-t border-gray-200 bg-gray-50">
                            <td className="px-3 py-2 font-medium">Derecha</td>
                            <GainCell value={data.horizontal.right.gain} />
                            <td className="px-3 py-2 text-center">{formatValue(data.horizontal.right.phase_lag, '°')}</td>
                        </tr>
                        {data.vertical && (
                            <>
                                <tr className="border-t border-gray-200">
                                    <td className="px-3 py-2 font-medium">Arriba</td>
                                    <GainCell value={data.vertical.up.gain} />
                                    <td className="px-3 py-2 text-center">{formatValue(data.vertical.up.phase_lag, '°')}</td>
                                </tr>
                                <tr className="border-t border-gray-200 bg-gray-50">
                                    <td className="px-3 py-2 font-medium">Abajo</td>
                                    <GainCell value={data.vertical.down.gain} />
                                    <td className="px-3 py-2 text-center">{formatValue(data.vertical.down.phase_lag, '°')}</td>
                                </tr>
                            </>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Test parameters */}
            <div className="mt-2 text-xs text-gray-500">
                Parámetros: Frecuencia {data.target_frequency} Hz, Amplitud {data.target_amplitude}°.
                Ganancia normal: {refs.gain.min}-{refs.gain.max}
            </div>

            {/* Pursuit gain diagram */}
            {showGraphs && <PursuitGainDiagram data={data} />}

            {/* Interpretation */}
            <div className={`mt-3 p-3 rounded ${data.is_normal ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                <span className="font-medium">Interpretación:</span>{' '}
                {data.is_normal
                    ? 'Rastreo ocular dentro de límites normales.'
                    : 'Se observan alteraciones en el rastreo ocular.'}
            </div>

            {data.clinical_notes && (
                <div className="mt-2 text-sm text-gray-600 italic">
                    Nota: {data.clinical_notes}
                </div>
            )}

            {/* Evaluator comment */}
            {onCommentChange && (
                <EditableField
                    value={comment || ''}
                    onChange={onCommentChange}
                    label="Observaciones del evaluador"
                    placeholder="Escribir observaciones sobre rastreo..."
                />
            )}
        </div>
    );
};
