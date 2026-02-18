import { useMemo, useRef, useCallback } from 'react'
import ReactECharts from 'echarts-for-react'
import type { ThresholdPoint, Ear, ConductionType } from '../../../types/audiometry'
import { STANDARD_FREQUENCIES } from '../../../types/audiometry'
import { getSymbolConfig, getSeriesName } from './AudiogramSymbols'

interface AudiogramProps {
  thresholds: ThresholdPoint[]
  activeEar: Ear
  activeConduction: ConductionType
  activeMasking: boolean
  onClickPoint: (frequency: number, intensity: number) => void
}

// Mapear frecuencia a posición logarítmica en eje X
const freqToLog = (f: number) => Math.log2(f)
const FREQ_TICKS = STANDARD_FREQUENCIES
const FREQ_MIN = freqToLog(100)
const FREQ_MAX = freqToLog(10000)

type SeriesKey = `${Ear}-${ConductionType}-${boolean}`

function groupThresholds(thresholds: ThresholdPoint[]) {
  const groups = new Map<SeriesKey, ThresholdPoint[]>()
  for (const t of thresholds) {
    const key: SeriesKey = `${t.ear}-${t.conduction}-${t.masked}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(t)
  }
  return groups
}

export default function Audiogram({
  thresholds,
  onClickPoint,
}: AudiogramProps) {
  const chartRef = useRef<ReactECharts>(null)
  const onClickPointRef = useRef(onClickPoint)
  onClickPointRef.current = onClickPoint

  const option = useMemo(() => {
    const groups = groupThresholds(thresholds)

    const series: any[] = []

    // Generar todas las combinaciones posibles para mostrar
    const combos: { ear: Ear; conduction: ConductionType; masked: boolean }[] = [
      { ear: 'od', conduction: 'aerea', masked: false },
      { ear: 'oi', conduction: 'aerea', masked: false },
      { ear: 'od', conduction: 'osea', masked: false },
      { ear: 'oi', conduction: 'osea', masked: false },
      { ear: 'od', conduction: 'aerea', masked: true },
      { ear: 'oi', conduction: 'aerea', masked: true },
      { ear: 'od', conduction: 'osea', masked: true },
      { ear: 'oi', conduction: 'osea', masked: true },
      { ear: 'od', conduction: 'ldl', masked: false },
      { ear: 'oi', conduction: 'ldl', masked: false },
    ]

    for (const combo of combos) {
      const key: SeriesKey = `${combo.ear}-${combo.conduction}-${combo.masked}`
      const points = groups.get(key) || []
      if (points.length === 0) continue

      const cfg = getSymbolConfig(combo.ear, combo.conduction, combo.masked)
      const name = getSeriesName(combo.ear, combo.conduction, combo.masked)

      // Ordenar por frecuencia
      const sorted = [...points].sort((a, b) => a.frequency - b.frequency)

      series.push({
        name,
        type: 'line',
        data: sorted.map(p => [freqToLog(p.frequency), p.intensity]),
        symbol: cfg.symbol,
        symbolSize: cfg.size,
        symbolOffset: cfg.offset,
        lineStyle: {
          color: cfg.color,
          width: combo.conduction === 'ldl' ? 1 : combo.conduction === 'osea' ? 1.5 : 2,
          type: combo.conduction === 'osea' ? 'dashed' : combo.conduction === 'ldl' ? 'dotted' : 'solid',
        },
        itemStyle: {
          color: cfg.fillColor,
          borderColor: cfg.borderColor,
          borderWidth: cfg.borderWidth,
        },
        // No-Response markers
        markPoint: {
          data: sorted
            .filter(p => p.noResponse)
            .map(p => ({
              coord: [freqToLog(p.frequency), p.intensity],
              symbol: 'arrow',
              symbolSize: 12,
              symbolRotate: 180,
              symbolOffset: cfg.offset,
              itemStyle: { color: cfg.color },
            })),
        },
      })
    }

    // Serie placeholder invisible para que SIEMPRE exista el sistema de coordenadas,
    // incluso cuando no hay umbrales. Sin esto, containPixel/convertFromPixel fallan.
    series.push({
      name: '_placeholder',
      type: 'scatter',
      data: [],
      silent: true,
      legendHoverLink: false,
      symbolSize: 0,
    })

    // Etiqueta "LDL:" subrayada cuando hay al menos un punto LDL
    const hasLdl = thresholds.some(t => t.conduction === 'ldl')
    if (hasLdl) {
      const labelX = (freqToLog(125) + freqToLog(250)) / 2
      series.push({
        name: '_ldl_label',
        type: 'scatter',
        data: [[labelX, 104]],
        silent: true,
        legendHoverLink: false,
        symbolSize: 0,
        label: {
          show: true,
          formatter: 'LDL:',
          color: '#D1D5DB',
          fontSize: 10,
          fontWeight: 'bold',
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#D1D5DB', width: 1 },
          data: [[
            { xAxis: freqToLog(140), yAxis: 106 },
            { xAxis: freqToLog(230), yAxis: 106 },
          ]],
          label: { show: false },
        },
      })
    }

    return {
      grid: {
        top: 36,
        right: 20,
        bottom: 12,
        left: 50,
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.seriesName === '_placeholder') return ''
          const freq = Math.round(Math.pow(2, params.data[0]))
          return `${params.seriesName}<br/>${freq} Hz: ${params.data[1]} dB HL`
        },
      },
      legend: { show: false },
      xAxis: {
        type: 'value',
        min: FREQ_MIN,
        max: FREQ_MAX,
        position: 'top',
        axisLabel: {
          formatter: (val: number) => {
            const closest = FREQ_TICKS.reduce((a, b) =>
              Math.abs(freqToLog(b) - val) < Math.abs(freqToLog(a) - val) ? b : a
            )
            if (Math.abs(freqToLog(closest) - val) < 0.01) {
              return closest >= 1000 ? `${closest / 1000}k` : String(closest)
            }
            return ''
          },
          color: '#9CA3AF',
          fontSize: 11,
          fontWeight: 'bold',
        },
        axisTick: {
          show: true,
          alignWithLabel: false,
        },
        splitLine: {
          show: true,
          lineStyle: { color: '#374151', type: 'solid', width: 0.5 },
        },
        axisLine: { lineStyle: { color: '#4B5563' } },
      },
      yAxis: {
        type: 'value',
        min: -10,
        max: 120,
        inverse: true,
        interval: 10,
        axisLabel: {
          color: '#9CA3AF',
          fontSize: 10,
        },
        splitLine: {
          show: true,
          lineStyle: { color: '#374151', type: 'solid', width: 0.5 },
        },
        axisLine: { lineStyle: { color: '#4B5563' } },
        name: 'dB HL',
        nameLocation: 'middle',
        nameGap: 38,
        nameTextStyle: { color: '#6B7280', fontSize: 10 },
      },
      series,
    }
  }, [thresholds])

  // Cuando el chart está listo, bindear click en ZRender
  const onChartReady = useCallback((chart: any) => {
    const zr = chart.getZr()

    // Limpiar handler previo por si se re-llama
    zr.off('click')

    zr.on('click', (params: any) => {
      const pointInPixel = [params.offsetX, params.offsetY]

      if (chart.containPixel({ gridIndex: 0 }, pointInPixel)) {
        const pointInGrid = chart.convertFromPixel({ gridIndex: 0 }, pointInPixel)
        const logFreq = pointInGrid[0]
        const rawIntensity = pointInGrid[1]

        // Snap a frecuencia más cercana
        let closestFreq = FREQ_TICKS[0]
        let minDist = Infinity
        for (const f of FREQ_TICKS) {
          const dist = Math.abs(freqToLog(f) - logFreq)
          if (dist < minDist) {
            minDist = dist
            closestFreq = f
          }
        }

        // Snap a 5 dB más cercano
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
