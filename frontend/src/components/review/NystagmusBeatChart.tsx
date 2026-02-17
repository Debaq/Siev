import { useMemo, useEffect, useRef, type MutableRefObject } from 'react'
import ReactECharts from 'echarts-for-react'
import type { NystagmusBeatMarker } from '../../types/review'

interface NystagmusBeatChartProps {
    beats: NystagmusBeatMarker[]
    currentTime: number
    currentTimeRef: MutableRefObject<number>
    onSeek: (time: number) => void
}

export default function NystagmusBeatChart({ beats, currentTime, currentTimeRef, onSeek }: NystagmusBeatChartProps) {
    const chartRef = useRef<ReactECharts>(null)

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

    const option = useMemo(() => {
        // Render beats as custom rectangles showing slow and fast phases
        const slowPhaseData = beats.map((b, i) => ({
            value: [b.slow_start, i, b.slow_end, i + 0.8, b.spv],
            itemStyle: { color: 'rgba(14, 165, 233, 0.4)' },
        }))

        const fastPhaseData = beats.map((b, i) => ({
            value: [b.slow_end, i, b.fast_end, i + 0.8, b.spv],
            itemStyle: { color: 'rgba(244, 63, 94, 0.5)' },
        }))

        const maxTime = beats.length > 0
            ? Math.max(...beats.map(b => b.fast_end)) * 1.1
            : 10

        return {
            backgroundColor: 'transparent',
            grid: { left: 50, right: 20, top: 25, bottom: 30 },
            xAxis: {
                type: 'value',
                name: 'Tiempo (s)',
                nameTextStyle: { color: '#6b7280', fontSize: 10 },
                max: maxTime,
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 10 },
                splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
            },
            yAxis: {
                type: 'value',
                name: 'Batido #',
                nameTextStyle: { color: '#6b7280', fontSize: 10 },
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 10, formatter: (v: number) => Math.floor(v).toString() },
                splitLine: { show: false },
                max: Math.min(beats.length + 1, 30),
            },
            tooltip: {
                trigger: 'item',
                backgroundColor: '#1f2937',
                borderColor: '#374151',
                textStyle: { color: '#e5e7eb', fontSize: 11 },
            },
            series: [
                {
                    name: 'Fase Lenta',
                    type: 'custom',
                    renderItem: (_params: any, api: any) => {
                        const start = api.coord([api.value(0), api.value(1)])
                        const end = api.coord([api.value(2), api.value(3)])
                        return {
                            type: 'rect',
                            shape: {
                                x: start[0],
                                y: start[1],
                                width: end[0] - start[0],
                                height: end[1] - start[1],
                            },
                            style: api.style(),
                        }
                    },
                    data: slowPhaseData,
                    encode: { x: [0, 2], y: [1, 3] },
                },
                {
                    name: 'Fase Rapida',
                    type: 'custom',
                    renderItem: (_params: any, api: any) => {
                        const start = api.coord([api.value(0), api.value(1)])
                        const end = api.coord([api.value(2), api.value(3)])
                        return {
                            type: 'rect',
                            shape: {
                                x: start[0],
                                y: start[1],
                                width: Math.max(end[0] - start[0], 2),
                                height: end[1] - start[1],
                            },
                            style: api.style(),
                        }
                    },
                    data: fastPhaseData,
                    encode: { x: [0, 2], y: [1, 3] },
                },
                // Auxiliary line series for the time cursor markLine
                {
                    name: '_cursor',
                    type: 'line',
                    data: [],
                    silent: true,
                    symbol: 'none',
                    lineStyle: { width: 0 },
                    markLine: {
                        silent: true,
                        symbol: 'none',
                        lineStyle: { color: '#0ea5e9', width: 1, type: 'solid' },
                        data: [{ xAxis: currentTimeRef.current }],
                        label: { show: false },
                    },
                },
            ],
        }
    }, [beats])

    // Imperatively update cursor markLine
    useEffect(() => {
        const instance = chartRef.current?.getEchartsInstance()
        if (!instance) return
        instance.setOption({
            series: [{}, {}, {
                markLine: {
                    silent: true,
                    symbol: 'none',
                    lineStyle: { color: '#0ea5e9', width: 1, type: 'solid' },
                    data: [{ xAxis: currentTime }],
                    label: { show: false },
                },
            }],
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
            <ReactECharts
                ref={chartRef}
                option={option}
                style={{ height: 250 }}
                opts={{ renderer: 'canvas' }}
            />
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
