import { useMemo, useRef, useCallback } from 'react'
import uPlot from 'uplot'
import type { SaccadeMarker } from '../../types/review'
import UPlotChart from '../charts/UPlotChart'
import { DARK_THEME, darkAxis } from '../charts/uplot-theme'

interface SaccadeAnalysisChartProps {
    saccades: SaccadeMarker[]
    onSeek: (time: number) => void
}

// Custom points renderer for scatter dots
function scatterPoints(color: string, size: number): uPlot.Series.Points {
    return {
        show: true,
        size,
        fill: color,
        stroke: color,
    }
}

export default function SaccadeAnalysisChart({ saccades, onSeek }: SaccadeAnalysisChartProps) {
    const chartInstanceRef = useRef<uPlot | null>(null)

    // Keep saccades accessible for click handler
    const saccadesRef = useRef(saccades)
    saccadesRef.current = saccades

    const stats = useMemo(() => {
        if (saccades.length === 0) return null
        const amplitudes = saccades.map(s => s.amplitude)
        const velocities = saccades.map(s => s.peak_velocity)
        return {
            count: saccades.length,
            avgAmplitude: amplitudes.reduce((a, b) => a + b, 0) / amplitudes.length,
            avgVelocity: velocities.reduce((a, b) => a + b, 0) / velocities.length,
            leftCount: saccades.filter(s => s.direction === 'left').length,
            rightCount: saccades.filter(s => s.direction === 'right').length,
        }
    }, [saccades])

    // Build aligned data: [amplitudes_all, vel_right, vel_left]
    // uPlot scatter needs aligned x values, so we use amplitude as x
    const uplotData = useMemo<uPlot.AlignedData>(() => {
        if (saccades.length === 0) return [[], [], []] as unknown as uPlot.AlignedData

        // Separate right and left saccades
        const right = saccades.filter(s => s.direction === 'right')
        const left = saccades.filter(s => s.direction === 'left')

        // Combine all amplitudes as x-axis, sorted
        const allAmplitudes: number[] = []
        const rightVel: (number | null)[] = []
        const leftVel: (number | null)[] = []

        // Right points first
        for (const s of right) {
            allAmplitudes.push(s.amplitude)
            rightVel.push(s.peak_velocity)
            leftVel.push(null)
        }
        // Then left points
        for (const s of left) {
            allAmplitudes.push(s.amplitude)
            rightVel.push(null)
            leftVel.push(s.peak_velocity)
        }

        // Sort by amplitude for uPlot (x must be ascending)
        const indices = Array.from({ length: allAmplitudes.length }, (_, i) => i)
        indices.sort((a, b) => allAmplitudes[a] - allAmplitudes[b])

        const sortedAmp = indices.map(i => allAmplitudes[i])
        const sortedRight = indices.map(i => rightVel[i])
        const sortedLeft = indices.map(i => leftVel[i])

        return [sortedAmp, sortedRight, sortedLeft]
    }, [saccades])

    const onCreateChart = useCallback((u: uPlot) => {
        chartInstanceRef.current = u

        // Click on point → seek to saccade start_time
        u.over.addEventListener('click', (e) => {
            const left = e.clientX - u.over.getBoundingClientRect().left
            const top = e.clientY - u.over.getBoundingClientRect().top
            const ampVal = u.posToVal(left, 'x')
            const velVal = u.posToVal(top, 'y')

            // Find closest saccade
            let minDist = Infinity
            let closest: SaccadeMarker | null = null
            for (const s of saccadesRef.current) {
                const dx = s.amplitude - ampVal
                const dy = s.peak_velocity - velVal
                const dist = dx * dx + dy * dy
                if (dist < minDist) {
                    minDist = dist
                    closest = s
                }
            }

            if (closest) {
                onSeek(closest.start_time)
            }
        })
    }, [onSeek])

    const options = useMemo((): Omit<uPlot.Options, 'width' | 'height'> => ({
        cursor: {
            show: true,
            y: false,
        },
        select: { show: false, left: 0, top: 0, width: 0, height: 0 },
        legend: { show: false },
        padding: [8, 10, 0, 0],
        axes: [
            {
                ...darkAxis('Amplitud (°)'),
                values: (_u: uPlot, vals: number[]) => vals.map(v => v.toFixed(1)),
            },
            darkAxis('Vel. Pico (°/s)'),
        ],
        scales: {
            x: { auto: true, time: false },
            y: { auto: true },
        },
        series: [
            {},
            {
                label: 'Derecha',
                stroke: DARK_THEME.colors.od,
                fill: DARK_THEME.colors.od,
                width: 0,
                paths: () => null,
                points: scatterPoints(DARK_THEME.colors.od, 6),
            },
            {
                label: 'Izquierda',
                stroke: DARK_THEME.colors.oi,
                fill: DARK_THEME.colors.oi,
                width: 0,
                paths: () => null,
                points: scatterPoints(DARK_THEME.colors.oi, 6),
            },
        ],
    }), [])

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-dark-300">Analisis de Sacadas (Main Sequence)</span>
                <span className="text-[10px] text-dark-500">
                    {stats ? `${stats.count} sacadas` : 'Sin datos'}
                </span>
            </div>
            <div style={{ height: 220 }}>
                <UPlotChart
                    options={options}
                    data={uplotData}
                    onCreate={onCreateChart}
                />
            </div>
            {stats && (
                <div className="px-3 py-1.5 border-t border-dark-800 flex items-center gap-4 text-[10px] text-dark-500">
                    <span>Amp. media: <span className="text-dark-300">{stats.avgAmplitude.toFixed(1)}°</span></span>
                    <span>Vel. media: <span className="text-dark-300">{stats.avgVelocity.toFixed(0)}°/s</span></span>
                    <span className="text-rose-400">D:{stats.rightCount}</span>
                    <span className="text-cyan-400">I:{stats.leftCount}</span>
                </div>
            )}
        </div>
    )
}
