import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { SPVTimePoint } from '../../types/review'

interface SPVChartProps {
    data: SPVTimePoint[]
    currentTime: number
    overallSPV: number
    onSeek: (time: number) => void
}

export default function SPVChart({ data, currentTime, overallSPV, onSeek }: SPVChartProps) {
    const option = useMemo(() => {
        const chartData = data.map(d => [d.time, d.spv])

        return {
            backgroundColor: 'transparent',
            grid: { left: 50, right: 20, top: 30, bottom: 30 },
            xAxis: {
                type: 'value',
                name: 'Tiempo (s)',
                nameTextStyle: { color: '#6b7280', fontSize: 10 },
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 10 },
                splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
            },
            yAxis: {
                type: 'value',
                name: 'SPV (°/s)',
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
            },
            series: [
                {
                    name: 'SPV',
                    type: 'line',
                    data: chartData,
                    symbol: 'none',
                    lineStyle: { color: '#a78bfa', width: 1.5 },
                    areaStyle: { color: 'rgba(167, 139, 250, 0.08)' },
                    markLine: {
                        silent: true,
                        symbol: 'none',
                        data: [
                            {
                                xAxis: currentTime,
                                lineStyle: { color: '#0ea5e9', width: 1, type: 'solid' },
                                label: { show: false },
                            },
                            {
                                yAxis: 6,
                                lineStyle: { color: '#22c55e', width: 1, type: 'dashed' },
                                label: { show: true, formatter: '6°/s', color: '#22c55e', fontSize: 9, position: 'end' },
                            },
                            {
                                yAxis: -6,
                                lineStyle: { color: '#22c55e', width: 1, type: 'dashed' },
                                label: { show: false },
                            },
                        ],
                    },
                },
            ],
        }
    }, [data, currentTime])

    const onEvents = useMemo(() => ({
        click: (params: any) => {
            if (params.value) onSeek(params.value[0])
        },
    }), [onSeek])

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-dark-300">SPV en Tiempo</span>
                <span className="text-[10px] text-dark-500">
                    Promedio: <span className="text-purple-400 font-medium">{overallSPV.toFixed(1)}°/s</span>
                </span>
            </div>
            <ReactECharts
                option={option}
                style={{ height: 250 }}
                opts={{ renderer: 'canvas' }}
                onEvents={onEvents}
            />
        </div>
    )
}
