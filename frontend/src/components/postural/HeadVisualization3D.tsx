import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Grid, Text } from '@react-three/drei'
import * as THREE from 'three'
import { CalibratedImuData } from '../../hooks/useImuData'

interface HeadModelProps {
    imuData: CalibratedImuData | null
    targetOrientation?: { yaw?: number; pitch?: number; roll?: number }
    showTarget: boolean
}

function degToRad(deg: number) {
    return (deg * Math.PI) / 180
}

function HeadModel({ imuData, targetOrientation, showTarget }: HeadModelProps) {
    const meshRef = useRef<THREE.Mesh>(null)
    const noseRef = useRef<THREE.Mesh>(null)
    const targetRef = useRef<THREE.Mesh>(null)

    // Smooth interpolation
    const currentEuler = useRef(new THREE.Euler(0, 0, 0, 'YXZ'))

    useFrame(() => {
        if (!meshRef.current) return

        if (imuData) {
            const targetEuler = new THREE.Euler(
                degToRad(imuData.calibrated.pitch),
                degToRad(imuData.calibrated.yaw),
                degToRad(imuData.calibrated.roll),
                'YXZ'
            )

            // Smooth lerp
            currentEuler.current.x += (targetEuler.x - currentEuler.current.x) * 0.15
            currentEuler.current.y += (targetEuler.y - currentEuler.current.y) * 0.15
            currentEuler.current.z += (targetEuler.z - currentEuler.current.z) * 0.15

            meshRef.current.rotation.copy(currentEuler.current)
            if (noseRef.current) {
                noseRef.current.rotation.copy(currentEuler.current)
            }
        }

        // Target ghost
        if (targetRef.current && showTarget && targetOrientation) {
            targetRef.current.rotation.set(
                degToRad(targetOrientation.pitch ?? 0),
                degToRad(targetOrientation.yaw ?? 0),
                degToRad(targetOrientation.roll ?? 0),
                'YXZ'
            )
        }
    })

    const headGeometry = useMemo(() => {
        const geo = new THREE.SphereGeometry(1, 32, 24)
        geo.scale(1, 1.3, 1) // Ellipsoid
        return geo
    }, [])

    return (
        <group>
            {/* Head */}
            <mesh ref={meshRef} geometry={headGeometry}>
                <meshStandardMaterial color="#4a90d9" transparent opacity={0.85} roughness={0.3} />
                {/* Nose indicator (child follows parent rotation) */}
                <mesh position={[0, 0, 1.05]}>
                    <coneGeometry args={[0.15, 0.4, 8]} />
                    <meshStandardMaterial color="#60a5fa" />
                </mesh>
                {/* Right ear marker */}
                <mesh position={[1.02, 0.1, 0]}>
                    <sphereGeometry args={[0.12, 8, 8]} />
                    <meshStandardMaterial color="#ef4444" />
                </mesh>
                {/* Left ear marker */}
                <mesh position={[-1.02, 0.1, 0]}>
                    <sphereGeometry args={[0.12, 8, 8]} />
                    <meshStandardMaterial color="#3b82f6" />
                </mesh>
            </mesh>

            {/* Target ghost */}
            {showTarget && targetOrientation && (
                <mesh ref={targetRef} geometry={headGeometry}>
                    <meshStandardMaterial
                        color="#f59e0b"
                        transparent
                        opacity={0.15}
                        wireframe
                    />
                    <mesh position={[0, 0, 1.05]}>
                        <coneGeometry args={[0.15, 0.4, 8]} />
                        <meshStandardMaterial color="#f59e0b" transparent opacity={0.25} />
                    </mesh>
                </mesh>
            )}
        </group>
    )
}

function SceneContent({ imuData, targetOrientation, showTarget }: HeadModelProps) {
    return (
        <>
            <ambientLight intensity={0.4} />
            <directionalLight position={[5, 5, 5]} intensity={0.8} />
            <directionalLight position={[-3, 2, -2]} intensity={0.3} />

            <HeadModel
                imuData={imuData}
                targetOrientation={targetOrientation}
                showTarget={showTarget}
            />

            <Grid
                args={[10, 10]}
                position={[0, -2, 0]}
                cellSize={0.5}
                cellThickness={0.5}
                cellColor="#334155"
                sectionSize={2}
                sectionThickness={1}
                sectionColor="#475569"
                fadeDistance={8}
                infiniteGrid
            />

            {/* Axis labels */}
            <Text position={[0, 0, 2.5]} fontSize={0.2} color="#94a3b8" anchorX="center">
                Frente
            </Text>
            <Text position={[2.2, 0, 0]} fontSize={0.15} color="#ef4444" anchorX="center">
                D
            </Text>
            <Text position={[-2.2, 0, 0]} fontSize={0.15} color="#3b82f6" anchorX="center">
                I
            </Text>
        </>
    )
}

interface HeadVisualization3DProps {
    imuData: CalibratedImuData | null
    isCalibrated: boolean
    targetOrientation?: { yaw?: number; pitch?: number; roll?: number }
    showTarget?: boolean
    onCalibrate?: () => void
}

export default function HeadVisualization3D({
    imuData,
    isCalibrated,
    targetOrientation,
    showTarget = true,
    onCalibrate,
}: HeadVisualization3DProps) {
    return (
        <div className="relative w-full h-full bg-dark-950 rounded-lg overflow-hidden border border-dark-800">
            <Canvas
                camera={{ position: [0, 1.5, 4], fov: 50 }}
                frameloop="always"
                gl={{ antialias: true, alpha: false }}
                onCreated={({ gl }) => {
                    gl.setClearColor('#0a0a0f')
                }}
            >
                <SceneContent
                    imuData={imuData}
                    targetOrientation={targetOrientation}
                    showTarget={showTarget}
                />
            </Canvas>

            {/* IMU values overlay */}
            {imuData && (
                <div className="absolute bottom-2 left-2 bg-dark-900/80 backdrop-blur-sm rounded px-2 py-1 text-[10px] font-mono text-dark-300 space-y-0.5">
                    <div>Y: <span className="text-yellow-400">{imuData.calibrated.yaw.toFixed(1)}°</span></div>
                    <div>P: <span className="text-green-400">{imuData.calibrated.pitch.toFixed(1)}°</span></div>
                    <div>R: <span className="text-blue-400">{imuData.calibrated.roll.toFixed(1)}°</span></div>
                </div>
            )}

            {/* Calibration overlay */}
            {!isCalibrated && (
                <div className="absolute inset-0 bg-dark-950/70 flex items-center justify-center">
                    <div className="text-center">
                        <p className="text-dark-300 text-sm mb-3">IMU no calibrada</p>
                        {onCalibrate && (
                            <button
                                onClick={onCalibrate}
                                className="btn btn-primary text-xs px-4 py-1.5"
                            >
                                Calibrar posición neutral
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* No data overlay */}
            {!imuData && isCalibrated && (
                <div className="absolute inset-0 bg-dark-950/50 flex items-center justify-center">
                    <p className="text-dark-500 text-xs">Sin datos IMU</p>
                </div>
            )}
        </div>
    )
}
