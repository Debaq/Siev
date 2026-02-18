import React from 'react';

interface SPVTimePoint {
    time: number;
    spv: number;
}

interface SPVTimelineDiagramProps {
    timeline: SPVTimePoint[];
    overallSPV: number;
}

export const SPVTimelineDiagram: React.FC<SPVTimelineDiagramProps> = ({ timeline, overallSPV }) => {
    if (timeline.length === 0) return null;

    const W = 400;
    const H = 200;
    const pad = { top: 20, right: 20, bottom: 35, left: 50 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    const maxTime = Math.max(...timeline.map(p => p.time));
    const maxSPV = Math.max(20, ...timeline.map(p => Math.abs(p.spv))) * 1.2;

    const scaleX = (t: number) => pad.left + (t / maxTime) * plotW;
    const scaleY = (spv: number) => pad.top + plotH / 2 - (spv / maxSPV) * (plotH / 2);

    // Build SVG path
    const pathD = timeline
        .map((p, i) => `${i === 0 ? 'M' : 'L'}${scaleX(p.time).toFixed(1)},${scaleY(p.spv).toFixed(1)}`)
        .join(' ');

    // Reference lines at ±6°/s
    const refY_pos = scaleY(6);
    const refY_neg = scaleY(-6);
    const zeroY = scaleY(0);

    // Time ticks
    const timeStep = maxTime > 60 ? 30 : maxTime > 20 ? 10 : 5;
    const timeTicks: number[] = [];
    for (let t = 0; t <= maxTime; t += timeStep) timeTicks.push(t);

    // SPV ticks
    const spvStep = maxSPV > 30 ? 10 : 5;
    const spvTicks: number[] = [];
    for (let v = -Math.floor(maxSPV / spvStep) * spvStep; v <= maxSPV; v += spvStep) spvTicks.push(v);

    return (
        <div className="my-3">
            <h4 className="text-xs font-medium text-gray-600 mb-1">Timeline de VCL (SPV)</h4>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 170 }}>
                <rect x={pad.left} y={pad.top} width={plotW} height={plotH} fill="white" stroke="#e5e7eb" />

                {/* Grid */}
                {spvTicks.map(v => (
                    <g key={`sv-${v}`}>
                        <line x1={pad.left} y1={scaleY(v)} x2={pad.left + plotW} y2={scaleY(v)}
                            stroke="#f3f4f6" strokeWidth="0.5" />
                        <text x={pad.left - 5} y={scaleY(v) + 3} fill="#6b7280" fontSize="7" textAnchor="end">
                            {v}
                        </text>
                    </g>
                ))}
                {timeTicks.map(t => (
                    <g key={`tt-${t}`}>
                        <line x1={scaleX(t)} y1={pad.top} x2={scaleX(t)} y2={pad.top + plotH}
                            stroke="#f3f4f6" strokeWidth="0.5" />
                        <text x={scaleX(t)} y={pad.top + plotH + 12} fill="#6b7280" fontSize="7" textAnchor="middle">
                            {t}s
                        </text>
                    </g>
                ))}

                {/* Zero line */}
                <line x1={pad.left} y1={zeroY} x2={pad.left + plotW} y2={zeroY}
                    stroke="#9ca3af" strokeWidth="0.5" />

                {/* Reference lines ±6°/s */}
                <line x1={pad.left} y1={refY_pos} x2={pad.left + plotW} y2={refY_pos}
                    stroke="#f59e0b" strokeWidth="0.8" strokeDasharray="4,3" />
                <line x1={pad.left} y1={refY_neg} x2={pad.left + plotW} y2={refY_neg}
                    stroke="#f59e0b" strokeWidth="0.8" strokeDasharray="4,3" />
                <text x={pad.left + plotW + 2} y={refY_pos + 3} fill="#f59e0b" fontSize="6">+6°/s</text>
                <text x={pad.left + plotW + 2} y={refY_neg + 3} fill="#f59e0b" fontSize="6">-6°/s</text>

                {/* SPV curve */}
                <path d={pathD} fill="none" stroke="#3b82f6" strokeWidth="1.5" />

                {/* Axes */}
                <line x1={pad.left} y1={pad.top + plotH} x2={pad.left + plotW} y2={pad.top + plotH} stroke="#374151" strokeWidth="1" />
                <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} stroke="#374151" strokeWidth="1" />

                {/* Labels */}
                <text x={pad.left + plotW / 2} y={H - 5} fill="#374151" fontSize="8" textAnchor="middle">
                    Tiempo (s)
                </text>
                <text x={10} y={pad.top + plotH / 2} fill="#374151" fontSize="8" textAnchor="middle"
                    transform={`rotate(-90, 10, ${pad.top + plotH / 2})`}>
                    SPV (°/s)
                </text>

                {/* Overall SPV badge */}
                <rect x={pad.left + 5} y={pad.top + 3} width={85} height={16} rx={3} fill="#eff6ff" stroke="#93c5fd" strokeWidth="0.5" />
                <text x={pad.left + 48} y={pad.top + 14} fill="#1d4ed8" fontSize="8" textAnchor="middle">
                    SPV prom: {overallSPV.toFixed(1)}°/s
                </text>
            </svg>
        </div>
    );
};
