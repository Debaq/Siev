import { createContext, useContext, ReactNode } from 'react';
import { useWebSocket as useWebSocketHook } from '../hooks/useWebSocket';

interface WebSocketContextType {
    connected: boolean;
    hardwareStatus: boolean;
    cameras: any[];
    resolutions: string[];
    resolutionsCameraId: number;
    send: (msg: any) => void;
    addListener: (type: string, callback: (data: any) => void) => void;
    removeListener: (type: string, callback: (data: any) => void) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export function WebSocketProvider({ children }: { children: ReactNode }) {
    const ws = useWebSocketHook();
    
    return (
        <WebSocketContext.Provider value={ws}>
            {children}
        </WebSocketContext.Provider>
    );
}

export function useWebSocket() {
    const context = useContext(WebSocketContext);
    if (context === undefined) {
        throw new Error('useWebSocket must be used within a WebSocketProvider');
    }
    return context;
}
