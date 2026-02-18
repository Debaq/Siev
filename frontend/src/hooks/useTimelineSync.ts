import { useState, useRef, useCallback, useEffect } from 'react'

export function useTimelineSync(duration: number) {
    const [currentTime, setCurrentTime] = useState(0)
    const [isPlaying, setIsPlaying] = useState(false)
    const [playbackRate, setPlaybackRateState] = useState(1)
    const [zoomRange, setZoomRange] = useState<[number, number] | null>(null)
    const videoRef = useRef<HTMLVideoElement>(null)
    const currentTimeRef = useRef(0)
    const rafId = useRef<number | null>(null)

    const onVideoTimeUpdate = useCallback((time: number) => {
        currentTimeRef.current = time
        if (rafId.current === null) {
            rafId.current = requestAnimationFrame(() => {
                setCurrentTime(currentTimeRef.current)
                rafId.current = null
            })
        }
    }, [])

    useEffect(() => {
        return () => {
            if (rafId.current !== null) {
                cancelAnimationFrame(rafId.current)
            }
        }
    }, [])

    const seekTo = useCallback((time: number) => {
        const clampedTime = Math.max(0, Math.min(time, duration))
        currentTimeRef.current = clampedTime
        setCurrentTime(clampedTime)
        if (videoRef.current) {
            videoRef.current.currentTime = clampedTime
        }
    }, [duration])

    const togglePlay = useCallback(() => {
        if (videoRef.current) {
            if (videoRef.current.paused) {
                videoRef.current.play()
                setIsPlaying(true)
            } else {
                videoRef.current.pause()
                setIsPlaying(false)
            }
        }
    }, [])

    const setPlaybackRate = useCallback((rate: number) => {
        setPlaybackRateState(rate)
        if (videoRef.current) {
            videoRef.current.playbackRate = rate
        }
    }, [])

    return {
        currentTime,
        currentTimeRef,
        isPlaying,
        playbackRate,
        zoomRange,
        videoRef,
        onVideoTimeUpdate,
        seekTo,
        togglePlay,
        setPlaybackRate,
        setZoomRange,
    }
}
