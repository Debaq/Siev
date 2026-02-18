import { useState, useEffect, useCallback, useRef } from 'react'
import { Loader2, FileText } from 'lucide-react'
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
    recordingId: number
    onBack: () => void
    onViewReport?: () => void
}

export default function SessionReviewView({ recordingId, onBack, onViewReport }: SessionReviewViewProps) {
    const { loading, error, payload, loadRecording, getEyeDataWindow, recalibrate } = useSessionReview()

    const duration = payload?.duration_seconds ?? 0
    const {
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
    } = useTimelineSync(duration)

    // Zoomed high-resolution data
    const [zoomedEyeData, setZoomedEyeData] = useState<ChartEyeDataPoint[] | null>(null)
    const zoomFetchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => {
        loadRecording(recordingId)
    }, [recordingId, loadRecording])

    const handleRecalibrate = useCallback(async (cal: CalibrationSnapshot) => {
        await recalibrate(recordingId, cal)
        setZoomedEyeData(null)
    }, [recordingId, recalibrate])

    // When zoom range changes, fetch full-resolution data (debounced)
    useEffect(() => {
        if (!zoomRange || !payload) {
            setZoomedEyeData(null)
            return
        }

        const [start, end] = zoomRange
        const totalDuration = payload.duration_seconds
        if ((end - start) >= totalDuration * 0.8) {
            setZoomedEyeData(null)
            return
        }

        if (zoomFetchTimer.current) clearTimeout(zoomFetchTimer.current)
        zoomFetchTimer.current = setTimeout(async () => {
            const data = await getEyeDataWindow(recordingId, start, end, 2000)
            if (data.length > 0) {
                setZoomedEyeData(data)
            }
        }, 300)

        return () => {
            if (zoomFetchTimer.current) clearTimeout(zoomFetchTimer.current)
        }
    }, [zoomRange, recordingId, payload, getEyeDataWindow])

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
            <div className="flex items-center shrink-0">
                <div className="flex-1">
                    <SessionInfoHeader payload={payload} onBack={onBack} />
                </div>
                {onViewReport && (
                    <button
                        onClick={onViewReport}
                        className="mr-4 flex items-center gap-2 px-3 py-1.5 bg-siev-600 hover:bg-siev-700 rounded-lg transition-colors text-xs font-medium text-white"
                        title="Generar Informe PDF"
                    >
                        <FileText className="w-3.5 h-3.5" />
                        Informe
                    </button>
                )}
            </div>

            {/* === FIXED: Video + Stats overlay + Timeline === */}
            <div className="shrink-0 border-b border-dark-800">
                {/* Video with stats overlay */}
                <div className="relative w-full" style={{ height: '27vh' }}>
                    <VideoPlayer
                        videoUrl={payload.video_url}
                        videoAvailable={payload.video_available}
                        videoRef={videoRef}
                        onTimeUpdate={onVideoTimeUpdate}
                        playbackRate={playbackRate}
                        videoCrop={payload.video_crop ?? null}
                    />

                    {/* Stats overlay - left side */}
                    <div className="absolute left-2 top-2 flex flex-col gap-1.5 pointer-events-none">
                        <div className="bg-dark-950/75 backdrop-blur-sm border border-dark-700/50 rounded px-2.5 py-1.5 text-[10px]">
                            <span className="text-dark-400 block leading-tight">SPV Global</span>
                            <span className="text-dark-100 font-semibold text-xs">{payload.overall_spv.toFixed(1)}°/s</span>
                        </div>
                        <div className="bg-dark-950/75 backdrop-blur-sm border border-dark-700/50 rounded px-2.5 py-1.5 text-[10px]">
                            <span className="text-dark-400 block leading-tight">Sacadas</span>
                            <span className="text-dark-100 font-semibold text-xs">{payload.saccades.length}</span>
                        </div>
                    </div>

                    {/* Stats overlay - right side */}
                    <div className="absolute right-2 top-2 flex flex-col gap-1.5 pointer-events-none">
                        <div className="bg-dark-950/75 backdrop-blur-sm border border-dark-700/50 rounded px-2.5 py-1.5 text-[10px]">
                            <span className="text-dark-400 block leading-tight">Batidos</span>
                            <span className="text-dark-100 font-semibold text-xs">{payload.nystagmus_beats.length}</span>
                        </div>
                        <div className="bg-dark-950/75 backdrop-blur-sm border border-dark-700/50 rounded px-2.5 py-1.5 text-[10px]">
                            <span className="text-dark-400 block leading-tight">Pursuit</span>
                            <span className="text-dark-100 font-semibold text-xs">
                                {payload.pursuit_gain !== null ? payload.pursuit_gain.toFixed(2) : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Timeline Scrubber - fixed */}
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
            </div>

            {/* === SCROLLABLE: Charts + Recalibration === */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="p-3 space-y-3">
                    {/* Recalibration */}
                    <RecalibrationPanel
                        calibration={payload.calibration}
                        loading={loading}
                        onRecalibrate={handleRecalibrate}
                    />

                    {/* Charts Grid */}
                    <div className="grid grid-cols-2 gap-3">
                        <EyePositionChart
                            data={zoomedEyeData ?? payload.eye_data}
                            saccades={payload.saccades}
                            deflectionPoints={payload.deflection_points}
                            currentTime={currentTime}
                            currentTimeRef={currentTimeRef}
                            axis="horizontal"
                            onSeek={seekTo}
                            zoomRange={zoomRange}
                            onZoomChange={handleZoomChange}
                        />
                        <EyePositionChart
                            data={zoomedEyeData ?? payload.eye_data}
                            saccades={payload.saccades}
                            deflectionPoints={[]}
                            currentTime={currentTime}
                            currentTimeRef={currentTimeRef}
                            axis="vertical"
                            onSeek={seekTo}
                            zoomRange={zoomRange}
                            onZoomChange={handleZoomChange}
                        />
                        <SPVChart
                            data={payload.spv_timeline}
                            currentTime={currentTime}
                            currentTimeRef={currentTimeRef}
                            overallSPV={payload.overall_spv}
                            onSeek={seekTo}
                            zoomRange={zoomRange}
                            onZoomChange={handleZoomChange}
                        />
                        <SaccadeAnalysisChart
                            saccades={payload.saccades}
                            onSeek={seekTo}
                        />
                        <NystagmusBeatChart
                            beats={payload.nystagmus_beats}
                            currentTime={currentTime}
                            currentTimeRef={currentTimeRef}
                            onSeek={seekTo}
                        />
                        <PursuitGainChart
                            pursuitGain={payload.pursuit_gain}
                        />
                    </div>
                </div>
            </div>

            {/* Footer */}
            <footer className="bg-dark-950 border-t border-dark-800 px-3 py-1 text-[10px] text-dark-600 flex justify-between items-center shrink-0 select-none">
                <span>{payload.total_samples.toLocaleString()} muestras | {payload.sample_rate_hz.toFixed(0)} Hz | {duration.toFixed(1)}s</span>
                <span>Revision de Grabacion #{payload.recording_id}</span>
            </footer>
        </div>
    )
}
