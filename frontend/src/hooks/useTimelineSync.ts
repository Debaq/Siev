import { useState, useRef, useCallback } from 'react'

export function useTimelineSync(duration: number) {
    const [currentTime, setCurrentTime] = useState(0)
    const [isPlaying, setIsPlaying] = useState(false)
    const [playbackRate, setPlaybackRateState] = useState(1)
    const [zoomRange, setZoomRange] = useState<[number, number] | null>(null)
    const videoRef = useRef<HTMLVideoElement>(null)

    const onVideoTimeUpdate = useCallback((time: number) => {
        setCurrentTime(time)
    }, [])

    const seekTo = useCallback((time: number) => {
        const clampedTime = Math.max(0, Math.min(time, duration))
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
