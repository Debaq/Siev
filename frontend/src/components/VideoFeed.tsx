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

  useEffect(() => {
    if (!isCapturing) {
        setHasSignal(false);
        return;
    }

    const image = new Image();
    
    const handleFrame = (data: string) => {
        if (!canvasRef.current) return;
        setHasSignal(true);
        
        // Load image and draw to canvas
        // Note: Ideally backend sends blobs, but for base64 this is the way
        image.onload = () => {
            if (!canvasRef.current) return;
            // Update canvas dimensions if needed to match source
            if (canvasRef.current.width !== image.width || canvasRef.current.height !== image.height) {
                canvasRef.current.width = image.width;
                canvasRef.current.height = image.height;
            }
            const ctx = canvasRef.current.getContext('2d', { alpha: false }); // alpha: false optimizes rendering
            if (ctx) {
                ctx.drawImage(image, 0, 0);
            }
        };
        image.src = `data:image/jpeg;base64,${data}`;
    };

    addListener('video_frame', handleFrame);
    
    return () => {
        removeListener('video_frame', handleFrame);
        // Clear canvas or state if needed
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