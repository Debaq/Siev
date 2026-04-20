import { useState, useEffect, useRef } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { emit, listen } from '@tauri-apps/api/event'
import { Settings, GripHorizontal, Shrink, Users } from 'lucide-react'
import { getCurrentWindow } from '@tauri-apps/api/window'
import VideoFeed from './components/VideoFeed'
import ControlPanel from './components/ControlPanel'
import StatusBar from './components/StatusBar'
import EyeDataPanel from './components/EyeDataPanel'
import SettingsView from './components/SettingsView'
import PatientsView from './components/PatientsView'
import SessionReviewView from './components/SessionReviewView'
import TestSelectionView from './components/TestSelectionView'
import WelcomeWizard from './components/WelcomeWizard'
import UserSelectionScreen from './components/UserSelectionScreen'
import SplashScreen from './components/SplashScreen'
import Sidebar from './components/Sidebar'
import TitleBar from './components/TitleBar'
import ScreenTooSmallOverlay from './components/ScreenTooSmallOverlay'
import { useTauriDb, Specialist, Patient, Recording } from './hooks/useTauriDb'
import { useSettingsConfig } from './hooks/useSettingsConfig'
import { useSessionConfig } from './hooks/useSessionConfig'
import { useCaloricProtocol } from './hooks/useCaloricProtocol'
import { useCaloricTimer } from './hooks/useCaloricTimer'
import { useWebSocket } from './contexts/WebSocketContext'
import { CaloricProtocol } from './types/config'
import { TestBattery } from './components/settings/ModuleSelector'
import CaloricTimeline from './components/CaloricTimeline'
import { CalibrationPage } from './pages/CalibrationPage'
import { ReportGenerator } from './components/reports'
import AudiometryView from './components/audiometry/AudiometryView'
import PosturalView from './components/postural/PosturalView'

import { ExternalDisplayPage } from './pages/ExternalDisplayPage'

// --- SEPARATION OF CONCERNS ---

// MainApp contains all the heavy logic (WebSockets, DB, etc.)
// This component should ONLY run in the main window.
const MainApp = () => {
  const { connected: isWsConnected, cameras: wsCameras, cameraStatus, send } = useWebSocket()
  const { getSetting, getSpecialists, createSession, createRecording } = useTauriDb()
  
  // Initialize hooks with WebSocket send capability
  const { config: appConfig, updateConfig } = useSettingsConfig(send)
  const sessionConfig = useSessionConfig(send, updateConfig)
  const caloricProtocol = useCaloricProtocol()
  const caloricTimer = useCaloricTimer(caloricProtocol.protocol?.timing ?? null)

  // Recording state (elevated from ControlPanel for caloric protocol integration)
  const [isRecording, setIsRecording] = useState(false)

  // Calibration state — required before any test can start
  const [isCalibrated, setIsCalibrated] = useState(false)
  const [calibrationSource, setCalibrationSource] = useState<'none' | 'saved' | 'new'>('none')

  // UX State
  const [showSplash, setShowSplash] = useState(true)

  // Navigation State
  const [activeView, setActiveView] = useState<'capture' | 'patients' | 'settings' | 'test_selection' | 'onboarding' | 'user_selection' | 'session_review' | 'report' | 'audiometry' | 'postural'>('user_selection')
  const [currentPatient, setCurrentPatient] = useState<Patient | null>(null)
  const [currentSession, setCurrentSession] = useState<any | null>(null)
  const [currentRecording, setCurrentRecording] = useState<Recording | null>(null)
  const [currentTestType, setCurrentTestType] = useState<string | null>(null)
  const [activeSpecialist, setActiveSpecialist] = useState<Specialist | null>(null)
  const [reviewRecordingId, setReviewRecordingId] = useState<number | null>(null)
  const [reportRecordingId, setReportRecordingId] = useState<number | null>(null)
  const [batteries, setBatteries] = useState<TestBattery[]>([])

  useEffect(() => {
    if (activeView === 'test_selection') {
      try {
        const stored = localStorage.getItem('siev_test_batteries')
        setBatteries(stored ? JSON.parse(stored) : [])
      } catch { setBatteries([]) }
      // Request camera list when user is about to start a test
      requestCamerasIfNeeded()
    }
  }, [activeView])

  // App State
  const [isCapturing, setIsCapturing] = useState(false)
  const [selectedCamera, setSelectedCamera] = useState<number>(2)
  const [dataPanelHeight, setDataPanelHeight] = useState(() => {
    const h = window.innerHeight
    if (h <= 768) return 160
    if (h <= 900) return 200
    return 240
  })
  const [isResizing, setIsResizing] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Check Initialization
  useEffect(() => {
    async function checkInit() {
      try {
        // Sync storage from disk to DB
        await invoke('sync_storage')
        
        const initialized = await getSetting('app_initialized')
        if (initialized !== 'true') {
          setActiveView('onboarding')
        } else {
          const specialists = await getSpecialists()
          if (specialists.length === 1) {
              setActiveSpecialist(specialists[0])
              setActiveView('patients')
          } else {
              setActiveView('user_selection')
          }
        }
      } catch (e) { console.error(e) }
    }
    checkInit()
  }, [])

  // Initialization: Request cameras via WebSocket (deferred until needed)
  const camerasRequestedRef = useRef(false)
  const requestCamerasIfNeeded = () => {
    if (isWsConnected && !camerasRequestedRef.current) {
      send({ type: 'list_cameras' })
      camerasRequestedRef.current = true
    }
  }

  const hasInitializedSessionRef = useRef(false);
  const lastCaptureConfigRef = useRef<string | null>(null);
  const captureStartedRef = useRef(false);

  // Extract camera config values to avoid object reference issues
  const cameraId = appConfig?.vng?.camera?.camera_id;
  const cameraWidth = appConfig?.vng?.camera?.resolution_width;
  const cameraHeight = appConfig?.vng?.camera?.resolution_height;
  const cameraFps = appConfig?.vng?.camera?.fps;

  // Auto-start capture when entering capture view (only if there's an active test)
  useEffect(() => {
    if (activeView === 'capture' && isWsConnected && currentTestType && cameraId !== undefined) {
      const currentConfig = `${cameraId}-${cameraWidth}-${cameraHeight}-${cameraFps}`;

      // Only start if config is different from last capture
      if (lastCaptureConfigRef.current !== currentConfig && !captureStartedRef.current) {
        console.log("[App] Starting capture with config:", currentConfig);
        lastCaptureConfigRef.current = currentConfig;
        captureStartedRef.current = true;
        const timer = setTimeout(() => {
          handleStartCapture();
          captureStartedRef.current = false;
        }, 200);
        return () => {
          clearTimeout(timer);
          captureStartedRef.current = false;
        };
      }
    }
  }, [activeView, isWsConnected, currentTestType, cameraId, cameraWidth, cameraHeight, cameraFps]);

  // Sync selected camera with config or camera list
  useEffect(() => {
    // First, try to use the camera from config
    if (appConfig?.vng?.camera?.camera_id !== undefined) {
      setSelectedCamera(appConfig.vng.camera.camera_id);
      
      // Initialize session config only once when appConfig is first loaded
      if (!hasInitializedSessionRef.current) {
        console.log("[App] Initializing sessionConfig with loaded appConfig");
        sessionConfig.initFromPersistentConfig(appConfig);
        hasInitializedSessionRef.current = true;
      }
    } else if (wsCameras.length > 0 && !wsCameras.find(c => c.id === selectedCamera)) {
      setSelectedCamera(wsCameras[0].id);
    }
  }, [wsCameras, appConfig, sessionConfig])

  // Resizing Logic
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      const newHeight = window.innerHeight - e.clientY - 24
      if (newHeight >= 100 && newHeight <= window.innerHeight * 0.7) setDataPanelHeight(newHeight)
    }
    const handleMouseUp = () => { setIsResizing(false); document.body.style.cursor = 'default' }
    
    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'row-resize'
    }
    return () => { window.removeEventListener('mousemove', handleMouseMove); window.removeEventListener('mouseup', handleMouseUp) }
  }, [isResizing])

  // Fullscreen management (F11 toggle, ESC to exit)
  useEffect(() => {
    const win = getCurrentWindow()
    const syncFullscreen = async () => {
      setIsFullscreen(await win.isFullscreen())
    }
    const handleKeyDown = async (e: KeyboardEvent) => {
      if (e.key === 'F11') {
        e.preventDefault()
        const current = await win.isFullscreen()
        await win.setFullscreen(!current)
        setTimeout(syncFullscreen, 100)
      }
      if (e.key === 'Escape') {
        if (await win.isFullscreen()) {
          await win.setFullscreen(false)
          setTimeout(syncFullscreen, 100)
        }
      }
    }
    syncFullscreen()
    const unlisten = win.onResized(() => syncFullscreen())
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      unlisten.then(f => f())
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const toggleFullscreen = async () => {
    const win = getCurrentWindow()
    const current = await win.isFullscreen()
    await win.setFullscreen(!current)
    setTimeout(async () => setIsFullscreen(await win.isFullscreen()), 100)
  }

  // Listen for manual calibration results
  useEffect(() => {
    let unlisten: (() => void) | undefined;

    const setup = async () => {
      unlisten = await listen('manual_calibration_complete', (event: any) => {
        const result = event.payload;
        console.log('[App] Manual calibration completed:', result);

        setIsCalibrated(true);
        setCalibrationSource('new');

        // Send calibration data to backend for processing
        send({
          type: 'calibration_data',
          points: result.points,
          patient_distance: result.patientDistance
        });

        // Persist calibration for current patient
        if (currentPatient) {
          setTimeout(() => {
            invoke('save_patient_calibration', { patientId: currentPatient.id }).catch(console.error);
          }, 150);
        }
      });
    };

    setup();

    return () => {
      if (unlisten) unlisten();
    };
  }, [send, currentPatient])

  // Sync caloric timer with recording state
  useEffect(() => {
    if (currentTestType === 'caloric' && caloricProtocol.isProtocolActive) {
      if (isRecording) {
        caloricTimer.start()
      } else {
        caloricTimer.stop()
        caloricTimer.reset()
      }
    }
  }, [isRecording, currentTestType, caloricProtocol.isProtocolActive])

  // Auto-stop recording when caloric timer reaches end
  useEffect(() => {
    if (caloricTimer.isRunning && caloricTimer.progress >= 1) {
      send({ type: 'stop_recording' })
      setIsRecording(false)
      caloricProtocol.advanceStage('completada')
    }
  }, [caloricTimer.progress, caloricTimer.isRunning])

  // Control fixation LED during OFI phase
  const prevPhaseRef = useRef<string | null>(null)
  useEffect(() => {
    const phaseKey = caloricTimer.currentPhase.key
    const prevPhase = prevPhaseRef.current
    prevPhaseRef.current = phaseKey

    if (!caloricTimer.isRunning || !caloricProtocol.protocol) return

    const fixationLed = caloricProtocol.protocol.timing.ofi.fixation_led

    if (phaseKey === 'ofi' && prevPhase !== 'ofi') {
      // Entering OFI: turn on configured LED(s)
      if (fixationLed === 'both') {
        invoke('send_hardware_command', { cmd: 'L_12_ON' })
        invoke('send_hardware_command', { cmd: 'L_14_ON' })
      } else if (fixationLed === 'left') {
        invoke('send_hardware_command', { cmd: 'L_12_ON' })
      } else {
        invoke('send_hardware_command', { cmd: 'L_14_ON' })
      }
    } else if (phaseKey !== 'ofi' && prevPhase === 'ofi') {
      // Leaving OFI: turn off both LEDs
      invoke('send_hardware_command', { cmd: 'L_12_OFF' })
      invoke('send_hardware_command', { cmd: 'L_14_OFF' })
    }
  }, [caloricTimer.currentPhase.key, caloricTimer.isRunning])

  // Actions
  const handleStartCapture = async () => {
    try {
      const cameraId = appConfig?.vng?.camera?.camera_id ?? selectedCamera;
      const width = appConfig?.vng?.camera?.resolution_width ?? 960;
      const height = appConfig?.vng?.camera?.resolution_height ?? 540;
      const fps = appConfig?.vng?.camera?.fps ?? 120;

      console.log("[App] Starting capture with config:", { cameraId, width, height, fps });
      
      send({
        type: 'start_capture',
        camera_id: cameraId,
        width: width,
        height: height,
        fps: fps
      })
      setIsCapturing(true)

      // Initial sync of settings to Backend via WebSocket
      if (appConfig) {
        // Ensure session config has the latest persistent values
        sessionConfig.initFromPersistentConfig(appConfig);
        
        // Use the values directly from appConfig for the initial sync to avoid race conditions
        const vng = appConfig.vng;
        const algo = (vng.algorithm || {}) as any;
        const cam = (vng.camera || {}) as any;

        send({
            type: 'set_config',
            key: 'session_update',
            value: {
                brightness: cam.brightness ?? cam.exposure ?? -21,
                contrast: cam.contrast ?? 50,
                threshold: [algo.threshold_right ?? 40, algo.threshold_left ?? 40],
                erode: [algo.erode_right ?? 0, algo.erode_left ?? 0],
                nose_width: algo.nose_width ?? 0.25,
                eye_height: algo.eye_height ?? 0.25,
                use_yolo: algo.use_yolo ?? false,
                show_debug: algo.show_debug ?? false,
                smooth: algo.smooth ?? 2.5,
                manual_roi_right: algo.manual_roi_right,
                manual_roi_left: algo.manual_roi_left,
            }
        });

        send({
            type: 'set_config',
            key: 'pupil_mode',
            value: (appConfig.vng as any).pupil_detection?.mode ?? 'legacy'
        });
      }
    } catch (e) { console.error(e) }
  }

  const handleCalibrate = async () => {
    try {
        if (!appConfig) return;

        // 1. Open external display window (patient screen)
        const wasCreated = await invoke<boolean>('open_external_display');

        // Always wait a bit for the window to be ready
        await new Promise(resolve => setTimeout(resolve, wasCreated ? 1500 : 500));

        // 2. Clear any previous state
        await emit('stop_stimulus');
        await new Promise(resolve => setTimeout(resolve, 100));

        // 3. Get VNG calibration config from settings
        const cal = appConfig.vng.calibration;

        // 4. Emit manual calibration event with config
        await emit('start_manual_calibration', {
            patternType: cal.pattern_type,
            horizontalAngle: cal.horizontal_angle,
            verticalAngle: cal.vertical_angle,
            patientDistance: cal.patient_distance_cm || 150
        });

        // 5. Notify backend (Native Video) to prepare for calibration
        send({ type: 'send_command', cmd: 'calibrate' });

        console.log("[App] Manual Calibration started with pattern:", cal.pattern_type);
    } catch (e) {
        console.error("Failed to start manual calibration", e);
    }
  }

  // Render Capture View
  const renderCaptureView = () => (
    <div className="h-full flex flex-col font-sans text-xs">
      {!isFullscreen && (
        <StatusBar
          fps={0}
          recording={false}
          testType={currentTestType}
          patientName={currentPatient ? `${currentPatient.last_name}, ${currentPatient.first_name}` : null}
          onSelectTest={() => setActiveView('test_selection')}
          onSelectPatient={() => setActiveView('patients')}
        />
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 bg-black/20 relative">

          {/* Video Section */}
          <div className="relative flex-1 flex flex-col min-h-0">
             <div className="flex-1 bg-black flex items-center justify-center overflow-hidden">
                <VideoFeed
                  isCapturing={isCapturing}
                  cameraStatus={cameraStatus}
                  patientName={currentPatient ? `${currentPatient.last_name}, ${currentPatient.first_name}` : null}
                  testType={currentTestType}
                  caloricStageLabel={caloricProtocol.currentStageLabel}
                  isRecording={isRecording}
                  caloricTimer={caloricTimer.isRunning ? {
                    elapsedSeconds: caloricTimer.elapsedSeconds,
                    totalDuration: caloricTimer.totalDuration,
                    phaseName: caloricTimer.currentPhase.name,
                    phaseKey: caloricTimer.currentPhase.key,
                  } : null}
                />
             </div>
          </div>

          {currentTestType === 'caloric' && caloricProtocol.isProtocolActive && (
            <CaloricTimeline
              protocolName={caloricProtocol.protocol?.name ?? ''}
              stageLabel={caloricProtocol.currentStageLabel ?? ''}
              timing={caloricProtocol.protocol!.timing}
              elapsedSeconds={caloricTimer.elapsedSeconds}
              currentPhase={caloricTimer.currentPhase}
              progress={caloricTimer.progress}
              isRunning={caloricTimer.isRunning}
            />
          )}

          <div
             className="h-1.5 bg-dark-900 hover:bg-siev-600/50 cursor-row-resize flex items-center justify-center transition-colors z-30 border-t border-dark-800"
             onMouseDown={() => setIsResizing(true)}
          >
             <GripHorizontal className="w-3 h-3 text-dark-600" />
          </div>

          <div style={{ height: dataPanelHeight }} className="bg-dark-900 flex flex-col shrink-0 transition-none">
             <div className="px-3 py-1 bg-dark-800 border-b border-dark-700 text-[10px] font-bold text-dark-400 uppercase tracking-wider flex items-center gap-2 select-none">
                <Settings className="w-3 h-3" />
                Datos de Seguimiento
             </div>
             <div className="flex-1 overflow-hidden p-2">
                <EyeDataPanel isCapturing={isCapturing} />
             </div>
          </div>
        </div>

        {/* Controls */}
        <div className="w-[220px] bg-dark-900 border-l border-dark-800 flex flex-col shrink-0 z-20 shadow-xl">
           <div className="p-3 border-b border-dark-800 font-bold text-dark-300 text-[11px] uppercase tracking-wider bg-dark-850 flex items-center justify-between">
              Panel de Control
              {isFullscreen && (
                <button
                  onClick={toggleFullscreen}
                  className="p-1 rounded hover:bg-dark-700 text-dark-400 hover:text-white transition-colors"
                  title="Salir de pantalla completa (F11)"
                >
                  <Shrink className="w-3.5 h-3.5" />
                </button>
              )}
           </div>
           <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
              <ControlPanel
                isCapturing={isCapturing}
                onCalibrate={handleCalibrate}
                sessionConfig={sessionConfig}
                appConfig={appConfig}
                currentSession={currentSession}
                currentRecording={currentRecording}
                currentTestType={currentTestType}
                caloricProtocol={currentTestType === 'caloric' ? caloricProtocol : undefined}
                isRecording={isRecording}
                onRecordingChange={setIsRecording}
                onStartRecording={async () => {
                  if (currentTestType === 'caloric' && currentSession && caloricProtocol.isProtocolActive) {
                    // For caloric: create a new recording for each irrigation
                    const stageLabel = caloricProtocol.currentStageLabel || 'Irrigacion'
                    const stageIndex = caloricProtocol.currentStageIndex ?? 0
                    const rec = await createRecording(
                      currentSession.id,
                      'caloric',
                      stageLabel,
                      stageIndex
                    )
                    if (rec) {
                      setCurrentRecording(rec)
                      send({ type: 'start_recording', recording_id: rec.id })
                    }
                  } else if (currentRecording) {
                    send({ type: 'start_recording', recording_id: currentRecording.id })
                  }
                  setIsRecording(true)
                }}
                isCalibrated={isCalibrated}
                calibrationSource={calibrationSource}
                onBypassCalibration={() => setIsCalibrated(true)}
                onReviewSession={currentRecording ? () => {
                  setReviewRecordingId(currentRecording.id)
                  setActiveView('session_review')
                } : undefined}
                caloricTimerInfo={currentTestType === 'caloric' && caloricProtocol.protocol?.timing ? {
                  elapsedSeconds: caloricTimer.elapsedSeconds,
                  timing: caloricProtocol.protocol.timing,
                } : undefined}
                onRedoStage={currentTestType === 'caloric' ? (index: number) => caloricProtocol.redoStage(index) : undefined}
              />
           </div>
           {isFullscreen && (
             <div className="p-2 border-t border-dark-800 grid grid-cols-2 gap-2">
               <button
                 onClick={() => setActiveView('patients')}
                 className="btn btn-secondary h-8 text-[10px]"
               >
                 <Users className="w-3 h-3" />
                 Pacientes
               </button>
               <button
                 onClick={() => setActiveView('settings')}
                 className="btn btn-secondary h-8 text-[10px]"
               >
                 <Settings className="w-3 h-3" />
                 Config
               </button>
             </div>
           )}
        </div>
      </div>
      {!isFullscreen && (
        <footer className="bg-dark-950 border-t border-dark-800 px-3 py-1 text-[10px] text-dark-600 flex justify-between items-center shrink-0 select-none">
           <span>Sistema Integrado de Evaluación Vestibular (SIEV)</span>
           <span>v1.0.0</span>
        </footer>
      )}
    </div>
  )

  return (
    <div className={`h-screen bg-dark-950 flex flex-col overflow-hidden relative ${isFullscreen ? '' : 'border border-dark-800'}`}>
      {showSplash && <SplashScreen onFinished={() => setShowSplash(false)} />}

      {!isFullscreen && <TitleBar />}
      
      {activeView === 'user_selection' ? (
        <UserSelectionScreen
            onSelect={(spec) => {
                setActiveSpecialist(spec)
                setActiveView('patients')
            }}
        />
      ) : activeView === 'session_review' && reviewRecordingId ? (
        <div className="flex-1 overflow-hidden relative">
            <SessionReviewView
                recordingId={reviewRecordingId}
                onBack={() => { setReviewRecordingId(null); setActiveView('patients') }}
                onViewReport={() => {
                    setReportRecordingId(reviewRecordingId)
                    setActiveView('report')
                }}
            />
        </div>
      ) : activeView === 'report' && reportRecordingId ? (
        <div className="flex-1 overflow-hidden relative">
            <ReportGenerator
                sessionId={reportRecordingId}
                config={appConfig?.vng?.report ?? {
                    template: 'standard' as const,
                    sections: [
                        { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
                        { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
                        { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 7 },
                        { id: 'signature', label: 'Firma', enabled: true, order: 8 },
                    ],
                    export_format: 'pdf' as const,
                    include_logo: true,
                    include_raw_data: false,
                    include_graphs: true,
                    compare_with_previous: false,
                    diagram_style: 'claussen' as const,
                    analysis_method: 'both' as const,
                }}
                institutionName={appConfig?.general?.institution?.name ?? 'Centro de Diagnóstico VNG'}
                institutionLogo={appConfig?.general?.institution?.logo_path || undefined}
                onClose={() => { setReportRecordingId(null); setActiveView('patients') }}
            />
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden relative">
            {!(isFullscreen && activeView === 'capture') && (
              <Sidebar
                  activeView={activeView}
                  onNavigate={setActiveView}
                  activeSpecialist={activeSpecialist}
                  hasActiveTest={currentTestType !== null}
                  hasAudioTest={currentTestType?.startsWith('audio_') ?? false}
                  hasPosturalTest={(currentTestType?.startsWith('vppb_') || currentTestType?.startsWith('custom_')) ?? false}
                  onLogout={() => {
                      setActiveSpecialist(null)
                      setActiveView('user_selection')
                  }}
              />
            )}
            <div className="flex-1 bg-dark-950 relative overflow-hidden">
            {activeView === 'onboarding' && (
                <WelcomeWizard onComplete={() => setActiveView('user_selection')} />
            )}
            {activeView === 'capture' && renderCaptureView()}
            {activeView === 'patients' && (
                <PatientsView
                onSelectPatient={(p) => { setCurrentPatient(p); setActiveView('test_selection') }}
                onReviewRecording={(recordingId) => { setReviewRecordingId(recordingId); setActiveView('session_review') }}
                onViewReport={(recordingId) => { setReportRecordingId(recordingId); setActiveView('report') }}
                />
            )}
            {activeView === 'test_selection' && (
                        <TestSelectionView
                          patientName={currentPatient ? `${currentPatient.last_name}, ${currentPatient.first_name}` : "Modo Captura Libre"}
                          caloricProtocols={appConfig?.vng?.tests?.caloric?.protocols}
                          batteries={batteries}
                          appConfig={appConfig}
                          onBack={() => {
                            if (currentPatient) setActiveView('capture');
                            else setActiveView('patients');
                          }}
                          onSelectTest={async (testId, protocol?: CaloricProtocol) => {
                              const isAudioTest = testId.startsWith('audio_')
                              const isPosturalTest = testId.startsWith('vppb_') || testId.startsWith('custom_')
                              if (!isAudioTest && !isPosturalTest) {
                                if (currentPatient) {
                                  try {
                                    const calInfo = await invoke('load_patient_calibration', { patientId: currentPatient.id })
                                    if (calInfo) {
                                      setIsCalibrated(true)
                                      setCalibrationSource('saved')
                                    } else {
                                      setIsCalibrated(false)
                                      setCalibrationSource('none')
                                    }
                                  } catch {
                                    setIsCalibrated(false)
                                    setCalibrationSource('none')
                                  }
                                } else {
                                  setIsCalibrated(false)
                                  setCalibrationSource('none')
                                }
                              }

                              if (currentPatient) {
                                const protocolType = testId
                                const protocolConfig = protocol ? JSON.stringify(protocol) : null
                                const description = protocol ? protocol.name : `Evaluacion: ${testId}`

                                const session = await createSession(
                                    currentPatient.id,
                                    activeSpecialist?.id || null,
                                    description,
                                    protocolType,
                                    protocolConfig,
                                )
                                setCurrentSession(session)

                                if (testId === 'caloric' && protocol) {
                                  // For caloric: session created, recordings will be created per irrigation
                                  caloricProtocol.startProtocol(protocol)
                                } else {
                                  // For simple tests: create recording immediately
                                  caloricProtocol.resetProtocol()
                                  if (session) {
                                    const recording = await createRecording(
                                      session.id,
                                      testId,
                                      description,
                                      0
                                    )
                                    setCurrentRecording(recording)
                                  }
                                }
                              }

                              setCurrentTestType(testId)
                              setActiveView(isPosturalTest ? 'postural' : isAudioTest ? 'audiometry' : 'capture')
                          }}
                        />
                      )}

            {activeView === 'audiometry' && (
                <AudiometryView
                    testType={currentTestType || 'audio_tonal_liminar'}
                    patientName={currentPatient ? `${currentPatient.last_name}, ${currentPatient.first_name}` : null}
                    sessionId={currentSession?.id ?? null}
                    recordingId={currentRecording?.id ?? null}
                    onSelectTest={() => setActiveView('test_selection')}
                    onSelectPatient={() => setActiveView('patients')}
                />
            )}
            {activeView === 'postural' && (
                <PosturalView
                    isCapturing={isCapturing}
                    patientName={currentPatient ? `${currentPatient.last_name}, ${currentPatient.first_name}` : null}
                    posturalConfig={appConfig?.postural ?? {
                        timing: { auto_advance: false, countdown_sound: true },
                        visualization: { show_3d_head: true, show_target_orientation: true, head_model: 'ellipsoid' },
                        symptoms: {
                            scale: { type: 'vas_0_10' },
                            symptoms: [
                                { id: 'vertigo', label: 'Vértigo', enabled: true },
                                { id: 'nausea', label: 'Náusea', enabled: true },
                                { id: 'vomito', label: 'Vómito', enabled: true },
                            ],
                        },
                        enabled_tests: [],
                        custom_tests: [],
                    }}
                    onSelectTest={() => setActiveView('test_selection')}
                    onSelectPatient={() => setActiveView('patients')}
                />
            )}
            {activeView === 'settings' && (
                <SettingsView />
            )}
            </div>
        </div>
      )}
    </div>
  )
}

// App Router - Decides which app to load based on URL/Hash
// This prevents the secondary window from loading heavy hooks
function App() {
  const [isCalibrationWindow, setIsCalibrationWindow] = useState(false);
  const [isExternalDisplay, setIsExternalDisplay] = useState(false);
  const [screenTooSmall, setScreenTooSmall] = useState(false);
  const [screenSize, setScreenSize] = useState({ width: window.screen.width, height: window.screen.height });

  useEffect(() => {
    // Check hash immediately
    const hash = window.location.hash;
    if (hash === '#/calibration') {
      setIsCalibrationWindow(true);
    } else if (hash === '#/external-display' || hash === '#/stimulus') {
       // Support legacy hash for a moment or redirect
      setIsExternalDisplay(true);
    }
  }, []);

  // Verificar resolución mínima solo en la ventana principal
  useEffect(() => {
    const hash = window.location.hash;
    if (hash === '#/calibration' || hash === '#/external-display' || hash === '#/stimulus') return;

    const checkResolution = () => {
      const w = window.screen.width;
      const h = window.screen.height;
      setScreenSize({ width: w, height: h });
      setScreenTooSmall(w < 1280 || h < 720);
    };

    checkResolution();
    // Re-verificar si cambia la pantalla (e.g. conectar monitor externo)
    const mq = window.matchMedia('(min-width: 1280px) and (min-height: 720px)');
    const handler = () => checkResolution();
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  if (isCalibrationWindow) {
    return <CalibrationPage />;
  }

  if (isExternalDisplay) {
    return <ExternalDisplayPage />;
  }

  if (screenTooSmall) {
    return <ScreenTooSmallOverlay screenWidth={screenSize.width} screenHeight={screenSize.height} />;
  }

  return <MainApp />;
}

export default App
