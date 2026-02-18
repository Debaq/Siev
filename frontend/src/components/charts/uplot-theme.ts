import uPlot from 'uplot'

export const DARK_THEME = {
  axes: {
    stroke: '#374151',
    grid: '#1f2937',
    ticks: '#374151',
    font: '10px system-ui',
    labelColor: '#9ca3af',
  },
  colors: {
    od: '#f43f5e',
    oi: '#0ea5e9',
    cursor: '#0ea5e9',
    spv: '#a78bfa',
    reference: '#22c55e',
    slowPhase: 'rgba(14, 165, 233, 0.4)',
    fastPhase: 'rgba(244, 63, 94, 0.5)',
    saccadeArea: 'rgba(251, 191, 36, 0.08)',
    deflection: '#fbbf24',
  },
} as const

export function darkAxis(name?: string): Partial<uPlot.Axis> {
  return {
    stroke: DARK_THEME.axes.labelColor,
    grid: { stroke: DARK_THEME.axes.grid, dash: [4, 4] },
    ticks: { stroke: DARK_THEME.axes.ticks },
    font: DARK_THEME.axes.font,
    ...(name ? { label: name, labelFont: '10px system-ui', labelGap: 4 } : {}),
  }
}

export function darkXAxis(name?: string): Partial<uPlot.Axis> {
  return {
    ...darkAxis(name),
    values: (_u: uPlot, vals: number[]) => vals.map(v => v.toFixed(1) + 's'),
  }
}
