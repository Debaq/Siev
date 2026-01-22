import { useState, useCallback, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { listen, UnlistenFn } from '@tauri-apps/api/event'

export interface ImuData {
  yaw: number
  pitch: number
  roll: number
  timestamp: number
}

interface UseTauriHardwareReturn {
  ports: string[]
  isConnected: boolean
  error: string | null
  imuData: ImuData | null
  refreshPorts: () => Promise<void>
  connect: (port: string, baudRate: number) => Promise<void>
  disconnect: () => Promise<void>
  sendCommand: (cmd: string) => Promise<void>
  controlLed: (led: 'left' | 'right' | 'all', action: 'on' | 'off') => Promise<void>
}

export function useTauriHardware(): UseTauriHardwareReturn {
  const [ports, setPorts] = useState<string[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imuData, setImuData] = useState<ImuData | null>(null)

  // Listen for IMU data from Rust
  useEffect(() => {
    let unlisten: UnlistenFn | undefined

    const setupListener = async () => {
      try {
        unlisten = await listen<ImuData>('imu-data', (event) => {
          setImuData(event.payload)
        })
      } catch (err) {
        console.error('Failed to setup IMU listener:', err)
      }
    }

    setupListener()

    return () => {
      if (unlisten) unlisten()
    }
  }, [])

  const refreshPorts = useCallback(async () => {
    try {
      const portList = await invoke<string[]>('list_serial_ports')
      setPorts(portList)
      setError(null)
    } catch (err) {
      console.error('Failed to list ports:', err)
      setError('Failed to list serial ports')
    }
  }, [])

  const connect = useCallback(async (port: string, baudRate: number) => {
    try {
      await invoke('connect_hardware', { port, baudRate })
      setIsConnected(true)
      setError(null)
    } catch (err) {
      console.error('Failed to connect:', err)
      setIsConnected(false)
      setError(typeof err === 'string' ? err : 'Connection failed')
      throw err
    }
  }, [])

  const disconnect = useCallback(async () => {
    try {
      await invoke('disconnect_hardware')
      setIsConnected(false)
    } catch (err) {
      console.error('Failed to disconnect:', err)
    }
  }, [])

  const sendCommand = useCallback(async (cmd: string) => {
    if (!isConnected) return
    try {
      await invoke('send_hardware_command', { cmd })
    } catch (err) {
      console.error(`Failed to send command ${cmd}:`, err)
      setError(`Failed to send command: ${cmd}`)
    }
  }, [isConnected])

  const controlLed = useCallback(async (led: 'left' | 'right' | 'all', action: 'on' | 'off') => {
    let cmd = ''
    if (led === 'all' && action === 'off') {
        // Turn off both
        await sendCommand('L_12_OFF')
        await sendCommand('L_14_OFF')
        return
    }

    // Map logic from Python backend to Serial commands
    // Left = 12, Right = 14
    const pin = led === 'left' ? '12' : '14'
    const state = action === 'on' ? 'ON' : 'OFF'
    cmd = `L_${pin}_${state}`
    
    await sendCommand(cmd)
  }, [sendCommand])

  // Initial port load
  useEffect(() => {
    refreshPorts()
  }, [refreshPorts])

  return {
    ports,
    isConnected,
    error,
    imuData,
    refreshPorts,
    connect,
    disconnect,
    sendCommand,
    controlLed
  }
}
