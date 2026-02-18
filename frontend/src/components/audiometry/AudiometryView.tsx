import { useEffect } from 'react'
import StatusBar from '../StatusBar'
import AudiometryControlPanel from './AudiometryControlPanel'
import Audiogram from './tonal/Audiogram'
import ThresholdTable from './tonal/ThresholdTable'
import SpeechAudiogram from './vocal/SpeechAudiogram'
import SpeechDataEntry from './vocal/SpeechDataEntry'
import AcumetryPanel from './AcumetryPanel'
import SupraliminarSection from './SupraliminarSection'
import SupraliminarPanel from './supraliminar/SupraliminarPanel'
import HighFreqAudiogram from './alta_frecuencia/HighFreqAudiogram'
import { useAudiometry } from '../../hooks/useAudiometry'
import type { ConductionType } from '../../types/audiometry'

interface AudiometryViewProps {
  testType: string
  patientName: string | null
  sessionId: number | null
  recordingId: number | null
  onSelectTest: () => void
  onSelectPatient: () => void
}

const MARK_MODES: { id: ConductionType; label: string }[] = [
  { id: 'aerea', label: 'Aérea' },
  { id: 'osea', label: 'Ósea' },
  { id: 'ldl', label: 'LDL' },
]

export default function AudiometryView({
  testType,
  patientName,
  sessionId,
  recordingId,
  onSelectTest,
  onSelectPatient,
}: AudiometryViewProps) {
  const audiometry = useAudiometry(sessionId, recordingId)

  useEffect(() => {
    audiometry.load()
  }, [recordingId])

  useEffect(() => {
    switch (testType) {
      case 'audio_tonal_liminar':
      case 'audio_vocal':
        audiometry.setActiveSubView('tonal')
        break
      case 'audio_supraliminar':
        audiometry.setActiveSubView('supraliminar')
        break
      case 'audio_altas_frecuencias':
        audiometry.setActiveSubView('alta_frecuencia')
        break
    }
  }, [testType])

  const renderMainContent = () => {
    switch (audiometry.activeSubView) {
      case 'tonal':
      case 'vocal':
        return (
          <div className="h-full flex flex-col">
            {/* Barra de controles */}
            <div className="flex items-center gap-3 px-3 py-1.5 bg-dark-900 border-b border-dark-800 shrink-0">
              {/* Modo de marcado: Aérea, Ósea, LDL */}
              <div className="flex gap-1">
                {MARK_MODES.map(m => (
                  <button
                    key={m.id}
                    onClick={() => audiometry.setActiveConduction(m.id)}
                    className={`px-2.5 py-1 rounded text-[10px] font-semibold transition-colors ${
                      audiometry.activeConduction === m.id
                        ? 'bg-siev-600 text-white'
                        : 'bg-dark-800 text-dark-400 hover:text-dark-200 hover:bg-dark-700'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              <div className="w-px h-4 bg-dark-700" />

              {/* Oído: OD / OI */}
              <div className="flex gap-1">
                <button
                  onClick={() => audiometry.setActiveEar('od')}
                  className={`px-2.5 py-1 rounded text-[10px] font-bold transition-colors ${
                    audiometry.activeEar === 'od'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-dark-800 text-dark-400 hover:bg-dark-700 border border-transparent'
                  }`}
                >
                  OD
                </button>
                <button
                  onClick={() => audiometry.setActiveEar('oi')}
                  className={`px-2.5 py-1 rounded text-[10px] font-bold transition-colors ${
                    audiometry.activeEar === 'oi'
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      : 'bg-dark-800 text-dark-400 hover:bg-dark-700 border border-transparent'
                  }`}
                >
                  OI
                </button>
              </div>

              <div className="w-px h-4 bg-dark-700" />

              {/* MKG */}
              <button
                onClick={() => audiometry.setActiveMasking(!audiometry.activeMasking)}
                className={`px-2.5 py-1 rounded text-[10px] font-bold transition-colors ${
                  audiometry.activeMasking
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-dark-800 text-dark-400 hover:bg-dark-700 border border-transparent'
                }`}
              >
                MKG
              </button>
            </div>

            {/* Contenido: Audiograma (3/5) + Logoaudiometría (2/5) */}
            <div className="flex-1 flex min-h-0">
              {/* Audiometría */}
              <div className="w-3/5 flex flex-col min-w-0 border-r border-dark-700">
                <div className="text-[9px] font-bold text-dark-500 uppercase tracking-wider px-3 py-1 bg-dark-900/50 border-b border-dark-800 shrink-0">Audiometría</div>
                <div className="flex-1 min-h-0">
                  <Audiogram
                    thresholds={audiometry.data.tonal.thresholds}
                    activeEar={audiometry.activeEar}
                    activeConduction={audiometry.activeConduction}
                    activeMasking={audiometry.activeMasking}
                    onClickPoint={audiometry.addThreshold}
                  />
                </div>
                <div className="shrink-0 border-t border-dark-700 p-2 bg-dark-900/50 max-h-[120px] overflow-y-auto custom-scrollbar">
                  <ThresholdTable
                    thresholds={audiometry.data.tonal.thresholds}
                    onRemove={audiometry.removeThreshold}
                  />
                </div>
              </div>

              {/* Columna derecha: Acumetría + Logo + Supraliminares */}
              <div className="w-2/5 flex flex-col min-w-0 overflow-y-auto custom-scrollbar">
                {/* Acumetría */}
                <div className="shrink-0 border-b border-dark-700 bg-dark-900/30">
                  <div className="text-[9px] font-bold text-dark-500 uppercase tracking-wider px-3 pt-1.5">Acumetría</div>
                  <AcumetryPanel
                    acumetry={audiometry.data.acumetry}
                    onUpdate={audiometry.updateAcumetry}
                  />
                </div>
                {/* Logoaudiometría */}
                <div className="text-[9px] font-bold text-dark-500 uppercase tracking-wider px-3 py-1 bg-dark-900/50 border-b border-dark-800 shrink-0">Logoaudiometría</div>
                <div className="shrink-0 border-b border-dark-700">
                  <SpeechDataEntry
                    vocal={audiometry.data.vocal}
                    onUpdateSDT={audiometry.updateSDT}
                    onUpdateSRT={audiometry.updateSRT}
                    onUpdateUMD={audiometry.updateUMD}
                    onRemoveUMD={audiometry.removeUMD}
                  />
                </div>
                {/* Curvas de logoaudiometría */}
                <div className="h-[220px] shrink-0 border-b border-dark-700 overflow-hidden">
                  <SpeechAudiogram
                    vocal={audiometry.data.vocal}
                  />
                </div>
                {/* Pruebas Supraliminares */}
                <div className="shrink-0">
                  <SupraliminarSection
                    data={audiometry.data.supraliminar}
                    activeEar={audiometry.activeEar}
                    onAddSISI={audiometry.addSISI}
                    onRemoveSISI={audiometry.removeSISI}
                    onAddFowler={audiometry.addFowler}
                    onRemoveFowler={audiometry.removeFowler}
                    onAddToneDecay={audiometry.addToneDecay}
                    onRemoveToneDecay={audiometry.removeToneDecay}
                    onAddLuscher={audiometry.addLuscher}
                    onRemoveLuscher={audiometry.removeLuscher}
                    onAddReger={audiometry.addReger}
                    onRemoveReger={audiometry.removeReger}
                    onAddBekesy={audiometry.addBekesy}
                    onRemoveBekesy={audiometry.removeBekesy}
                  />
                </div>
              </div>
            </div>
          </div>
        )

      case 'supraliminar':
        return (
          <SupraliminarPanel
            data={audiometry.data.supraliminar}
            activeEar={audiometry.activeEar}
            onAddSISI={audiometry.addSISI}
            onRemoveSISI={audiometry.removeSISI}
            onAddFowler={audiometry.addFowler}
            onRemoveFowler={audiometry.removeFowler}
            onAddToneDecay={audiometry.addToneDecay}
            onRemoveToneDecay={audiometry.removeToneDecay}
          />
        )

      case 'alta_frecuencia':
        return (
          <HighFreqAudiogram
            thresholds={audiometry.data.highFreq.thresholds}
            activeEar={audiometry.activeEar}
            onClickPoint={audiometry.addHighFreqThreshold}
          />
        )
    }
  }

  return (
    <div className="h-full flex flex-col font-sans text-xs">
      <StatusBar
        hardwareStatus="offline"
        fps={0}
        recording={false}
        testType={testType}
        patientName={patientName}
        onSelectTest={onSelectTest}
        onSelectPatient={onSelectPatient}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Área principal */}
        <div className="flex-1 flex flex-col min-w-0 bg-dark-950">
          <div className="flex-1 overflow-hidden">
            {renderMainContent()}
          </div>
        </div>

        {/* Panel de control lateral */}
        <div className="w-[200px] bg-dark-900 border-l border-dark-800 flex flex-col shrink-0 z-20 shadow-xl">
          <AudiometryControlPanel
            activeSubView={audiometry.activeSubView}
            classifications={audiometry.classifications}
            notes={audiometry.data.notes}
            saving={audiometry.saving}
            onSetSubView={audiometry.setActiveSubView}
            onSetNotes={audiometry.setNotes}
            onSave={audiometry.save}
            onClear={audiometry.clearAll}
          />
        </div>
      </div>

      <footer className="bg-dark-950 border-t border-dark-800 px-3 py-1 text-[10px] text-dark-600 flex justify-between items-center shrink-0 select-none">
        <span>Evaluación Audiológica — SIEV</span>
        <span>v1.0.0</span>
      </footer>
    </div>
  )
}
