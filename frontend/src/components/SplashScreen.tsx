import { useEffect, useState } from 'react'
import { Activity, Eye } from 'lucide-react'

interface SplashScreenProps {
  onFinished: () => void
  minimumWait?: number
}

export default function SplashScreen({ onFinished, minimumWait = 5000 }: SplashScreenProps) {
  const [isExiting, setIsExiting] = useState(false)
  const [showText, setShowText] = useState(false)

  useEffect(() => {
    // Stage 1: Show logo, then show text
    const textTimer = setTimeout(() => setShowText(true), 600)
    
    // Stage 2: Start exit transition
    const exitTimer = setTimeout(() => {
      setIsExiting(true)
    }, minimumWait)

    return () => {
        clearTimeout(textTimer)
        clearTimeout(exitTimer)
    }
  }, [minimumWait])

  const handleTransitionEnd = () => {
    if (isExiting) onFinished()
  }

  return (
    <div 
      className={`fixed inset-0 z-[9999] bg-dark-950 flex flex-col items-center justify-center transition-all duration-1000 ease-in-out ${
        isExiting ? 'opacity-0 scale-105' : 'opacity-100'
      }`}
      onTransitionEnd={handleTransitionEnd}
    >
      {/* Dynamic Background Glow */}
      <div className="absolute w-[500px] h-[500px] bg-siev-600/10 blur-[120px] rounded-full animate-pulse" />

      <div className="relative flex flex-col items-center">
        
        {/* Animated Logo */}
        <div className={`relative mb-10 transition-all duration-1000 transform ${showText ? 'scale-100 opacity-100' : 'scale-75 opacity-0'}`}>
            <div className="absolute inset-0 bg-siev-500/30 blur-2xl rounded-full animate-ping [animation-duration:3s]" />
            <img 
                src="/logo-large.png" 
                alt="SIEV Logo" 
                className="relative w-32 h-32 object-contain drop-shadow-[0_0_15px_rgba(14,165,233,0.3)]" 
            />
        </div>

        {/* Branding Container */}
        <div className={`flex flex-col items-center transition-all duration-1000 delay-300 transform ${showText ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}>
            <h1 className="text-7xl font-black tracking-tighter text-white mb-2">
                <span className="bg-clip-text text-transparent bg-gradient-to-b from-white to-dark-400">
                    SIEV
                </span>
            </h1>
            
            <div className="h-1 w-12 bg-siev-500 rounded-full mb-6" />

            <div className="space-y-1 text-center">
                <p className="text-dark-200 text-lg font-bold tracking-[0.3em] uppercase">
                    Sistema Integrado
                </p>
                <p className="text-dark-500 text-sm font-medium tracking-[0.1em] uppercase">
                    de Evaluación Vestibular
                </p>
            </div>
        </div>

        {/* Sub-components/Security Badges */}
        <div className={`absolute -bottom-40 flex gap-8 transition-all duration-1000 delay-700 ${showText ? 'opacity-100' : 'opacity-0'}`}>
            <div className="flex items-center gap-2 text-dark-600">
                <div className="w-1 h-1 bg-siev-500 rounded-full" />
                <span className="text-[10px] font-bold tracking-widest uppercase">Precision Tracking</span>
            </div>
            <div className="flex items-center gap-2 text-dark-600">
                <div className="w-1 h-1 bg-siev-500 rounded-full" />
                <span className="text-[10px] font-bold tracking-widest uppercase">Multi-Device Engine</span>
            </div>
        </div>
      </div>
    </div>
  )
}