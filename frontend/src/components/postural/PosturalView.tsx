import { useState, useEffect, useCallback } from 'react'
import { GripHorizontal } from 'lucide-react'
import { PosturalTestDefinition, PosturalConfig } from '../../types/config'
import { usePosturalProtocol } from '../../hooks/usePosturalProtocol'
import { usePosturalTimer } from '../../hooks/usePosturalTimer'
import { useImuData } from '../../hooks/useImuData'
import VideoFeed from '../VideoFeed'
import StatusBar from '../StatusBar'
import OrientationGauges from '../settings/postural/OrientationGauges'
import BodyPositionIcon from '../settings/postural/BodyPositionIcon'
import EyeDataPanel from '../EyeDataPanel'
import PosturalControlPanel from './PosturalControlPanel'
import PosturalTimeline from './PosturalTimeline'

interface PosturalViewProps {
    isCapturing: boolean
    patientName: string | null
    posturalConfig: PosturalConfig
    hardwareStatus: boolean
    onSelectTest: () => void
    onSelectPatient: () => void
}

export default function PosturalView({
    isCapturing,
    patientName,
    posturalConfig,
    hardwareStatus,
    onSelectTest,
    onSelectPatient,
}: PosturalViewProps) {
    const protocol = usePosturalProtocol()
    const timer = usePosturalTimer()
    const imu = useImuData()

    const [dataPanelHeight, setDataPanelHeight] = useState(() => {
        const h = window.innerHeight
        if (h <= 768) return 120
        if (h <= 900) return 150
        return 180
    })
    const [isResizing, setIsResizing] = useState(false)

    // Resizing
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing) return
            const newHeight = window.innerHeight - e.clientY - 24
            if (newHeight >= 80 && newHeight <= window.innerHeight * 0.5) setDataPanelHeight(newHeight)
        }
        const handleMouseUp = () => { setIsResizing(false); document.body.style.cursor = 'default' }

        if (isResizing) {
            window.addEventListener('mousemove', handleMouseMove)
            window.addEventListener('mouseup', handleMouseUp)
            document.body.style.cursor = 'row-resize'
        }
        return () => { window.removeEventListener('mousemove', handleMouseMove); window.removeEventListener('mouseup', handleMouseUp) }
    }, [isResizing])

    // Auto-advance when timer completes
    useEffect(() => {
        if (timer.isRunning && timer.progress >= 1) {
            timer.stop()
            if (posturalConfig.timing.auto_advance) {
                protocol.advancePosition()
            }
        }
    }, [timer.progress, timer.isRunning])

    // Start timer when advancing to a new active position
    useEffect(() => {
        if (protocol.isActive && protocol.currentStageIndex >= 0) {
            const stage = protocol.stages[protocol.currentStageIndex]
            if (stage.status === 'active' && !timer.isRunning && !timer.isPaused) {
                // Don't auto-start; user starts from control panel
            }
        }
    }, [protocol.currentStageIndex, protocol.isActive])

    const handleStartTest = useCallback((test: PosturalTestDefinition) => {
        protocol.startTest(test)
        imu.calibrate()
        imu.clearHistory()
    }, [])

    const handleAdvance = useCallback(() => {
        if (!protocol.isActive) return
        const stage = protocol.stages[protocol.currentStageIndex]
        if (timer.isRunning) {
            // Timer running -> stop and advance
            timer.stop()
            protocol.advancePosition()
        } else {
            // Timer not running -> start it
            timer.start(stage.duration)
        }
    }, [protocol.isActive, protocol.currentStageIndex, protocol.stages, timer])

    const handleSkip = useCallback(() => {
        timer.stop()
        protocol.skipPosition()
    }, [])

    const handlePause = useCallback(() => {
        timer.pause()
    }, [])

    const handleResume = useCallback(() => {
        timer.resume()
    }, [])

    const handleStop = useCallback(() => {
        timer.stop()
        protocol.advancePosition()
    }, [])

    const handleReset = useCallback(() => {
        timer.stop()
        protocol.resetTest()
        imu.clearHistory()
    }, [])

    const currentStage = protocol.isActive && protocol.currentStageIndex >= 0
        ? protocol.stages[protocol.currentStageIndex]
        : null

    const targetOrientation = currentStage?.position.target_head_orientation

    return (
        <div className="h-full flex flex-col font-sans text-xs">
            <StatusBar
                hardwareStatus={hardwareStatus ? 'online' : 'offline'}
                fps={0}
                recording={false}
                testType={protocol.test?.id ?? 'vppb'}
                patientName={patientName}
                onSelectTest={onSelectTest}
                onSelectPatient={onSelectPatient}
            />

            <div className="flex-1 flex overflow-hidden">
                {/* Main Content */}
                <div className="flex-1 flex flex-col min-w-0 bg-black/20">
                    {/* Top: Video + 3D side by side */}
                    <div className="flex-1 flex min-h-0">
                        {/* Video Feed */}
                        <div className="flex-1 bg-black flex items-center justify-center overflow-hidden">
                            <VideoFeed
                                isCapturing={isCapturing}
                                patientName={patientName}
                                testType={protocol.test?.id ?? null}
                                caloricStageLabel={null}
                                isRecording={timer.isRunning}
                                caloricTimer={null}
                            />
                        </div>

                        {/* Orientation Gauges + Position Guide */}
                        {posturalConfig.visualization.show_3d_head && (
                            <div className="w-[280px] shrink-0 border-l border-dark-800 flex flex-col bg-dark-900">
                                <div className="flex-1 flex flex-col items-center justify-center p-3 gap-3 min-h-0">
                                    {/* Body position pictogram */}
                                    {currentStage?.position.body_position && (
                                        <BodyPositionIcon position={currentStage.position.body_position} />
                                    )}

                                    {/* Orientation gauges with target markers */}
                                    <OrientationGauges
                                        yaw={imu.current?.calibrated.yaw ?? 0}
                                        pitch={imu.current?.calibrated.pitch ?? 0}
                                        roll={imu.current?.calibrated.roll ?? 0}
                                        targetYaw={posturalConfig.visualization.show_target_orientation ? targetOrientation?.yaw : undefined}
                                        targetPitch={posturalConfig.visualization.show_target_orientation ? targetOrientation?.pitch : undefined}
                                        targetRoll={posturalConfig.visualization.show_target_orientation ? targetOrientation?.roll : undefined}
                                        className="grid grid-cols-3 gap-2 w-full"
                                    />

                                    {/* Calibration hint */}
                                    {!imu.isCalibrated && protocol.isActive && (
                                        <p className="text-[9px] text-yellow-500/70 text-center">
                                            IMU sin calibrar — calibre desde el panel
                                        </p>
                                    )}
                                </div>

                                {/* Position guide text */}
                                {currentStage && (
                                    <div className="p-2 border-t border-dark-800">
                                        <p className="text-[10px] text-orange-400 font-bold mb-0.5">
                                            {currentStage.position.label}
                                        </p>
                                        <p className="text-[10px] text-dark-400 leading-tight">
                                            {currentStage.position.description}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Timeline */}
                    {protocol.isActive && (
                        <PosturalTimeline
                            testName={protocol.test?.name ?? ''}
                            stages={protocol.stages}
                            currentStageIndex={protocol.currentStageIndex}
                            elapsedSeconds={timer.elapsedSeconds}
                            totalDuration={currentStage?.duration ?? 0}
                            progress={timer.progress}
                            isRunning={timer.isRunning}
                        />
                    )}

                    {/* Resize handle */}
                    <div
                        className="h-1.5 bg-dark-900 hover:bg-siev-600/50 cursor-row-resize flex items-center justify-center transition-colors z-30 border-t border-dark-800"
                        onMouseDown={() => setIsResizing(true)}
                    >
                        <GripHorizontal className="w-3 h-3 text-dark-600" />
                    </div>

                    {/* Eye Data Panel */}
                    <div style={{ height: dataPanelHeight }} className="bg-dark-900 flex flex-col shrink-0 transition-none">
                        <div className="flex-1 overflow-hidden">
                            <EyeDataPanel isCapturing={isCapturing} />
                        </div>
                    </div>
                </div>

                {/* Control Panel */}
                <div className="w-[220px] bg-dark-900 border-l border-dark-800 flex flex-col shrink-0 z-20 shadow-xl">
                    <div className="p-3 border-b border-dark-800 font-bold text-dark-300 text-[11px] uppercase tracking-wider bg-dark-850">
                        Panel VPPB
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
                        <PosturalControlPanel
                            protocol={protocol}
                            timer={timer}
                            imu={imu}
                            symptomsConfig={posturalConfig.symptoms}
                            enabledTests={posturalConfig.enabled_tests}
                            customTests={posturalConfig.custom_tests}
                            onStartTest={handleStartTest}
                            onAdvance={handleAdvance}
                            onSkip={handleSkip}
                            onPause={handlePause}
                            onResume={handleResume}
                            onStop={handleStop}
                            onReset={handleReset}
                        />
                    </div>
                </div>
            </div>

            <footer className="bg-dark-950 border-t border-dark-800 px-3 py-1 text-[10px] text-dark-600 flex justify-between items-center shrink-0 select-none">
                <span>VPPB — Seguimiento Cefálico + Eye Tracking</span>
                <span>SIEV v1.0.0</span>
            </footer>
        </div>
    )
}
