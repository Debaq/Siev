import { Video, VideoOff } from 'lucide-react'
import { useRef, useEffect, useState } from 'react'
import { useWebSocket } from '../contexts/WebSocketContext'

interface CaloricTimerOverlay {
  elapsedSeconds: number
  totalDuration: number
  phaseName: string
  phaseKey: 'delay' | 'irrigation' | 'recording' | 'torok' | 'ofi'
}

interface VideoFeedProps {
  isCapturing: boolean
  patientName?: string | null
  testType?: string | null
  caloricStageLabel?: string | null
  isRecording?: boolean
  caloricTimer?: CaloricTimerOverlay | null
}

const TEST_LABELS: Record<string, string> = {
  'spontaneous': 'Espontáneo',
  'saccades': 'Sacadas',
  'pursuit': 'Seguimiento',
  'positional': 'Posicional',
  'caloric': 'Calórico',
  'optokinetic': 'Optocinético',
}

const phaseBgColors: Record<string, string> = {
  delay: 'bg-dark-700/80',
  recording: 'bg-red-600/70',
  irrigation: 'bg-orange-600/70',
  torok: 'bg-amber-500/70',
  ofi: 'bg-green-500/70',
}

function formatOverlayTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function VideoFeed({ isCapturing, patientName, testType, caloricStageLabel, isRecording, caloricTimer }: VideoFeedProps) {
  const { addListener, removeListener } = useWebSocket()
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hasSignal, setHasSignal] = useState(false)
  const [fps, setFps] = useState(0)

  // Refs for the rendering loop logic
  const latestFrameRef = useRef<Blob | string | null>(null);
  const isRenderingRef = useRef(false);
  const animationFrameRef = useRef<number | null>(null);
  const frameCountRef = useRef(0);

  useEffect(() => {
    // FPS Counter interval
    const fpsInterval = setInterval(() => {
        setFps(frameCountRef.current);
        frameCountRef.current = 0;
    }, 1000);

    return () => clearInterval(fpsInterval);
  }, []);

  useEffect(() => {
    if (!isCapturing) {
        setHasSignal(false);
        return;
    }

    // 1. WebSocket Listener: Just update the latest frame reference (Zero overhead)
    const handleFrame = (data: Blob | string) => {
        latestFrameRef.current = data;
        // Solo actualizar estado si cambió (evita re-renders innecesarios)
        if (!hasSignal) setHasSignal(true);
    };

    // 2. Render Loop: Decoupled from network rate, synced to monitor refresh rate
    const renderLoop = async () => {
        if (!canvasRef.current || !latestFrameRef.current) {
            animationFrameRef.current = requestAnimationFrame(renderLoop);
            return;
        }

        // If already rendering a frame, skip this V-Sync cycle to avoid tearing/ordering issues
        if (isRenderingRef.current) {
            animationFrameRef.current = requestAnimationFrame(renderLoop);
            return;
        }

        isRenderingRef.current = true;
        const data = latestFrameRef.current;
        
        // Clear the ref so we don't re-render the same frame next time
        // (unless you want persistence, but for live video, clearing avoids duplicate work)
        latestFrameRef.current = null; 

        try {
            if (data instanceof Blob) {
                // Fast path: Binary
                const bitmap = await createImageBitmap(data);

                // Check if component is still mounted and canvas exists
                if (canvasRef.current && containerRef.current) {
                    // Obtener tamaño actual del contenedor
                    const containerW = containerRef.current.clientWidth;
                    const containerH = containerRef.current.clientHeight;

                    if (containerW === 0 || containerH === 0) {
                        bitmap.close();
                        isRenderingRef.current = false;
                        animationFrameRef.current = requestAnimationFrame(renderLoop);
                        return;
                    }

                    // Ajustar canvas al tamaño del contenedor (solo si cambió)
                    if (canvasRef.current.width !== containerW || canvasRef.current.height !== containerH) {
                        canvasRef.current.width = containerW;
                        canvasRef.current.height = containerH;
                    }

                    const ctx = canvasRef.current.getContext('2d', { alpha: false, desynchronized: true });
                    if (ctx) {
                        // Calcular escala manteniendo aspect ratio (contain)
                        const scale = Math.min(containerW / bitmap.width, containerH / bitmap.height);
                        const drawW = bitmap.width * scale;
                        const drawH = bitmap.height * scale;
                        const offsetX = (containerW - drawW) / 2;
                        const offsetY = (containerH - drawH) / 2;

                        // Limpiar y dibujar centrado
                        ctx.fillStyle = '#000';
                        ctx.fillRect(0, 0, containerW, containerH);
                        ctx.drawImage(bitmap, offsetX, offsetY, drawW, drawH);
                        frameCountRef.current += 1;
                    }
                }
                bitmap.close();
            } else {
                // Legacy path: Base64
                await new Promise<void>((resolve) => {
                    const img = new Image();
                    img.onload = () => {
                        if (canvasRef.current && containerRef.current) {
                            const containerW = containerRef.current.clientWidth;
                            const containerH = containerRef.current.clientHeight;

                            if (containerW === 0 || containerH === 0) {
                                resolve();
                                return;
                            }

                            if (canvasRef.current.width !== containerW || canvasRef.current.height !== containerH) {
                                canvasRef.current.width = containerW;
                                canvasRef.current.height = containerH;
                            }

                            const ctx = canvasRef.current.getContext('2d', { alpha: false });
                            if (ctx) {
                                const scale = Math.min(containerW / img.width, containerH / img.height);
                                const drawW = img.width * scale;
                                const drawH = img.height * scale;
                                const offsetX = (containerW - drawW) / 2;
                                const offsetY = (containerH - drawH) / 2;

                                ctx.fillStyle = '#000';
                                ctx.fillRect(0, 0, containerW, containerH);
                                ctx.drawImage(img, offsetX, offsetY, drawW, drawH);
                                frameCountRef.current += 1;
                            }
                        }
                        resolve();
                    };
                    img.src = `data:image/jpeg;base64,${data}`;
                });
            }
        } catch (e) {
            console.error("Frame render error:", e);
        } finally {
            isRenderingRef.current = false;
            animationFrameRef.current = requestAnimationFrame(renderLoop);
        }
    };

    addListener('video_frame', handleFrame);
    animationFrameRef.current = requestAnimationFrame(renderLoop);
    
    return () => {
        removeListener('video_frame', handleFrame);
        if (animationFrameRef.current !== null) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [isCapturing, addListener, removeListener]);

  if (!isCapturing) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="text-center text-dark-400">
          <VideoOff className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">Video no iniciado</p>
          <p className="text-sm mt-1">Presiona "Iniciar Captura" para comenzar</p>
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="w-full h-full relative bg-black overflow-hidden">
      <canvas
        ref={canvasRef}
        className={`absolute inset-0 ${hasSignal ? 'block' : 'hidden'}`}
      />
      
      {!hasSignal && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
          <div className="w-8 h-8 border-2 border-siev-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-dark-400">Esperando señal...</span>
        </div>
      )}
      
      {/* Video overlay with status */}
      <div className="absolute top-2 left-2 flex items-center gap-2">
        <div className="glass px-2 py-1 rounded flex items-center gap-2">
          <Video className="w-4 h-4 text-green-400" />
          <span className="text-xs text-green-400">LIVE</span>
        </div>
        <div className="glass px-2 py-1 rounded flex items-center gap-2">
          <span className={`text-xs font-mono font-bold ${fps < 25 ? 'text-red-400' : fps < 55 ? 'text-yellow-400' : 'text-green-400'}`}>
            {fps} FPS
          </span>
        </div>
        {patientName && (
          <div className="glass px-2 py-1 rounded">
            <span className="text-xs text-white font-medium">{patientName}</span>
          </div>
        )}
        {testType && (
          <div className="glass px-2 py-1 rounded">
            <span className="text-xs text-siev-400 font-medium">{TEST_LABELS[testType] || testType}</span>
          </div>
        )}
      </div>

      {/* Caloric timer overlay - centered, large */}
      {isRecording && caloricTimer && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className={`${phaseBgColors[caloricTimer.phaseKey] || 'bg-dark-700/80'} backdrop-blur-sm px-8 py-4 rounded-2xl shadow-2xl flex flex-col items-center gap-1`}>
            <span className="text-[56px] font-mono font-black text-white tabular-nums leading-none drop-shadow-lg">
              {formatOverlayTime(caloricTimer.elapsedSeconds)}
            </span>
            <span className="text-sm font-bold text-white/80 uppercase tracking-widest">
              {caloricTimer.phaseName}
            </span>
          </div>
        </div>
      )}

      {/* Caloric stage overlay - top right */}
      {isRecording && caloricStageLabel && (
        <div className="absolute top-2 right-2 bg-red-600/80 backdrop-blur-sm px-4 py-2 rounded-lg shadow-lg">
          <span className="text-xl font-black text-white tracking-wide">{caloricStageLabel}</span>
        </div>
      )}
    </div>
  )
}

export default VideoFeed