'use client'

import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import type { Mesh } from 'three'

export interface GlobeSignal {
  id: string
  lat: number
  lng: number
  severity: string
}

interface GlobeProps {
  signals?: GlobeSignal[]
  className?: string
}

function RotatingEarth() {
  const meshRef = useRef<Mesh>(null)

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.15
    }
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1.8, 48, 48]} />
      <meshBasicMaterial color="#3b82f6" wireframe />
    </mesh>
  )
}

export function Globe({ signals, className }: GlobeProps) {
  return (
    <div className={`relative w-full h-full ${className ?? ''}`}>
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <RotatingEarth />
      </Canvas>
      <div className="absolute top-3 right-3 font-mono text-xs tracking-widest text-blue-400/70">
        {signals?.length ?? 0} ACTIVE TRACKS
      </div>
    </div>
  )
}
