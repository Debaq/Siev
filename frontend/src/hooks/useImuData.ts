import { useState, useCallback, useRef, useEffect } from 'react'
import { listen, UnlistenFn } from '@tauri-apps/api/event'

interface RawImuEvent {
    yaw: number
    pitch: number
    roll: number
    timestamp: number
}

export interface CalibratedImuData {
    raw: { yaw: number; pitch: number; roll: number }
    calibrated: { yaw: number; pitch: number; roll: number }
    timestamp: number
}

export interface UseImuDataReturn {
    current: CalibratedImuData | null
    history: CalibratedImuData[]
    isCalibrated: boolean
    calibrate: () => void
    resetCalibration: () => void
    clearHistory: () => void
}

const MAX_HISTORY = 600 // ~60s at 10Hz batching

export function useImuData(): UseImuDataReturn {
    const [current, setCurrent] = useState<CalibratedImuData | null>(null)
    const [history, setHistory] = useState<CalibratedImuData[]>([])
    const [isCalibrated, setIsCalibrated] = useState(false)

    const offsetRef = useRef<{ yaw: number; pitch: number; roll: number } | null>(null)
    const lastRawRef = useRef<RawImuEvent | null>(null)
    const batchTimerRef = useRef<number | null>(null)

    const processImu = useCallback((raw: RawImuEvent) => {
        lastRawRef.current = raw

        const offset = offsetRef.current
        const calibrated = offset
            ? {
                yaw: raw.yaw - offset.yaw,
                pitch: raw.pitch - offset.pitch,
                roll: raw.roll - offset.roll,
            }
            : { yaw: raw.yaw, pitch: raw.pitch, roll: raw.roll }

        const data: CalibratedImuData = {
            raw: { yaw: raw.yaw, pitch: raw.pitch, roll: raw.roll },
            calibrated,
            timestamp: raw.timestamp ?? Date.now(),
        }

        setCurrent(data)
        return data
    }, [])

    // Listen IMU events from Tauri, batch history at ~10Hz
    useEffect(() => {
        let unlisten: UnlistenFn | undefined

        const setup = async () => {
            try {
                unlisten = await listen<RawImuEvent>('imu-data', (event) => {
                    const data = processImu(event.payload)

                    // Batch history updates at ~100ms
                    if (batchTimerRef.current === null) {
                        batchTimerRef.current = window.setTimeout(() => {
                            batchTimerRef.current = null
                            setHistory(prev => {
                                const next = [...prev, data]
                                return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next
                            })
                        }, 100)
                    }
                })
            } catch (err) {
                console.error('Failed to setup IMU listener for postural:', err)
            }
        }

        setup()

        return () => {
            if (unlisten) unlisten()
            if (batchTimerRef.current !== null) {
                clearTimeout(batchTimerRef.current)
                batchTimerRef.current = null
            }
        }
    }, [processImu])

    const calibrate = useCallback(() => {
        if (lastRawRef.current) {
            offsetRef.current = {
                yaw: lastRawRef.current.yaw,
                pitch: lastRawRef.current.pitch,
                roll: lastRawRef.current.roll,
            }
            setIsCalibrated(true)
        }
    }, [])

    const resetCalibration = useCallback(() => {
        offsetRef.current = null
        setIsCalibrated(false)
    }, [])

    const clearHistory = useCallback(() => {
        setHistory([])
    }, [])

    return {
        current,
        history,
        isCalibrated,
        calibrate,
        resetCalibration,
        clearHistory,
    }
}
