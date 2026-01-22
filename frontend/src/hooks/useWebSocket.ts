import { useState, useEffect, useCallback, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';

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
    | { type: 'status'; python_connected: boolean; hardware_connected: boolean }
    | { type: 'error'; source: string; message: string }
    | { type: 'cameras_list'; cameras: any[] }
    | { type: 'list_cameras' }
    | { type: 'start_capture'; camera_id: number; width: number; height: number }
    | { type: 'stop_capture' }
    | { type: 'set_config'; key: string; value: any }
    | { type: 'connect_hardware'; port: string; baud_rate: number }
    | { type: 'send_hardware_command'; cmd: string };

export function useWebSocket() {
    const [connected, setConnected] = useState(false);
    const [pythonStatus, setPythonStatus] = useState(false);
    const [hardwareStatus, setHardwareStatus] = useState(false);
    const [cameras, setCameras] = useState<any[]>([]);
    const [eyeData, setEyeData] = useState<EyeData | null>(null);
    const [imuData, setImuData] = useState<ImuData | null>(null);
    const [videoFrame, setVideoFrame] = useState<string | null>(null);
    
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimeout = useRef<number | null>(null);

    const connect = useCallback(async () => {
        try {
            const port = await invoke<number>('get_websocket_port');
            console.log(`Connecting to WebSocket on port ${port}...`);
            
            const socket = new WebSocket(`ws://127.0.0.1:${port}`);
            
            socket.onopen = () => {
                console.log('WebSocket connected');
                setConnected(true);
                if (reconnectTimeout.current) {
                    clearTimeout(reconnectTimeout.current);
                    reconnectTimeout.current = null;
                }
            };
            
            socket.onmessage = (event) => {
                try {
                    const msg: WsMessage = JSON.parse(event.data);
                    
                    switch (msg.type) {
                        case 'eye_data':
                            setEyeData({
                                left: msg.left,
                                right: msg.right,
                                timestamp: msg.timestamp,
                                is_calibrated: msg.is_calibrated
                            });
                            break;
                        case 'video_frame':
                            setVideoFrame(msg.data);
                            break;
                        case 'imu_data':
                            setImuData({
                                yaw: msg.yaw,
                                pitch: msg.pitch,
                                roll: msg.roll
                            });
                            break;
                        case 'status':
                            setPythonStatus(msg.python_connected);
                            setHardwareStatus(msg.hardware_connected);
                            break;
                        case 'cameras_list':
                            setCameras(msg.cameras);
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
                // Attempt to reconnect after 2 seconds
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
            if (ws.current) {
                ws.current.close();
            }
            if (reconnectTimeout.current) {
                clearTimeout(reconnectTimeout.current);
            }
        };
    }, [connect]);

    const send = useCallback((msg: any) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(msg));
        } else {
            console.warn('Cannot send: WebSocket not connected');
        }
    }, []);

    return {
        connected,
        pythonStatus,
        hardwareStatus,
        cameras,
        eyeData,
        imuData,
        videoFrame,
        send
    };
}
