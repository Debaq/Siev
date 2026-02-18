import { useState, useEffect, useCallback, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

export interface EyeData {
    left: [number, number] | null;
    right: [number, number] | null;
    timestamp: number;
    is_calibrated: boolean;
}

export interface ImuData {
    yaw: number;
    pitch: number;
    roll: number;
}

export type WsMessage =
    | { type: 'eye_data'; left: [number, number] | null; right: [number, number] | null; timestamp: number; is_calibrated: boolean }
    | { type: 'video_frame'; data: string }
    | { type: 'imu_data'; yaw: number; pitch: number; roll: number }
    | { type: 'error'; source: string; message: string }
    | { type: 'cameras_list'; cameras: any[] }
    | { type: 'resolutions_list'; resolutions: string[]; camera_id: number }
    | { type: 'list_cameras' }
    | { type: 'list_resolutions'; camera_id: number }
    | { type: 'start_capture'; camera_id: number; width: number; height: number; fps?: number }
    | { type: 'stop_capture' }
    | { type: 'set_config'; key: string; value: any }
    | { type: 'connect_hardware'; port: string; baud_rate: number }
    | { type: 'send_hardware_command'; cmd: string };

type ListenerCallback = (data: any) => void;

export function useWebSocket() {
    // Low frequency state (UI Status)
    const [connected, setConnected] = useState(false);
    const [hardwareStatus, setHardwareStatus] = useState(false);
    const [cameras, setCameras] = useState<any[]>([]);
    const [resolutions, setResolutions] = useState<string[]>([]);
    const [resolutionsCameraId, setResolutionsCameraId] = useState<number>(-1);
    
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimeout = useRef<number | null>(null);
    
    // Subscription system for high-frequency data
    const listeners = useRef<Record<string, Set<ListenerCallback>>>({
        video_frame: new Set(),
        eye_data: new Set(),
        imu_data: new Set()
    });

    const addListener = useCallback((type: string, callback: ListenerCallback) => {
        if (!listeners.current[type]) listeners.current[type] = new Set();
        listeners.current[type].add(callback);
    }, []);

    const removeListener = useCallback((type: string, callback: ListenerCallback) => {
        if (listeners.current[type]) {
            listeners.current[type].delete(callback);
        }
    }, []);

    // Fase 5: Diagnóstico de frames recibidos
    const framesReceived = useRef(0);
    const lastDiagTime = useRef(Date.now());

    const connect = useCallback(async () => {
        try {
            const port = await invoke<number>('get_websocket_port');
            console.log(`Connecting to WebSocket on port ${port}...`);

            const socket = new WebSocket(`ws://127.0.0.1:${port}`);
            socket.binaryType = 'blob';

            socket.onopen = () => {
                console.log('WebSocket connected');
                setConnected(true);
                if (reconnectTimeout.current) {
                    clearTimeout(reconnectTimeout.current);
                    reconnectTimeout.current = null;
                }
            };

            socket.onmessage = (event) => {
                // Handle binary video frame
                if (event.data instanceof Blob) {
                    framesReceived.current++;

                    // Diagnóstico cada segundo
                    const now = Date.now();
                    if (now - lastDiagTime.current >= 1000) {
                        console.log(`[DIAG-FE] Frames recibidos: ${framesReceived.current}/s`);
                        framesReceived.current = 0;
                        lastDiagTime.current = now;
                    }

                    listeners.current.video_frame.forEach(cb => cb(event.data));
                    return;
                }

                try {
                    const msg: WsMessage = JSON.parse(event.data);
                    
                    switch (msg.type) {
                        case 'video_frame':
                            // Fallback for legacy base64 frames if any
                            listeners.current.video_frame.forEach(cb => cb(msg.data));
                            break;
                        case 'eye_data':
                            const eData: EyeData = {
                                left: msg.left,
                                right: msg.right,
                                timestamp: msg.timestamp,
                                is_calibrated: msg.is_calibrated
                            };
                            listeners.current.eye_data.forEach(cb => cb(eData));
                            break;
                        case 'imu_data':
                            const iData: ImuData = {
                                yaw: msg.yaw,
                                pitch: msg.pitch,
                                roll: msg.roll
                            };
                            listeners.current.imu_data.forEach(cb => cb(iData));
                            break;
                        case 'cameras_list':
                            setCameras(msg.cameras);
                            break;
                        case 'resolutions_list':
                            console.log('[WS] Received resolutions_list:', msg);
                            setResolutions(msg.resolutions);
                            setResolutionsCameraId(msg.camera_id);
                            break;
                        case 'error':
                            console.error(`Error from ${msg.source}: ${msg.message}`);
                            break;
                    }
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };
            
            socket.onclose = () => {
                console.warn('WebSocket disconnected');
                setConnected(false);
                reconnectTimeout.current = window.setTimeout(connect, 2000);
            };
            
            socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                socket.close();
            };
            
            ws.current = socket;
        } catch (e) {
            console.error('Failed to get WebSocket port or connect:', e);
            reconnectTimeout.current = window.setTimeout(connect, 2000);
        }
    }, []);

    useEffect(() => {
        connect();
        return () => {
            if (ws.current) ws.current.close();
            if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
        };
    }, [connect]);

    // Hardware/IMU status: listen for Tauri events from HardwareManager
    useEffect(() => {
        // Check initial state
        invoke<boolean>('is_hardware_connected').then(setHardwareStatus).catch(() => {});

        // Listen for status changes
        const unlisten = listen<{ connected: boolean }>('hardware-status', (event) => {
            setHardwareStatus(event.payload.connected);
        });

        return () => { unlisten.then(fn => fn()); };
    }, []);

    const send = useCallback((msg: any) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            console.log('[WS] Sending:', msg);
            ws.current.send(JSON.stringify(msg));
        } else {
            console.warn('Cannot send: WebSocket not connected');
        }
    }, []);

    return {
        connected,
        hardwareStatus,
        cameras,
        resolutions,
        resolutionsCameraId,
        send,
        addListener,
        removeListener
    };
}
