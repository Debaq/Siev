import { useRef, useCallback } from 'react'
import { Play, Pause, SkipBack, SkipForward } from 'lucide-react'
import type { SaccadeMarker } from '../../types/review'

interface TimelineScrubberProps {
    currentTime: number
    duration: number
    isPlaying: boolean
    playbackRate: number
    saccades: SaccadeMarker[]
    onSeek: (time: number) => void
    onTogglePlay: () => void
    onSetPlaybackRate: (rate: number) => void
}

const PLAYBACK_RATES = [0.25, 0.5, 1, 2]

export default function TimelineScrubber({
    currentTime,
    duration,
    isPlaying,
    playbackRate,
    saccades,
    onSeek,
    onTogglePlay,
    onSetPlaybackRate,
}: TimelineScrubberProps) {
    const trackRef = useRef<HTMLDivElement>(null)

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60)
        const s = Math.floor(seconds % 60)
        return `${m}:${s.toString().padStart(2, '0')}`
    }

    const progress = duration > 0 ? (currentTime / duration) * 100 : 0

    const handleTrackClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (!trackRef.current || duration <= 0) return
        const rect = trackRef.current.getBoundingClientRect()
        const x = e.clientX - rect.left
        const ratio = Math.max(0, Math.min(1, x / rect.width))
        onSeek(ratio * duration)
    }, [duration, onSeek])

    const handleTrackDrag = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (e.buttons !== 1 || !trackRef.current || duration <= 0) return
        const rect = trackRef.current.getBoundingClientRect()
        const x = e.clientX - rect.left
        const ratio = Math.max(0, Math.min(1, x / rect.width))
        onSeek(ratio * duration)
    }, [duration, onSeek])

    return (
        <div className="bg-dark-900/80 border-t border-b border-dark-800 px-4 py-2 flex items-center gap-3 shrink-0 select-none">
            {/* Play controls */}
            <div className="flex items-center gap-1">
                <button
                    onClick={() => onSeek(Math.max(0, currentTime - 5))}
                    className="p-1.5 hover:bg-dark-800 rounded text-dark-400 hover:text-white transition-colors"
                    title="-5s"
                >
                    <SkipBack className="w-3.5 h-3.5" />
                </button>
                <button
                    onClick={onTogglePlay}
                    className="p-2 hover:bg-dark-800 rounded-lg text-dark-300 hover:text-white transition-colors"
                >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <button
                    onClick={() => onSeek(Math.min(duration, currentTime + 5))}
                    className="p-1.5 hover:bg-dark-800 rounded text-dark-400 hover:text-white transition-colors"
                    title="+5s"
                >
                    <SkipForward className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Time display */}
            <span className="text-xs text-dark-400 font-mono w-[80px] shrink-0">
                {formatTime(currentTime)} / {formatTime(duration)}
            </span>

            {/* Scrub track */}
            <div
                ref={trackRef}
                className="flex-1 h-6 relative cursor-pointer group"
                onClick={handleTrackClick}
                onMouseMove={handleTrackDrag}
            >
                {/* Background track */}
                <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-1.5 bg-dark-800 rounded-full">
                    {/* Saccade markers */}
                    {duration > 0 && saccades.map((s, i) => (
                        <div
                            key={i}
                            className="absolute top-0 h-full bg-amber-500/30 rounded"
                            style={{
                                left: `${(s.start_time / duration) * 100}%`,
                                width: `${Math.max(0.2, ((s.end_time - s.start_time) / duration) * 100)}%`,
                            }}
                        />
                    ))}
                    {/* Progress */}
                    <div
                        className="absolute top-0 left-0 h-full bg-siev-500 rounded-full transition-[width] duration-75"
                        style={{ width: `${progress}%` }}
                    />
                </div>
                {/* Thumb */}
                <div
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-siev-400 rounded-full shadow-md border-2 border-dark-950 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ left: `calc(${progress}% - 6px)` }}
                />
            </div>

            {/* Playback rate */}
            <div className="flex items-center gap-1">
                {PLAYBACK_RATES.map(rate => (
                    <button
                        key={rate}
                        onClick={() => onSetPlaybackRate(rate)}
                        className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
                            playbackRate === rate
                                ? 'bg-siev-500/20 text-siev-400 border border-siev-500/30'
                                : 'text-dark-500 hover:text-dark-300 hover:bg-dark-800'
                        }`}
                    >
                        {rate}x
                    </button>
                ))}
            </div>
        </div>
    )
}
