import { useState } from 'react'
import { Plus, X, Trash2, ChevronDown } from 'lucide-react'
import type {
  Ear,
  SupraliminarData,
  SISIResult,
  FowlerResult,
  FowlerStep,
  ToneDecayResult,
  LuscherResult,
  RegerResult,
  BekesyResult,
  BekesyJergerType,
} from '../../types/audiometry'

type TestType = 'sisi' | 'fowler' | 'toneDecay' | 'luscher' | 'reger' | 'bekesy'

interface TestDef {
  id: TestType
  name: string
  desc: string
}

const AVAILABLE_TESTS: TestDef[] = [
  { id: 'sisi', name: 'SISI', desc: 'Reclutamiento coclear. Incrementos de 1dB a 20dB SL.' },
  { id: 'fowler', name: 'Fowler (ABLB)', desc: 'Balance binaural alterno de sonoridad.' },
  { id: 'toneDecay', name: 'Tone Decay', desc: 'Deterioro tonal de Carhart. Tono sostenido 60s.' },
  { id: 'luscher', name: 'Lüscher', desc: 'Umbral diferencial de intensidad (DLI). Modulación de amplitud.' },
  { id: 'reger', name: 'Reger (DL)', desc: 'Limen diferencial. Mínimo cambio de intensidad detectable.' },
  { id: 'bekesy', name: 'Békésy', desc: 'Audiometría automática. Clasificación de Jerger I-V.' },
]

interface SupraliminarSectionProps {
  data: SupraliminarData
  activeEar: Ear
  onAddSISI: (r: SISIResult) => void
  onRemoveSISI: (i: number) => void
  onAddFowler: (r: FowlerResult) => void
  onRemoveFowler: (i: number) => void
  onAddToneDecay: (r: ToneDecayResult) => void
  onRemoveToneDecay: (i: number) => void
  onAddLuscher: (r: LuscherResult) => void
  onRemoveLuscher: (i: number) => void
  onAddReger: (r: RegerResult) => void
  onRemoveReger: (i: number) => void
  onAddBekesy: (r: BekesyResult) => void
  onRemoveBekesy: (i: number) => void
}

// --- Interpretaciones ---
function interpretSISI(pos: number) {
  const p = (pos / 20) * 100
  if (p >= 70) return { text: 'Positivo (Coclear)', color: 'text-red-400' }
  if (p >= 20) return { text: 'Dudoso', color: 'text-yellow-400' }
  return { text: 'Negativo', color: 'text-green-400' }
}

function interpretDecay(db: number) {
  if (db <= 5) return { text: 'Normal', color: 'text-green-400' }
  if (db <= 15) return { text: 'Leve (Coclear)', color: 'text-yellow-400' }
  if (db <= 25) return { text: 'Moderado', color: 'text-orange-400' }
  return { text: 'Severo (Retrococlear)', color: 'text-red-400' }
}

function interpretDL(dl: number) {
  if (dl < 1) return { text: 'Reclutamiento (+)', color: 'text-red-400' }
  return { text: 'Normal', color: 'text-green-400' }
}

const JERGER_DESC: Record<BekesyJergerType, string> = {
  I: 'Normal / Conductiva',
  II: 'Coclear',
  III: 'Retrococlear',
  IV: 'Retrococlear (severo)',
  V: 'Funcional / No orgánica',
}

// --- Mini formularios por tipo de prueba ---

function SISIForm({ ear, onAdd }: { ear: Ear; onAdd: (r: SISIResult) => void }) {
  const [freq, setFreq] = useState(1000)
  const [int_, setInt] = useState(70)
  const [pos, setPos] = useState(0)
  return (
    <div className="flex items-end gap-1 flex-wrap">
      <select value={freq} onChange={e => setFreq(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-16">
        {[500, 1000, 2000, 4000].map(f => <option key={f} value={f}>{f} Hz</option>)}
      </select>
      <input type="number" value={int_} onChange={e => setInt(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-12" placeholder="dB" step={5} />
      <input type="number" value={pos} onChange={e => setPos(Math.min(20, Math.max(0, Number(e.target.value))))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-10" placeholder="/20" min={0} max={20} />
      <span className="text-[8px] text-dark-500">/20</span>
      <button onClick={() => onAdd({ ear, frequency: freq, intensity: int_, positiveResponses: pos })} className="bg-siev-600 hover:bg-siev-500 text-white rounded px-1.5 py-0.5 text-[9px]">
        <Plus className="w-2.5 h-2.5" />
      </button>
    </div>
  )
}

function FowlerForm({ ear, onAdd }: { ear: Ear; onAdd: (r: FowlerResult) => void }) {
  const [freq, setFreq] = useState(1000)
  const [steps, setSteps] = useState<FowlerStep[]>([{ referenceIntensity: 60, testIntensity: 60 }])
  const refEar: Ear = ear === 'od' ? 'oi' : 'od'
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <select value={freq} onChange={e => setFreq(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-16">
          {[500, 1000, 2000, 4000].map(f => <option key={f} value={f}>{f} Hz</option>)}
        </select>
        <span className="text-[8px] text-dark-500">Ref: <span className={refEar === 'od' ? 'text-red-400' : 'text-blue-400'}>{refEar.toUpperCase()}</span></span>
      </div>
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-1">
          <input type="number" value={s.referenceIntensity} onChange={e => setSteps(p => p.map((st, j) => j === i ? { ...st, referenceIntensity: Number(e.target.value) } : st))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-12" step={5} />
          <span className="text-[8px] text-dark-500">→</span>
          <input type="number" value={s.testIntensity} onChange={e => setSteps(p => p.map((st, j) => j === i ? { ...st, testIntensity: Number(e.target.value) } : st))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-12" step={5} />
          {steps.length > 1 && <button onClick={() => setSteps(p => p.filter((_, j) => j !== i))} className="text-dark-600 hover:text-red-400"><X className="w-2.5 h-2.5" /></button>}
        </div>
      ))}
      <div className="flex gap-1">
        <button onClick={() => setSteps(p => [...p, { referenceIntensity: 0, testIntensity: 0 }])} className="bg-dark-700 hover:bg-dark-600 text-dark-300 rounded px-1.5 py-0.5 text-[8px]">+ Paso</button>
        <button onClick={() => { onAdd({ referenceEar: refEar, testEar: ear, frequency: freq, steps: [...steps] }); setSteps([{ referenceIntensity: 60, testIntensity: 60 }]) }} className="bg-siev-600 hover:bg-siev-500 text-white rounded px-1.5 py-0.5 text-[9px]">
          <Plus className="w-2.5 h-2.5 inline" /> Guardar
        </button>
      </div>
    </div>
  )
}

function ToneDecayForm({ ear, onAdd }: { ear: Ear; onAdd: (r: ToneDecayResult) => void }) {
  const [freq, setFreq] = useState(1000)
  const [ini, setIni] = useState(70)
  const [fin, setFin] = useState(70)
  const [dur, setDur] = useState(60)
  const decay = fin - ini
  return (
    <div className="space-y-1">
      <div className="flex items-end gap-1 flex-wrap">
        <select value={freq} onChange={e => setFreq(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-16">
          {[500, 1000, 2000, 4000].map(f => <option key={f} value={f}>{f} Hz</option>)}
        </select>
        <input type="number" value={ini} onChange={e => setIni(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-12" placeholder="Ini" step={5} />
        <span className="text-[8px] text-dark-500">→</span>
        <input type="number" value={fin} onChange={e => setFin(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-12" placeholder="Fin" step={5} />
        <input type="number" value={dur} onChange={e => setDur(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-10" placeholder="s" />
        <span className="text-[8px] text-dark-500">s</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[8px] text-dark-400">Decay: <span className="text-white">{decay} dB</span> — <span className={interpretDecay(decay).color}>{interpretDecay(decay).text}</span></span>
        <button onClick={() => onAdd({ ear, frequency: freq, initialIntensity: ini, finalIntensity: fin, decayDb: decay, durationSeconds: dur })} className="bg-siev-600 hover:bg-siev-500 text-white rounded px-1.5 py-0.5 text-[9px]">
          <Plus className="w-2.5 h-2.5" />
        </button>
      </div>
    </div>
  )
}

function DLForm({ ear, onAdd }: { ear: Ear; onAdd: (r: LuscherResult | RegerResult) => void }) {
  const [freq, setFreq] = useState(1000)
  const [int_, setInt] = useState(70)
  const [dl, setDl] = useState(1)
  return (
    <div className="flex items-end gap-1 flex-wrap">
      <select value={freq} onChange={e => setFreq(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-16">
        {[500, 1000, 2000, 4000].map(f => <option key={f} value={f}>{f} Hz</option>)}
      </select>
      <input type="number" value={int_} onChange={e => setInt(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-12" placeholder="dB" step={5} />
      <input type="number" value={dl} onChange={e => setDl(Number(e.target.value))} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white w-12" placeholder="DL" step={0.1} min={0} />
      <span className="text-[8px] text-dark-500">dB DL</span>
      <span className={`text-[8px] ${interpretDL(dl).color}`}>{interpretDL(dl).text}</span>
      <button onClick={() => onAdd({ ear, frequency: freq, intensity: int_, dlDb: dl })} className="bg-siev-600 hover:bg-siev-500 text-white rounded px-1.5 py-0.5 text-[9px]">
        <Plus className="w-2.5 h-2.5" />
      </button>
    </div>
  )
}

function BekesyForm({ ear, onAdd }: { ear: Ear; onAdd: (r: BekesyResult) => void }) {
  const [type, setType] = useState<BekesyJergerType>('I')
  return (
    <div className="flex items-end gap-1 flex-wrap">
      <select value={type} onChange={e => setType(e.target.value as BekesyJergerType)} className="bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[9px] text-white">
        {(['I', 'II', 'III', 'IV', 'V'] as BekesyJergerType[]).map(t => (
          <option key={t} value={t}>Tipo {t}</option>
        ))}
      </select>
      <span className="text-[8px] text-dark-500">{JERGER_DESC[type]}</span>
      <button onClick={() => onAdd({ ear, jergerType: type })} className="bg-siev-600 hover:bg-siev-500 text-white rounded px-1.5 py-0.5 text-[9px]">
        <Plus className="w-2.5 h-2.5" />
      </button>
    </div>
  )
}

// --- Fila de resultado guardado ---
function ResultRow({ children, earColor, onRemove }: { children: React.ReactNode; earColor: string; onRemove: () => void }) {
  return (
    <div className="flex items-center justify-between bg-dark-800/20 rounded px-1.5 py-0.5 text-[9px]">
      <div className={`flex items-center gap-1.5 ${earColor}`}>{children}</div>
      <button onClick={onRemove} className="text-dark-600 hover:text-red-400 transition-colors shrink-0">
        <Trash2 className="w-2.5 h-2.5" />
      </button>
    </div>
  )
}

export default function SupraliminarSection(props: SupraliminarSectionProps) {
  const { data, activeEar } = props
  const [menuOpen, setMenuOpen] = useState(false)
  const [openTests, setOpenTests] = useState<TestType[]>([])

  const addTest = (id: TestType) => {
    if (!openTests.includes(id)) setOpenTests(prev => [...prev, id])
    setMenuOpen(false)
  }

  const removeTest = (id: TestType) => {
    setOpenTests(prev => prev.filter(t => t !== id))
  }

  const earColor = (ear: Ear) => ear === 'od' ? 'text-red-400' : 'text-blue-400'

  const hasResults =
    data.sisi.length > 0 || data.fowler.length > 0 || data.toneDecay.length > 0 ||
    data.luscher.length > 0 || data.reger.length > 0 || data.bekesy.length > 0

  return (
    <div>
      {/* Header: título + botón agregar */}
      <div className="flex items-center justify-between px-3 py-1 bg-dark-900/50 border-b border-dark-800">
        <div className="text-[9px] font-bold text-dark-500 uppercase tracking-wider">Pruebas Supraliminares</div>
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-0.5 px-1.5 py-0.5 bg-dark-800 hover:bg-dark-700 rounded text-[9px] text-dark-400 hover:text-dark-200 transition-colors"
          >
            <Plus className="w-2.5 h-2.5" />
            Agregar
            <ChevronDown className="w-2.5 h-2.5" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-0.5 z-50 bg-dark-800 border border-dark-700 rounded shadow-xl w-56">
              {AVAILABLE_TESTS.map(t => (
                <button
                  key={t.id}
                  onClick={() => addTest(t.id)}
                  className={`w-full text-left px-2 py-1.5 hover:bg-dark-700 transition-colors border-b border-dark-700/50 last:border-0 ${
                    openTests.includes(t.id) ? 'opacity-40' : ''
                  }`}
                  disabled={openTests.includes(t.id)}
                >
                  <div className="text-[10px] font-semibold text-dark-200">{t.name}</div>
                  <div className="text-[8px] text-dark-500 leading-tight">{t.desc}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Tests abiertos */}
      <div className="p-2 space-y-1.5">
      {openTests.map(testId => {
        const def = AVAILABLE_TESTS.find(t => t.id === testId)!
        return (
          <div key={testId} className="bg-dark-800/20 rounded border border-dark-700/40 p-1.5 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-bold text-dark-300">{def.name}</span>
              <button onClick={() => removeTest(testId)} className="text-dark-600 hover:text-red-400 transition-colors">
                <X className="w-3 h-3" />
              </button>
            </div>

            {testId === 'sisi' && (
              <>
                <SISIForm ear={activeEar} onAdd={props.onAddSISI} />
                {data.sisi.map((r, i) => {
                  const interp = interpretSISI(r.positiveResponses)
                  return (
                    <ResultRow key={i} earColor={earColor(r.ear)} onRemove={() => props.onRemoveSISI(i)}>
                      <span className="font-bold">{r.ear.toUpperCase()}</span>
                      <span>{r.frequency}Hz</span>
                      <span>@{r.intensity}dB</span>
                      <span className="font-mono">{r.positiveResponses}/20</span>
                      <span className={interp.color}>{interp.text}</span>
                    </ResultRow>
                  )
                })}
              </>
            )}

            {testId === 'fowler' && (
              <>
                <FowlerForm ear={activeEar} onAdd={props.onAddFowler} />
                {data.fowler.map((r, i) => (
                  <ResultRow key={i} earColor={earColor(r.testEar)} onRemove={() => props.onRemoveFowler(i)}>
                    <span className="font-bold">{r.testEar.toUpperCase()}</span>
                    <span>{r.frequency}Hz</span>
                    <span>{r.steps.length} pasos</span>
                  </ResultRow>
                ))}
              </>
            )}

            {testId === 'toneDecay' && (
              <>
                <ToneDecayForm ear={activeEar} onAdd={props.onAddToneDecay} />
                {data.toneDecay.map((r, i) => {
                  const interp = interpretDecay(r.decayDb)
                  return (
                    <ResultRow key={i} earColor={earColor(r.ear)} onRemove={() => props.onRemoveToneDecay(i)}>
                      <span className="font-bold">{r.ear.toUpperCase()}</span>
                      <span>{r.frequency}Hz</span>
                      <span>{r.initialIntensity}→{r.finalIntensity}dB</span>
                      <span className={interp.color}>{interp.text}</span>
                    </ResultRow>
                  )
                })}
              </>
            )}

            {testId === 'luscher' && (
              <>
                <DLForm ear={activeEar} onAdd={props.onAddLuscher} />
                {data.luscher.map((r, i) => {
                  const interp = interpretDL(r.dlDb)
                  return (
                    <ResultRow key={i} earColor={earColor(r.ear)} onRemove={() => props.onRemoveLuscher(i)}>
                      <span className="font-bold">{r.ear.toUpperCase()}</span>
                      <span>{r.frequency}Hz</span>
                      <span>@{r.intensity}dB</span>
                      <span>DL:{r.dlDb}dB</span>
                      <span className={interp.color}>{interp.text}</span>
                    </ResultRow>
                  )
                })}
              </>
            )}

            {testId === 'reger' && (
              <>
                <DLForm ear={activeEar} onAdd={props.onAddReger} />
                {data.reger.map((r, i) => {
                  const interp = interpretDL(r.dlDb)
                  return (
                    <ResultRow key={i} earColor={earColor(r.ear)} onRemove={() => props.onRemoveReger(i)}>
                      <span className="font-bold">{r.ear.toUpperCase()}</span>
                      <span>{r.frequency}Hz</span>
                      <span>@{r.intensity}dB</span>
                      <span>DL:{r.dlDb}dB</span>
                      <span className={interp.color}>{interp.text}</span>
                    </ResultRow>
                  )
                })}
              </>
            )}

            {testId === 'bekesy' && (
              <>
                <BekesyForm ear={activeEar} onAdd={props.onAddBekesy} />
                {data.bekesy.map((r, i) => (
                  <ResultRow key={i} earColor={earColor(r.ear)} onRemove={() => props.onRemoveBekesy(i)}>
                    <span className="font-bold">{r.ear.toUpperCase()}</span>
                    <span>Tipo {r.jergerType}</span>
                    <span className="text-dark-500">{JERGER_DESC[r.jergerType]}</span>
                  </ResultRow>
                ))}
              </>
            )}
          </div>
        )
      })}

      {/* Resultados existentes sin formulario abierto */}
      {!openTests.length && hasResults && (
        <div className="text-[8px] text-dark-600 italic">Hay resultados guardados. Abre una prueba para verlos.</div>
      )}
      </div>
    </div>
  )
}
