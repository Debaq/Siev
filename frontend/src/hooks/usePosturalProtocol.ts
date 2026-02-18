import { useState, useCallback, useMemo } from 'react'
import { PosturalTestDefinition, PosturalPosition, SubjectiveSymptomRecord } from '../types/config'

export type PosturalStageStatus = 'pending' | 'active' | 'completed' | 'skipped'

export interface PosturalStage {
    position: PosturalPosition
    status: PosturalStageStatus
    duration: number
    observation?: string
    nystagmusDetected?: boolean
    nystagmusDirection?: string
    symptoms: SubjectiveSymptomRecord[]
}

export interface UsePosturalProtocolReturn {
    test: PosturalTestDefinition | null
    stages: PosturalStage[]
    currentStageIndex: number
    isActive: boolean
    isComplete: boolean
    currentPositionLabel: string | null
    startTest: (test: PosturalTestDefinition) => void
    advancePosition: () => void
    skipPosition: () => void
    goToStage: (index: number) => void
    addObservation: (index: number, obs: string) => void
    markNystagmus: (index: number, detected: boolean, direction?: string) => void
    setSymptom: (stageIndex: number, symptomId: string, value: number) => void
    resetTest: () => void
}

export function usePosturalProtocol(): UsePosturalProtocolReturn {
    const [test, setTest] = useState<PosturalTestDefinition | null>(null)
    const [stages, setStages] = useState<PosturalStage[]>([])
    const [currentStageIndex, setCurrentStageIndex] = useState(-1)

    const isActive = currentStageIndex >= 0 && currentStageIndex < stages.length
    const isComplete = stages.length > 0 && stages.every(s => s.status === 'completed' || s.status === 'skipped')

    const currentPositionLabel = useMemo(() => {
        if (currentStageIndex < 0 || currentStageIndex >= stages.length) return null
        const stage = stages[currentStageIndex]
        if (stage.status !== 'active') return null
        return stage.position.label
    }, [stages, currentStageIndex])

    const startTest = useCallback((testDef: PosturalTestDefinition) => {
        setTest(testDef)
        const newStages: PosturalStage[] = testDef.positions.map((pos, i) => ({
            position: pos,
            status: i === 0 ? 'active' : 'pending',
            duration: pos.default_duration_seconds,
            symptoms: [],
        }))
        setStages(newStages)
        setCurrentStageIndex(0)
    }, [])

    const advancePosition = useCallback(() => {
        setStages(prev => {
            const updated = [...prev]
            const activeIdx = updated.findIndex(s => s.status === 'active')
            if (activeIdx === -1) return prev

            updated[activeIdx] = { ...updated[activeIdx], status: 'completed' }

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

    const skipPosition = useCallback(() => {
        setStages(prev => {
            const updated = [...prev]
            const activeIdx = updated.findIndex(s => s.status === 'active')
            if (activeIdx === -1) return prev

            updated[activeIdx] = { ...updated[activeIdx], status: 'skipped' }

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
            const updated = prev.map((s, i) => {
                if (s.status === 'active') return { ...s, status: 'pending' as PosturalStageStatus }
                if (i === index) return { ...s, status: 'active' as PosturalStageStatus }
                return s
            })
            setCurrentStageIndex(index)
            return updated
        })
    }, [])

    const addObservation = useCallback((index: number, obs: string) => {
        setStages(prev => {
            if (index < 0 || index >= prev.length) return prev
            const updated = [...prev]
            updated[index] = { ...updated[index], observation: obs }
            return updated
        })
    }, [])

    const markNystagmus = useCallback((index: number, detected: boolean, direction?: string) => {
        setStages(prev => {
            if (index < 0 || index >= prev.length) return prev
            const updated = [...prev]
            updated[index] = {
                ...updated[index],
                nystagmusDetected: detected,
                nystagmusDirection: direction,
            }
            return updated
        })
    }, [])

    const setSymptom = useCallback((stageIndex: number, symptomId: string, value: number) => {
        setStages(prev => {
            if (stageIndex < 0 || stageIndex >= prev.length) return prev
            const updated = [...prev]
            const stage = { ...updated[stageIndex] }
            const symptoms = [...stage.symptoms]
            const existingIdx = symptoms.findIndex(s => s.symptom_id === symptomId)
            if (existingIdx >= 0) {
                symptoms[existingIdx] = { symptom_id: symptomId, value }
            } else {
                symptoms.push({ symptom_id: symptomId, value })
            }
            stage.symptoms = symptoms
            updated[stageIndex] = stage
            return updated
        })
    }, [])

    const resetTest = useCallback(() => {
        setTest(null)
        setStages([])
        setCurrentStageIndex(-1)
    }, [])

    return {
        test,
        stages,
        currentStageIndex,
        isActive,
        isComplete,
        currentPositionLabel,
        startTest,
        advancePosition,
        skipPosition,
        goToStage,
        addObservation,
        markNystagmus,
        setSymptom,
        resetTest,
    }
}
