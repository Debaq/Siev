import { useState, useEffect } from 'react'
import { Video, Settings, GripHorizontal, User, X } from 'lucide-react'
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
import { useBackend } from './hooks/useBackend'
import { useTauriDb, Specialist } from './hooks/useTauriDb'
import { useTauriHardware } from './hooks/useTauriHardware'
import { syncWithBackend, DEFAULT_APP_CONFIG, deepMerge, useSettingsConfig } from './hooks/useSettingsConfig'
import { useSessionConfig } from './hooks/useSessionConfig'

const API_URL = 'http://localhost:8000'

// ... (existing interfaces)

function App() {
  const { health, isConnected: isBackendConnected, checkHealth } = useBackend(API_URL)
  const { getSetting, getSpecialists, createSession } = useTauriDb()
  const { config: appConfig } = useSettingsConfig(API_URL)
  const sessionConfig = useSessionConfig(API_URL)
  
  // Tauri Hardware Integration
  const { isConnected: isHwConnected } = useTauriHardware(appConfig)
  
  // UX State
  const [showSplash, setShowSplash] = useState(true)

  // Navigation State
  const [activeView, setActiveView] = useState<'capture' | 'patients' | 'settings' | 'test_selection' | 'onboarding' | 'user_selection'>('user_selection')
  const [currentPatient, setCurrentPatient] = useState<Patient | null>(null)
  const [currentTestType, setCurrentTestType] = useState<string | null>(null)
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [activeSpecialist, setActiveSpecialist] = useState<Specialist | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)

  // App State
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    video: 'offline', hardware: 'offline', recording: false, fps: 0,
  })

  // Sync Hardware Status
  useEffect(() => {
    setSystemStatus(prev => {
      const newStatus = isHwConnected ? 'online' : 'offline'
      if (prev.hardware === newStatus) return prev
      return { ...prev, hardware: newStatus }
    })
  }, [isHwConnected])
  const [isCapturing, setIsCapturing] = useState(false)
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCamera, setSelectedCamera] = useState<number>(2)
  const [dataPanelHeight, setDataPanelHeight] = useState(240)
  const [isResizing, setIsResizing] = useState(false)

  // Check Initialization
  useEffect(() => {
    async function checkInit() {
      try {
        const initialized = await getSetting('app_initialized')
        if (initialized !== 'true') {
          setActiveView('onboarding')
        } else {
          setIsInitialized(true)
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

  // Initialization
  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const res = await fetch(`${API_URL}/video/cameras`)
        const data = await res.json()
        if (data.cameras?.length) {
          setCameras(data.cameras)
          if (!data.cameras.find((c: any) => c.id === selectedCamera)) setSelectedCamera(data.cameras[0].id)
        }
      } catch (e) { console.error(e) }
    }

    fetchCameras()

    const interval = setInterval(checkHealth, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (health) {
      setSystemStatus(prev => {
        const newVideo = health.video_status === 'capturing' ? 'online' : 'offline'
        const newRecording = health.recording_status === 'recording'
        
        if (prev.video === newVideo && prev.recording === newRecording) return prev
        
        return {
          ...prev,
          video: newVideo,
          recording: newRecording,
          fps: health.uptime > 0 ? prev.fps : 0,
        }
      })
    }
  }, [health])

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
      const storagePath = await getSetting('storage_path')

      await fetch(`${API_URL}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            camera_id: selectedCamera,
            storage_path: storagePath
        })
      })
      setIsCapturing(true)

      // Sync pupil detection config with backend after starting capture
      // Initialize sessionConfig from persistent config
      try {
        const storedConfig = await getSetting('app_config')
        const config = storedConfig
          ? deepMerge(DEFAULT_APP_CONFIG, JSON.parse(storedConfig))
          : DEFAULT_APP_CONFIG

        // Initialize session config base values from persistent config
        sessionConfig.initFromPersistentConfig(config)

        // Sync persistent config (camera setup, pupil detection) with backend
        // Include session fields only if there are no active overrides
        const hasActiveOverrides = sessionConfig.hasOverrides
        await syncWithBackend(config, API_URL, sessionConfig.getOverrides(), !hasActiveOverrides)

        // If there are active session overrides, apply them on top
        if (hasActiveOverrides) {
          await sessionConfig.syncToBackend()
        }
      } catch (syncError) {
        console.error('Error syncing pupil config:', syncError)
      }
    } catch (e) { console.error(e) }
  }

  const handleStopCapture = async () => {
    try { await fetch(`${API_URL}/stop`, { method: 'POST' }); setIsCapturing(false) } catch (e) { console.error(e) }
  }

  // Render Capture View
  const renderCaptureView = () => (
    <div className="h-full flex flex-col font-sans text-xs">
      <StatusBar
        isConnected={isBackendConnected}
        videoStatus={systemStatus.video}
        hardwareStatus={systemStatus.hardware}
        fps={systemStatus.fps}
        recording={systemStatus.recording}
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
                      {cameras.map(c => <option key={c.id} value={c.id} className="bg-dark-800 text-dark-100">{c.name}</option>)}
                      {cameras.length === 0 && <option value={2} className="bg-dark-800 text-dark-100">Default Camera</option>}
                   </select>
                </div>
                
                <div className="flex items-center gap-2">
                   {!currentPatient && (
                     <button onClick={() => setActiveView('patients')} className="flex items-center gap-1 bg-yellow-500/10 border border-yellow-500/30 text-yellow-500 px-2 py-0.5 rounded text-[10px] hover:bg-yellow-500/20">
                       <User className="w-3 h-3" />
                       Seleccionar Paciente
                     </button>
                   )}
                   {systemStatus.recording && (
                      <span className="flex items-center gap-1 bg-red-500/20 border border-red-500/50 text-red-400 px-2 py-0.5 rounded text-[10px] font-bold">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                        REC
                      </span>
                   )}
                   {isCapturing && <span className="text-green-400 text-[10px] font-bold bg-green-500/10 px-2 py-0.5 rounded border border-green-500/20">ONLINE</span>}
                </div>
             </div>

             <div className="flex-1 bg-black flex items-center justify-center overflow-hidden">
                <VideoFeed apiUrl={API_URL} isCapturing={isCapturing} />
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
                <EyeDataPanel apiUrl={API_URL} isCapturing={isCapturing} />
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
                isRecording={systemStatus.recording}
                hardwareStatus={systemStatus.hardware}
                onStartCapture={handleStartCapture}
                onStopCapture={handleStopCapture}
                onStartRecording={async () => { try { await fetch(`${API_URL}/recording/start`, { method: 'POST' }) } catch (e) { console.error(e) } }}
                onStopRecording={async () => { try { await fetch(`${API_URL}/recording/stop`, { method: 'POST' }) } catch (e) { console.error(e) } }}
                onCalibrate={async () => { try { await fetch(`${API_URL}/calibrate`, { method: 'POST' }) } catch (e) { console.error(e) } }}
                sessionConfig={sessionConfig}
                appConfig={appConfig}
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
                              // If there is a patient, create a formal session in DB
                              if (currentPatient) {
                                const session = await createSession(
                                    currentPatient.id, 
                                    activeSpecialist?.id || null, 
                                    `Evaluación: ${testId}`
                                )
                                if (session) {
                                    setCurrentSessionId(session.id)
                                }
                              } else {
                                // If no patient, we just set the UI state for the capture view
                                setCurrentSessionId(null);
                              }
                              
                              setCurrentTestType(testId)
                              setActiveView('capture')
                          }}
                        />
                      )}
            
            {activeView === 'settings' && (
                <SettingsView apiUrl={API_URL} />
            )}
            </div>
        </div>
      )}
    </div>
  )
}

export default App
