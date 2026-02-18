import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { ToneDecayResult, Ear } from '../../../types/audiometry'

interface ToneDecayTestProps {
  results: ToneDecayResult[]
  activeEar: Ear
  onAdd: (result: ToneDecayResult) => void
  onRemove: (index: number) => void
}

function interpretDecay(decayDb: number): { text: string; color: string } {
  if (decayDb <= 5) return { text: 'Normal', color: 'text-green-400' }
  if (decayDb <= 15) return { text: 'Leve (Coclear)', color: 'text-yellow-400' }
  if (decayDb <= 25) return { text: 'Moderado', color: 'text-orange-400' }
  return { text: 'Severo (Retrococlear)', color: 'text-red-400' }
}

export default function ToneDecayTest({ results, activeEar, onAdd, onRemove }: ToneDecayTestProps) {
  const [frequency, setFrequency] = useState(1000)
  const [initialIntensity, setInitialIntensity] = useState(70)
  const [finalIntensity, setFinalIntensity] = useState(70)
  const [durationSeconds, setDurationSeconds] = useState(60)

  const decayDb = finalIntensity - initialIntensity

  const handleAdd = () => {
    onAdd({
      ear: activeEar,
      frequency,
      initialIntensity,
      finalIntensity,
      decayDb,
      durationSeconds,
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-bold text-dark-200 mb-1">Tone Decay (Deterioro Tonal)</h3>
        <p className="text-[10px] text-dark-500">
          Evalúa adaptación patológica. Se mide cuánto debe incrementarse la intensidad para mantener la percepción.
        </p>
      </div>

      <div className="bg-dark-800/30 rounded-lg p-3 border border-dark-700/50 space-y-2">
        <div className={`text-[10px] font-bold uppercase ${
          activeEar === 'od' ? 'text-red-400' : 'text-blue-400'
        }`}>
          {activeEar === 'od' ? 'Oído Derecho' : 'Oído Izquierdo'}
        </div>

        <div className="grid grid-cols-2 gap-2">
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
            <label className="text-[10px] text-dark-400 block mb-0.5">Duración (seg)</label>
            <input
              type="number"
              value={durationSeconds}
              onChange={e => setDurationSeconds(Number(e.target.value))}
              className="w-full bg-dark-900 border border-dark-700 rounded px-1.5 py-1 text-[10px] text-white"
              min={10}
              max={300}
            />
          </div>
          <div>
            <label className="text-[10px] text-dark-400 block mb-0.5">Intensidad inicial (dB)</label>
            <input
              type="number"
              value={initialIntensity}
              onChange={e => setInitialIntensity(Number(e.target.value))}
              className="w-full bg-dark-900 border border-dark-700 rounded px-1.5 py-1 text-[10px] text-white"
              step={5}
            />
          </div>
          <div>
            <label className="text-[10px] text-dark-400 block mb-0.5">Intensidad final (dB)</label>
            <input
              type="number"
              value={finalIntensity}
              onChange={e => setFinalIntensity(Number(e.target.value))}
              className="w-full bg-dark-900 border border-dark-700 rounded px-1.5 py-1 text-[10px] text-white"
              step={5}
            />
          </div>
        </div>

        <div className="text-[10px] text-dark-400">
          Decay: <span className="text-white font-mono">{decayDb} dB</span>
          {' — '}
          <span className={interpretDecay(decayDb).color}>{interpretDecay(decayDb).text}</span>
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
            const interp = interpretDecay(r.decayDb)
            return (
              <div key={i} className="flex items-center justify-between bg-dark-800/30 rounded px-2 py-1.5 border border-dark-700/30">
                <div className="flex items-center gap-3 text-[10px]">
                  <span className={r.ear === 'od' ? 'text-red-400 font-bold' : 'text-blue-400 font-bold'}>
                    {r.ear.toUpperCase()}
                  </span>
                  <span className="text-dark-300">{r.frequency} Hz</span>
                  <span className="text-dark-400">{r.initialIntensity}→{r.finalIntensity} dB</span>
                  <span className="text-white font-mono">Decay: {r.decayDb} dB</span>
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
