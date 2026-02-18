import { useMemo, useEffect, useRef, useCallback, type MutableRefObject } from 'react'
import uPlot from 'uplot'
import type { SPVTimePoint } from '../../types/review'
import UPlotChart from '../charts/UPlotChart'
import { DARK_THEME, darkAxis, darkXAxis } from '../charts/uplot-theme'

interface SPVChartProps {
    data: SPVTimePoint[]
    currentTime: number
    currentTimeRef: MutableRefObject<number>
    overallSPV: number
    onSeek: (time: number) => void
    zoomRange: [number, number] | null
    onZoomChange: (range: [number, number]) => void
}

export default function SPVChart({ data, currentTime, currentTimeRef: _, overallSPV, onSeek, zoomRange, onZoomChange }: SPVChartProps) {
    const chartInstanceRef = useRef<uPlot | null>(null)
    const currentTimeInternalRef = useRef(currentTime)
    currentTimeInternalRef.current = currentTime

    const uplotData = useMemo<uPlot.AlignedData>(() => {
        if (data.length === 0) return [[], []] as unknown as uPlot.AlignedData
        const timestamps = data.map(d => d.time)
        const spvValues = data.map(d => d.spv)
        return [timestamps, spvValues]
    }, [data])

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

                    // Reference lines ±6°/s
                    const y6 = u.valToPos(6, 'y', true)
                    const yNeg6 = u.valToPos(-6, 'y', true)

                    ctx.strokeStyle = DARK_THEME.colors.reference
                    ctx.lineWidth = 1
                    ctx.setLineDash([6, 4])

                    // +6°/s line
                    if (y6 >= top && y6 <= top + height) {
                        ctx.beginPath()
                        ctx.moveTo(left, y6)
                        ctx.lineTo(left + width, y6)
                        ctx.stroke()

                        // Label
                        ctx.fillStyle = DARK_THEME.colors.reference
                        ctx.font = '9px system-ui'
                        ctx.textAlign = 'right'
                        ctx.fillText('6°/s', left + width - 4, y6 - 3)
                    }

                    // -6°/s line
                    if (yNeg6 >= top && yNeg6 <= top + height) {
                        ctx.beginPath()
                        ctx.moveTo(left, yNeg6)
                        ctx.lineTo(left + width, yNeg6)
                        ctx.stroke()
                    }

                    ctx.setLineDash([])

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
            darkAxis('SPV (°/s)'),
        ],
        scales: {
            x: { auto: true, time: false },
            y: { auto: true },
        },
        series: [
            {},
            {
                label: 'SPV',
                stroke: DARK_THEME.colors.spv,
                width: 1.5,
                fill: 'rgba(167, 139, 250, 0.08)',
                points: { show: false },
            },
        ],
    }), [onZoomChange])

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-dark-300">SPV en Tiempo</span>
                <span className="text-[10px] text-dark-500">
                    Promedio: <span className="text-purple-400 font-medium">{overallSPV.toFixed(1)}°/s</span>
                </span>
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
