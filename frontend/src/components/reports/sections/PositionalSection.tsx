import React from 'react';
import { PositionalTestResult, NystagmusData, DixHallpikeResult } from '../../../types/vng';
import { NystagmusSummaryDiagram } from '../charts/NystagmusSummaryDiagram';
import { EditableField } from '../shared/EditableField';

interface PositionalSectionProps {
    data: PositionalTestResult;
    showGraphs?: boolean;
    comment?: string;
    onCommentChange?: (value: string) => void;
}

const directionLabels: Record<string, string> = {
    left: 'Izquierda',
    right: 'Derecha',
    up: 'Arriba',
    down: 'Abajo',
    rotatory_cw: 'Rotatorio horario',
    rotatory_ccw: 'Rotatorio antihorario'
};

const NystagmusDisplay: React.FC<{ nystagmus: NystagmusData | null | undefined; label: string }> = ({
    nystagmus,
    label
}) => {
    if (!nystagmus) {
        return (
            <tr className="border-t border-gray-200">
                <td className="px-3 py-2 font-medium">{label}</td>
                <td className="px-3 py-2 text-center text-gray-400">-</td>
                <td className="px-3 py-2 text-center text-gray-400">-</td>
                <td className="px-3 py-2 text-center text-green-600">Ausente</td>
            </tr>
        );
    }

    return (
        <tr className="border-t border-gray-200">
            <td className="px-3 py-2 font-medium">{label}</td>
            <td className="px-3 py-2 text-center">{nystagmus.spv.toFixed(1)}°/s</td>
            <td className="px-3 py-2 text-center">{directionLabels[nystagmus.direction] || nystagmus.direction}</td>
            <td className="px-3 py-2 text-center text-red-600 font-medium">Presente</td>
        </tr>
    );
};

const DixHallpikeDisplay: React.FC<{ result: DixHallpikeResult; side: string }> = ({ result, side }) => {
    return (
        <div className={`p-3 rounded-lg ${result.bppv_suspected ? 'bg-red-50' : 'bg-gray-50'}`}>
            <div className="font-medium text-gray-800 mb-2">
                {side === 'left' ? 'Lado Izquierdo' : 'Lado Derecho'}
            </div>
            {result.nystagmus_present ? (
                <div className="text-sm space-y-1">
                    <div className="text-red-600 font-medium">Nistagmo presente</div>
                    {result.nystagmus && (
                        <>
                            <div>Dirección: {directionLabels[result.nystagmus.direction]}</div>
                            <div>Latencia: {result.nystagmus.latency_seconds.toFixed(1)}s</div>
                            <div>Duración: {result.nystagmus.duration_seconds.toFixed(1)}s</div>
                            <div>Intensidad: {
                                result.nystagmus.intensity === 'mild' ? 'Leve' :
                                result.nystagmus.intensity === 'moderate' ? 'Moderada' : 'Severa'
                            }</div>
                            {result.nystagmus.fatigable && <div className="text-gray-600">Fatigable</div>}
                        </>
                    )}
                    {result.vertigo_reported && <div className="text-orange-600">Vértigo reportado</div>}
                    {result.bppv_suspected && (
                        <div className="mt-2 font-medium text-red-700">
                            Sospecha de VPPB - Canal {
                                result.affected_canal === 'posterior' ? 'posterior' :
                                result.affected_canal === 'horizontal' ? 'horizontal' : 'anterior'
                            }
                        </div>
                    )}
                </div>
            ) : (
                <div className="text-green-600 font-medium">Negativo</div>
            )}
        </div>
    );
};

export const PositionalSection: React.FC<PositionalSectionProps> = ({
    data,
    showGraphs,
    comment,
    onCommentChange,
}) => {
    return (
        <div className="mb-6">
            <h2 className="text-base font-semibold text-gray-800 border-b border-gray-300 pb-2 mb-3">
                Pruebas Posicionales
            </h2>

            {/* Spontaneous Nystagmus */}
            <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Nistagmo Espontáneo</h3>
                <div className="overflow-hidden rounded-lg border border-gray-200">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-100">
                            <tr>
                                <th className="px-3 py-2 text-left text-gray-700">Condición</th>
                                <th className="px-3 py-2 text-center text-gray-700">SPV</th>
                                <th className="px-3 py-2 text-center text-gray-700">Dirección</th>
                                <th className="px-3 py-2 text-center text-gray-700">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            <NystagmusDisplay nystagmus={data.spontaneous_dark} label="Sin fijación (oscuro)" />
                            <NystagmusDisplay nystagmus={data.spontaneous_fixation} label="Con fijación" />
                        </tbody>
                    </table>
                </div>

                {/* Fixation Index */}
                {data.fixation_index !== undefined && (
                    <div className="mt-2 text-sm">
                        <span className="text-gray-600">Índice de fijación: </span>
                        <span className={`font-medium ${data.fixation_index >= 60 ? 'text-green-600' : 'text-red-600'}`}>
                            {data.fixation_index.toFixed(1)}%
                        </span>
                        <span className="text-gray-500 text-xs ml-2">(Normal &gt;60%)</span>
                    </div>
                )}
            </div>

            {/* Gaze-Evoked Nystagmus */}
            {data.gaze_evoked && (
                <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Nistagmo Evocado por la Mirada</h3>
                    <div className="overflow-hidden rounded-lg border border-gray-200">
                        <table className="w-full text-sm">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="px-3 py-2 text-left text-gray-700">Posición</th>
                                    <th className="px-3 py-2 text-center text-gray-700">SPV</th>
                                    <th className="px-3 py-2 text-center text-gray-700">Dirección</th>
                                    <th className="px-3 py-2 text-center text-gray-700">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                <NystagmusDisplay nystagmus={data.gaze_evoked.center} label="Centro" />
                                <NystagmusDisplay nystagmus={data.gaze_evoked.right} label="Derecha 20°" />
                                <NystagmusDisplay nystagmus={data.gaze_evoked.left} label="Izquierda 20°" />
                                {data.gaze_evoked.up && <NystagmusDisplay nystagmus={data.gaze_evoked.up} label="Arriba 20°" />}
                                {data.gaze_evoked.down && <NystagmusDisplay nystagmus={data.gaze_evoked.down} label="Abajo 20°" />}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Nystagmus summary diagram */}
            {showGraphs && <NystagmusSummaryDiagram data={data} />}

            {/* Dix-Hallpike */}
            {data.dix_hallpike && (
                <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Maniobra de Dix-Hallpike</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <DixHallpikeDisplay result={data.dix_hallpike.left} side="left" />
                        <DixHallpikeDisplay result={data.dix_hallpike.right} side="right" />
                    </div>
                </div>
            )}

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
                    placeholder="Escribir observaciones sobre pruebas posicionales..."
                />
            )}
        </div>
    );
};
