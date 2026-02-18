import { useState } from 'react'
import { X, RotateCcw, Check, Search, Zap, Unlock } from 'lucide-react'
import { PosturalTestDefinition } from '../types/config'
import {
    VPPB_PROVOCATION_TESTS,
    VPPB_LIBERATION_TESTS,
    VPPB_REPOSITIONING_TESTS,
} from '../data/vppbTests'

interface PositionalProtocolModalProps {
    enabledTests: string[]
    onSelect: (test: PosturalTestDefinition) => void
    onCancel: () => void
}

type TabId = 'provocation' | 'liberation' | 'repositioning'

const TABS: { id: TabId; label: string; icon: typeof Search; tests: PosturalTestDefinition[] }[] = [
    { id: 'provocation', label: 'Provocaci\u00f3n', icon: Search, tests: VPPB_PROVOCATION_TESTS },
    { id: 'liberation', label: 'Liberaci\u00f3n', icon: Zap, tests: VPPB_LIBERATION_TESTS },
    { id: 'repositioning', label: 'Reposici\u00f3n', icon: Unlock, tests: VPPB_REPOSITIONING_TESTS },
]

function PositionalProtocolModal({ enabledTests, onSelect, onCancel }: PositionalProtocolModalProps) {
    const [activeTab, setActiveTab] = useState<TabId>('provocation')

    const currentTab = TABS.find(t => t.id === activeTab)!
    const filteredTests = currentTab.tests.filter(t => enabledTests.includes(t.id))

    return (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-8">
            <div className="bg-dark-900 border border-dark-700 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-orange-500/10">
                            <RotateCcw className="w-6 h-6 text-orange-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">Pruebas Posicionales</h2>
                            <p className="text-sm text-dark-400">Seleccione la maniobra a realizar</p>
                        </div>
                    </div>
                    <button
                        onClick={onCancel}
                        className="p-2 hover:bg-dark-800 rounded-lg text-dark-400 hover:text-white transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-dark-700">
                    {TABS.map(tab => {
                        const Icon = tab.icon
                        const count = tab.tests.filter(t => enabledTests.includes(t.id)).length
                        const isActive = activeTab === tab.id
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors relative ${
                                    isActive
                                        ? 'text-orange-400'
                                        : 'text-dark-400 hover:text-dark-200'
                                }`}
                            >
                                <Icon className="w-4 h-4" />
                                <span>{tab.label}</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                                    isActive ? 'bg-orange-500/20 text-orange-400' : 'bg-dark-800 text-dark-500'
                                }`}>
                                    {count}
                                </span>
                                {isActive && (
                                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-500" />
                                )}
                            </button>
                        )
                    })}
                </div>

                {/* Test Cards */}
                <div className="flex-1 overflow-y-auto p-6">
                    {filteredTests.length === 0 ? (
                        <div className="text-center py-12 text-dark-500 text-sm">
                            No hay pruebas habilitadas en esta categor&iacute;a.
                            <br />
                            <span className="text-xs">Active pruebas en Configuraci&oacute;n &gt; Postural &gt; Pruebas</span>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {filteredTests.map(test => {
                                const sideLabel = test.side === 'right' ? 'Derecho' : test.side === 'left' ? 'Izquierdo' : ''
                                const canalLabel = test.canal === 'posterior' ? 'CSP' : test.canal === 'lateral' ? 'CSL' : 'CSA'
                                return (
                                    <button
                                        key={test.id}
                                        onClick={() => onSelect(test)}
                                        className="flex flex-col p-5 rounded-xl border border-dark-700 bg-dark-800/50 hover:bg-dark-800 hover:border-orange-500/40 transition-all group text-left"
                                    >
                                        <div className="flex items-center gap-3 mb-3">
                                            <div className="w-9 h-9 rounded-lg bg-orange-500/15 border border-orange-500/25 flex items-center justify-center shrink-0">
                                                <RotateCcw className="w-4.5 h-4.5 text-orange-400" />
                                            </div>
                                            <h3 className="text-sm font-bold text-white group-hover:text-orange-400 transition-colors">
                                                {test.name}
                                            </h3>
                                        </div>

                                        <div className="flex items-center gap-2 text-xs text-dark-400 mb-3">
                                            <span className="px-1.5 py-0.5 rounded bg-dark-700 text-dark-300 text-[10px] font-medium">
                                                {canalLabel}
                                            </span>
                                            {sideLabel && (
                                                <span className="px-1.5 py-0.5 rounded bg-dark-700 text-dark-300 text-[10px] font-medium">
                                                    {sideLabel}
                                                </span>
                                            )}
                                            <span>{test.positions.length} posiciones</span>
                                        </div>

                                        <div className="flex items-center justify-between mt-auto pt-3 border-t border-dark-700">
                                            <div className="flex items-center gap-1">
                                                {test.positions.map((_, i) => (
                                                    <div key={i} className="w-1.5 h-1.5 rounded-full bg-dark-600" />
                                                ))}
                                            </div>
                                            <span className="text-[10px] text-dark-500 group-hover:text-orange-400 flex items-center gap-1 transition-colors">
                                                <Check className="w-3 h-3" />
                                                Seleccionar
                                            </span>
                                        </div>
                                    </button>
                                )
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default PositionalProtocolModal
