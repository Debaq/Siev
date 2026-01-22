import { useState, useEffect } from 'react'
import { Settings, Camera, Activity, FileText, Monitor, Save, Database, Cpu } from 'lucide-react'
import { useTauriHardware } from '../hooks/useTauriHardware'

interface SettingsViewProps {
  apiUrl: string
}

function SettingsView({ apiUrl }: SettingsViewProps) {
  const [activeTab, setActiveTab] = useState('general')
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [cameras, setCameras] = useState<any[]>([])
  const [resolutions, setResolutions] = useState<string[]>([])
  const [showSuccess, setShowSuccess] = useState(false)
  const [applyingResolution, setApplyingResolution] = useState(false)
  
  // Tauri Hardware Hook
  const { ports, connect, disconnect, isConnected: isHwConnected, refreshPorts } = useTauriHardware()

  useEffect(() => {
    fetchConfig()
    fetchCameras()
  }, [])

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${apiUrl}/config`)
      if (res.ok) {
        setConfig(await res.json())
      }
    } catch (e) { console.error(e) } finally { setLoading(false) }
  }

  const fetchCameras = async () => {
    try {
      const res = await fetch(`${apiUrl}/video/cameras`)
      const data = await res.json()
      if (data.cameras) setCameras(data.cameras)
    } catch (e) { console.error(e) }
  }

  const fetchResolutions = async (cameraId?: number) => {
    try {
      const url = cameraId !== undefined
        ? `${apiUrl}/video/resolutions?camera_id=${cameraId}`
        : `${apiUrl}/video/resolutions`
      const res = await fetch(url)
      const data = await res.json()
      if (data.resolutions) setResolutions(data.resolutions)
    } catch (e) { console.error(e) }
  }

  // Fetch resolutions when camera changes
  useEffect(() => {
    if (config?.video?.camera_id !== undefined) {
      fetchResolutions(config.video.camera_id)
    }
  }, [config?.video?.camera_id])

  const handleResolutionSelect = async (resolutionStr: string) => {
    // Parse "widthxheight@fps" format
    const match = resolutionStr.match(/(\d+)x(\d+)@(\d+)/)
    if (match) {
      const width = parseInt(match[1])
      const height = parseInt(match[2])
      const fps = parseInt(match[3])

      // Update local state
      setConfig((prev: any) => ({
        ...prev,
        video: {
          ...prev.video,
          resolution_width: width,
          resolution_height: height,
          fps: fps
        }
      }))

      // Apply resolution change immediately
      setApplyingResolution(true)
      try {
        await fetch(`${apiUrl}/video/resolution?width=${width}&height=${height}&fps=${fps}`, {
          method: 'POST'
        })
      } catch (e) {
        console.error('Error applying resolution:', e)
      } finally {
        setApplyingResolution(false)
      }
    }
  }

  const getCurrentResolutionString = () => {
    if (config?.video) {
      return `${config.video.resolution_width}x${config.video.resolution_height}@${config.video.fps}`
    }
    return ''
  }

  const handleSave = async () => {
    try {
      // Save general config
      const res = await fetch(`${apiUrl}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })

      // Apply pupil detection config if it exists
      if (config.pupil_detection) {
        await fetch(`${apiUrl}/video/pupil/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config.pupil_detection)
        })
      }

      if (res.ok) {
        setShowSuccess(true)
        setTimeout(() => setShowSuccess(false), 3000)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const updateConfig = (section: string, key: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      [section]: { ...prev[section], [key]: value }
    }))
  }

  if (loading || !config) return <div className="text-white p-10">Cargando configuración...</div>

  const TabButton = ({ id, icon: Icon, label }: any) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors border-l-2 ${
        activeTab === id
          ? 'bg-dark-800 border-siev-500 text-white'
          : 'border-transparent text-dark-400 hover:text-dark-200 hover:bg-dark-900'
      }`}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )

  return (
    <div className="h-full flex bg-dark-950 text-dark-100 overflow-hidden">
      {/* Settings Sidebar */}
      <div className="w-64 bg-dark-950 border-r border-dark-800 flex flex-col shrink-0">
        <div className="p-6 border-b border-dark-800">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-siev-500" />
            Configuración
          </h2>
          <p className="text-xs text-dark-500 mt-1">Ajustes del sistema VNG</p>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          <TabButton id="general" icon={FileText} label="Datos Institucionales" />
          <TabButton id="video" icon={Camera} label="Video y Captura" />
          <TabButton id="hardware" icon={Monitor} label="Hardware Externo" />
          <TabButton id="processing" icon={Cpu} label="Algoritmos y Proceso" />
          <TabButton id="calibration" icon={Activity} label="Protocolo Calibración" />
          <TabButton id="reference" icon={Database} label="Valores Referencia" />
        </div>
        <div className="p-4 border-t border-dark-800">
          {showSuccess && (
            <div className="mb-3 p-2 bg-green-900/40 border border-green-800 text-green-400 text-[10px] rounded text-center animate-fade-in">
              ✓ Configuración guardada
            </div>
          )}
          <button 
            onClick={handleSave}
            className="btn btn-primary w-full py-2 flex items-center justify-center gap-2"
          >
            <Save className="w-4 h-4" />
            Guardar Cambios
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto bg-dark-900 p-8 custom-scrollbar">
        <div className="max-w-3xl mx-auto space-y-8">
          
          {/* General Settings */}
          {activeTab === 'general' && (
            <div className="space-y-6 animate-fade-in">
              <h3 className="text-lg font-bold text-white border-b border-dark-700 pb-2">Información de la Clínica</h3>
              <div className="grid grid-cols-1 gap-6">
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-1">Nombre de la Institución</label>
                  <input 
                    className="input" 
                    value={config.clinic.name}
                    onChange={e => updateConfig('clinic', 'name', e.target.value)}
                  />
                  <p className="text-xs text-dark-500 mt-1">Aparecerá en el encabezado de los reportes PDF.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-1">Nombre del Especialista (Default)</label>
                  <input 
                    className="input" 
                    value={config.clinic.doctor_name}
                    onChange={e => updateConfig('clinic', 'doctor_name', e.target.value)}
                  />
                </div>
                <div>
                    <label className="block text-sm font-medium text-dark-300 mb-1">Ruta del Logo</label>
                    <div className="flex gap-2">
                        <input 
                            className="input" 
                            value={config.clinic.logo_path}
                            onChange={e => updateConfig('clinic', 'logo_path', e.target.value)}
                            placeholder="/ruta/a/logo.png"
                        />
                        <button className="btn btn-secondary">Examinar</button>
                    </div>
                </div>
              </div>
            </div>
          )}

          {/* Video Settings */}
          {activeTab === 'video' && (
            <div className="space-y-6 animate-fade-in">
              <h3 className="text-lg font-bold text-white border-b border-dark-700 pb-2">Configuración de Cámara VNG</h3>

              <div className="grid grid-cols-2 gap-6">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-dark-300 mb-1">Dispositivo de Captura</label>
                  <select
                    className="select"
                    value={config.video.camera_id}
                    onChange={e => updateConfig('video', 'camera_id', Number(e.target.value))}
                  >
                    {cameras.map((c: any) => (
                      <option key={c.id} value={c.id}>{c.name} ({c.path})</option>
                    ))}
                  </select>
                </div>

                <div className="col-span-2">
                    <label className="block text-sm font-medium text-dark-300 mb-1">
                        Resolución de Captura
                        {applyingResolution && <span className="ml-2 text-siev-400 animate-pulse">Aplicando...</span>}
                    </label>
                    <select
                        className="select"
                        value={getCurrentResolutionString()}
                        onChange={e => handleResolutionSelect(e.target.value)}
                        disabled={applyingResolution}
                    >
                        {resolutions.length === 0 && (
                            <option value={getCurrentResolutionString()}>
                                {config.video.resolution_width}x{config.video.resolution_height}@{config.video.fps}
                            </option>
                        )}
                        {resolutions.map((res: string) => (
                            <option key={res} value={res}>{res}</option>
                        ))}
                    </select>
                    <p className="text-xs text-dark-500 mt-1">
                        Resolución actual: {config.video.resolution_width}x{config.video.resolution_height} @ {config.video.fps} FPS
                    </p>
                </div>

                <div className="col-span-2">
                    <label className="block text-sm font-medium text-dark-300 mb-1">Exposición (Manual)</label>
                    <input
                        type="number" className="input"
                        value={config.video.exposure}
                        onChange={e => updateConfig('video', 'exposure', Number(e.target.value))}
                    />
                    <p className="text-xs text-dark-500 mt-1">Valor negativo usualmente reduce luz ambiente.</p>
                </div>
              </div>

              <div className="pt-4 border-t border-dark-800">
                  <h4 className="font-bold text-white mb-4">Orientación de Imagen</h4>
                  <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={config.video.flip_horizontal}
                            onChange={e => updateConfig('video', 'flip_horizontal', e.target.checked)}
                          />
                          <span className="text-sm">Invertir Horizontalmente (Espejo)</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={config.video.flip_vertical}
                            onChange={e => updateConfig('video', 'flip_vertical', e.target.checked)}
                          />
                          <span className="text-sm">Invertir Verticalmente</span>
                      </label>
                  </div>
              </div>
            </div>
          )}

          {/* Hardware Settings */}
          {activeTab === 'hardware' && (
            <div className="space-y-6 animate-fade-in">
              <h3 className="text-lg font-bold text-white border-b border-dark-700 pb-2">Hardware Externo (Tauri/Rust)</h3>
              
              <div>
                  <label className="block text-sm font-medium text-dark-300 mb-1">Puerto Serial (IMU / Lights)</label>
                  <div className="flex gap-2">
                    <select 
                        className="select" 
                        value={config.hardware.serial_port}
                        onChange={e => updateConfig('hardware', 'serial_port', e.target.value)}
                    >
                        <option value="">Seleccione un puerto...</option>
                        {ports.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <button className="btn btn-secondary" onClick={refreshPorts}>Refrescar</button>
                  </div>
              </div>

              <div>
                  <label className="block text-sm font-medium text-dark-300 mb-1">Baud Rate</label>
                  <select 
                      className="select"
                      value={config.hardware.baudrate}
                      onChange={e => updateConfig('hardware', 'baudrate', Number(e.target.value))}
                  >
                      <option value="9600">9600</option>
                      <option value="115200">115200</option>
                      <option value="250000">250000</option>
                  </select>
              </div>

              <div className="flex items-center gap-4 pt-2">
                  <div className={`text-sm ${isHwConnected ? 'text-green-400' : 'text-red-400'}`}>
                      Estado: {isHwConnected ? 'CONECTADO' : 'DESCONECTADO'}
                  </div>
                  {!isHwConnected ? (
                      <button 
                        className="btn btn-primary"
                        onClick={() => connect(config.hardware.serial_port, config.hardware.baudrate)}
                        disabled={!config.hardware.serial_port}
                      >
                        Conectar Hardware
                      </button>
                  ) : (
                      <button 
                        className="btn btn-danger"
                        onClick={disconnect}
                      >
                        Desconectar
                      </button>
                  )}
              </div>

              <div>
                  <label className="block text-sm font-medium text-dark-300 mb-1">Pantalla de Estímulos</label>
                  <select 
                      className="select"
                      value={config.hardware.stimulus_screen}
                      onChange={e => updateConfig('hardware', 'stimulus_screen', Number(e.target.value))}
                  >
                      <option value="0">Pantalla Principal (0)</option>
                      <option value="1">Pantalla Secundaria (1)</option>
                      <option value="2">Pantalla Terciaria (2)</option>
                  </select>
                  <p className="text-xs text-dark-500 mt-1">Seleccione dónde se mostrará la barra de luces o estímulos optocinéticos.</p>
              </div>
            </div>
          )}

          {/* Processing Settings */}
          {activeTab === 'processing' && (
            <div className="space-y-6 animate-fade-in">
              <h3 className="text-lg font-bold text-white border-b border-dark-700 pb-2">Algoritmos de Rastreo</h3>

              <div>
                  <label className="block text-sm font-medium text-dark-300 mb-1">Algoritmo Principal</label>
                  <select
                      className="select"
                      value={config.processing.algorithm}
                      onChange={e => updateConfig('processing', 'algorithm', e.target.value)}
                  >
                      <option value="yolo">Deep Learning (YOLOv8) - Recomendado</option>
                      <option value="hough">Hough Circle Transform</option>
                      <option value="threshold">Dark Threshold (Pupil only)</option>
                  </select>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-medium text-dark-300 mb-1">Umbral de Binarización</label>
                    <input
                        type="number" className="input"
                        value={config.processing.threshold}
                        onChange={e => updateConfig('processing', 'threshold', Number(e.target.value))}
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-dark-300 mb-1">Tamaño Mín. Pupila (px)</label>
                    <input
                        type="number" className="input"
                        value={config.processing.min_pupil_size}
                        onChange={e => updateConfig('processing', 'min_pupil_size', Number(e.target.value))}
                    />
                </div>
              </div>

              {/* Pupil Detection Section */}
              <div className="pt-6 border-t border-dark-800">
                <h4 className="font-bold text-white mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 bg-siev-500 rounded-full"></span>
                  Detección de Pupila
                </h4>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-dark-300 mb-1">Modo de Detección</label>
                    <select
                        className="select"
                        value={config.pupil_detection?.mode || 'hybrid'}
                        onChange={e => updateConfig('pupil_detection', 'mode', e.target.value)}
                    >
                        <option value="hybrid">Híbrido (Recomendado) - Fast + Fallback Legacy</option>
                        <option value="fast">Fast - Ventana Local + Starburst</option>
                        <option value="legacy">Legacy - Threshold + CLAHE + Contornos</option>
                    </select>
                    <p className="text-xs text-dark-500 mt-1">
                      {config.pupil_detection?.mode === 'fast' && 'Máximo rendimiento, puede perder tracking en movimientos rápidos.'}
                      {config.pupil_detection?.mode === 'legacy' && 'Método tradicional, procesa toda la ROI en cada frame.'}
                      {(config.pupil_detection?.mode === 'hybrid' || !config.pupil_detection?.mode) && 'Combina velocidad del Fast con robustez del Legacy como respaldo.'}
                    </p>
                  </div>

                  {/* Advanced Settings - Only show for fast/hybrid */}
                  {(config.pupil_detection?.mode === 'fast' || config.pupil_detection?.mode === 'hybrid' || !config.pupil_detection?.mode) && (
                    <div className="mt-4 p-4 bg-dark-800/50 rounded-lg border border-dark-700">
                      <h5 className="text-sm font-medium text-dark-200 mb-3">Parámetros Avanzados (Fast/Hybrid)</h5>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-dark-400 mb-1">
                            Multiplicador Ventana
                          </label>
                          <input
                            type="number"
                            step="0.5"
                            min="1.5"
                            max="5"
                            className="input text-sm"
                            value={config.pupil_detection?.search_window_multiplier || 3.0}
                            onChange={e => updateConfig('pupil_detection', 'search_window_multiplier', Number(e.target.value))}
                          />
                          <p className="text-[10px] text-dark-500 mt-0.5">Ventana = radio × N</p>
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-dark-400 mb-1">
                            Offset Umbral Oscuro (%)
                          </label>
                          <input
                            type="number"
                            min="5"
                            max="50"
                            className="input text-sm"
                            value={config.pupil_detection?.dark_threshold_percent || 20}
                            onChange={e => updateConfig('pupil_detection', 'dark_threshold_percent', Number(e.target.value))}
                          />
                          <p className="text-[10px] text-dark-500 mt-0.5">% sobre punto más oscuro</p>
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-dark-400 mb-1">
                            Rayos Starburst
                          </label>
                          <select
                            className="select text-sm"
                            value={config.pupil_detection?.starburst_rays || 16}
                            onChange={e => updateConfig('pupil_detection', 'starburst_rays', Number(e.target.value))}
                          >
                            <option value="8">8 rayos (45°)</option>
                            <option value="12">12 rayos (30°)</option>
                            <option value="16">16 rayos (22.5°)</option>
                            <option value="24">24 rayos (15°)</option>
                          </select>
                          <p className="text-[10px] text-dark-500 mt-0.5">Más rayos = más precisión</p>
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-dark-400 mb-1">
                            Gradiente Mín. Borde
                          </label>
                          <input
                            type="number"
                            min="10"
                            max="80"
                            className="input text-sm"
                            value={config.pupil_detection?.starburst_min_gradient || 30}
                            onChange={e => updateConfig('pupil_detection', 'starburst_min_gradient', Number(e.target.value))}
                          />
                          <p className="text-[10px] text-dark-500 mt-0.5">Sensibilidad del borde</p>
                        </div>

                        {(config.pupil_detection?.mode === 'hybrid' || !config.pupil_detection?.mode) && (
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-dark-400 mb-1">
                              Umbral Fallback (frames)
                            </label>
                            <input
                              type="number"
                              min="1"
                              max="30"
                              className="input text-sm"
                              value={config.pupil_detection?.fallback_threshold || 5}
                              onChange={e => updateConfig('pupil_detection', 'fallback_threshold', Number(e.target.value))}
                            />
                            <p className="text-[10px] text-dark-500 mt-0.5">
                              Frames sin detección antes de activar Legacy como respaldo
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Legacy Settings - Show for legacy/hybrid */}
                  {(config.pupil_detection?.mode === 'legacy' || config.pupil_detection?.mode === 'hybrid' || !config.pupil_detection?.mode) && (
                    <div className="mt-4 p-4 bg-dark-800/50 rounded-lg border border-dark-700">
                      <h5 className="text-sm font-medium text-dark-200 mb-3">
                        Parámetros Legacy {config.pupil_detection?.mode === 'hybrid' ? '(usado en fallback)' : ''}
                      </h5>

                      {/* Blur Stage */}
                      <div className="mb-4 p-3 bg-dark-900/50 rounded border border-dark-600">
                        <div className="flex items-center justify-between mb-2">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={config.pupil_detection?.legacy_blur_enabled ?? true}
                              onChange={e => updateConfig('pupil_detection', 'legacy_blur_enabled', e.target.checked)}
                              className="rounded"
                            />
                            <span className="text-xs font-medium text-dark-300">1. GaussianBlur</span>
                          </label>
                          <span className="text-[10px] text-dark-500">Reducción de ruido</span>
                        </div>
                        {(config.pupil_detection?.legacy_blur_enabled ?? true) && (
                          <div className="ml-6">
                            <label className="block text-[10px] text-dark-400 mb-1">Tamaño Kernel</label>
                            <select
                              className="select text-sm w-32"
                              value={config.pupil_detection?.legacy_blur_kernel || 5}
                              onChange={e => updateConfig('pupil_detection', 'legacy_blur_kernel', Number(e.target.value))}
                            >
                              <option value="3">3×3</option>
                              <option value="5">5×5</option>
                              <option value="7">7×7</option>
                              <option value="9">9×9</option>
                            </select>
                          </div>
                        )}
                      </div>

                      {/* CLAHE Stage */}
                      <div className="mb-4 p-3 bg-dark-900/50 rounded border border-dark-600">
                        <div className="flex items-center justify-between mb-2">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={config.pupil_detection?.legacy_clahe_enabled ?? true}
                              onChange={e => updateConfig('pupil_detection', 'legacy_clahe_enabled', e.target.checked)}
                              className="rounded"
                            />
                            <span className="text-xs font-medium text-dark-300">2. CLAHE</span>
                          </label>
                          <span className="text-[10px] text-dark-500">Mejora de contraste</span>
                        </div>
                        {(config.pupil_detection?.legacy_clahe_enabled ?? true) && (
                          <div className="ml-6 grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-[10px] text-dark-400 mb-1">Clip Limit</label>
                              <input
                                type="number"
                                step="0.5"
                                min="1"
                                max="5"
                                className="input text-sm"
                                value={config.pupil_detection?.legacy_clahe_clip_limit || 2.0}
                                onChange={e => updateConfig('pupil_detection', 'legacy_clahe_clip_limit', Number(e.target.value))}
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] text-dark-400 mb-1">Grid Size</label>
                              <select
                                className="select text-sm"
                                value={config.pupil_detection?.legacy_clahe_grid_size || 8}
                                onChange={e => updateConfig('pupil_detection', 'legacy_clahe_grid_size', Number(e.target.value))}
                              >
                                <option value="4">4×4</option>
                                <option value="8">8×8</option>
                                <option value="16">16×16</option>
                              </select>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Morphological Stage */}
                      <div className="p-3 bg-dark-900/50 rounded border border-dark-600">
                        <div className="flex items-center justify-between mb-2">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={config.pupil_detection?.legacy_morph_enabled ?? true}
                              onChange={e => updateConfig('pupil_detection', 'legacy_morph_enabled', e.target.checked)}
                              className="rounded"
                            />
                            <span className="text-xs font-medium text-dark-300">3. Morfología</span>
                          </label>
                          <span className="text-[10px] text-dark-500">Close + Dilate</span>
                        </div>
                        {(config.pupil_detection?.legacy_morph_enabled ?? true) && (
                          <div className="ml-6 grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-[10px] text-dark-400 mb-1">Close Iters</label>
                              <input
                                type="number"
                                min="0"
                                max="5"
                                className="input text-sm"
                                value={config.pupil_detection?.legacy_morph_close_iterations ?? 1}
                                onChange={e => updateConfig('pupil_detection', 'legacy_morph_close_iterations', Number(e.target.value))}
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] text-dark-400 mb-1">Dilate Iters</label>
                              <input
                                type="number"
                                min="0"
                                max="5"
                                className="input text-sm"
                                value={config.pupil_detection?.legacy_morph_dilate_iterations ?? 1}
                                onChange={e => updateConfig('pupil_detection', 'legacy_morph_dilate_iterations', Number(e.target.value))}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

           {/* Calibration Settings */}
           {activeTab === 'calibration' && (
            <div className="space-y-6 animate-fade-in">
              <h3 className="text-lg font-bold text-white border-b border-dark-700 pb-2">Protocolo de Calibración</h3>
              
              <div>
                  <label className="block text-sm font-medium text-dark-300 mb-1">Patrón de Puntos</label>
                  <select 
                      className="select"
                      value={config.calibration.pattern_type}
                      onChange={e => updateConfig('calibration', 'pattern_type', e.target.value)}
                  >
                      <option value="3_points">3 Puntos (Horizontal)</option>
                      <option value="5_points">5 Puntos (Cruz)</option>
                      <option value="9_points">9 Puntos (Rejilla)</option>
                  </select>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-medium text-dark-300 mb-1">Ángulo Horizontal (Grados)</label>
                    <input 
                        type="number" className="input" 
                        value={config.calibration.horizontal_angle}
                        onChange={e => updateConfig('calibration', 'horizontal_angle', Number(e.target.value))}
                    />
                    <p className="text-xs text-dark-500 mt-1">Normalmente 15° o 30°.</p>
                </div>
                <div>
                    <label className="block text-sm font-medium text-dark-300 mb-1">Ángulo Vertical (Grados)</label>
                    <input 
                        type="number" className="input" 
                        value={config.calibration.vertical_angle}
                        onChange={e => updateConfig('calibration', 'vertical_angle', Number(e.target.value))}
                    />
                    <p className="text-xs text-dark-500 mt-1">Normalmente 10° o 20°.</p>
                </div>
                <div>
                    <label className="block text-sm font-medium text-dark-300 mb-1">Duración por Punto (seg)</label>
                    <input 
                        type="number" step="0.5" className="input" 
                        value={config.calibration.point_duration}
                        onChange={e => updateConfig('calibration', 'point_duration', Number(e.target.value))}
                    />
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

export default SettingsView
