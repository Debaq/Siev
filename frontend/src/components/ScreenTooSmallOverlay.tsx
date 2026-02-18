import { AlertTriangle } from 'lucide-react'

interface ScreenTooSmallOverlayProps {
  screenWidth: number
  screenHeight: number
}

export default function ScreenTooSmallOverlay({ screenWidth, screenHeight }: ScreenTooSmallOverlayProps) {
  return (
    <div className="fixed inset-0 z-[9999] bg-dark-950 flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
        <h1 className="text-xl font-bold text-white mb-3">
          Resolución Insuficiente
        </h1>
        <p className="text-dark-300 mb-4 text-sm leading-relaxed">
          SIEV requiere una resolución mínima de <span className="text-white font-semibold">1280 x 720</span> píxeles para funcionar correctamente.
        </p>
        <div className="bg-dark-900 border border-dark-700 rounded-lg px-4 py-3 inline-block">
          <p className="text-dark-400 text-xs">
            Resolución detectada: <span className="text-red-400 font-mono font-semibold">{screenWidth} x {screenHeight}</span>
          </p>
        </div>
        <p className="text-dark-500 text-xs mt-4">
          Por favor, conecte un monitor con mayor resolución o ajuste la configuración de pantalla.
        </p>
      </div>
    </div>
  )
}
