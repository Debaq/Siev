import { useState, useCallback } from 'react'
import { invoke } from '@tauri-apps/api/core'
import type { SessionReviewPayload, ChartEyeDataPoint, CalibrationSnapshot } from '../types/review'

export function useSessionReview() {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [payload, setPayload] = useState<SessionReviewPayload | null>(null)

    const loadSession = useCallback(async (sessionId: number) => {
        setLoading(true)
        setError(null)
        try {
            const result = await invoke<SessionReviewPayload>('load_session_review', { sessionId })
            setPayload(result)
            return result
        } catch (err) {
            const errMsg = typeof err === 'string' ? err : 'Error al cargar la sesión'
            setError(errMsg)
            console.error('[useSessionReview] loadSession error:', err)
            return null
        } finally {
            setLoading(false)
        }
    }, [])

    const getEyeDataWindow = useCallback(async (
        sessionId: number,
        startTime: number,
        endTime: number,
        maxPoints?: number,
    ): Promise<ChartEyeDataPoint[]> => {
        try {
            return await invoke<ChartEyeDataPoint[]>('get_eye_data_window', {
                sessionId,
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
        sessionId: number,
        calibration: CalibrationSnapshot,
    ) => {
        setLoading(true)
        setError(null)
        try {
            const result = await invoke<SessionReviewPayload>('recalibrate_session', {
                sessionId,
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
        loadSession,
        getEyeDataWindow,
        recalibrate,
    }
}
