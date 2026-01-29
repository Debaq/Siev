import { useState, useEffect, useCallback, useRef } from 'react'
import { Loader2 } from 'lucide-react'
import { useSessionReview } from '../hooks/useSessionReview'
import { useTimelineSync } from '../hooks/useTimelineSync'
import SessionInfoHeader from './review/SessionInfoHeader'
import VideoPlayer from './review/VideoPlayer'
import TimelineScrubber from './review/TimelineScrubber'
import EyePositionChart from './review/EyePositionChart'
import SPVChart from './review/SPVChart'
import SaccadeAnalysisChart from './review/SaccadeAnalysisChart'
import NystagmusBeatChart from './review/NystagmusBeatChart'
import PursuitGainChart from './review/PursuitGainChart'
import RecalibrationPanel from './review/RecalibrationPanel'
import type { CalibrationSnapshot, ChartEyeDataPoint } from '../types/review'

interface SessionReviewViewProps {
    sessionId: number
    onBack: () => void
}

export default function SessionReviewView({ sessionId, onBack }: SessionReviewViewProps) {
    const { loading, error, payload, loadSession, getEyeDataWindow, recalibrate } = useSessionReview()

    const duration = payload?.duration_seconds ?? 0
    const {
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
    } = useTimelineSync(duration)

    // Zoomed high-resolution data
    const [zoomedEyeData, setZoomedEyeData] = useState<ChartEyeDataPoint[] | null>(null)
    const zoomFetchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => {
        loadSession(sessionId)
    }, [sessionId, loadSession])

    const handleRecalibrate = useCallback(async (cal: CalibrationSnapshot) => {
        await recalibrate(sessionId, cal)
        setZoomedEyeData(null) // Reset zoom data on recalibration
    }, [sessionId, recalibrate])

    // When zoom range changes, fetch full-resolution data (debounced)
    useEffect(() => {
        if (!zoomRange || !payload) {
            setZoomedEyeData(null)
            return
        }

        const [start, end] = zoomRange
        const totalDuration = payload.duration_seconds
        // Only fetch if zoomed to less than 80% of total duration
        if ((end - start) >= totalDuration * 0.8) {
            setZoomedEyeData(null)
            return
        }

        if (zoomFetchTimer.current) clearTimeout(zoomFetchTimer.current)
        zoomFetchTimer.current = setTimeout(async () => {
            const data = await getEyeDataWindow(sessionId, start, end, 2000)
            if (data.length > 0) {
                setZoomedEyeData(data)
            }
        }, 300) // 300ms debounce

        return () => {
            if (zoomFetchTimer.current) clearTimeout(zoomFetchTimer.current)
        }
    }, [zoomRange, sessionId, payload, getEyeDataWindow])

    const handleZoomChange = useCallback((range: [number, number]) => {
        setZoomRange(range)
    }, [setZoomRange])

    if (loading && !payload) {
        return (
            <div className="h-full flex flex-col items-center justify-center bg-dark-950 text-dark-400">
                <Loader2 className="w-8 h-8 animate-spin mb-4 text-siev-500" />
                <p className="text-sm">Cargando sesion...</p>
            </div>
        )
    }

    if (error && !payload) {
        return (
            <div className="h-full flex flex-col items-center justify-center bg-dark-950 text-dark-400">
                <p className="text-red-400 text-sm mb-2">Error al cargar la sesion</p>
                <p className="text-xs text-dark-600">{error}</p>
                <button onClick={onBack} className="mt-4 btn btn-secondary text-xs">
                    Volver
                </button>
            </div>
        )
    }

    if (!payload) return null

    return (
        <div className="h-full flex flex-col bg-dark-950 overflow-hidden">
            {/* Header */}
            <SessionInfoHeader payload={payload} onBack={onBack} />

            {/* Main content */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left: Video + Controls */}
                <div className="w-[60%] flex flex-col border-r border-dark-800">
                    {/* Video */}
                    <div className="flex-1 min-h-0">
                        <VideoPlayer
                            videoUrl={payload.video_url}
                            videoAvailable={payload.video_available}
                            videoRef={videoRef}
                            onTimeUpdate={onVideoTimeUpdate}
                            playbackRate={playbackRate}
                        />
                    </div>
                </div>

                {/* Right: Recalibration + Stats */}
                <div className="w-[40%] flex flex-col overflow-y-auto custom-scrollbar p-3 gap-3">
                    <RecalibrationPanel
                        calibration={payload.calibration}
                        loading={loading}
                        onRecalibrate={handleRecalibrate}
                    />

                    {/* Session stats */}
                    <div className="bg-dark-900/50 border border-dark-800 rounded-lg p-3">
                        <h3 className="text-xs font-semibold text-dark-300 mb-2">Estadisticas</h3>
                        <div className="grid grid-cols-2 gap-2 text-[10px]">
                            <div className="bg-dark-800 rounded px-2 py-1.5">
                                <span className="text-dark-500 block">SPV Global</span>
                                <span className="text-dark-200 font-medium">{payload.overall_spv.toFixed(1)}°/s</span>
                            </div>
                            <div className="bg-dark-800 rounded px-2 py-1.5">
                                <span className="text-dark-500 block">Sacadas</span>
                                <span className="text-dark-200 font-medium">{payload.saccades.length}</span>
                            </div>
                            <div className="bg-dark-800 rounded px-2 py-1.5">
                                <span className="text-dark-500 block">Batidos</span>
                                <span className="text-dark-200 font-medium">{payload.nystagmus_beats.length}</span>
                            </div>
                            <div className="bg-dark-800 rounded px-2 py-1.5">
                                <span className="text-dark-500 block">Pursuit</span>
                                <span className="text-dark-200 font-medium">
                                    {payload.pursuit_gain !== null ? payload.pursuit_gain.toFixed(2) : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Pursuit gauge (if available) */}
                    {payload.pursuit_gain !== null && (
                        <PursuitGainChart pursuitGain={payload.pursuit_gain} />
                    )}
                </div>
            </div>

            {/* Timeline Scrubber */}
            <TimelineScrubber
                currentTime={currentTime}
                duration={duration}
                isPlaying={isPlaying}
                playbackRate={playbackRate}
                saccades={payload.saccades}
                onSeek={seekTo}
                onTogglePlay={togglePlay}
                onSetPlaybackRate={setPlaybackRate}
            />

            {/* Charts Grid */}
            <div className="overflow-y-auto custom-scrollbar p-3">
                <div className="grid grid-cols-2 gap-3">
                    <EyePositionChart
                        data={zoomedEyeData ?? payload.eye_data}
                        saccades={payload.saccades}
                        currentTime={currentTime}
                        axis="horizontal"
                        onSeek={seekTo}
                        zoomRange={zoomRange}
                        onZoomChange={handleZoomChange}
                    />
                    <EyePositionChart
                        data={zoomedEyeData ?? payload.eye_data}
                        saccades={payload.saccades}
                        currentTime={currentTime}
                        axis="vertical"
                        onSeek={seekTo}
                        zoomRange={zoomRange}
                        onZoomChange={handleZoomChange}
                    />
                    <SPVChart
                        data={payload.spv_timeline}
                        currentTime={currentTime}
                        overallSPV={payload.overall_spv}
                        onSeek={seekTo}
                    />
                    <SaccadeAnalysisChart
                        saccades={payload.saccades}
                        currentTime={currentTime}
                        onSeek={seekTo}
                    />
                    <NystagmusBeatChart
                        beats={payload.nystagmus_beats}
                        currentTime={currentTime}
                        onSeek={seekTo}
                    />
                    <PursuitGainChart
                        pursuitGain={payload.pursuit_gain}
                    />
                </div>
            </div>

            {/* Footer */}
            <footer className="bg-dark-950 border-t border-dark-800 px-3 py-1 text-[10px] text-dark-600 flex justify-between items-center shrink-0 select-none">
                <span>{payload.total_samples.toLocaleString()} muestras | {payload.sample_rate_hz.toFixed(0)} Hz | {duration.toFixed(1)}s</span>
                <span>Revision de Sesion #{payload.session_id}</span>
            </footer>
        </div>
    )
}
