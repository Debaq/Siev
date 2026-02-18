import { useState, useRef, useCallback } from 'react'
import { CaloricProtocolTiming } from '../types/config'

export interface CaloricTimerPhase {
  name: string
  key: 'delay' | 'irrigation' | 'recording' | 'torok' | 'ofi'
}

export interface UseCaloricTimerReturn {
  elapsedSeconds: number
  currentPhase: CaloricTimerPhase
  progress: number
  isRunning: boolean
  totalDuration: number
  start: () => void
  stop: () => void
  reset: () => void
}

export type CompletionStatus = 'fallida' | 'incompleta' | 'sin_ofi' | 'completada'

export function computeCompletionStatus(elapsedSeconds: number, timing: CaloricProtocolTiming): CompletionStatus {
  const recordingElapsed = elapsedSeconds - timing.delay

  const torokStart = timing.torok.start_time
  const torokEnd = torokStart + timing.torok.duration
  const ofiEnd = timing.ofi.start_time + timing.ofi.duration

  if (recordingElapsed < torokStart) return 'fallida'
  if (recordingElapsed < torokEnd) return 'incompleta'
  if (recordingElapsed < ofiEnd) return 'sin_ofi'
  return 'completada'
}

export function computePhase(elapsed: number, timing: CaloricProtocolTiming): CaloricTimerPhase {
  if (elapsed < timing.delay) {
    return { name: 'Espera', key: 'delay' }
  }

  const recordingElapsed = elapsed - timing.delay

  // Irrigation period: immediately after delay
  const irrigationDur = timing.irrigation_duration ?? 0
  if (irrigationDur > 0 && recordingElapsed < irrigationDur) {
    return { name: 'Irrigación', key: 'irrigation' }
  }

  const torokStart = timing.torok.start_time
  const torokEnd = torokStart + timing.torok.duration
  if (recordingElapsed >= torokStart && recordingElapsed < torokEnd) {
    return { name: 'Evaluación Török', key: 'torok' }
  }

  const ofiStart = timing.ofi.start_time
  const ofiEnd = ofiStart + timing.ofi.duration
  if (recordingElapsed >= ofiStart && recordingElapsed < ofiEnd) {
    return { name: 'Índice de Fijación', key: 'ofi' }
  }

  return { name: 'Registro', key: 'recording' }
}

export function useCaloricTimer(timing: CaloricProtocolTiming | null): UseCaloricTimerReturn {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [isRunning, setIsRunning] = useState(false)

  const rafRef = useRef<number | null>(null)
  const startTimeRef = useRef<number>(0)
  const lastUpdateRef = useRef<number>(0)
  const timingRef = useRef(timing)
  timingRef.current = timing

  const totalDuration = timing ? timing.delay + timing.total_duration : 0

  const tick = useCallback(() => {
    const now = performance.now()
    // Throttle state updates to ~100ms
    if (now - lastUpdateRef.current >= 100) {
      const elapsed = (now - startTimeRef.current) / 1000
      setElapsedSeconds(elapsed)
      lastUpdateRef.current = now
    }
    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const start = useCallback(() => {
    if (rafRef.current !== null) return
    startTimeRef.current = performance.now()
    lastUpdateRef.current = 0
    setElapsedSeconds(0)
    setIsRunning(true)
    rafRef.current = requestAnimationFrame(tick)
  }, [tick])

  const stop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    setIsRunning(false)
  }, [])

  const reset = useCallback(() => {
    setElapsedSeconds(0)
  }, [])

  const currentPhase = timing
    ? computePhase(elapsedSeconds, timing)
    : { name: 'Grabación', key: 'recording' as const }

  const progress = totalDuration > 0
    ? Math.min(elapsedSeconds / totalDuration, 1)
    : 0

  return {
    elapsedSeconds,
    currentPhase,
    progress,
    isRunning,
    totalDuration,
    start,
    stop,
    reset,
  }
}
