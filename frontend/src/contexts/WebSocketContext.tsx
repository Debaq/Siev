import React, { createContext, useContext, ReactNode } from 'react';
import { useWebSocket as useWebSocketHook, EyeData, ImuData } from '../hooks/useWebSocket';

interface WebSocketContextType {
    connected: boolean;
    pythonStatus: boolean;
    hardwareStatus: boolean;
    cameras: any[];
    eyeData: EyeData | null;
    imuData: ImuData | null;
    videoFrame: string | null;
    send: (msg: any) => void;
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
