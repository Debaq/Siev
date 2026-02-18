import { useMemo } from 'react'
import { RotateCcw, ArrowRight } from 'lucide-react'
import { PosturalTestDefinition } from '../../types/config'
import { getAllTestsByCategory } from '../../data/vppbTests'

interface PosturalTestSelectorProps {
    enabledTests: string[]
    customTests?: PosturalTestDefinition[]
    onSelect: (test: PosturalTestDefinition) => void
    onClose: () => void
}

function TestCard({ test, onSelect }: { test: PosturalTestDefinition; onSelect: () => void }) {
    const sideLabel = test.side === 'right' ? 'D' : test.side === 'left' ? 'I' : ''
    const canalLabel = test.canal === 'posterior' ? 'CSP' : test.canal === 'lateral' ? 'CSL' : 'CSA'

    return (
        <button
            onClick={onSelect}
            className="flex items-center gap-3 p-3 rounded-lg border border-orange-500/20 bg-orange-500/5 hover:bg-orange-500/10 transition-all hover:scale-[1.02] group text-left w-full"
        >
            <div className="w-8 h-8 rounded-lg bg-orange-500/15 border border-orange-500/25 flex items-center justify-center shrink-0">
                <RotateCcw className="w-4 h-4 text-orange-400" />
            </div>
            <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-white group-hover:text-orange-400 transition-colors truncate">
                    {test.name}
                </h4>
                <div className="flex items-center gap-2 text-[10px] text-dark-400">
                    <span className="px-1 py-0.5 rounded bg-dark-800 text-dark-300">{canalLabel}</span>
                    {sideLabel && <span className="px-1 py-0.5 rounded bg-dark-800 text-dark-300">{sideLabel}</span>}
                    <span>{test.positions.length} posiciones</span>
                </div>
            </div>
            <ArrowRight className="w-4 h-4 text-dark-500 group-hover:text-orange-400 transition-colors" />
        </button>
    )
}

export default function PosturalTestSelector({ enabledTests, customTests = [], onSelect }: PosturalTestSelectorProps) {
    const { provocation, liberation, repositioning } = useMemo(
        () => getAllTestsByCategory(customTests),
        [customTests]
    )

    const provTests = provocation.filter(t => enabledTests.includes(t.id))
    const libTests = liberation.filter(t => enabledTests.includes(t.id))
    const repoTests = repositioning.filter(t => enabledTests.includes(t.id))

    return (
        <div className="space-y-4">
            {provTests.length > 0 && (
                <div>
                    <h3 className="text-[10px] font-bold text-dark-500 uppercase tracking-wider mb-2 px-1">
                        Provocación
                    </h3>
                    <div className="space-y-1.5">
                        {provTests.map(test => (
                            <TestCard key={test.id} test={test} onSelect={() => onSelect(test)} />
                        ))}
                    </div>
                </div>
            )}

            {libTests.length > 0 && (
                <div>
                    <h3 className="text-[10px] font-bold text-dark-500 uppercase tracking-wider mb-2 px-1">
                        Liberación
                    </h3>
                    <div className="space-y-1.5">
                        {libTests.map(test => (
                            <TestCard key={test.id} test={test} onSelect={() => onSelect(test)} />
                        ))}
                    </div>
                </div>
            )}

            {repoTests.length > 0 && (
                <div>
                    <h3 className="text-[10px] font-bold text-dark-500 uppercase tracking-wider mb-2 px-1">
                        Reposición
                    </h3>
                    <div className="space-y-1.5">
                        {repoTests.map(test => (
                            <TestCard key={test.id} test={test} onSelect={() => onSelect(test)} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
