import React from 'react';
import { SmoothPursuitTestResult } from '../../../types/vng';

interface PursuitGainDiagramProps {
    data: SmoothPursuitTestResult;
}

export const PursuitGainDiagram: React.FC<PursuitGainDiagramProps> = ({ data }) => {
    const W = 400;
    const H = 180;
    const pad = { top: 25, right: 30, bottom: 25, left: 70 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    // Collect gain values per direction
    const directions: { label: string; gain: number }[] = [
        { label: 'Izquierda', gain: data.horizontal.left.gain },
        { label: 'Derecha', gain: data.horizontal.right.gain },
    ];
    if (data.vertical) {
        directions.push(
            { label: 'Arriba', gain: data.vertical.up.gain },
            { label: 'Abajo', gain: data.vertical.down.gain },
        );
    }

    const maxGain = Math.max(1.3, ...directions.map(d => d.gain)) * 1.1;
    const barH = Math.min(22, plotH / directions.length - 4);
    const totalBarsH = directions.length * (barH + 4) - 4;
    const startY = pad.top + (plotH - totalBarsH) / 2;

    const scaleX = (g: number) => pad.left + (g / maxGain) * plotW;

    // Normal zone (0.8 - 1.0)
    const normalLeft = scaleX(0.8);
    const normalRight = scaleX(1.0);

    // Gain ticks
    const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2].filter(v => v <= maxGain);

    return (
        <div className="my-3">
            <h4 className="text-xs font-medium text-gray-600 mb-1">Ganancia de Rastreo por Dirección</h4>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 160 }}>
                <rect x={pad.left} y={pad.top} width={plotW} height={plotH} fill="white" stroke="#e5e7eb" />

                {/* Normal zone */}
                <rect x={normalLeft} y={pad.top} width={normalRight - normalLeft} height={plotH}
                    fill="#dcfce7" opacity={0.5} />

                {/* Grid and ticks */}
                {ticks.map(v => (
                    <g key={`t-${v}`}>
                        <line x1={scaleX(v)} y1={pad.top} x2={scaleX(v)} y2={pad.top + plotH}
                            stroke="#f3f4f6" strokeWidth="0.5" />
                        <text x={scaleX(v)} y={pad.top + plotH + 12} fill="#6b7280" fontSize="7" textAnchor="middle">
                            {v.toFixed(1)}
                        </text>
                    </g>
                ))}

                {/* Bars */}
                {directions.map((d, i) => {
                    const y = startY + i * (barH + 4);
                    const barW = scaleX(d.gain) - pad.left;
                    const isNormal = d.gain >= 0.8 && d.gain <= 1.0;
                    return (
                        <g key={d.label}>
                            <text x={pad.left - 5} y={y + barH / 2 + 3} fill="#374151" fontSize="8" textAnchor="end">
                                {d.label}
                            </text>
                            <rect x={pad.left} y={y} width={Math.max(0, barW)} height={barH} rx={2}
                                fill={isNormal ? '#22c55e' : '#ef4444'} opacity={0.8} />
                            <text x={pad.left + barW + 4} y={y + barH / 2 + 3} fill="#374151" fontSize="8">
                                {d.gain.toFixed(2)}
                            </text>
                        </g>
                    );
                })}

                {/* Axes */}
                <line x1={pad.left} y1={pad.top + plotH} x2={pad.left + plotW} y2={pad.top + plotH} stroke="#374151" strokeWidth="1" />
                <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} stroke="#374151" strokeWidth="1" />

                {/* Pattern badge */}
                <rect x={W - pad.right - 55} y={pad.top + 3} width={50} height={16} rx={8}
                    fill={data.pattern === 'I' ? '#dcfce7' : data.pattern === 'II' ? '#fef9c3' : '#fecaca'}
                    stroke={data.pattern === 'I' ? '#22c55e' : data.pattern === 'II' ? '#eab308' : '#ef4444'}
                    strokeWidth="0.5" />
                <text x={W - pad.right - 30} y={pad.top + 14} fill="#374151" fontSize="8" textAnchor="middle" fontWeight="bold">
                    Patrón {data.pattern}
                </text>

                {/* Gain label */}
                <text x={pad.left + plotW / 2} y={H - 5} fill="#374151" fontSize="8" textAnchor="middle">
                    Ganancia
                </text>
            </svg>
        </div>
    );
};
