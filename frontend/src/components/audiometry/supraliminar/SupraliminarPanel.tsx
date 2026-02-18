import { useState } from 'react'
import type { SupraliminarData, Ear } from '../../../types/audiometry'
import type { SISIResult, FowlerResult, ToneDecayResult } from '../../../types/audiometry'
import SISITest from './SISITest'
import FowlerTest from './FowlerTest'
import ToneDecayTest from './ToneDecayTest'

type SupraTab = 'sisi' | 'fowler' | 'tone_decay'

interface SupraliminarPanelProps {
  data: SupraliminarData
  activeEar: Ear
  onAddSISI: (result: SISIResult) => void
  onRemoveSISI: (index: number) => void
  onAddFowler: (result: FowlerResult) => void
  onRemoveFowler: (index: number) => void
  onAddToneDecay: (result: ToneDecayResult) => void
  onRemoveToneDecay: (index: number) => void
}

const TABS: { id: SupraTab; label: string }[] = [
  { id: 'sisi', label: 'SISI' },
  { id: 'fowler', label: 'Fowler' },
  { id: 'tone_decay', label: 'Tone Decay' },
]

export default function SupraliminarPanel({
  data,
  activeEar,
  onAddSISI,
  onRemoveSISI,
  onAddFowler,
  onRemoveFowler,
  onAddToneDecay,
  onRemoveToneDecay,
}: SupraliminarPanelProps) {
  const [activeTab, setActiveTab] = useState<SupraTab>('sisi')

  return (
    <div className="h-full flex flex-col">
      {/* Tabs */}
      <div className="flex border-b border-dark-700 shrink-0">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-siev-400 border-b-2 border-siev-500 bg-dark-800/50'
                : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800/30'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {activeTab === 'sisi' && (
          <SISITest
            results={data.sisi}
            activeEar={activeEar}
            onAdd={onAddSISI}
            onRemove={onRemoveSISI}
          />
        )}
        {activeTab === 'fowler' && (
          <FowlerTest
            results={data.fowler}
            activeEar={activeEar}
            onAdd={onAddFowler}
            onRemove={onRemoveFowler}
          />
        )}
        {activeTab === 'tone_decay' && (
          <ToneDecayTest
            results={data.toneDecay}
            activeEar={activeEar}
            onAdd={onAddToneDecay}
            onRemove={onRemoveToneDecay}
          />
        )}
      </div>
    </div>
  )
}
