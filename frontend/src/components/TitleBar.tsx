import { useState, useEffect } from 'react'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { X, Minus, Square, Copy, Maximize2, Shrink } from 'lucide-react'

export default function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const appWindow = getCurrentWindow()

  // Function to sync state with the actual window
  const updateWindowState = async () => {
    try {
      const maximized = await appWindow.isMaximized()
      const fullscreen = await appWindow.isFullscreen()
      setIsMaximized(maximized)
      setIsFullscreen(fullscreen)
    } catch (e) {
      console.error("Failed to update window state:", e)
    }
  }

  useEffect(() => {
    updateWindowState()

    // Listen for resize to catch maximize/unmaximize from OS gestures
    const unlisten = appWindow.onResized(() => {
      updateWindowState()
    })

    const handleKeyDown = async (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (await appWindow.isFullscreen()) {
          await appWindow.setFullscreen(false)
          updateWindowState()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      unlisten.then(f => f())
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const handleMinimize = async () => {
    await appWindow.minimize()
  }

  const handleMaximize = async () => {
    try {
      await appWindow.toggleMaximize()
      setTimeout(updateWindowState, 100)
    } catch (e) {
      console.error(e)
    }
  }

  const handleFullscreen = async () => {
    const current = await appWindow.isFullscreen()
    await appWindow.setFullscreen(!current)
    setTimeout(updateWindowState, 100)
  }

  const handleClose = async () => {
    await appWindow.close()
  }

  return (
    <div className="h-8 bg-dark-950 flex items-center select-none border-b border-dark-800 shrink-0 overflow-hidden">
      
      {/* Logo & Draggable Title Area */}
      <div 
        data-tauri-drag-region 
        className="flex-1 h-full flex items-center gap-3 px-4 cursor-default"
      >
        <img src="/logo-small.png" alt="Logo" className="w-4 h-4 pointer-events-none" />
        <span className="text-xs font-semibold text-dark-300 tracking-wide pointer-events-none">
            SIEV <span className="text-dark-600 font-normal">v1.0.0</span>
        </span>
      </div>

      {/* Control Buttons Area */}
      <div className="flex h-full shrink-0">
        <button
          onClick={handleFullscreen}
          className="h-full px-3 hover:bg-dark-800 text-dark-400 hover:text-white transition-colors focus:outline-none"
          title={isFullscreen ? "Salir de Pantalla Completa" : "Pantalla Completa"}
        >
          {isFullscreen ? <Shrink className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
        </button>
        
        <button
          onClick={handleMinimize}
          className="h-full px-3 hover:bg-dark-800 text-dark-400 hover:text-white transition-colors focus:outline-none"
          title="Minimizar"
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
        
        <button
          onClick={handleMaximize}
          className="h-full px-3 hover:bg-dark-800 text-dark-400 hover:text-white transition-colors focus:outline-none"
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