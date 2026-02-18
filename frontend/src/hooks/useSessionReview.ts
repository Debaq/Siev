import { useState, useCallback } from 'react'
import { invoke } from '@tauri-apps/api/core'
import type { SessionReviewPayload, ChartEyeDataPoint, CalibrationSnapshot } from '../types/review'

export function useSessionReview() {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [payload, setPayload] = useState<SessionReviewPayload | null>(null)

    const loadRecording = useCallback(async (recordingId: number) => {
        setLoading(true)
        setError(null)
        try {
            const result = await invoke<SessionReviewPayload>('load_recording_review', { recordingId })
            setPayload(result)
            return result
        } catch (err) {
            const errMsg = typeof err === 'string' ? err : 'Error al cargar la grabacion'
            setError(errMsg)
            console.error('[useSessionReview] loadRecording error:', err)
            return null
        } finally {
            setLoading(false)
        }
    }, [])

    const getEyeDataWindow = useCallback(async (
        recordingId: number,
        startTime: number,
        endTime: number,
        maxPoints?: number,
    ): Promise<ChartEyeDataPoint[]> => {
        try {
            return await invoke<ChartEyeDataPoint[]>('get_eye_data_window', {
                recordingId,
                startTime,
                endTime,
                maxPoints: maxPoints ?? 2000,
            })
        } catch (err) {
            console.error('[useSessionReview] getEyeDataWindow error:', err)
            return []
        }
    }, [])

    const recalibrate = useCallback(async (
        recordingId: number,
        calibration: CalibrationSnapshot,
    ) => {
        setLoading(true)
        setError(null)
        try {
            const result = await invoke<SessionReviewPayload>('recalibrate_recording', {
                recordingId,
                calibration,
            })
            setPayload(result)
            return result
        } catch (err) {
            const errMsg = typeof err === 'string' ? err : 'Error al recalibrar'
            setError(errMsg)
            console.error('[useSessionReview] recalibrate error:', err)
            return null
        } finally {
            setLoading(false)
        }
    }, [])

    return {
        loading,
        error,
        payload,
        loadRecording,
        getEyeDataWindow,
        recalibrate,
    }
}
