import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'

interface PursuitGainChartProps {
    pursuitGain: number | null
}

export default function PursuitGainChart({ pursuitGain }: PursuitGainChartProps) {
    const option = useMemo(() => {
        const gain = pursuitGain ?? 0

        return {
            backgroundColor: 'transparent',
            series: [
                {
                    type: 'gauge',
                    startAngle: 200,
                    endAngle: -20,
                    min: 0,
                    max: 1.2,
                    radius: '90%',
                    axisLine: {
                        lineStyle: {
                            width: 12,
                            color: [
                                [0.5, '#ef4444'],
                                [0.67, '#f59e0b'],
                                [0.83, '#22c55e'],
                                [1, '#f59e0b'],
                            ],
                        },
                    },
                    pointer: {
                        length: '60%',
                        width: 4,
                        itemStyle: { color: '#e5e7eb' },
                    },
                    axisTick: { show: false },
                    splitLine: {
                        length: 8,
                        lineStyle: { color: '#4b5563', width: 1 },
                    },
                    axisLabel: {
                        color: '#9ca3af',
                        fontSize: 9,
                        distance: 15,
                        formatter: (v: number) => v.toFixed(1),
                    },
                    detail: {
                        valueAnimation: true,
                        formatter: (v: number) => v.toFixed(2),
                        color: '#e5e7eb',
                        fontSize: 18,
                        offsetCenter: [0, '40%'],
                    },
                    title: {
                        offsetCenter: [0, '60%'],
                        color: '#6b7280',
                        fontSize: 11,
                    },
                    data: [{ value: gain, name: 'Ganancia' }],
                },
            ],
        }
    }, [pursuitGain])

    if (pursuitGain === null) {
        return (
            <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
                <div className="px-3 py-2 border-b border-dark-800">
                    <span className="text-xs font-semibold text-dark-300">Ganancia Pursuit</span>
                </div>
                <div className="h-[250px] flex items-center justify-center text-dark-600 text-sm">
                    No disponible
                </div>
            </div>
        )
    }

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-dark-300">Ganancia Pursuit</span>
                <span className={`text-[10px] font-medium ${
                    pursuitGain >= 0.8 && pursuitGain <= 1.0 ? 'text-green-400' : 'text-amber-400'
                }`}>
                    {pursuitGain >= 0.8 && pursuitGain <= 1.0 ? 'Normal' : 'Anormal'}
                </span>
            </div>
            <ReactECharts
                option={option}
                style={{ height: 250 }}
                opts={{ renderer: 'canvas' }}
            />
        </div>
    )
}
