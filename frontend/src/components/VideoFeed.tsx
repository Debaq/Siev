import { Video, VideoOff } from 'lucide-react'
import { useRef, useEffect, useState } from 'react'
import { useWebSocket } from '../contexts/WebSocketContext'

interface VideoFeedProps {
  isCapturing: boolean
}

function VideoFeed({ isCapturing }: VideoFeedProps) {
  const { addListener, removeListener } = useWebSocket()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hasSignal, setHasSignal] = useState(false)
  
  // Refs for the rendering loop logic
  const latestFrameRef = useRef<Blob | string | null>(null);
  const isRenderingRef = useRef(false);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isCapturing) {
        setHasSignal(false);
        return;
    }

    // 1. WebSocket Listener: Just update the latest frame reference (Zero overhead)
    const handleFrame = (data: Blob | string) => {
        latestFrameRef.current = data;
        setHasSignal(true);
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
                if (canvasRef.current) {
                    if (canvasRef.current.width !== bitmap.width || canvasRef.current.height !== bitmap.height) {
                        canvasRef.current.width = bitmap.width;
                        canvasRef.current.height = bitmap.height;
                    }
                    
                    const ctx = canvasRef.current.getContext('2d', { alpha: false, desynchronized: true });
                    if (ctx) {
                        ctx.drawImage(bitmap, 0, 0);
                    }
                }
                bitmap.close();
            } else {
                // Legacy path: Base64
                await new Promise<void>((resolve) => {
                    const img = new Image();
                    img.onload = () => {
                        if (canvasRef.current) {
                             if (canvasRef.current.width !== img.width || canvasRef.current.height !== img.height) {
                                canvasRef.current.width = img.width;
                                canvasRef.current.height = img.height;
                            }
                            const ctx = canvasRef.current.getContext('2d', { alpha: false });
                            ctx?.drawImage(img, 0, 0);
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
    <div className="w-full h-full relative flex items-center justify-center bg-black">
      <canvas 
        ref={canvasRef}
        className={`max-w-full max-h-full object-contain ${hasSignal ? 'block' : 'hidden'}`}
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
      </div>
    </div>
  )
}

export default VideoFeed