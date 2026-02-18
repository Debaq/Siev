import { useState, useCallback, useMemo } from 'react'
import { CaloricProtocol, CaloricIrrigation } from '../types/config'
import { CompletionStatus } from './useCaloricTimer'

export type StageStatus = 'pending' | 'active' | 'completed'

export interface CaloricStage {
  irrigation: CaloricIrrigation
  status: StageStatus
  completionStatus?: CompletionStatus
}

export interface UseCaloricProtocolReturn {
  protocol: CaloricProtocol | null
  stages: CaloricStage[]
  currentStageIndex: number
  isProtocolActive: boolean
  isProtocolComplete: boolean
  currentStageLabel: string | null
  startProtocol: (protocol: CaloricProtocol) => void
  advanceStage: (completionStatus?: CompletionStatus) => void
  goToStage: (index: number) => void
  addStage: (irrigation: CaloricIrrigation) => void
  redoStage: (index: number) => void
  resetProtocol: () => void
}

export function useCaloricProtocol(): UseCaloricProtocolReturn {
  const [protocol, setProtocol] = useState<CaloricProtocol | null>(null)
  const [stages, setStages] = useState<CaloricStage[]>([])
  const [currentStageIndex, setCurrentStageIndex] = useState(-1)

  const isProtocolActive = currentStageIndex >= 0 && currentStageIndex < stages.length
  const isProtocolComplete = stages.length > 0 && stages.every(s => s.status === 'completed' && s.completionStatus === 'completada')

  const currentStageLabel = useMemo(() => {
    if (currentStageIndex < 0 || currentStageIndex >= stages.length) return null
    const stage = stages[currentStageIndex]
    if (stage.status !== 'active') return null
    const { temperature, ear } = stage.irrigation
    return `${temperature}°C ${ear.toUpperCase()}`
  }, [stages, currentStageIndex])

  const startProtocol = useCallback((proto: CaloricProtocol) => {
    setProtocol(proto)
    const newStages: CaloricStage[] = proto.irrigations.map((irr, i) => ({
      irrigation: irr,
      status: i === 0 ? 'active' : 'pending',
    }))
    setStages(newStages)
    setCurrentStageIndex(0)
  }, [])

  const advanceStage = useCallback((completionStatus?: CompletionStatus) => {
    setStages(prev => {
      const updated = [...prev]
      const activeIdx = updated.findIndex(s => s.status === 'active')
      if (activeIdx === -1) return prev

      updated[activeIdx] = {
        ...updated[activeIdx],
        status: 'completed',
        completionStatus: completionStatus ?? 'completada',
      }

      const nextIdx = activeIdx + 1
      if (nextIdx < updated.length) {
        updated[nextIdx] = { ...updated[nextIdx], status: 'active' }
        setCurrentStageIndex(nextIdx)
      } else {
        setCurrentStageIndex(-1)
      }

      return updated
    })
  }, [])

  const goToStage = useCallback((index: number) => {
    setStages(prev => {
      if (index < 0 || index >= prev.length) return prev
      if (prev[index].status === 'completed') return prev
      const updated = prev.map((s, i) => {
        if (s.status === 'active') return { ...s, status: 'pending' as StageStatus }
        if (i === index) return { ...s, status: 'active' as StageStatus }
        return s
      })
      setCurrentStageIndex(index)
      return updated
    })
  }, [])

  const addStage = useCallback((irrigation: CaloricIrrigation) => {
    setStages(prev => {
      const allCompleted = prev.every(s => s.status === 'completed')
      const newStage: CaloricStage = {
        irrigation,
        status: allCompleted ? 'active' : 'pending',
      }
      const updated = [...prev, newStage]
      if (allCompleted) {
        setCurrentStageIndex(updated.length - 1)
      }
      return updated
    })
  }, [])

  const redoStage = useCallback((index: number) => {
    setStages(prev => {
      if (index < 0 || index >= prev.length) return prev
      if (prev[index].completionStatus === 'completada') return prev

      const updated = prev.map((s, i) => {
        if (s.status === 'active') return { ...s, status: 'pending' as StageStatus }
        if (i === index) return { ...s, status: 'active' as StageStatus, completionStatus: undefined }
        return s
      })
      setCurrentStageIndex(index)
      return updated
    })
  }, [])

  const resetProtocol = useCallback(() => {
    setProtocol(null)
    setStages([])
    setCurrentStageIndex(-1)
  }, [])

  return {
    protocol,
    stages,
    currentStageIndex,
    isProtocolActive,
    isProtocolComplete,
    currentStageLabel,
    startProtocol,
    advanceStage,
    goToStage,
    addStage,
    redoStage,
    resetProtocol,
  }
}
