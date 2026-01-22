import { useState, useEffect } from 'react'
import { 
  ArrowRight, Check, HardDrive, Building, Activity, LayoutGrid, CheckCircle2
} from 'lucide-react'
import { useTauriDb } from '../hooks/useTauriDb'
import { invoke } from '@tauri-apps/api/core'

interface WelcomeWizardProps {
  onComplete: () => void
}

export default function WelcomeWizard({ onComplete }: WelcomeWizardProps) {
  const [step, setStep] = useState(0)
  const { setSetting, createSpecialist } = useTauriDb()
  
  // Form State
  const [storagePath, setStoragePath] = useState('')
  const [clinicName, setClinicName] = useState('')
  const [doctorName, setDoctorName] = useState('')
  const [selectedModules, setSelectedModules] = useState<Record<string, boolean>>({
    vng: false,
    stimulus_screen: false
  })
  const [loading, setLoading] = useState(false)

  // Initialize defaults
  useEffect(() => {
    async function loadDefaults() {
      try {
        const defaultPath = await invoke<string>('get_default_storage_path')
        setStoragePath(defaultPath)
      } catch (e) {
        console.error(e)
      }
    }
    loadDefaults()
  }, [])

  const handleNext = async () => {
    if (step < 3) {
      setStep(prev => prev + 1)
    } else {
      // Finish
      setLoading(true)
      try {
        // 1. Create App Config object
        const appConfig = {
            modules: {
                vng: selectedModules.vng,
                vhit: false,
                static_posturography: false,
                imu_posturography: false,
                vemp: false,
                stimulus_screen: selectedModules.stimulus_screen,
                point_projector: false
            },
            clinic: {
                name: clinicName || "Centro de Diagnóstico VNG",
                doctor_name: doctorName || "",
                logo_path: ""
            },
            video: {
                camera_id: 2,
                resolution_width: 960,
                resolution_height: 540,
                fps: 120,
                exposure: -5,
                contrast: 50,
                flip_horizontal: false,
                flip_vertical: false
            },
            processing: {
                algorithm: "yolo",
                threshold: 40,
                min_pupil_size: 10,
                roi_enabled: true
            },
            hardware: {
                serial_port: "/dev/ttyUSB0",
                baudrate: 115200,
                stimulus_screen: 1
            }
        }

        // 2. Save Full Config & Individual settings
        await setSetting('app_config', JSON.stringify(appConfig))
        if (storagePath) await setSetting('storage_path', storagePath)
        if (clinicName) await setSetting('clinic_name', clinicName)
        
        // 3. Create first specialist profile
        if (doctorName && doctorName.trim()) {
            await createSpecialist(doctorName)
        }
        
        // 4. Mark as initialized
        await setSetting('app_initialized', 'true')
        
        setTimeout(() => {
            onComplete()
        }, 800)
      } catch (error) {
        console.error("Error finalizing setup:", error)
        setLoading(false)
      }
    }
  }

  const toggleModule = (id: string) => {
      setSelectedModules(prev => ({
          ...prev,
          [id]: !prev[id]
      }))
  }

  const steps = [
    {
      title: "Bienvenido a SIEV",
      subtitle: "Sistema Integrado de Evaluación Vestibular",
      icon: Activity,
      content: (
        <div className="text-center space-y-4 text-dark-300">
          <p className="text-base">
            Plataforma modular para la evaluación de la función vestibular. 
            SIEV unifica herramientas de diagnóstico en un entorno clínico diseñado para la precisión.
          </p>
          <div className="grid grid-cols-2 gap-3 mt-6">
            <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700 text-left">
                <span className="text-siev-400 font-bold text-[10px] uppercase">Protocolos</span>
                <p className="text-xs text-white">VNG, vHIT y VEMP</p>
            </div>
            <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700 text-left">
                <span className="text-purple-400 font-bold text-[10px] uppercase">Equilibrio</span>
                <p className="text-xs text-white">Análisis de Postura</p>
            </div>
            <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700 text-left">
                <span className="text-green-400 font-bold text-[10px] uppercase">Gestión</span>
                <p className="text-xs text-white">Historia Clínica Digital</p>
            </div>
            <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700 text-left">
                <span className="text-orange-400 font-bold text-[10px] uppercase">Hardware</span>
                <p className="text-xs text-white">Captura de Sensores e IMU</p>
            </div>
          </div>
        </div>
      )
    },
    {
      title: "Módulos de Diagnóstico",
      subtitle: "¿Qué hardware tienes disponible?",
      icon: LayoutGrid,
      content: (
        <div className="space-y-4">
          <p className="text-sm text-dark-300 mb-4">
            Selecciona los componentes físicos que conectarás a este equipo. 
            Podrás activar más módulos después desde los ajustes.
          </p>
          <div className="grid grid-cols-1 gap-3">
            {[
                { id: 'vng', name: 'Gafas VNG (Video)', desc: 'Cámara infrarroja de alta velocidad.', icon: '/mod_vng.png' },
                { id: 'stimulus_screen', name: 'Pantalla de Estímulos', desc: 'Monitor secundario para pruebas visuales.', icon: '/mod_stimulus.png' }
            ].map(m => (
                <button 
                    key={m.id}
                    onClick={() => toggleModule(m.id)}
                    className={`flex items-center gap-4 p-4 rounded-xl border transition-all text-left ${
                        selectedModules[m.id] 
                            ? 'bg-siev-500/10 border-siev-500 shadow-lg shadow-siev-900/10' 
                            : 'bg-dark-800 border-dark-700 hover:border-dark-600'
                    }`}
                >
                    <div className="w-12 h-12 rounded-lg bg-dark-950 border border-dark-700 flex items-center justify-center overflow-hidden flex-shrink-0">
                        <img src={m.icon} alt={m.name} className="w-10 h-10 object-contain" />
                    </div>

                    <div className="flex-1">
                        <div className={`font-bold text-sm ${selectedModules[m.id] ? 'text-white' : 'text-dark-200'}`}>{m.name}</div>
                        <div className="text-[11px] text-dark-500">{m.desc}</div>
                    </div>

                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                        selectedModules[m.id] ? 'bg-siev-500 border-siev-500' : 'border-dark-600'
                    }`}>
                        {selectedModules[m.id] && <Check className="w-4 h-4 text-white" />}
                    </div>
                </button>
            ))}
          </div>
        </div>
      )
    },
    {
      title: "Ecosistema de Datos",
      subtitle: "Almacenamiento Local",
      icon: HardDrive,
      content: (
        <div className="space-y-4">
          <p className="text-sm text-dark-300 leading-relaxed">
            El sistema utiliza una arquitectura de datos híbrida. La información clínica se gestiona en un núcleo de base de datos local, 
            mientras que las grabaciones de video se almacenan en una estructura de archivos dedicada.
          </p>
          
          <div className="space-y-2 pt-2">
            <label className="text-xs font-bold text-dark-400 uppercase tracking-wider">Directorio de Almacenamiento Principal</label>
            <div className="flex gap-2">
                <input 
                    className="input font-mono text-xs" 
                    value={storagePath}
                    onChange={(e) => setStoragePath(e.target.value)}
                />
            </div>
            <p className="text-[10px] text-dark-500">
                Esta ruta se utilizará para organizar los archivos binarios y multimedia de cada sesión.
            </p>
          </div>
        </div>
      )
    },
    {
      title: "Configuración Inicial",
      subtitle: "Identidad del Centro y Especialista",
      icon: Building,
      content: (
        <div className="space-y-4">
          <p className="text-sm text-dark-300 leading-relaxed">
            Registre los datos de su institución y cree el primer perfil de especialista. 
            Esto permitirá personalizar los informes y la gestión multi-usuario.
          </p>
          
          <div className="space-y-3 pt-2">
            <div>
                <label className="block text-xs font-bold text-dark-400 mb-1">Institución / Centro Médico</label>
                <input 
                    className="input" 
                    placeholder="Nombre de la institución"
                    value={clinicName}
                    onChange={(e) => setClinicName(e.target.value)}
                />
            </div>
            <div>
                <label className="block text-xs font-bold text-dark-400 mb-1">Nombre del Especialista</label>
                <input 
                    className="input" 
                    placeholder="Nombre Completo"
                    value={doctorName}
                    onChange={(e) => setDoctorName(e.target.value)}
                />
            </div>
          </div>
        </div>
      )
    }
  ]

  const CurrentIcon = steps[step].icon

  return (
    <div className="fixed inset-0 z-[100] bg-dark-950 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-dark-900 border border-dark-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-fade-in">
        
        {/* Progress Bar */}
        <div className="h-1 bg-dark-800 w-full flex">
            <div 
                className="bg-siev-500 transition-all duration-500 ease-out" 
                style={{ width: `${((step + 1) / steps.length) * 100}%` }}
            />
        </div>

        <div className="p-8 flex-1">
            <div className="flex flex-col items-center mb-8 text-center">
                <div className="relative mb-4">
                    <img 
                        src="/logo-large.png" 
                        alt="Logo" 
                        className={`w-20 h-20 object-contain transition-all duration-1000 ${step === 0 ? 'scale-100 opacity-100' : 'scale-75 opacity-0 absolute'}`}
                    />
                    {step !== 0 && (
                        <div className="w-16 h-16 bg-dark-800 rounded-full flex items-center justify-center text-siev-400 shadow-lg shadow-siev-900/20">
                            <CurrentIcon className="w-8 h-8" />
                        </div>
                    )}
                </div>
                <h2 className="text-2xl font-bold text-white mb-1">{steps[step].title}</h2>
                <p className="text-siev-200 font-medium">{steps[step].subtitle}</p>
            </div>

            <div className="max-w-md mx-auto min-h-[200px]">
                {steps[step].content}
            </div>
        </div>

        {/* Footer Actions */}
        <div className="p-6 bg-dark-850 border-t border-dark-800 flex justify-between items-center">
            {/* Step Indicators */}
            <div className="flex gap-2">
                {steps.map((_, i) => (
                    <div 
                        key={i} 
                        className={`w-2 h-2 rounded-full transition-colors ${
                            i === step ? 'bg-siev-500' : 
                            i < step ? 'bg-siev-800' : 'bg-dark-700'
                        }`} 
                    />
                ))}
            </div>

            <div className="flex gap-3">
                {step > 0 && (
                    <button 
                        onClick={() => setStep(prev => prev - 1)}
                        className="btn btn-secondary"
                        disabled={loading}
                    >
                        Anterior
                    </button>
                )}
                <button 
                    onClick={handleNext}
                    className="btn btn-primary px-6 flex items-center gap-2"
                    disabled={loading}
                >
                    {loading ? 'Finalizando...' : (step === steps.length - 1 ? 'Finalizar Configuración' : 'Siguiente')}
                    {!loading && (step === steps.length - 1 ? <Check className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />)}
                </button>
            </div>
        </div>
      </div>
    </div>
  )
}