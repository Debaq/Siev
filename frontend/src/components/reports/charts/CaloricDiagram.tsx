import React from 'react';
import { CaloricTestResult } from '../../../types/vng';

interface CaloricDiagramProps {
    data: CaloricTestResult;
    style: 'claussen' | 'freyss' | 'butterfly';
}

export const CaloricDiagram: React.FC<CaloricDiagramProps> = ({ data, style }) => {
    const { irrigations, jongkees } = data;
    const { right_warm, right_cool, left_warm, left_cool } = irrigations;

    // Normalize values for display (max 60°/s typical)
    const maxSPV = 60;
    const normalize = (v: number) => Math.min((v / maxSPV) * 100, 100);

    if (style === 'claussen') {
        return <ClaussenDiagram
            rw={normalize(right_warm.spv_max)}
            rc={normalize(right_cool.spv_max)}
            lw={normalize(left_warm.spv_max)}
            lc={normalize(left_cool.spv_max)}
            uwPercent={jongkees.unilateral_weakness_percent}
            dpPercent={jongkees.directional_preponderance_percent}
        />;
    }

    if (style === 'freyss') {
        return <FreyssDiagram
            rw={right_warm.spv_max}
            rc={right_cool.spv_max}
            lw={left_warm.spv_max}
            lc={left_cool.spv_max}
        />;
    }

    return <ButterflyDiagram
        rightWarm={right_warm.spv_timeline}
        rightCool={right_cool.spv_timeline}
        leftWarm={left_warm.spv_timeline}
        leftCool={left_cool.spv_timeline}
    />;
};

// Claussen (Traditional quadrant diagram)
const ClaussenDiagram: React.FC<{
    rw: number; rc: number; lw: number; lc: number;
    uwPercent: number; dpPercent: number;
}> = ({ rw, rc, lw, lc, uwPercent, dpPercent }) => {
    const size = 200;
    const center = size / 2;
    const scale = 0.8;

    return (
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-xs mx-auto">
            {/* Grid */}
            <line x1="0" y1={center} x2={size} y2={center} stroke="#e5e7eb" strokeWidth="1" />
            <line x1={center} y1="0" x2={center} y2={size} stroke="#e5e7eb" strokeWidth="1" />

            {/* Labels */}
            <text x={center - 40} y="15" className="text-[10px]" fill="#6b7280">OD FRÍA</text>
            <text x={center + 5} y="15" className="text-[10px]" fill="#6b7280">OI FRÍA</text>
            <text x={center - 50} y={size - 5} className="text-[10px]" fill="#6b7280">OD CALIENTE</text>
            <text x={center + 5} y={size - 5} className="text-[10px]" fill="#6b7280">OI CALIENTE</text>

            {/* Bars - positioned in quadrants */}
            {/* RC (Right Cool) - Top Left */}
            <rect
                x={center - 35}
                y={center - (rc * scale)}
                width="30"
                height={rc * scale}
                fill="#3b82f6"
                opacity="0.8"
            />

            {/* LC (Left Cool) - Top Right */}
            <rect
                x={center + 5}
                y={center - (lc * scale)}
                width="30"
                height={lc * scale}
                fill="#3b82f6"
                opacity="0.8"
            />

            {/* RW (Right Warm) - Bottom Left */}
            <rect
                x={center - 35}
                y={center}
                width="30"
                height={rw * scale}
                fill="#ef4444"
                opacity="0.8"
            />

            {/* LW (Left Warm) - Bottom Right */}
            <rect
                x={center + 5}
                y={center}
                width="30"
                height={lw * scale}
                fill="#ef4444"
                opacity="0.8"
            />

            {/* UW/DP indicators */}
            <text x="5" y={center + 4} className="text-[9px]" fill="#6b7280">
                UW: {uwPercent > 0 ? '+' : ''}{uwPercent.toFixed(0)}%
            </text>
            <text x={size - 50} y={center + 4} className="text-[9px]" fill="#6b7280">
                DP: {dpPercent > 0 ? '+' : ''}{dpPercent.toFixed(0)}%
            </text>

            {/* Legend */}
            <rect x="5" y={size - 25} width="10" height="10" fill="#ef4444" opacity="0.8" />
            <text x="18" y={size - 17} className="text-[8px]" fill="#6b7280">Caliente</text>
            <rect x="55" y={size - 25} width="10" height="10" fill="#3b82f6" opacity="0.8" />
            <text x="68" y={size - 17} className="text-[8px]" fill="#6b7280">Fría</text>
        </svg>
    );
};

// Freyss (Vector diagram)
const FreyssDiagram: React.FC<{
    rw: number; rc: number; lw: number; lc: number;
}> = ({ rw, rc, lw, lc }) => {
    const size = 200;
    const center = size / 2;
    const maxRadius = 80;

    // Calculate vectors
    const rightTotal = rw + rc;
    const leftTotal = lw + lc;
    const maxTotal = Math.max(rightTotal, leftTotal, 1);

    const rightRadius = (rightTotal / maxTotal) * maxRadius;
    const leftRadius = (leftTotal / maxTotal) * maxRadius;

    // Right ear at 45°, Left ear at 135°
    const rightAngle = -45 * (Math.PI / 180);
    const leftAngle = -135 * (Math.PI / 180);

    const rightX = center + rightRadius * Math.cos(rightAngle);
    const rightY = center + rightRadius * Math.sin(rightAngle);
    const leftX = center + leftRadius * Math.cos(leftAngle);
    const leftY = center + leftRadius * Math.sin(leftAngle);

    return (
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-xs mx-auto">
            {/* Circles */}
            <circle cx={center} cy={center} r={maxRadius} fill="none" stroke="#e5e7eb" strokeWidth="1" />
            <circle cx={center} cy={center} r={maxRadius * 0.5} fill="none" stroke="#e5e7eb" strokeWidth="0.5" strokeDasharray="4,4" />

            {/* Axes */}
            <line x1={center} y1="10" x2={center} y2={size - 10} stroke="#e5e7eb" strokeWidth="0.5" />
            <line x1="10" y1={center} x2={size - 10} y2={center} stroke="#e5e7eb" strokeWidth="0.5" />

            {/* Vectors */}
            <line x1={center} y1={center} x2={rightX} y2={rightY} stroke="#10b981" strokeWidth="3" markerEnd="url(#arrowhead)" />
            <line x1={center} y1={center} x2={leftX} y2={leftY} stroke="#f59e0b" strokeWidth="3" markerEnd="url(#arrowhead)" />

            {/* Arrow marker */}
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#374151" />
                </marker>
            </defs>

            {/* Labels */}
            <text x={rightX + 5} y={rightY - 5} className="text-[9px]" fill="#10b981">OD</text>
            <text x={leftX - 15} y={leftY - 5} className="text-[9px]" fill="#f59e0b">OI</text>

            {/* Values */}
            <text x={center - 30} y={size - 10} className="text-[8px]" fill="#6b7280">
                OD: {(rw + rc).toFixed(0)}°/s | OI: {(lw + lc).toFixed(0)}°/s
            </text>
        </svg>
    );
};

// Butterfly (Timeline diagram)
const ButterflyDiagram: React.FC<{
    rightWarm: { time_seconds: number; spv: number }[];
    rightCool: { time_seconds: number; spv: number }[];
    leftWarm: { time_seconds: number; spv: number }[];
    leftCool: { time_seconds: number; spv: number }[];
}> = ({ rightWarm, rightCool, leftWarm, leftCool }) => {
    const width = 300;
    const height = 150;
    const padding = { top: 20, bottom: 30, left: 40, right: 20 };
    const graphWidth = width - padding.left - padding.right;
    const graphHeight = height - padding.top - padding.bottom;

    // Generate sample data if empty
    const generateSampleData = (peak: number, offset: number = 0) => {
        const data = [];
        for (let t = 0; t <= 180; t += 10) {
            const normalizedT = (t - 60) / 30;
            const spv = peak * Math.exp(-normalizedT * normalizedT / 2) + offset;
            data.push({ time_seconds: t, spv: Math.max(0, spv) });
        }
        return data;
    };

    const rwData = rightWarm.length > 2 ? rightWarm : generateSampleData(25, 2);
    const rcData = rightCool.length > 2 ? rightCool : generateSampleData(20, 1);
    const lwData = leftWarm.length > 2 ? leftWarm : generateSampleData(23, 2);
    const lcData = leftCool.length > 2 ? leftCool : generateSampleData(18, 1);

    const maxTime = 180;
    const maxSPV = Math.max(
        ...rwData.map(d => d.spv),
        ...rcData.map(d => d.spv),
        ...lwData.map(d => d.spv),
        ...lcData.map(d => d.spv),
        40
    );

    const scaleX = (t: number) => padding.left + (t / maxTime) * graphWidth;
    const scaleY = (spv: number) => padding.top + graphHeight - (spv / maxSPV) * graphHeight;

    const pathFromData = (data: { time_seconds: number; spv: number }[]) => {
        if (data.length === 0) return '';
        return data.map((d, i) =>
            `${i === 0 ? 'M' : 'L'} ${scaleX(d.time_seconds)} ${scaleY(d.spv)}`
        ).join(' ');
    };

    return (
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
            {/* Grid */}
            {[0, 60, 120, 180].map(t => (
                <line key={t} x1={scaleX(t)} y1={padding.top} x2={scaleX(t)} y2={height - padding.bottom} stroke="#e5e7eb" strokeWidth="0.5" />
            ))}
            {[0, maxSPV / 2, maxSPV].map(spv => (
                <line key={spv} x1={padding.left} y1={scaleY(spv)} x2={width - padding.right} y2={scaleY(spv)} stroke="#e5e7eb" strokeWidth="0.5" />
            ))}

            {/* Axes labels */}
            <text x={width / 2} y={height - 5} className="text-[8px]" fill="#6b7280" textAnchor="middle">Tiempo (s)</text>
            <text x="10" y={height / 2} className="text-[8px]" fill="#6b7280" textAnchor="middle" transform={`rotate(-90, 10, ${height / 2})`}>SPV (°/s)</text>

            {/* Data lines */}
            <path d={pathFromData(rwData)} fill="none" stroke="#ef4444" strokeWidth="2" />
            <path d={pathFromData(rcData)} fill="none" stroke="#3b82f6" strokeWidth="2" />
            <path d={pathFromData(lwData)} fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="4,2" />
            <path d={pathFromData(lcData)} fill="none" stroke="#06b6d4" strokeWidth="2" strokeDasharray="4,2" />

            {/* Legend */}
            <g transform={`translate(${padding.left}, ${height - 15})`}>
                <line x1="0" y1="0" x2="15" y2="0" stroke="#ef4444" strokeWidth="2" />
                <text x="18" y="3" className="text-[7px]" fill="#6b7280">OD Cal</text>
                <line x1="50" y1="0" x2="65" y2="0" stroke="#3b82f6" strokeWidth="2" />
                <text x="68" y="3" className="text-[7px]" fill="#6b7280">OD Fría</text>
                <line x1="105" y1="0" x2="120" y2="0" stroke="#f97316" strokeWidth="2" strokeDasharray="4,2" />
                <text x="123" y="3" className="text-[7px]" fill="#6b7280">OI Cal</text>
                <line x1="155" y1="0" x2="170" y2="0" stroke="#06b6d4" strokeWidth="2" strokeDasharray="4,2" />
                <text x="173" y="3" className="text-[7px]" fill="#6b7280">OI Fría</text>
            </g>
        </svg>
    );
};
