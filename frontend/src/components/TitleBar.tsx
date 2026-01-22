import { useState, useEffect } from 'react'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { X, Minus, Square, Copy } from 'lucide-react'

export default function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false)
  const appWindow = getCurrentWindow()

  useEffect(() => {
    const checkMaximized = async () => {
      setIsMaximized(await appWindow.isMaximized())
    }
    
    // Check initially
    checkMaximized()

    // Listen for resize events to update the icon
    const unlisten = appWindow.onResized(() => {
      checkMaximized()
    })

    return () => {
      unlisten.then(f => f())
    }
  }, [])

  const handleMinimize = () => appWindow.minimize()
  const handleMaximize = async () => {
    await appWindow.toggleMaximize()
    setIsMaximized(await appWindow.isMaximized())
  }
  const handleClose = () => appWindow.close()

  return (
    <div 
        data-tauri-drag-region 
        className="h-8 bg-dark-950 flex justify-between items-center select-none border-b border-dark-800 shrink-0"
    >
      {/* App Logo/Title - Draggable Area */}
      <div className="flex items-center gap-3 px-4 h-full pointer-events-none">
        <div className="w-4 h-4 bg-siev-600 rounded flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
            S
        </div>
        <span className="text-xs font-semibold text-dark-300 tracking-wide">
            SIEV <span className="text-dark-600 font-normal">v1.0.0</span>
        </span>
      </div>

      {/* Window Controls - Non-Draggable */}
      <div className="flex h-full">
        <button
          onClick={handleMinimize}
          className="h-full px-4 hover:bg-dark-800 text-dark-400 hover:text-white transition-colors focus:outline-none"
          title="Minimizar"
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleMaximize}
          className="h-full px-4 hover:bg-dark-800 text-dark-400 hover:text-white transition-colors focus:outline-none"
          title={isMaximized ? "Restaurar" : "Maximizar"}
        >
          {isMaximized ? <Copy className="w-3 h-3" /> : <Square className="w-3 h-3" />}
        </button>
        <button
          onClick={handleClose}
          className="h-full px-4 hover:bg-red-600 text-dark-400 hover:text-white transition-colors focus:outline-none"
          title="Cerrar"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
