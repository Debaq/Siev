import { PosturalStage } from '../../hooks/usePosturalProtocol'

interface PosturalTimelineProps {
    testName: string
    stages: PosturalStage[]
    currentStageIndex: number
    elapsedSeconds: number
    totalDuration: number
    progress: number
    isRunning: boolean
}

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const statusColors: Record<string, string> = {
    pending: 'bg-dark-700',
    active: 'bg-orange-500',
    completed: 'bg-green-500',
    skipped: 'bg-yellow-500/60',
}

export default function PosturalTimeline({
    testName,
    stages,
    currentStageIndex,
    elapsedSeconds,
    totalDuration,
    progress,
    isRunning,
}: PosturalTimelineProps) {
    if (stages.length === 0) return null

    // Compute total test duration for timeline proportions
    const totalTestDuration = stages.reduce((sum, s) => sum + s.duration, 0)
    if (totalTestDuration <= 0) return null

    // Compute cumulative positions for each stage
    const stageMeta = stages.map((stage, i) => {
        const startPct = stages.slice(0, i).reduce((sum, s) => sum + s.duration, 0) / totalTestDuration * 100
        const widthPct = stage.duration / totalTestDuration * 100
        return { startPct, widthPct }
    })

    // Overall progress across the whole test
    const completedDuration = stages.slice(0, currentStageIndex).reduce((sum, s) => sum + s.duration, 0)
    const overallProgressPct = currentStageIndex >= 0
        ? ((completedDuration + elapsedSeconds) / totalTestDuration) * 100
        : 0

    const currentLabel = currentStageIndex >= 0 && currentStageIndex < stages.length
        ? stages[currentStageIndex].position.label
        : ''

    return (
        <div className="h-[56px] bg-dark-900 border-t border-b border-dark-800 px-3 py-1 flex flex-col justify-center select-none shrink-0">
            {/* Header row */}
            <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-dark-400 truncate">
                    {testName} <span className="text-dark-500">•</span> {currentLabel}
                </span>
                <div className="flex items-center gap-2">
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-medium bg-orange-500/20 text-orange-400">
                        Pos {currentStageIndex + 1}/{stages.length}
                    </span>
                    <span className="text-[10px] text-dark-500 tabular-nums">
                        {formatTime(elapsedSeconds)} / {formatTime(totalDuration)}
                    </span>
                </div>
            </div>

            {/* Triangle indicator */}
            <div className="relative h-3 shrink-0">
                {isRunning && (
                    <div
                        className="absolute bottom-0 transition-[left] duration-100 ease-linear"
                        style={{ left: `${Math.min(overallProgressPct, 100)}%` }}
                    >
                        <div
                            className="absolute bottom-0 -translate-x-1/2"
                            style={{
                                width: 0,
                                height: 0,
                                borderLeft: '6px solid transparent',
                                borderRight: '6px solid transparent',
                                borderTop: '8px solid white',
                            }}
                        />
                    </div>
                )}
            </div>

            {/* Timeline bar */}
            <div className="relative h-3 bg-dark-800 rounded-sm overflow-hidden flex">
                {stages.map((stage, i) => (
                    <div
                        key={i}
                        className="relative h-full border-r border-dark-700/50 last:border-r-0"
                        style={{ width: `${stageMeta[i].widthPct}%` }}
                    >
                        {/* Status fill */}
                        <div className={`absolute inset-0 ${statusColors[stage.status]} opacity-30`} />

                        {/* Active position progress */}
                        {stage.status === 'active' && isRunning && (
                            <div
                                className="absolute inset-y-0 left-0 bg-orange-500/50 transition-[width] duration-100 ease-linear"
                                style={{ width: `${progress * 100}%` }}
                            />
                        )}

                        {/* Label */}
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className={`text-[8px] font-medium truncate px-0.5 ${
                                stage.status === 'active' ? 'text-white' : 'text-dark-400'
                            }`}>
                                {stage.position.label}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
