import { useState, useRef, useCallback, useEffect } from 'react'
import { PosturalPosition } from '../types/config'

export interface UsePhasePlaybackReturn {
    isPlaying: boolean
    currentPhaseIndex: number
    elapsedInPhase: number
    phaseProgress: number
    play: (phases: PosturalPosition[], startFromIndex?: number) => void
    pause: () => void
    resume: () => void
    stop: () => void
}

export function usePhasePlayback(
    onPhaseChange?: (newIndex: number) => void,
): UsePhasePlaybackReturn {
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0)
    const [elapsedInPhase, setElapsedInPhase] = useState(0)
    const [phaseProgress, setPhaseProgress] = useState(0)

    const rafRef = useRef<number | null>(null)
    const startTimeRef = useRef(0)
    const pausedElapsedRef = useRef(0)
    const lastUpdateRef = useRef(0)
    const phasesRef = useRef<PosturalPosition[]>([])
    const phaseIndexRef = useRef(0)
    const isPausedRef = useRef(false)

    const cancelRaf = useCallback(() => {
        if (rafRef.current !== null) {
            cancelAnimationFrame(rafRef.current)
            rafRef.current = null
        }
    }, [])

    const tick = useCallback(() => {
        const now = performance.now()
        if (now - lastUpdateRef.current >= 100) {
            const elapsed = pausedElapsedRef.current + (now - startTimeRef.current) / 1000
            const phases = phasesRef.current
            const idx = phaseIndexRef.current

            if (idx >= phases.length) {
                cancelRaf()
                setIsPlaying(false)
                return
            }

            const duration = phases[idx].default_duration_seconds
            if (elapsed >= duration) {
                // Advance to next phase
                const nextIdx = idx + 1
                if (nextIdx >= phases.length) {
                    // Done — all phases complete
                    cancelRaf()
                    setIsPlaying(false)
                    setElapsedInPhase(duration)
                    setPhaseProgress(1)
                    return
                }
                phaseIndexRef.current = nextIdx
                pausedElapsedRef.current = 0
                startTimeRef.current = now
                setCurrentPhaseIndex(nextIdx)
                setElapsedInPhase(0)
                setPhaseProgress(0)
                onPhaseChange?.(nextIdx)
            } else {
                setElapsedInPhase(elapsed)
                setPhaseProgress(duration > 0 ? elapsed / duration : 0)
            }
            lastUpdateRef.current = now
        }
        rafRef.current = requestAnimationFrame(tick)
    }, [cancelRaf, onPhaseChange])

    const play = useCallback((phases: PosturalPosition[], startFromIndex = 0) => {
        cancelRaf()
        phasesRef.current = phases
        phaseIndexRef.current = startFromIndex
        pausedElapsedRef.current = 0
        startTimeRef.current = performance.now()
        lastUpdateRef.current = 0
        isPausedRef.current = false
        setIsPlaying(true)
        setCurrentPhaseIndex(startFromIndex)
        setElapsedInPhase(0)
        setPhaseProgress(0)
        onPhaseChange?.(startFromIndex)
        rafRef.current = requestAnimationFrame(tick)
    }, [tick, cancelRaf, onPhaseChange])

    const pause = useCallback(() => {
        if (!isPlaying || isPausedRef.current) return
        cancelRaf()
        pausedElapsedRef.current += (performance.now() - startTimeRef.current) / 1000
        isPausedRef.current = true
    }, [isPlaying, cancelRaf])

    const resume = useCallback(() => {
        if (!isPlaying || !isPausedRef.current) return
        startTimeRef.current = performance.now()
        lastUpdateRef.current = 0
        isPausedRef.current = false
        rafRef.current = requestAnimationFrame(tick)
    }, [isPlaying, tick])

    const stop = useCallback(() => {
        cancelRaf()
        setIsPlaying(false)
        isPausedRef.current = false
        pausedElapsedRef.current = 0
        setElapsedInPhase(0)
        setPhaseProgress(0)
    }, [cancelRaf])

    // Cleanup on unmount
    useEffect(() => cancelRaf, [cancelRaf])

    return {
        isPlaying,
        currentPhaseIndex,
        elapsedInPhase,
        phaseProgress,
        play,
        pause,
        resume,
        stop,
    }
}
