import { useMemo, useEffect, useRef, useCallback, type MutableRefObject } from 'react'
import uPlot from 'uplot'
import type { ChartEyeDataPoint, SaccadeMarker } from '../../types/review'
import UPlotChart from '../charts/UPlotChart'
import { DARK_THEME, darkAxis, darkXAxis } from '../charts/uplot-theme'

interface EyePositionChartProps {
    data: ChartEyeDataPoint[]
    saccades: SaccadeMarker[]
    deflectionPoints: [number, number][]
    currentTime: number
    currentTimeRef: MutableRefObject<number>
    axis: 'horizontal' | 'vertical'
    onSeek: (time: number) => void
    zoomRange: [number, number] | null
    onZoomChange: (range: [number, number]) => void
}

export default function EyePositionChart({
    data,
    saccades,
    deflectionPoints,
    currentTime,
    currentTimeRef: _,
    axis,
    onSeek,
    zoomRange,
    onZoomChange,
}: EyePositionChartProps) {
    const title = axis === 'horizontal' ? 'Posicion X (Horizontal)' : 'Posicion Y (Vertical)'
    const chartInstanceRef = useRef<uPlot | null>(null)
    const currentTimeInternalRef = useRef(currentTime)
    currentTimeInternalRef.current = currentTime

    // Refs for draw hook data (avoid options recreation)
    const saccadesRef = useRef(saccades)
    saccadesRef.current = saccades
    const deflectionPointsRef = useRef(deflectionPoints)
    deflectionPointsRef.current = deflectionPoints
    const axisRef = useRef(axis)
    axisRef.current = axis

    const uplotData = useMemo<uPlot.AlignedData>(() => {
        if (data.length === 0) return [[], [], []] as unknown as uPlot.AlignedData
        const timestamps = data.map(d => d.t)
        const rightData = data.map(d => axis === 'horizontal' ? d.rx : d.ry)
        const leftData = data.map(d => axis === 'horizontal' ? d.lx : d.ly)
        return [timestamps, rightData as (number | null)[], leftData as (number | null)[]]
    }, [data, axis])

    // Apply external zoom range
    useEffect(() => {
        const u = chartInstanceRef.current
        if (!u || !zoomRange) return
        u.setScale('x', { min: zoomRange[0], max: zoomRange[1] })
    }, [zoomRange])

    // Redraw cursor line when currentTime changes
    useEffect(() => {
        const u = chartInstanceRef.current
        if (u) u.redraw(false, false)
    }, [currentTime])

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
            setScale: [
                (u: uPlot, scaleKey: string) => {
                    if (scaleKey === 'x') {
                        const xMin = u.scales.x.min
                        const xMax = u.scales.x.max
                        if (xMin != null && xMax != null) {
                            onZoomChange([xMin, xMax])
                        }
                    }
                }
            ],
            draw: [
                (u: uPlot) => {
                    const ctx = u.ctx
                    const { left, top, width, height } = u.bbox

                    ctx.save()

                    // Saccade areas (horizontal only)
                    if (axisRef.current === 'horizontal') {
                        ctx.fillStyle = DARK_THEME.colors.saccadeArea
                        for (const s of saccadesRef.current) {
                            const x0 = u.valToPos(s.start_time, 'x', true)
                            const x1 = u.valToPos(s.end_time, 'x', true)
                            if (x1 > left && x0 < left + width) {
                                ctx.fillRect(
                                    Math.max(x0, left),
                                    top,
                                    Math.min(x1, left + width) - Math.max(x0, left),
                                    height,
                                )
                            }
                        }

                        // Deflection points (diamonds)
                        const dps = deflectionPointsRef.current
                        if (dps.length > 0) {
                            ctx.fillStyle = DARK_THEME.colors.deflection
                            ctx.strokeStyle = '#f59e0b'
                            ctx.lineWidth = 1
                            const size = 4
                            for (const [t, pos] of dps) {
                                const cx = u.valToPos(t, 'x', true)
                                const cy = u.valToPos(pos, 'y', true)
                                if (cx >= left && cx <= left + width) {
                                    ctx.beginPath()
                                    ctx.moveTo(cx, cy - size)
                                    ctx.lineTo(cx + size, cy)
                                    ctx.lineTo(cx, cy + size)
                                    ctx.lineTo(cx - size, cy)
                                    ctx.closePath()
                                    ctx.fill()
                                    ctx.stroke()
                                }
                            }
                        }
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
            darkAxis('Grados'),
        ],
        scales: {
            x: { auto: true, time: false },
            y: { auto: true },
        },
        series: [
            {},
            {
                label: 'OD',
                stroke: DARK_THEME.colors.od,
                width: 1.2,
                points: { show: false },
            },
            {
                label: 'OI',
                stroke: DARK_THEME.colors.oi,
                width: 1.2,
                points: { show: false },
            },
        ],
    }), [onZoomChange])

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-dark-300">{title}</span>
                <div className="flex items-center gap-3 text-[10px] text-dark-500">
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-0.5 bg-rose-500 rounded-full inline-block" /> OD
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-0.5 bg-cyan-500 rounded-full inline-block" /> OI
                    </span>
                    {deflectionPoints.length > 0 && axis === 'horizontal' && (
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 bg-amber-400 inline-block rotate-45" /> Deflexiones
                        </span>
                    )}
                </div>
            </div>
            <div style={{ height: 250 }}>
                <UPlotChart
                    options={options}
                    data={uplotData}
                    onCreate={onCreateChart}
                />
            </div>
        </div>
    )
}
