import { useMemo, useRef, useCallback } from 'react'
import ReactECharts from 'echarts-for-react'
import type { HighFreqThreshold, Ear } from '../../../types/audiometry'
import { HIGH_FREQUENCIES } from '../../../types/audiometry'

interface HighFreqAudiogramProps {
  thresholds: HighFreqThreshold[]
  activeEar: Ear
  onClickPoint: (frequency: number, intensity: number) => void
}

const freqToLog = (f: number) => Math.log2(f)
const FREQ_MIN = freqToLog(7500)
const FREQ_MAX = freqToLog(17000)

export default function HighFreqAudiogram({
  thresholds,
  onClickPoint,
}: HighFreqAudiogramProps) {
  const chartRef = useRef<ReactECharts>(null)
  const onClickPointRef = useRef(onClickPoint)
  onClickPointRef.current = onClickPoint

  const option = useMemo(() => {
    const odPoints = thresholds
      .filter(t => t.ear === 'od')
      .sort((a, b) => a.frequency - b.frequency)
    const oiPoints = thresholds
      .filter(t => t.ear === 'oi')
      .sort((a, b) => a.frequency - b.frequency)

    const series: any[] = []

    if (odPoints.length > 0) {
      series.push({
        name: 'OD',
        type: 'line',
        data: odPoints.map(p => [freqToLog(p.frequency), p.intensity]),
        symbol: 'circle',
        symbolSize: 10,
        lineStyle: { color: '#EF4444', width: 2 },
        itemStyle: { color: '#EF4444', borderWidth: 2, borderColor: '#EF4444' },
        markPoint: {
          data: odPoints
            .filter(p => p.noResponse)
            .map(p => ({
              coord: [freqToLog(p.frequency), p.intensity],
              symbol: 'arrow',
              symbolSize: 8,
              symbolRotate: 180,
              itemStyle: { color: '#EF4444' },
            })),
        },
      })
    }

    if (oiPoints.length > 0) {
      series.push({
        name: 'OI',
        type: 'line',
        data: oiPoints.map(p => [freqToLog(p.frequency), p.intensity]),
        symbol: 'path://M4,4 L16,16 M16,4 L4,16',
        symbolSize: 10,
        lineStyle: { color: '#3B82F6', width: 2 },
        itemStyle: { color: 'transparent', borderWidth: 2, borderColor: '#3B82F6' },
        markPoint: {
          data: oiPoints
            .filter(p => p.noResponse)
            .map(p => ({
              coord: [freqToLog(p.frequency), p.intensity],
              symbol: 'arrow',
              symbolSize: 8,
              symbolRotate: 180,
              itemStyle: { color: '#3B82F6' },
            })),
        },
      })
    }

    // Placeholder para que siempre exista el sistema de coordenadas
    series.push({
      name: '_placeholder',
      type: 'scatter',
      data: [],
      silent: true,
      legendHoverLink: false,
      symbolSize: 0,
    })

    return {
      grid: { top: 30, right: 20, bottom: 40, left: 50 },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.seriesName === '_placeholder') return ''
          const freq = Math.round(Math.pow(2, params.data[0]))
          return `${params.seriesName}<br/>${freq} Hz: ${params.data[1]} dB HL`
        },
      },
      legend: {
        top: 0,
        textStyle: { color: '#9CA3AF', fontSize: 10 },
        data: [
          ...(odPoints.length > 0 ? ['OD'] : []),
          ...(oiPoints.length > 0 ? ['OI'] : []),
        ],
      },
      xAxis: {
        type: 'value',
        min: FREQ_MIN,
        max: FREQ_MAX,
        axisLabel: {
          formatter: (val: number) => {
            const closest = HIGH_FREQUENCIES.reduce((a, b) =>
              Math.abs(freqToLog(b) - val) < Math.abs(freqToLog(a) - val) ? b : a
            )
            if (Math.abs(freqToLog(closest) - val) < 0.01) {
              return closest >= 1000 ? `${(closest / 1000).toFixed(closest % 1000 === 0 ? 0 : 1)}k` : String(closest)
            }
            return ''
          },
          color: '#9CA3AF',
          fontSize: 10,
        },
        splitLine: { lineStyle: { color: '#374151', type: 'dashed' } },
        axisLine: { lineStyle: { color: '#4B5563' } },
        name: 'Frecuencia (Hz)',
        nameLocation: 'middle',
        nameGap: 28,
        nameTextStyle: { color: '#6B7280', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        min: -10,
        max: 120,
        inverse: true,
        interval: 10,
        axisLabel: { color: '#9CA3AF', fontSize: 10 },
        splitLine: { lineStyle: { color: '#374151', type: 'dashed' } },
        axisLine: { lineStyle: { color: '#4B5563' } },
        name: 'dB HL',
        nameLocation: 'middle',
        nameGap: 38,
        nameTextStyle: { color: '#6B7280', fontSize: 10 },
      },
      series,
    }
  }, [thresholds])

  const onChartReady = useCallback((chart: any) => {
    const zr = chart.getZr()
    zr.off('click')

    zr.on('click', (params: any) => {
      const pointInPixel = [params.offsetX, params.offsetY]

      if (chart.containPixel({ gridIndex: 0 }, pointInPixel)) {
        const pointInGrid = chart.convertFromPixel({ gridIndex: 0 }, pointInPixel)
        const logFreq = pointInGrid[0]
        const rawIntensity = pointInGrid[1]

        let closestFreq = HIGH_FREQUENCIES[0]
        let minDist = Infinity
        for (const f of HIGH_FREQUENCIES) {
          const dist = Math.abs(freqToLog(f) - logFreq)
          if (dist < minDist) {
            minDist = dist
            closestFreq = f
          }
        }

        const snappedIntensity = Math.round(rawIntensity / 5) * 5
        const clampedIntensity = Math.max(-10, Math.min(120, snappedIntensity))

        onClickPointRef.current(closestFreq, clampedIntensity)
      }
    })
  }, [])

  return (
    <div className="w-full h-full min-h-[300px]">
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: '100%', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        theme="dark"
        onChartReady={onChartReady}
      />
    </div>
  )
}
