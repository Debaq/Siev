import { PosturalPosition } from '../../../types/config'

interface PhaseTimelineProps {
    phases: PosturalPosition[]
    selectedIndex: number
    onSelectPhase: (index: number) => void
    playbackProgress?: { phaseIndex: number; progress: number }
}

export default function PhaseTimeline({
    phases,
    selectedIndex,
    onSelectPhase,
    playbackProgress,
}: PhaseTimelineProps) {
    const totalDuration = phases.reduce((sum, p) => sum + p.default_duration_seconds, 0)
    if (totalDuration <= 0) return null

    // Overall progress indicator position
    let trianglePct = 0
    if (playbackProgress) {
        const beforeDuration = phases.slice(0, playbackProgress.phaseIndex).reduce((s, p) => s + p.default_duration_seconds, 0)
        const currentDuration = phases[playbackProgress.phaseIndex]?.default_duration_seconds ?? 0
        trianglePct = ((beforeDuration + currentDuration * playbackProgress.progress) / totalDuration) * 100
    }

    return (
        <div className="space-y-1">
            {/* Triangle indicator */}
            {playbackProgress && (
                <div className="relative h-3">
                    <div
                        className="absolute bottom-0 transition-[left] duration-100 ease-linear"
                        style={{ left: `${Math.min(trianglePct, 100)}%` }}
                    >
                        <div
                            className="absolute bottom-0 -translate-x-1/2"
                            style={{
                                width: 0,
                                height: 0,
                                borderLeft: '5px solid transparent',
                                borderRight: '5px solid transparent',
                                borderTop: '7px solid white',
                            }}
                        />
                    </div>
                </div>
            )}

            {/* Timeline bar */}
            <div className="relative h-8 bg-dark-800 rounded-md overflow-hidden flex">
                {phases.map((phase, i) => {
                    const widthPct = (phase.default_duration_seconds / totalDuration) * 100
                    const isSelected = i === selectedIndex
                    const isPlaybackActive = playbackProgress?.phaseIndex === i

                    return (
                        <button
                            key={phase.id}
                            type="button"
                            onClick={() => onSelectPhase(i)}
                            className={`relative h-full border-r border-dark-700/50 last:border-r-0 transition-colors ${
                                isSelected
                                    ? 'bg-orange-500/30 ring-1 ring-inset ring-orange-500/60'
                                    : 'bg-dark-800 hover:bg-dark-700/50'
                            }`}
                            style={{ width: `${widthPct}%` }}
                        >
                            {/* Playback progress fill */}
                            {isPlaybackActive && playbackProgress && (
                                <div
                                    className="absolute inset-y-0 left-0 bg-orange-500/40 transition-[width] duration-100 ease-linear"
                                    style={{ width: `${playbackProgress.progress * 100}%` }}
                                />
                            )}
                            {/* Label */}
                            <span className={`absolute inset-0 flex items-center justify-center text-[8px] font-medium truncate px-0.5 ${
                                isSelected ? 'text-white' : 'text-dark-400'
                            }`}>
                                {phase.label}
                            </span>
                        </button>
                    )
                })}
            </div>
        </div>
    )
}
