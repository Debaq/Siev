import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { VocalData } from '../../../types/audiometry'

interface SpeechAudiogramProps {
  vocal: VocalData
}

export default function SpeechAudiogram({ vocal }: SpeechAudiogramProps) {
  const option = useMemo(() => {
    // Construir curva OD: SDT(intensity, 0%) + SRT(intensity, 50%) + UMDs
    const odPoints: number[][] = []
    if (vocal.sdt_od?.intensity !== undefined) {
      odPoints.push([vocal.sdt_od.intensity, 0])
    }
    if (vocal.srt_od?.intensity !== undefined) {
      odPoints.push([vocal.srt_od.intensity, 50])
    }
    for (const e of vocal.umd_od) {
      if (e.intensity !== undefined && e.percentage !== undefined) {
        odPoints.push([e.intensity, e.percentage])
      }
    }
    odPoints.sort((a, b) => a[0] - b[0])

    // Construir curva OI: SDT(intensity, 0%) + SRT(intensity, 50%) + UMDs
    const oiPoints: number[][] = []
    if (vocal.sdt_oi?.intensity !== undefined) {
      oiPoints.push([vocal.sdt_oi.intensity, 0])
    }
    if (vocal.srt_oi?.intensity !== undefined) {
      oiPoints.push([vocal.srt_oi.intensity, 50])
    }
    for (const e of vocal.umd_oi) {
      if (e.intensity !== undefined && e.percentage !== undefined) {
        oiPoints.push([e.intensity, e.percentage])
      }
    }
    oiPoints.sort((a, b) => a[0] - b[0])

    const series: any[] = []

    if (odPoints.length > 0) {
      series.push({
        name: 'OD',
        type: 'line',
        smooth: true,
        data: odPoints,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#EF4444', width: 2 },
        itemStyle: { color: '#EF4444', borderWidth: 2, borderColor: '#EF4444' },
      })
    }

    if (oiPoints.length > 0) {
      series.push({
        name: 'OI',
        type: 'line',
        smooth: true,
        data: oiPoints,
        symbol: 'path://M4,4 L16,16 M16,4 L4,16',
        symbolSize: 8,
        lineStyle: { color: '#3B82F6', width: 2 },
        itemStyle: { color: '#3B82F6', borderWidth: 2, borderColor: '#3B82F6' },
      })
    }

    return {
      grid: { top: 30, right: 20, bottom: 40, left: 50 },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) =>
          `${params.seriesName}<br/>${params.data[0]} dB: ${params.data[1]}%`,
      },
      legend: {
        top: 0,
        textStyle: { color: '#9CA3AF', fontSize: 10 },
      },
      xAxis: {
        type: 'value',
        min: 0,
        max: 120,
        interval: 10,
        name: 'Intensidad (dB HL)',
        nameLocation: 'middle',
        nameGap: 28,
        nameTextStyle: { color: '#6B7280', fontSize: 10 },
        axisLabel: { color: '#9CA3AF', fontSize: 10 },
        splitLine: { lineStyle: { color: '#374151', type: 'dashed' } },
        axisLine: { lineStyle: { color: '#4B5563' } },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        interval: 10,
        name: 'Discriminación (%)',
        nameLocation: 'middle',
        nameGap: 38,
        nameTextStyle: { color: '#6B7280', fontSize: 10 },
        axisLabel: { color: '#9CA3AF', fontSize: 10 },
        splitLine: { lineStyle: { color: '#374151', type: 'dashed' } },
        axisLine: { lineStyle: { color: '#4B5563' } },
      },
      series,
    }
  }, [vocal])

  return (
    <div className="w-full h-full">
      <ReactECharts
        option={option}
        style={{ height: '100%', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        theme="dark"
      />
    </div>
  )
}
