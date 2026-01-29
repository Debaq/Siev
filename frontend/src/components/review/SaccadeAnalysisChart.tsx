import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { SaccadeMarker } from '../../types/review'

interface SaccadeAnalysisChartProps {
    saccades: SaccadeMarker[]
    currentTime: number
    onSeek: (time: number) => void
}

export default function SaccadeAnalysisChart({ saccades, currentTime: _currentTime, onSeek }: SaccadeAnalysisChartProps) {
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

    const option = useMemo(() => {
        const rightSaccades = saccades
            .filter(s => s.direction === 'right')
            .map(s => [s.amplitude, s.peak_velocity, s.start_time])
        const leftSaccades = saccades
            .filter(s => s.direction === 'left')
            .map(s => [s.amplitude, s.peak_velocity, s.start_time])

        return {
            backgroundColor: 'transparent',
            grid: { left: 55, right: 20, top: 30, bottom: 35 },
            xAxis: {
                type: 'value',
                name: 'Amplitud (°)',
                nameTextStyle: { color: '#6b7280', fontSize: 10 },
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 10 },
                splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
            },
            yAxis: {
                type: 'value',
                name: 'Vel. Pico (°/s)',
                nameTextStyle: { color: '#6b7280', fontSize: 10 },
                axisLine: { lineStyle: { color: '#374151' } },
                axisLabel: { color: '#9ca3af', fontSize: 10 },
                splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
            },
            tooltip: {
                trigger: 'item',
                backgroundColor: '#1f2937',
                borderColor: '#374151',
                textStyle: { color: '#e5e7eb', fontSize: 11 },
                formatter: (p: any) => {
                    return `${p.seriesName}<br/>Amplitud: ${p.value[0].toFixed(1)}°<br/>Velocidad: ${p.value[1].toFixed(0)}°/s`
                },
            },
            series: [
                {
                    name: 'Derecha',
                    type: 'scatter',
                    data: rightSaccades,
                    symbolSize: 6,
                    itemStyle: { color: '#f43f5e', opacity: 0.7 },
                },
                {
                    name: 'Izquierda',
                    type: 'scatter',
                    data: leftSaccades,
                    symbolSize: 6,
                    itemStyle: { color: '#0ea5e9', opacity: 0.7 },
                },
            ],
        }
    }, [saccades])

    const onEvents = useMemo(() => ({
        click: (params: any) => {
            if (params.value?.[2] !== undefined) {
                onSeek(params.value[2])
            }
        },
    }), [onSeek])

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-dark-300">Analisis de Sacadas (Main Sequence)</span>
                <span className="text-[10px] text-dark-500">
                    {stats ? `${stats.count} sacadas` : 'Sin datos'}
                </span>
            </div>
            <ReactECharts
                option={option}
                style={{ height: 220 }}
                opts={{ renderer: 'canvas' }}
                onEvents={onEvents}
            />
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
