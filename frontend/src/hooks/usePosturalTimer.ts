import { useState, useRef, useCallback } from 'react'

export interface UsePosturalTimerReturn {
    elapsedSeconds: number
    remainingSeconds: number
    totalDuration: number
    progress: number
    isRunning: boolean
    isPaused: boolean
    start: (duration: number) => void
    stop: () => void
    pause: () => void
    resume: () => void
}

export function usePosturalTimer(): UsePosturalTimerReturn {
    const [elapsedSeconds, setElapsedSeconds] = useState(0)
    const [isRunning, setIsRunning] = useState(false)
    const [isPaused, setIsPaused] = useState(false)
    const [totalDuration, setTotalDuration] = useState(0)

    const rafRef = useRef<number | null>(null)
    const startTimeRef = useRef<number>(0)
    const pausedElapsedRef = useRef<number>(0)
    const lastUpdateRef = useRef<number>(0)

    const tick = useCallback(() => {
        const now = performance.now()
        if (now - lastUpdateRef.current >= 100) {
            const elapsed = pausedElapsedRef.current + (now - startTimeRef.current) / 1000
            setElapsedSeconds(elapsed)
            lastUpdateRef.current = now
        }
        rafRef.current = requestAnimationFrame(tick)
    }, [])

    const cancelRaf = useCallback(() => {
        if (rafRef.current !== null) {
            cancelAnimationFrame(rafRef.current)
            rafRef.current = null
        }
    }, [])

    const start = useCallback((duration: number) => {
        cancelRaf()
        setTotalDuration(duration)
        setElapsedSeconds(0)
        setIsRunning(true)
        setIsPaused(false)
        pausedElapsedRef.current = 0
        startTimeRef.current = performance.now()
        lastUpdateRef.current = 0
        rafRef.current = requestAnimationFrame(tick)
    }, [tick, cancelRaf])

    const stop = useCallback(() => {
        cancelRaf()
        setIsRunning(false)
        setIsPaused(false)
        pausedElapsedRef.current = 0
    }, [cancelRaf])

    const pause = useCallback(() => {
        if (!isRunning || isPaused) return
        cancelRaf()
        pausedElapsedRef.current += (performance.now() - startTimeRef.current) / 1000
        setIsPaused(true)
    }, [isRunning, isPaused, cancelRaf])

    const resume = useCallback(() => {
        if (!isRunning || !isPaused) return
        startTimeRef.current = performance.now()
        lastUpdateRef.current = 0
        setIsPaused(false)
        rafRef.current = requestAnimationFrame(tick)
    }, [isRunning, isPaused, tick])

    const remainingSeconds = Math.max(0, totalDuration - elapsedSeconds)
    const progress = totalDuration > 0 ? Math.min(elapsedSeconds / totalDuration, 1) : 0

    return {
        elapsedSeconds,
        remainingSeconds,
        totalDuration,
        progress,
        isRunning,
        isPaused,
        start,
        stop,
        pause,
        resume,
    }
}
