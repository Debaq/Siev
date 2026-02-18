import React from 'react'
import { RotateCcw } from 'lucide-react'
import { AppConfig } from '../../../types/config'
import { VPPB_PROVOCATION_TESTS, VPPB_LIBERATION_TESTS, VPPB_REPOSITIONING_TESTS } from '../../../data/vppbTests'

interface TestsTabProps {
    config: AppConfig
    updateConfig: (path: string, value: any) => void
}

export const TestsTab: React.FC<TestsTabProps> = ({ config, updateConfig }) => {
    const enabledTests = config.postural?.enabled_tests ?? []

    const toggleTest = (testId: string) => {
        const newEnabled = enabledTests.includes(testId)
            ? enabledTests.filter(id => id !== testId)
            : [...enabledTests, testId]
        updateConfig('postural.enabled_tests', newEnabled)
    }

    const allIds = [...VPPB_PROVOCATION_TESTS, ...VPPB_LIBERATION_TESTS, ...VPPB_REPOSITIONING_TESTS].map(t => t.id)
    const allEnabled = allIds.every(id => enabledTests.includes(id))

    const toggleAll = () => {
        if (allEnabled) {
            updateConfig('postural.enabled_tests', [])
        } else {
            updateConfig('postural.enabled_tests', allIds)
        }
    }

    return (
        <div className="space-y-6 py-4">
            <div className="flex items-center justify-between">
                <p className="text-sm text-dark-300">
                    Seleccione los tests VPPB disponibles en la vista de evaluación.
                </p>
                <button
                    onClick={toggleAll}
                    className="text-xs text-siev-400 hover:text-siev-300 transition-colors"
                >
                    {allEnabled ? 'Desmarcar todos' : 'Marcar todos'}
                </button>
            </div>

            {[
                { label: 'Provocación', tests: VPPB_PROVOCATION_TESTS },
                { label: 'Liberación', tests: VPPB_LIBERATION_TESTS },
                { label: 'Reposición', tests: VPPB_REPOSITIONING_TESTS },
            ].map(section => (
                <div key={section.label}>
                    <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-3">
                        {section.label}
                    </h3>
                    <div className="space-y-2">
                        {section.tests.map(test => {
                            const enabled = enabledTests.includes(test.id)
                            const sideLabel = test.side === 'right' ? 'D' : test.side === 'left' ? 'I' : ''
                            return (
                                <label
                                    key={test.id}
                                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                                        enabled
                                            ? 'border-orange-500/30 bg-orange-500/5'
                                            : 'border-dark-700/30 bg-dark-900/30 opacity-60'
                                    }`}
                                >
                                    <input
                                        type="checkbox"
                                        checked={enabled}
                                        onChange={() => toggleTest(test.id)}
                                        className="rounded border-dark-600"
                                    />
                                    <RotateCcw className="w-4 h-4 text-orange-400 shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <span className="text-sm font-medium text-white">{test.name}</span>
                                        <span className="text-xs text-dark-400 ml-2">
                                            {test.positions.length} pos • {test.canal} {sideLabel}
                                        </span>
                                    </div>
                                </label>
                            )
                        })}
                    </div>
                </div>
            ))}
        </div>
    )
}
