import { useMemo, useEffect, useRef, type MutableRefObject } from 'react'
import ReactECharts from 'echarts-for-react'
import type { ChartEyeDataPoint, SaccadeMarker } from '../../types/review'

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
    currentTimeRef,
    axis,
    onSeek,
    zoomRange,
    onZoomChange,
}: EyePositionChartProps) {
    const title = axis === 'horizontal' ? 'Posicion X (Horizontal)' : 'Posicion Y (Vertical)'
    const chartRef = useRef<ReactECharts>(null)

    const option = useMemo(() => {
        const rightData = data.map(d => [d.t, axis === 'horizontal' ? d.rx : d.ry])
        const leftData = data.map(d => [d.t, axis === 'horizontal' ? d.lx : d.ly])

        // Saccade markAreas
        const markAreaData = saccades.map(s => ([
            { xAxis: s.start_time },
            { xAxis: s.end_time },
        ]))

        // Deflection point markers (diamonds on the signal)
        const deflectionData = deflectionPoints.map(([t, pos]) => [t, pos])

        const dataZoomStart = zoomRange ? (zoomRange[0] / (data[data.length - 1]?.t || 1)) * 100 : 0
        const dataZoomEnd = zoomRange ? (zoomRange[1] / (data[data.length - 1]?.t || 1)) * 100 : 100

        const series: any[] = [
            {
                name: 'OD',
                type: 'line',
                data: rightData,
                symbol: 'none',
                lineStyle: { color: '#f43f5e', width: 1.2 },
                itemStyle: { color: '#f43f5e' },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    lineStyle: { color: '#0ea5e9', width: 1, type: 'solid' },
                    data: [{ xAxis: currentTimeRef.current }],
                    label: { show: false },
                },
                markArea: axis === 'horizontal' ? {
                    silent: true,
                    itemStyle: { color: 'rgba(251, 191, 36, 0.08)' },
                    data: markAreaData,
                } : undefined,
            },
            {
                name: 'OI',
                type: 'line',
                data: leftData,
                symbol: 'none',
                lineStyle: { color: '#0ea5e9', width: 1.2 },
                itemStyle: { color: '#0ea5e9' },
            },
        ]

        // Add deflection points as scatter series (only for horizontal)
        if (deflectionData.length > 0 && axis === 'horizontal') {
            series.push({
                name: 'Deflexiones',
                type: 'scatter',
                data: deflectionData,
                symbol: 'diamond',
                symbolSize: 6,
                itemStyle: { color: '#fbbf24', borderColor: '#f59e0b', borderWidth: 1 },
                z: 10,
            })
        }

        return {
            backgroundColor: 'transparent',
            grid: { left: 50, right: 20, top: 30, bottom: 50 },
            xAxis: {
                type: 'value',
                name: 'Tiempo (s)',
                nameTextStyle: { color: '#6b7280', fontSize: 10 },
                axisLine: { lineStyle: { color: '#374151' } },
                axisTick: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 10 },
                splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
            },
            yAxis: {
                type: 'value',
                name: 'Grados',
                nameTextStyle: { color: '#6b7280', fontSize: 10 },
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 10 },
                splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: '#1f2937',
                borderColor: '#374151',
                textStyle: { color: '#e5e7eb', fontSize: 11 },
                formatter: (params: any) => {
                    const t = params[0]?.value?.[0]?.toFixed(2) ?? '?'
                    const lines = params
                        .filter((p: any) => p.seriesName !== 'Deflexiones')
                        .map((p: any) =>
                            `<span style="color:${p.color}">${p.seriesName}</span>: ${p.value?.[1]?.toFixed(2) ?? '-'}°`
                        ).join('<br/>')
                    return `${t}s<br/>${lines}`
                },
            },
            dataZoom: [
                {
                    type: 'inside',
                    start: dataZoomStart,
                    end: dataZoomEnd,
                },
                {
                    type: 'slider',
                    height: 15,
                    bottom: 5,
                    start: dataZoomStart,
                    end: dataZoomEnd,
                    borderColor: '#374151',
                    backgroundColor: '#111827',
                    fillerColor: 'rgba(14, 165, 233, 0.1)',
                    handleStyle: { color: '#0ea5e9' },
                    textStyle: { color: '#9ca3af', fontSize: 9 },
                },
            ],
            series,
        }
    }, [data, saccades, deflectionPoints, axis, zoomRange])

    // Imperatively update markLine cursor without re-rendering the full chart
    useEffect(() => {
        const instance = chartRef.current?.getEchartsInstance()
        if (!instance) return
        instance.setOption({
            series: [{
                markLine: {
                    silent: true,
                    symbol: 'none',
                    lineStyle: { color: '#0ea5e9', width: 1, type: 'solid' },
                    data: [{ xAxis: currentTime }],
                    label: { show: false },
                },
            }, {}],
        })
    }, [currentTime])

    // Click-to-seek anywhere on the chart grid via zrender
    useEffect(() => {
        const instance = chartRef.current?.getEchartsInstance()
        if (!instance) return
        const zr = instance.getZr()
        const handler = (e: any) => {
            const pointInPixel = [e.offsetX, e.offsetY]
            if (instance.containPixel('grid', pointInPixel)) {
                const coordX = instance.convertFromPixel({ seriesIndex: 0 }, pointInPixel)[0]
                if (typeof coordX === 'number' && isFinite(coordX)) {
                    onSeek(coordX)
                }
            }
        }
        zr.on('click', handler)
        return () => { zr.off('click', handler) }
    }, [onSeek])

    const onEvents = useMemo(() => ({
        datazoom: (params: any) => {
            if (data.length === 0) return
            const maxT = data[data.length - 1].t
            const start = (params.start ?? params.batch?.[0]?.start ?? 0) / 100 * maxT
            const end = (params.end ?? params.batch?.[0]?.end ?? 100) / 100 * maxT
            onZoomChange([start, end])
        },
    }), [data, onZoomChange])

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
            <ReactECharts
                ref={chartRef}
                option={option}
                style={{ height: 250 }}
                opts={{ renderer: 'canvas' }}
                onEvents={onEvents}
            />
        </div>
    )
}
