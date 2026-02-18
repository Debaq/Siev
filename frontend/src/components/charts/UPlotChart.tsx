import { useRef, useEffect, useCallback } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'

interface UPlotChartProps {
  options: Omit<uPlot.Options, 'width' | 'height'>
  data: uPlot.AlignedData
  className?: string
  onCreate?: (chart: uPlot) => void
}

export default function UPlotChart({ options, data, className, onCreate }: UPlotChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<uPlot | null>(null)
  const onCreateRef = useRef(onCreate)
  onCreateRef.current = onCreate

  // Track options identity to know when to recreate
  const optionsRef = useRef(options)

  const init = useCallback((el: HTMLDivElement, opts: Omit<uPlot.Options, 'width' | 'height'>, d: uPlot.AlignedData) => {
    const rect = el.getBoundingClientRect()
    const chart = new uPlot(
      { ...opts, width: Math.floor(rect.width), height: Math.floor(rect.height) },
      d,
      el,
    )
    chartRef.current = chart
    onCreateRef.current?.(chart)
    return chart
  }, [])

  // Create chart on mount, destroy on unmount
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const chart = init(el, options, data)
    optionsRef.current = options

    return () => {
      chart.destroy()
      chartRef.current = null
    }
    // Recreate only when options identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options])

  // Update data efficiently without recreating
  useEffect(() => {
    if (chartRef.current && options === optionsRef.current) {
      chartRef.current.setData(data)
    }
  }, [data, options])

  // ResizeObserver for auto-resize
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const ro = new ResizeObserver(entries => {
      const entry = entries[0]
      if (!entry || !chartRef.current) return
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) {
        chartRef.current.setSize({ width: Math.floor(width), height: Math.floor(height) })
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height: '100%', overflow: 'hidden' }}
    />
  )
}
