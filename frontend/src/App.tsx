import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { Video, Settings, GripHorizontal, User } from 'lucide-react'
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

function App() {
  const { connected: isWsConnected, pythonStatus, hardwareStatus, cameras: wsCameras, send } = useWebSocket()
  const { getSetting, getSpecialists, createSession } = useTauriDb()
  
  // Initialize hooks with WebSocket send capability
  const { config: appConfig } = useSettingsConfig(send)
  const sessionConfig = useSessionConfig(send)
  
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

  // Sync selected camera with config or camera list
  useEffect(() => {
    // First, try to use the camera from config
    if (appConfig?.vng?.camera?.camera_id !== undefined) {
      setSelectedCamera(appConfig.vng.camera.camera_id);
    } else if (wsCameras.length > 0 && !wsCameras.find(c => c.id === selectedCamera)) {
      setSelectedCamera(wsCameras[0].id);
    }
  }, [wsCameras, appConfig?.vng?.camera?.camera_id])

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
      // Use config values from appConfig or defaults
      const cameraId = appConfig?.vng?.camera?.camera_id ?? selectedCamera;
      const width = appConfig?.vng?.camera?.resolution_width ?? 960;
      const height = appConfig?.vng?.camera?.resolution_height ?? 540;
      const fps = appConfig?.vng?.camera?.fps ?? 120;

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
        sessionConfig.initFromPersistentConfig(appConfig)
        // Sync current session values
        send({
            type: 'set_config',
            key: 'full_sync',
            value: sessionConfig.values
        });
      }
    } catch (e) { console.error(e) }
  }

  const handleStopCapture = async () => {
    try { 
      send({ type: 'stop_capture' })
      setIsCapturing(false) 
    } catch (e) { console.error(e) }
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
             {/* Toolbar Overlay */}
             <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-3 py-2 bg-gradient-to-b from-black/80 to-transparent">
                <div className="flex items-center gap-3">
                   <div className="flex items-center gap-1.5 text-white/90 font-medium">
                      <Video className="w-4 h-4 text-siev-400" />
                      <span>LIVE FEED</span>
                   </div>
                   <select 
                      className="bg-dark-800/80 border border-white/20 rounded text-dark-100 text-[10px] px-2 py-0.5 outline-none hover:bg-dark-700 focus:border-siev-500 transition-colors cursor-pointer"
                      value={selectedCamera}
                      onChange={(e) => setSelectedCamera(Number(e.target.value))}
                      disabled={isCapturing}
                   >
                      {wsCameras.map(c => (
                        <option key={c.id} value={c.id} className="bg-dark-800 text-dark-100">
                          {c.name}
                        </option>
                      ))}
                      {wsCameras.length === 0 && (
                        <option value={2} className="bg-dark-800 text-dark-100">Cámara VNG</option>
                      )}
                   </select>
                </div>
                
                <div className="flex items-center gap-2">
                   {!currentPatient && (
                     <button onClick={() => setActiveView('patients')} className="flex items-center gap-1 bg-yellow-500/10 border border-yellow-500/30 text-yellow-500 px-2 py-0.5 rounded text-[10px] hover:bg-yellow-500/20">
                       <User className="w-3 h-3" />
                       Seleccionar Paciente
                     </button>
                   )}
                   {isCapturing && <span className="text-green-400 text-[10px] font-bold bg-green-500/10 px-2 py-0.5 rounded border border-green-500/20">ONLINE</span>}
                </div>
             </div>

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
                onStartCapture={handleStartCapture}
                onStopCapture={handleStopCapture}
                onCalibrate={() => send({ type: 'send_command', cmd: 'calibrate' })}
                sessionConfig={sessionConfig}
                appConfig={appConfig}
                currentSession={currentSession}
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

export default App