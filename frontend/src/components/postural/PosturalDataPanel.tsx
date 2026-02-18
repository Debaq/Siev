import { useRef, useEffect } from 'react'
import { CalibratedImuData } from '../../hooks/useImuData'

interface PosturalDataPanelProps {
    history: CalibratedImuData[]
}

function MiniChart({ data, color, label, unit }: { data: number[]; color: string; label: string; unit: string }) {
    const canvasRef = useRef<HTMLCanvasElement>(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas || data.length < 2) return

        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const dpr = window.devicePixelRatio || 1
        const rect = canvas.getBoundingClientRect()
        canvas.width = rect.width * dpr
        canvas.height = rect.height * dpr
        ctx.scale(dpr, dpr)
        const w = rect.width
        const h = rect.height

        ctx.clearRect(0, 0, w, h)

        // Compute range
        const min = Math.min(...data)
        const max = Math.max(...data)
        const range = max - min || 1
        const padding = range * 0.1

        const yMin = min - padding
        const yMax = max + padding
        const yRange = yMax - yMin

        // Draw zero line
        const zeroY = h - ((0 - yMin) / yRange) * h
        ctx.strokeStyle = '#334155'
        ctx.lineWidth = 0.5
        ctx.setLineDash([2, 2])
        ctx.beginPath()
        ctx.moveTo(0, zeroY)
        ctx.lineTo(w, zeroY)
        ctx.stroke()
        ctx.setLineDash([])

        // Draw data
        ctx.strokeStyle = color
        ctx.lineWidth = 1.5
        ctx.beginPath()

        const step = w / (data.length - 1)
        data.forEach((val, i) => {
            const x = i * step
            const y = h - ((val - yMin) / yRange) * h
            if (i === 0) ctx.moveTo(x, y)
            else ctx.lineTo(x, y)
        })
        ctx.stroke()
    }, [data, color])

    const lastVal = data.length > 0 ? data[data.length - 1] : 0

    return (
        <div className="flex-1 min-w-0 flex flex-col">
            <div className="flex items-center justify-between mb-0.5 px-1">
                <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color }}>{label}</span>
                <span className="text-[10px] font-mono text-dark-300 tabular-nums">
                    {lastVal.toFixed(1)}{unit}
                </span>
            </div>
            <div className="flex-1 bg-dark-800/50 rounded border border-dark-700/30 relative overflow-hidden">
                <canvas ref={canvasRef} className="w-full h-full" style={{ display: 'block' }} />
            </div>
        </div>
    )
}

export default function PosturalDataPanel({ history }: PosturalDataPanelProps) {
    const yawData = history.map(d => d.calibrated.yaw)
    const pitchData = history.map(d => d.calibrated.pitch)
    const rollData = history.map(d => d.calibrated.roll)

    if (history.length === 0) {
        return (
            <div className="h-full flex items-center justify-center text-dark-500 text-xs">
                Sin datos IMU registrados
            </div>
        )
    }

    return (
        <div className="h-full flex gap-2 p-1">
            <MiniChart data={yawData} color="#eab308" label="Yaw" unit="°" />
            <MiniChart data={pitchData} color="#22c55e" label="Pitch" unit="°" />
            <MiniChart data={rollData} color="#3b82f6" label="Roll" unit="°" />
        </div>
    )
}
