import { useEffect, useCallback, RefObject, useState, useRef, useMemo } from 'react'
import { VideoOff } from 'lucide-react'
import type { VideoCropInfo } from '../../types/review'

interface VideoPlayerProps {
    videoUrl: string | null
    videoAvailable: boolean
    videoRef: RefObject<HTMLVideoElement | null>
    onTimeUpdate: (time: number) => void
    playbackRate: number
    videoCrop: VideoCropInfo | null
}

/** Detecta bordes negros analizando el primer frame del video */
function detectBlackBorders(video: HTMLVideoElement): VideoCropInfo | null {
    const vw = video.videoWidth
    const vh = video.videoHeight
    if (vw === 0 || vh === 0) return null

    const canvas = document.createElement('canvas')
    canvas.width = vw
    canvas.height = vh
    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    ctx.drawImage(video, 0, 0, vw, vh)
    const imageData = ctx.getImageData(0, 0, vw, vh)
    const data = imageData.data

    const threshold = 12

    // Escanear desde arriba
    let top = 0
    topLoop: for (let y = 0; y < vh; y++) {
        for (let x = 0; x < vw; x += 4) {
            const idx = (y * vw + x) * 4
            if (data[idx] > threshold || data[idx + 1] > threshold || data[idx + 2] > threshold) {
                top = y
                break topLoop
            }
        }
    }

    // Escanear desde abajo
    let bottom = vh - 1
    bottomLoop: for (let y = vh - 1; y >= top; y--) {
        for (let x = 0; x < vw; x += 4) {
            const idx = (y * vw + x) * 4
            if (data[idx] > threshold || data[idx + 1] > threshold || data[idx + 2] > threshold) {
                bottom = y
                break bottomLoop
            }
        }
    }

    // Escanear desde la izquierda
    let left = 0
    leftLoop: for (let x = 0; x < vw; x++) {
        for (let y = top; y <= bottom; y += 4) {
            const idx = (y * vw + x) * 4
            if (data[idx] > threshold || data[idx + 1] > threshold || data[idx + 2] > threshold) {
                left = x
                break leftLoop
            }
        }
    }

    // Escanear desde la derecha
    let right = vw - 1
    rightLoop: for (let x = vw - 1; x >= left; x--) {
        for (let y = top; y <= bottom; y += 4) {
            const idx = (y * vw + x) * 4
            if (data[idx] > threshold || data[idx + 1] > threshold || data[idx + 2] > threshold) {
                right = x
                break rightLoop
            }
        }
    }

    const contentWidth = right - left + 1
    const contentHeight = bottom - top + 1

    // Solo aplicar si hay bordes significativos (> 2% en algún eje)
    const minBorderRatio = 0.02
    if ((vw - contentWidth) / vw < minBorderRatio && (vh - contentHeight) / vh < minBorderRatio) {
        return null
    }

    return {
        content_width: contentWidth,
        content_height: contentHeight,
        encoder_width: vw,
        encoder_height: vh,
    }
}

export default function VideoPlayer({
    videoUrl,
    videoAvailable,
    videoRef,
    onTimeUpdate,
    playbackRate,
    videoCrop,
}: VideoPlayerProps) {
    const [error, setError] = useState<string | null>(null)
    const [detectedCrop, setDetectedCrop] = useState<VideoCropInfo | null>(null)
    const detectionDone = useRef(false)

    useEffect(() => {
        if (videoRef.current) {
            videoRef.current.playbackRate = playbackRate
        }
    }, [playbackRate, videoRef])

    // Resetear detección cuando cambia la URL del video
    useEffect(() => {
        detectionDone.current = false
        setDetectedCrop(null)
    }, [videoUrl])

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            onTimeUpdate(videoRef.current.currentTime)
        }
    }

    // Detectar bordes negros en el primer frame si no tenemos metadata
    const handleLoadedData = useCallback(() => {
        if (videoCrop || detectionDone.current || !videoRef.current) return
        detectionDone.current = true
        const crop = detectBlackBorders(videoRef.current)
        if (crop) {
            console.log('[VideoPlayer] Bordes negros detectados:', crop)
            setDetectedCrop(crop)
        }
    }, [videoCrop, videoRef])

    const activeCrop = videoCrop || detectedCrop

    // Calcular escala uniforme para eliminar bordes negros via transform
    // Usa la escala mayor entre ancho y alto para asegurar que al menos
    // los bordes más grandes desaparecen. El contenido se centra y
    // overflow:hidden del padre recorta el exceso.
    const cropScale = useMemo(() => {
        if (!activeCrop) return 1
        const { content_width, content_height, encoder_width, encoder_height } = activeCrop
        if (content_width >= encoder_width && content_height >= encoder_height) return 1
        const scaleX = encoder_width / content_width
        const scaleY = encoder_height / content_height
        return Math.max(scaleX, scaleY)
    }, [activeCrop])

    if (!videoAvailable || !videoUrl) {
        return (
            <div className="w-full h-full bg-dark-950 flex flex-col items-center justify-center text-dark-500">
                <VideoOff className="w-12 h-12 mb-3 opacity-30" />
                <p className="text-sm">Video no disponible</p>
                <p className="text-xs text-dark-600 mt-1">La grabacion no incluye video</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="w-full h-full bg-dark-950 flex flex-col items-center justify-center text-dark-500">
                <VideoOff className="w-12 h-12 mb-3 opacity-30" />
                <p className="text-sm">Error al cargar el video</p>
                <p className="text-xs text-dark-600 mt-1">{error}</p>
            </div>
        )
    }

    return (
        <div className="w-full h-full bg-black flex items-center justify-center overflow-hidden">
            <video
                ref={videoRef}
                src={videoUrl}
                className="max-w-full max-h-full object-contain"
                style={cropScale > 1 ? {
                    transform: `scale(${cropScale.toFixed(4)})`,
                    transformOrigin: 'center center',
                } : undefined}
                onTimeUpdate={handleTimeUpdate}
                onLoadedData={handleLoadedData}
                onError={(e) => {
                    const video = e.currentTarget
                    const mediaErr = video.error
                    const code = mediaErr?.code ?? 'unknown'
                    const msg = mediaErr?.message ?? ''
                    console.error('[VideoPlayer] Media error:', code, msg, 'src:', videoUrl)
                    setError(`Error de video (code: ${code}) ${msg}`)
                }}
                onPlay={() => {}}
                onPause={() => {}}
                playsInline
                preload="auto"
            />
        </div>
    )
}
