import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { FowlerResult, FowlerStep, Ear } from '../../../types/audiometry'

interface FowlerTestProps {
  results: FowlerResult[]
  activeEar: Ear
  onAdd: (result: FowlerResult) => void
  onRemove: (index: number) => void
}

export default function FowlerTest({ results, activeEar, onAdd, onRemove }: FowlerTestProps) {
  const [frequency, setFrequency] = useState(1000)
  const [steps, setSteps] = useState<FowlerStep[]>([
    { referenceIntensity: 60, testIntensity: 60 },
  ])

  const referenceEar: Ear = activeEar === 'od' ? 'oi' : 'od'
  const testEar: Ear = activeEar

  const addStep = () => {
    setSteps(prev => [...prev, { referenceIntensity: 0, testIntensity: 0 }])
  }

  const updateStep = (index: number, field: keyof FowlerStep, value: number) => {
    setSteps(prev => prev.map((s, i) => (i === index ? { ...s, [field]: value } : s)))
  }

  const removeStep = (index: number) => {
    setSteps(prev => prev.filter((_, i) => i !== index))
  }

  const handleSave = () => {
    if (steps.length === 0) return
    onAdd({
      referenceEar,
      testEar,
      frequency,
      steps: [...steps],
    })
    setSteps([{ referenceIntensity: 60, testIntensity: 60 }])
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-xs font-bold text-dark-200 mb-1">Balance Binaural Alterno de Fowler (ABLB)</h3>
        <p className="text-[10px] text-dark-500">
          Compara sonoridad percibida entre ambos oídos. Detecta reclutamiento.
        </p>
      </div>

      <div className="bg-dark-800/30 rounded-lg p-3 border border-dark-700/50 space-y-2">
        <div className="flex items-center gap-3">
          <div>
            <label className="text-[10px] text-dark-400 block mb-0.5">Frecuencia</label>
            <select
              value={frequency}
              onChange={e => setFrequency(Number(e.target.value))}
              className="bg-dark-900 border border-dark-700 rounded px-1.5 py-1 text-[10px] text-white"
            >
              {[500, 1000, 2000, 4000].map(f => (
                <option key={f} value={f}>{f} Hz</option>
              ))}
            </select>
          </div>
          <div className="text-[10px] text-dark-400">
            Ref: <span className={referenceEar === 'od' ? 'text-red-400 font-bold' : 'text-blue-400 font-bold'}>{referenceEar.toUpperCase()}</span>
            {' → '}
            Test: <span className={testEar === 'od' ? 'text-red-400 font-bold' : 'text-blue-400 font-bold'}>{testEar.toUpperCase()}</span>
          </div>
        </div>

        {/* Pasos */}
        <div className="space-y-1">
          <div className="grid grid-cols-[1fr,1fr,auto] gap-1 text-[9px] text-dark-500 font-medium uppercase">
            <span>Ref ({referenceEar.toUpperCase()}) dB</span>
            <span>Test ({testEar.toUpperCase()}) dB</span>
            <span className="w-5" />
          </div>
          {steps.map((step, i) => (
            <div key={i} className="grid grid-cols-[1fr,1fr,auto] gap-1">
              <input
                type="number"
                value={step.referenceIntensity}
                onChange={e => updateStep(i, 'referenceIntensity', Number(e.target.value))}
                className="bg-dark-900 border border-dark-700 rounded px-1.5 py-0.5 text-[10px] text-white"
                step={5}
              />
              <input
                type="number"
                value={step.testIntensity}
                onChange={e => updateStep(i, 'testIntensity', Number(e.target.value))}
                className="bg-dark-900 border border-dark-700 rounded px-1.5 py-0.5 text-[10px] text-white"
                step={5}
              />
              <button onClick={() => removeStep(i)} className="text-dark-600 hover:text-red-400 transition-colors">
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <button
            onClick={addStep}
            className="flex items-center gap-1 px-2 py-1 bg-dark-700 hover:bg-dark-600 rounded text-dark-200 text-[10px] transition-colors"
          >
            <Plus className="w-3 h-3" />
            Paso
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1 px-2 py-1 bg-siev-600 hover:bg-siev-500 rounded text-white text-[10px] transition-colors"
          >
            Guardar resultado
          </button>
        </div>
      </div>

      {/* Resultados guardados */}
      {results.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] font-medium text-dark-400 uppercase tracking-wider">Resultados</div>
          {results.map((r, i) => (
            <div key={i} className="bg-dark-800/30 rounded px-2 py-1.5 border border-dark-700/30">
              <div className="flex items-center justify-between">
                <div className="text-[10px] text-dark-300">
                  {r.frequency} Hz — Ref: {r.referenceEar.toUpperCase()}, Test: {r.testEar.toUpperCase()} — {r.steps.length} pasos
                </div>
                <button onClick={() => onRemove(i)} className="text-dark-600 hover:text-red-400 transition-colors">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
