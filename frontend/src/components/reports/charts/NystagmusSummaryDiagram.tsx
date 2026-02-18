import React from 'react';
import { PositionalTestResult, NystagmusData } from '../../../types/vng';

interface NystagmusSummaryDiagramProps {
    data: PositionalTestResult;
}

const dirLabels: Record<string, string> = {
    left: '←', right: '→', up: '↑', down: '↓',
    rotatory_cw: '↻', rotatory_ccw: '↺',
};

export const NystagmusSummaryDiagram: React.FC<NystagmusSummaryDiagramProps> = ({ data }) => {
    // Collect positions with nystagmus data
    const positions: { label: string; nystagmus: NystagmusData | null | undefined }[] = [];

    positions.push({ label: 'Espontáneo (oscuro)', nystagmus: data.spontaneous_dark });
    positions.push({ label: 'Con fijación', nystagmus: data.spontaneous_fixation });

    if (data.gaze_evoked) {
        positions.push({ label: 'Mirada centro', nystagmus: data.gaze_evoked.center });
        positions.push({ label: 'Mirada der. 20°', nystagmus: data.gaze_evoked.right });
        positions.push({ label: 'Mirada izq. 20°', nystagmus: data.gaze_evoked.left });
        if (data.gaze_evoked.up) positions.push({ label: 'Mirada arriba', nystagmus: data.gaze_evoked.up });
        if (data.gaze_evoked.down) positions.push({ label: 'Mirada abajo', nystagmus: data.gaze_evoked.down });
    }

    if (positions.length === 0) return null;

    const W = 400;
    const barH = 18;
    const gap = 3;
    const pad = { top: 20, right: 30, bottom: 25, left: 120 };
    const plotW = W - pad.left - pad.right;
    const H = pad.top + positions.length * (barH + gap) + pad.bottom;

    const maxSPV = Math.max(15, ...positions.map(p => Math.abs(p.nystagmus?.spv || 0))) * 1.2;

    const scaleX = (spv: number) => pad.left + plotW / 2 + (spv / maxSPV) * (plotW / 2);
    const centerX = pad.left + plotW / 2;

    // Ticks
    const spvStep = maxSPV > 20 ? 5 : 3;
    const ticks: number[] = [];
    for (let v = -Math.floor(maxSPV / spvStep) * spvStep; v <= maxSPV; v += spvStep) ticks.push(v);

    // No-nystagmus zone (±3°/s)
    const noNysLeft = scaleX(-3);
    const noNysRight = scaleX(3);

    return (
        <div className="my-3">
            <h4 className="text-xs font-medium text-gray-600 mb-1">Resumen de Nistagmo por Posición</h4>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: Math.min(300, H) }}>
                <rect x={pad.left} y={pad.top} width={plotW} height={H - pad.top - pad.bottom}
                    fill="white" stroke="#e5e7eb" />

                {/* No-nystagmus zone */}
                <rect x={noNysLeft} y={pad.top} width={noNysRight - noNysLeft}
                    height={H - pad.top - pad.bottom} fill="#f0fdf4" opacity={0.6} />
                <text x={centerX} y={pad.top - 5} fill="#16a34a" fontSize="6" textAnchor="middle" opacity={0.7}>
                    &lt;3°/s
                </text>

                {/* Grid */}
                {ticks.map(v => (
                    <g key={`t-${v}`}>
                        <line x1={scaleX(v)} y1={pad.top}
                            x2={scaleX(v)} y2={H - pad.bottom}
                            stroke={v === 0 ? '#9ca3af' : '#f3f4f6'} strokeWidth={v === 0 ? 0.8 : 0.5} />
                        <text x={scaleX(v)} y={H - pad.bottom + 12} fill="#6b7280" fontSize="7" textAnchor="middle">
                            {v}
                        </text>
                    </g>
                ))}

                {/* Bars */}
                {positions.map((pos, i) => {
                    const y = pad.top + i * (barH + gap) + gap / 2;
                    const spv = pos.nystagmus?.spv || 0;
                    const dir = pos.nystagmus?.direction;
                    const hasNystagmus = pos.nystagmus && Math.abs(spv) > 0.5;
                    const barWidth = Math.abs(scaleX(spv) - centerX);
                    const barX = spv >= 0 ? centerX : centerX - barWidth;

                    return (
                        <g key={`p-${i}`}>
                            {/* Label */}
                            <text x={pad.left - 5} y={y + barH / 2 + 3} fill="#374151" fontSize="7.5" textAnchor="end">
                                {pos.label}
                            </text>

                            {hasNystagmus ? (
                                <>
                                    <rect x={barX} y={y} width={barWidth} height={barH} rx={2}
                                        fill={Math.abs(spv) > 6 ? '#fca5a5' : '#fde68a'} />
                                    {/* Direction arrow */}
                                    <text x={scaleX(spv) + (spv >= 0 ? 4 : -10)} y={y + barH / 2 + 3}
                                        fill="#374151" fontSize="9">
                                        {dir ? dirLabels[dir] || '' : ''}
                                    </text>
                                    {/* SPV value */}
                                    <text x={spv >= 0 ? scaleX(spv) + 14 : scaleX(spv) - 20} y={y + barH / 2 + 3}
                                        fill="#6b7280" fontSize="7">
                                        {spv.toFixed(1)}°/s
                                    </text>
                                </>
                            ) : (
                                <text x={centerX + 5} y={y + barH / 2 + 3} fill="#9ca3af" fontSize="7">—</text>
                            )}
                        </g>
                    );
                })}

                {/* Bottom axis */}
                <line x1={pad.left} y1={H - pad.bottom} x2={pad.left + plotW} y2={H - pad.bottom}
                    stroke="#374151" strokeWidth="1" />
                <text x={centerX} y={H - 5} fill="#374151" fontSize="8" textAnchor="middle">
                    SPV (°/s)
                </text>
            </svg>
        </div>
    );
};
