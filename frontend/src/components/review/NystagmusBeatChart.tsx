import { useMemo, useEffect, useRef, useCallback, type MutableRefObject } from 'react'
import uPlot from 'uplot'
import type { NystagmusBeatMarker } from '../../types/review'
import UPlotChart from '../charts/UPlotChart'
import { DARK_THEME, darkAxis, darkXAxis } from '../charts/uplot-theme'

interface NystagmusBeatChartProps {
    beats: NystagmusBeatMarker[]
    currentTime: number
    currentTimeRef: MutableRefObject<number>
    onSeek: (time: number) => void
}

export default function NystagmusBeatChart({ beats, currentTime, currentTimeRef: _, onSeek }: NystagmusBeatChartProps) {
    const chartInstanceRef = useRef<uPlot | null>(null)
    const currentTimeInternalRef = useRef(currentTime)
    currentTimeInternalRef.current = currentTime

    const beatsRef = useRef(beats)
    beatsRef.current = beats

    const stats = useMemo(() => {
        if (beats.length === 0) return null
        const spvs = beats.map(b => Math.abs(b.spv))
        const rightCount = beats.filter(b => b.direction === 'right').length
        const leftCount = beats.filter(b => b.direction === 'left').length
        const dominantDir = rightCount >= leftCount ? 'Der' : 'Izq'
        return {
            count: beats.length,
            avgSPV: spvs.reduce((a, b) => a + b, 0) / spvs.length,
            avgAmplitude: beats.map(b => b.amplitude).reduce((a, b) => a + b, 0) / beats.length,
            dominantDir,
        }
    }, [beats])

    const maxTime = useMemo(() => {
        return beats.length > 0 ? Math.max(...beats.map(b => b.fast_end)) * 1.1 : 10
    }, [beats])

    const maxBeat = useMemo(() => Math.min(beats.length + 1, 30), [beats.length])

    // We need a dummy series so uPlot creates the axes/scales
    const uplotData = useMemo<uPlot.AlignedData>(() => {
        // Minimal data just to define the x range
        return [[0, maxTime], [0, 0]] as uPlot.AlignedData
    }, [maxTime])

    // Redraw when currentTime changes
    useEffect(() => {
        const u = chartInstanceRef.current
        if (u) u.redraw(false, false)
    }, [currentTime])

    // Redraw when beats change (the draw hook reads from ref)
    useEffect(() => {
        const u = chartInstanceRef.current
        if (u) u.redraw()
    }, [beats])

    const onCreateChart = useCallback((u: uPlot) => {
        chartInstanceRef.current = u

        // Click-to-seek
        u.over.addEventListener('click', (e) => {
            const left = e.clientX - u.over.getBoundingClientRect().left
            const timeVal = u.posToVal(left, 'x')
            if (isFinite(timeVal)) onSeek(timeVal)
        })

        // Double-click to reset zoom
        u.over.addEventListener('dblclick', () => {
            u.setScale('x', { min: u.data[0][0], max: u.data[0][u.data[0].length - 1] })
        })
    }, [onSeek])

    const options = useMemo((): Omit<uPlot.Options, 'width' | 'height'> => ({
        cursor: {
            drag: { x: true, y: false, setScale: true },
            show: true,
            y: false,
        },
        select: { show: false, left: 0, top: 0, width: 0, height: 0 },
        legend: { show: false },
        padding: [8, 10, 0, 0],
        hooks: {
            draw: [
                (u: uPlot) => {
                    const ctx = u.ctx
                    const { left, top, width, height } = u.bbox

                    ctx.save()

                    // Draw beat rectangles
                    for (let i = 0; i < beatsRef.current.length; i++) {
                        const b = beatsRef.current[i]

                        // Slow phase (cyan)
                        const sx0 = u.valToPos(b.slow_start, 'x', true)
                        const sx1 = u.valToPos(b.slow_end, 'x', true)
                        const sy0 = u.valToPos(i, 'y', true)
                        const sy1 = u.valToPos(i + 0.8, 'y', true)

                        ctx.fillStyle = DARK_THEME.colors.slowPhase
                        ctx.fillRect(sx0, sy0, sx1 - sx0, sy1 - sy0)

                        // Fast phase (rose)
                        const fx0 = u.valToPos(b.slow_end, 'x', true)
                        const fx1 = u.valToPos(b.fast_end, 'x', true)

                        ctx.fillStyle = DARK_THEME.colors.fastPhase
                        ctx.fillRect(fx0, sy0, Math.max(fx1 - fx0, 2), sy1 - sy0)
                    }

                    // Time cursor line
                    const cursorX = u.valToPos(currentTimeInternalRef.current, 'x', true)
                    if (cursorX >= left && cursorX <= left + width) {
                        ctx.strokeStyle = DARK_THEME.colors.cursor
                        ctx.lineWidth = 1
                        ctx.beginPath()
                        ctx.moveTo(cursorX, top)
                        ctx.lineTo(cursorX, top + height)
                        ctx.stroke()
                    }

                    ctx.restore()
                }
            ],
        },
        axes: [
            darkXAxis('Tiempo (s)'),
            {
                ...darkAxis('Batido #'),
                values: (_u: uPlot, vals: number[]) => vals.map(v => Math.floor(v).toString()),
            },
        ],
        scales: {
            x: { auto: false, min: 0, max: maxTime, time: false },
            y: { auto: false, min: 0, max: maxBeat },
        },
        series: [
            {},
            {
                label: '_dummy',
                stroke: 'transparent',
                points: { show: false },
                show: false,
            },
        ],
    }), [maxTime, maxBeat])

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-dark-300">Batidos de Nistagmo</span>
                <div className="flex items-center gap-3 text-[10px] text-dark-500">
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-cyan-500/40 inline-block rounded-sm" /> Fase Lenta
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-rose-500/50 inline-block rounded-sm" /> Fase Rapida
                    </span>
                </div>
            </div>
            <div style={{ height: 250 }}>
                <UPlotChart
                    options={options}
                    data={uplotData}
                    onCreate={onCreateChart}
                />
            </div>
            {stats && (
                <div className="px-3 py-1.5 border-t border-dark-800 flex items-center gap-4 text-[10px] text-dark-500">
                    <span>Batidos: <span className="text-dark-300">{stats.count}</span></span>
                    <span>SPV medio: <span className="text-dark-300">{stats.avgSPV.toFixed(1)}°/s</span></span>
                    <span>Amp. media: <span className="text-dark-300">{stats.avgAmplitude.toFixed(1)}°</span></span>
                    <span>Dir: <span className="text-dark-300">{stats.dominantDir}</span></span>
                </div>
            )}
        </div>
    )
}
