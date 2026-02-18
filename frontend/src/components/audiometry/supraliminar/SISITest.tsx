import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { SISIResult, Ear } from '../../../types/audiometry'

interface SISITestProps {
  results: SISIResult[]
  activeEar: Ear
  onAdd: (result: SISIResult) => void
  onRemove: (index: number) => void
}

function interpretSISI(positive: number): { text: string; color: string } {
  const percent = (positive / 20) * 100
  if (percent >= 70) return { text: 'Positivo (Coclear)', color: 'text-red-400' }
  if (percent >= 20) return { text: 'Dudoso', color: 'text-yellow-400' }
  return { text: 'Negativo', color: 'text-green-400' }
}

export default function SISITest({ results, activeEar, onAdd, onRemove }: SISITestProps) {
  const [frequency, setFrequency] = useState(1000)
  const [intensity, setIntensity] = useState(70)
  const [positiveResponses, setPositiveResponses] = useState(0)

  const handleAdd = () => {
    onAdd({ ear: activeEar, frequency, intensity, positiveResponses })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-bold text-dark-200 mb-1">SISI (Short Increment Sensitivity Index)</h3>
        <p className="text-[10px] text-dark-500">
          Detecta reclutamiento coclear. Se presentan incrementos de 1 dB sobre tono continuo.
        </p>
      </div>

      {/* Formulario */}
      <div className="bg-dark-800/30 rounded-lg p-3 border border-dark-700/50 space-y-2">
        <div className={`text-[10px] font-bold uppercase ${
          activeEar === 'od' ? 'text-red-400' : 'text-blue-400'
        }`}>
          {activeEar === 'od' ? 'Oído Derecho' : 'Oído Izquierdo'}
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-[10px] text-dark-400 block mb-0.5">Frecuencia</label>
            <select
              value={frequency}
              onChange={e => setFrequency(Number(e.target.value))}
              className="w-full bg-dark-900 border border-dark-700 rounded px-1.5 py-1 text-[10px] text-white"
            >
              {[500, 1000, 2000, 4000].map(f => (
                <option key={f} value={f}>{f} Hz</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-dark-400 block mb-0.5">Intensidad</label>
            <input
              type="number"
              value={intensity}
              onChange={e => setIntensity(Number(e.target.value))}
              className="w-full bg-dark-900 border border-dark-700 rounded px-1.5 py-1 text-[10px] text-white"
              step={5}
              min={20}
              max={120}
            />
          </div>
          <div>
            <label className="text-[10px] text-dark-400 block mb-0.5">Positivas /20</label>
            <input
              type="number"
              value={positiveResponses}
              onChange={e => setPositiveResponses(Math.min(20, Math.max(0, Number(e.target.value))))}
              className="w-full bg-dark-900 border border-dark-700 rounded px-1.5 py-1 text-[10px] text-white"
              min={0}
              max={20}
            />
          </div>
        </div>

        <button
          onClick={handleAdd}
          className="flex items-center gap-1 px-2 py-1 bg-siev-600 hover:bg-siev-500 rounded text-white text-[10px] transition-colors"
        >
          <Plus className="w-3 h-3" />
          Agregar resultado
        </button>
      </div>

      {/* Resultados */}
      {results.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] font-medium text-dark-400 uppercase tracking-wider">Resultados</div>
          {results.map((r, i) => {
            const interp = interpretSISI(r.positiveResponses)
            return (
              <div key={i} className="flex items-center justify-between bg-dark-800/30 rounded px-2 py-1.5 border border-dark-700/30">
                <div className="flex items-center gap-3 text-[10px]">
                  <span className={r.ear === 'od' ? 'text-red-400 font-bold' : 'text-blue-400 font-bold'}>
                    {r.ear.toUpperCase()}
                  </span>
                  <span className="text-dark-300">{r.frequency} Hz</span>
                  <span className="text-dark-400">@ {r.intensity} dB</span>
                  <span className="text-dark-200 font-mono">{r.positiveResponses}/20 ({((r.positiveResponses / 20) * 100).toFixed(0)}%)</span>
                  <span className={interp.color}>{interp.text}</span>
                </div>
                <button onClick={() => onRemove(i)} className="text-dark-600 hover:text-red-400 transition-colors">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
