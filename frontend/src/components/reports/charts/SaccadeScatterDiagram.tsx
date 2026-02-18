import React from 'react';
import { SaccadeMarkerReport } from '../../../types/vng';

interface SaccadeScatterDiagramProps {
    saccades: SaccadeMarkerReport[];
}

export const SaccadeScatterDiagram: React.FC<SaccadeScatterDiagramProps> = ({ saccades }) => {
    const W = 400;
    const H = 260;
    const pad = { top: 25, right: 20, bottom: 40, left: 55 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    // Determine axis ranges
    const maxAmp = Math.max(40, ...saccades.map(s => s.amplitude)) * 1.1;
    const maxVel = Math.max(700, ...saccades.map(s => s.peak_velocity)) * 1.1;

    const scaleX = (amp: number) => pad.left + (amp / maxAmp) * plotW;
    const scaleY = (vel: number) => pad.top + plotH - (vel / maxVel) * plotH;

    // Main sequence reference line: vel ≈ 18 * amp (approximate normal relationship)
    const msPoints = [0, maxAmp].map(a => `${scaleX(a)},${scaleY(Math.min(18 * a, maxVel))}`).join(' ');

    // Normal velocity band (300-600 °/s)
    const bandTop = scaleY(600);
    const bandBottom = scaleY(300);

    // Axis ticks
    const ampTicks = [0, 10, 20, 30, 40].filter(v => v <= maxAmp);
    const velTicks = [0, 100, 200, 300, 400, 500, 600, 700].filter(v => v <= maxVel);

    return (
        <div className="my-3">
            <h4 className="text-xs font-medium text-gray-600 mb-1">Scatter: Amplitud vs Velocidad Pico</h4>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 220 }}>
                {/* Background */}
                <rect x={pad.left} y={pad.top} width={plotW} height={plotH} fill="white" stroke="#e5e7eb" />

                {/* Normal velocity band */}
                <rect
                    x={pad.left} y={bandTop}
                    width={plotW} height={bandBottom - bandTop}
                    fill="#dcfce7" opacity={0.5}
                />
                <text x={pad.left + 3} y={bandTop + 10} fill="#16a34a" fontSize="7" opacity={0.7}>
                    Rango normal
                </text>

                {/* Main sequence reference */}
                <polyline points={msPoints} fill="none" stroke="#9ca3af" strokeWidth="1" strokeDasharray="4,3" />

                {/* Grid lines */}
                {velTicks.map(v => (
                    <g key={`vg-${v}`}>
                        <line x1={pad.left} y1={scaleY(v)} x2={pad.left + plotW} y2={scaleY(v)}
                            stroke="#f3f4f6" strokeWidth="0.5" />
                        <text x={pad.left - 5} y={scaleY(v) + 3} fill="#6b7280" fontSize="8" textAnchor="end">
                            {v}
                        </text>
                    </g>
                ))}
                {ampTicks.map(a => (
                    <g key={`ag-${a}`}>
                        <line x1={scaleX(a)} y1={pad.top} x2={scaleX(a)} y2={pad.top + plotH}
                            stroke="#f3f4f6" strokeWidth="0.5" />
                        <text x={scaleX(a)} y={pad.top + plotH + 14} fill="#6b7280" fontSize="8" textAnchor="middle">
                            {a}°
                        </text>
                    </g>
                ))}

                {/* Data points */}
                {saccades.map((s, i) => (
                    <circle
                        key={i}
                        cx={scaleX(s.amplitude)}
                        cy={scaleY(s.peak_velocity)}
                        r={3}
                        fill={s.direction === 'right' ? '#f472b6' : '#22d3ee'}
                        opacity={0.7}
                    />
                ))}

                {/* Axes */}
                <line x1={pad.left} y1={pad.top + plotH} x2={pad.left + plotW} y2={pad.top + plotH} stroke="#374151" strokeWidth="1" />
                <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} stroke="#374151" strokeWidth="1" />

                {/* Labels */}
                <text x={pad.left + plotW / 2} y={H - 5} fill="#374151" fontSize="9" textAnchor="middle">
                    Amplitud (°)
                </text>
                <text x={12} y={pad.top + plotH / 2} fill="#374151" fontSize="9" textAnchor="middle"
                    transform={`rotate(-90, 12, ${pad.top + plotH / 2})`}>
                    Velocidad (°/s)
                </text>

                {/* Legend */}
                <circle cx={pad.left + plotW - 80} cy={pad.top + 10} r={3} fill="#f472b6" />
                <text x={pad.left + plotW - 74} y={pad.top + 13} fill="#6b7280" fontSize="8">Derecha</text>
                <circle cx={pad.left + plotW - 80} cy={pad.top + 22} r={3} fill="#22d3ee" />
                <text x={pad.left + plotW - 74} y={pad.top + 25} fill="#6b7280" fontSize="8">Izquierda</text>
            </svg>
        </div>
    );
};
