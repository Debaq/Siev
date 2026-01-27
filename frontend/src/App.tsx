import { useState, useEffect, useRef } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { emit } from '@tauri-apps/api/event'
import { Settings, GripHorizontal } from 'lucide-react'
import VideoFeed from './components/VideoFeed'
import ControlPanel from './components/ControlPanel'
import StatusBar from './components/StatusBar'
import EyeDataPanel from './components/EyeDataPanel'
import SettingsView from './components/SettingsView'
import PatientsView from './components/PatientsView'
import TestSelectionView from './components/TestSelectionView'
import WelcomeWizard from './components/WelcomeWizard'
import UserSelectionScreen from './components/UserSelectionScreen'
import SplashScreen from './components/SplashScreen'
import Sidebar from './components/Sidebar'
import TitleBar from './components/TitleBar'
import { useTauriDb, Specialist, Patient } from './hooks/useTauriDb'
import { useSettingsConfig } from './hooks/useSettingsConfig'
import { useSessionConfig } from './hooks/useSessionConfig'
import { useWebSocket } from './contexts/WebSocketContext'
import { CalibrationPage } from './pages/CalibrationPage'

import { ExternalDisplayPage } from './pages/ExternalDisplayPage'

// --- SEPARATION OF CONCERNS ---

// MainApp contains all the heavy logic (WebSockets, DB, etc.)
// This component should ONLY run in the main window.
const MainApp = () => {
  const { connected: isWsConnected, pythonStatus, hardwareStatus, cameras: wsCameras, send } = useWebSocket()
  const { getSetting, getSpecialists, createSession } = useTauriDb()
  
  // Initialize hooks with WebSocket send capability
  const { config: appConfig, updateConfig } = useSettingsConfig(send)
  const sessionConfig = useSessionConfig(send, updateConfig)
  
  // UX State
  const [showSplash, setShowSplash] = useState(true)

  // Navigation State
  const [activeView, setActiveView] = useState<'capture' | 'patients' | 'settings' | 'test_selection' | 'onboarding' | 'user_selection'>('user_selection')
  const [currentPatient, setCurrentPatient] = useState<Patient | null>(null)
  const [currentSession, setCurrentSession] = useState<any | null>(null)
  const [currentTestType, setCurrentTestType] = useState<string | null>(null)
  const [activeSpecialist, setActiveSpecialist] = useState<Specialist | null>(null)

  // App State
  const [isCapturing, setIsCapturing] = useState(false)
  const [selectedCamera, setSelectedCamera] = useState<number>(2)
  const [dataPanelHeight, setDataPanelHeight] = useState(240)
  const [isResizing, setIsResizing] = useState(false)

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

  // Initialization: Request cameras via WebSocket
  useEffect(() => {
    if (isWsConnected) {
        send({ type: 'list_cameras' })
    }
  }, [isWsConnected, send])

  const hasInitializedSessionRef = useRef(false);

  // Auto-start capture when entering capture view
  useEffect(() => {
    if (activeView === 'capture' && !isCapturing && isWsConnected) {
      console.log("[App] Auto-starting capture for VNG...");
      handleStartCapture();
    }
  }, [activeView, isWsConnected]);

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

      // Initial sync of settings to Python via WebSocket
      if (appConfig) {
        // Ensure session config has the latest persistent values
        sessionConfig.initFromPersistentConfig(appConfig);
        
        // Use the values directly from appConfig for the initial sync to avoid race conditions
        const vng = appConfig.vng;
        const algo = vng.algorithm || {};
        const cam = vng.camera || {};

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
            value: appConfig.vng.pupil_detection?.mode ?? 'legacy'
        });
      }
    } catch (e) { console.error(e) }
  }

  const handleCalibrate = async () => {
    try {
        if (!appConfig) return;

        // 1. Open external display window (patient screen)
        const wasCreated = await invoke<boolean>('open_external_display');
        
        if (wasCreated) {
            // Wait for window to load (React hydration)
            await new Promise(resolve => setTimeout(resolve, 1500));
        }

        // 2. Map VNG persistent calibration config to stimulus config
        const cal = appConfig.vng.calibration;
        const testConfig = {
            test: 'calibration',
            params: {
                type: cal.pattern_type === '3_points' ? 'points_3' : 
                      cal.pattern_type === '5_points' ? 'points_5' : 'points_9',
                horizontal_fov: cal.horizontal_angle,
                vertical_fov: cal.vertical_angle,
                duration_per_point: cal.point_duration,
                auto_advance: true
            }
        };

        // 3. Screen config from persistence
        const screenConfig = appConfig.stimulus_screen?.display;

        // 4. Target config (can be default or from config if added later)
        const targetConfig = {
            size_degrees: 1.5,
            color: 'red',
            shape: 'circle',
            brightness: 100
        };

        // 5. Emit stimulus event
        await emit('start_stimulus', {
            testConfig,
            targetConfig,
            screenConfig
        });

        // 6. Notify backend (Native Video) to start calibration mode
        send({ type: 'send_command', cmd: 'calibrate' });
        
        console.log("[App] Ocular Calibration started with pattern:", cal.pattern_type);
    } catch (e) {
        console.error("Failed to start ocular calibration", e);
    }
  }

  // Render Capture View
  const renderCaptureView = () => (
    <div className="h-full flex flex-col font-sans text-xs">
      <StatusBar
        isConnected={isWsConnected}
        videoStatus={pythonStatus ? 'online' : 'offline'}
        hardwareStatus={hardwareStatus ? 'online' : 'offline'}
        fps={0} 
        recording={false} 
        testType={currentTestType}
        patientName={currentPatient ? `${currentPatient.last_name}, ${currentPatient.first_name}` : null}
        onSelectTest={() => setActiveView('test_selection')}
        onSelectPatient={() => setActiveView('patients')}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 bg-black/20 relative">
          
          {/* Video Section */}
          <div className="relative flex-1 flex flex-col min-h-0">
             <div className="flex-1 bg-black flex items-center justify-center overflow-hidden">
                <VideoFeed isCapturing={isCapturing} />
             </div>
          </div>

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
           <div className="p-3 border-b border-dark-800 font-bold text-dark-300 text-[11px] uppercase tracking-wider bg-dark-850">
              Panel de Control
           </div>
           <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
              <ControlPanel
                isCapturing={isCapturing}
                onCalibrate={handleCalibrate}
                sessionConfig={sessionConfig}
                appConfig={appConfig}
                currentSession={currentSession}
                currentTestType={currentTestType}
              />
           </div>
        </div>
      </div>
      <footer className="bg-dark-950 border-t border-dark-800 px-3 py-1 text-[10px] text-dark-600 flex justify-between items-center shrink-0 select-none">
         <span>Sistema Integrado de Evaluación Vestibular (SIEV)</span>
         <span>v1.0.0</span>
      </footer>
    </div>
  )

  return (
    <div className="h-screen bg-dark-950 flex flex-col overflow-hidden border border-dark-800 relative">
      {showSplash && <SplashScreen onFinished={() => setShowSplash(false)} />}
      
      <TitleBar />
      
      {activeView === 'user_selection' ? (
        <UserSelectionScreen 
            onSelect={(spec) => {
                setActiveSpecialist(spec)
                setActiveView('patients')
            }}
        />
      ) : (
        <div className="flex-1 flex overflow-hidden relative">
            <Sidebar 
                activeView={activeView} 
                onNavigate={setActiveView} 
                activeSpecialist={activeSpecialist}
                onLogout={() => {
                    setActiveSpecialist(null)
                    setActiveView('user_selection')
                }}
            />
            <div className="flex-1 bg-dark-950 relative overflow-hidden">
            {activeView === 'onboarding' && (
                <WelcomeWizard onComplete={() => setActiveView('user_selection')} />
            )}
            {activeView === 'capture' && renderCaptureView()}
            {activeView === 'patients' && (
                <PatientsView 
                onSelectPatient={(p) => { setCurrentPatient(p); setActiveView('test_selection') }} 
                />
            )}
            {activeView === 'test_selection' && (
                        <TestSelectionView 
                          patientName={currentPatient ? `${currentPatient.last_name}, ${currentPatient.first_name}` : "Modo Captura Libre"}
                          onBack={() => { 
                            if (currentPatient) setActiveView('capture');
                            else setActiveView('patients');
                          }}
                          onSelectTest={async (testId) => { 
                              if (currentPatient) {
                                const session = await createSession(
                                    currentPatient.id, 
                                    activeSpecialist?.id || null, 
                                    `Evaluación: ${testId}`
                                )
                                setCurrentSession(session)
                              }
                              
                              setCurrentTestType(testId)
                              setActiveView('capture')
                          }}
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

  if (isCalibrationWindow) {
    return <CalibrationPage />;
  }

  if (isExternalDisplay) {
    return <ExternalDisplayPage />;
  }

  return <MainApp />;
}

export default App
