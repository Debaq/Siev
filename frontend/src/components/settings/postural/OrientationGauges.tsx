import React from 'react'

const CX = 50, CY = 50, R = 38

function polar(angleDeg: number, radius: number) {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return { x: CX + radius * Math.cos(rad), y: CY + radius * Math.sin(rad) }
}

function arcPath(startDeg: number, endDeg: number, radius: number) {
    const diff = endDeg - startDeg
    if (Math.abs(diff) < 0.5) return ''
    const s = polar(startDeg, radius)
    const e = polar(endDeg, radius)
    const large = Math.abs(diff) > 180 ? 1 : 0
    const sweep = diff > 0 ? 1 : 0
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large} ${sweep} ${e.x} ${e.y}`
}

interface GaugeConfig {
    label: string
    value: number
    color: string
    zeroAt: number     // SVG angle where value=0 sits (0=top, 90=right)
    direction: number  // 1=CW positive, -1=CCW positive
    min: number
    max: number
    tickStep: number
    majorStep: number
    target?: number    // optional target angle to show as guide marker
}

function Gauge({ label, value, color, zeroAt, direction, min, max, tickStep, majorStep, target }: GaugeConfig) {
    const svgAngle = zeroAt + direction * value
    const targetSvgAngle = target !== undefined ? zeroAt + direction * target : undefined

    // Ticks
    const ticks: React.JSX.Element[] = []
    for (let v = min; v <= max; v += tickStep) {
        const a = zeroAt + direction * v
        const isMajor = v % majorStep === 0
        const o = polar(a, R)
        const inner = polar(a, R - (isMajor ? 6 : 3))
        ticks.push(
            <line key={v} x1={o.x} y1={o.y} x2={inner.x} y2={inner.y}
                stroke={isMajor ? '#475569' : '#1e293b'} strokeWidth={isMajor ? 0.8 : 0.5} />
        )
    }

    const arc = arcPath(zeroAt, svgAngle, R - 3)
    const zeroPt = polar(zeroAt, R - 9)

    return (
        <div className="flex flex-col items-center">
            <svg viewBox="0 0 100 100" className="w-full">
                {/* Background */}
                <circle cx={CX} cy={CY} r={R} fill="#0f172a" stroke="#1e293b" strokeWidth="1.5" />

                {ticks}

                {/* Zero reference */}
                <circle cx={zeroPt.x} cy={zeroPt.y} r="1.5" fill="#334155" />

                {/* Target marker — triangle pointing inward */}
                {targetSvgAngle !== undefined && (
                    <g style={{
                        transform: `rotate(${targetSvgAngle}deg)`,
                        transformOrigin: `${CX}px ${CY}px`,
                    }}>
                        <polygon
                            points={`${CX},${CY - R - 1} ${CX - 3},${CY - R + 4} ${CX + 3},${CY - R + 4}`}
                            fill="#f59e0b" opacity="0.8"
                        />
                    </g>
                )}

                {/* Arc from zero to value */}
                {arc && (
                    <path d={arc} fill="none" stroke={color} strokeWidth="2.5"
                        strokeLinecap="round" opacity="0.4" />
                )}

                {/* Needle — uses CSS rotate for smooth transition */}
                <g style={{
                    transform: `rotate(${svgAngle}deg)`,
                    transformOrigin: `${CX}px ${CY}px`,
                    transition: 'transform 0.3s ease-out',
                }}>
                    <line x1={CX} y1={CY} x2={CX} y2={CY - R + 6}
                        stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                    <circle cx={CX} cy={CY - R + 3} r="2.5" fill={color} />
                </g>

                {/* Center */}
                <circle cx={CX} cy={CY} r="3" fill="#0f172a" stroke={color} strokeWidth="1" />
            </svg>
            <div className="flex items-center gap-1 -mt-1">
                <span className="text-[10px] font-bold tracking-wide" style={{ color }}>{label}</span>
                <span className="text-xs font-mono text-white tabular-nums">{value}°</span>
            </div>
        </div>
    )
}

interface OrientationGaugesProps {
    yaw: number
    pitch: number
    roll: number
    targetYaw?: number
    targetPitch?: number
    targetRoll?: number
    className?: string
}

export default function OrientationGauges({ yaw, pitch, roll, targetYaw, targetPitch, targetRoll, className }: OrientationGaugesProps) {
    return (
        <div className={className ?? 'grid grid-cols-3 gap-3'}>
            <Gauge label="YAW" value={yaw} color="#facc15" target={targetYaw}
                zeroAt={0} direction={1} min={-180} max={180} tickStep={15} majorStep={45} />
            <Gauge label="PITCH" value={pitch} color="#4ade80" target={targetPitch}
                zeroAt={90} direction={-1} min={-90} max={90} tickStep={15} majorStep={45} />
            <Gauge label="ROLL" value={roll} color="#60a5fa" target={targetRoll}
                zeroAt={0} direction={1} min={-180} max={180} tickStep={15} majorStep={45} />
        </div>
    )
}
