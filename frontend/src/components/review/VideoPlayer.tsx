import { useEffect, useMemo, RefObject } from 'react'
import { convertFileSrc } from '@tauri-apps/api/core'
import { VideoOff } from 'lucide-react'

interface VideoPlayerProps {
    videoUrl: string | null
    videoAvailable: boolean
    videoRef: RefObject<HTMLVideoElement | null>
    onTimeUpdate: (time: number) => void
    playbackRate: number
}

export default function VideoPlayer({
    videoUrl,
    videoAvailable,
    videoRef,
    onTimeUpdate,
    playbackRate,
}: VideoPlayerProps) {
    useEffect(() => {
        if (videoRef.current) {
            videoRef.current.playbackRate = playbackRate
        }
    }, [playbackRate, videoRef])

    // Convert local file path to asset URL for the webview
    const assetUrl = useMemo(() => {
        if (!videoUrl) return null
        // If it's already a protocol URL (asset://, http://, blob:), use as-is
        if (videoUrl.startsWith('asset:') || videoUrl.startsWith('http') || videoUrl.startsWith('blob:')) {
            return videoUrl
        }
        // Convert filesystem path to asset URL
        return convertFileSrc(videoUrl)
    }, [videoUrl])

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            onTimeUpdate(videoRef.current.currentTime)
        }
    }

    if (!videoAvailable || !assetUrl) {
        return (
            <div className="w-full h-full bg-dark-950 flex flex-col items-center justify-center text-dark-500">
                <VideoOff className="w-12 h-12 mb-3 opacity-30" />
                <p className="text-sm">Video no disponible</p>
                <p className="text-xs text-dark-600 mt-1">La grabacion no incluye video</p>
            </div>
        )
    }

    return (
        <div className="w-full h-full bg-black flex items-center justify-center">
            <video
                ref={videoRef}
                src={assetUrl}
                className="max-w-full max-h-full object-contain"
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => {}}
                onPause={() => {}}
                playsInline
                preload="auto"
            />
        </div>
    )
}
