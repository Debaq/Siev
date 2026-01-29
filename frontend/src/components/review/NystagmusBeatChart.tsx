import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { NystagmusBeatMarker } from '../../types/review'

interface NystagmusBeatChartProps {
    beats: NystagmusBeatMarker[]
    currentTime: number
    onSeek: (time: number) => void
}

export default function NystagmusBeatChart({ beats, currentTime, onSeek }: NystagmusBeatChartProps) {
    const stats = useMemo(() => {
        if (beats.length === 0) return null
        const spvs = beats.map(b => Math.abs(b.spv))
        return {
            count: beats.length,
            avgSPV: spvs.reduce((a, b) => a + b, 0) / spvs.length,
            avgAmplitude: beats.map(b => b.amplitude).reduce((a, b) => a + b, 0) / beats.length,
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
            ],
            // Current time marker
            graphic: currentTime > 0 ? [{
                type: 'line',
                shape: { x1: 0, y1: 0, x2: 0, y2: 1 },
                style: { stroke: '#0ea5e9', lineWidth: 1 },
                invisible: true,
            }] : [],
        }
    }, [beats, currentTime])

    const onEvents = useMemo(() => ({
        click: (params: any) => {
            if (params.value?.[0] !== undefined) {
                onSeek(params.value[0])
            }
        },
    }), [onSeek])

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
                option={option}
                style={{ height: 250 }}
                opts={{ renderer: 'canvas' }}
                onEvents={onEvents}
            />
            {stats && (
                <div className="px-3 py-1.5 border-t border-dark-800 flex items-center gap-4 text-[10px] text-dark-500">
                    <span>Batidos: <span className="text-dark-300">{stats.count}</span></span>
                    <span>SPV medio: <span className="text-dark-300">{stats.avgSPV.toFixed(1)}°/s</span></span>
                    <span>Amp. media: <span className="text-dark-300">{stats.avgAmplitude.toFixed(1)}°</span></span>
                </div>
            )}
        </div>
    )
}
