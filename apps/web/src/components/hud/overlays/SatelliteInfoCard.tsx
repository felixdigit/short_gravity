'use client'

import Link from 'next/link'
import { cn } from '@/lib/utils'
import type { SatelliteInfo } from '@/lib/data/satellites'

interface SatelliteInfoCardProps {
  noradId: string
  name: string
  type: string
  latitude: number
  longitude: number
  altitude: number
  velocity: number
  inclination: number
  bstar: number
  satelliteInfo?: SatelliteInfo
  onClose: () => void
}

export function SatelliteInfoCard({
  noradId,
  name,
  latitude,
  longitude,
  altitude,
  velocity,
  inclination,
  bstar,
  satelliteInfo,
  onClose,
}: SatelliteInfoCardProps) {
  const stats = [
    { label: 'LAT', value: `${latitude.toFixed(2)}\u00b0` },
    { label: 'LON', value: `${longitude.toFixed(2)}\u00b0` },
    { label: 'ALT', value: `${altitude.toFixed(1)} km` },
    { label: 'VEL', value: `${velocity.toFixed(2)} km/s` },
    { label: 'INC', value: `${inclination.toFixed(1)}\u00b0` },
    { label: 'B*', value: bstar.toExponential(2) },
  ]

  return (
    <div
      className="absolute top-24 left-[17.5rem] z-30 w-64 bg-[var(--nebula-depth)] border border-white/10 rounded-lg p-4 font-mono animate-fadeIn"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-[14px] text-white font-light">{name}</div>
          {satelliteInfo && (
            <div className="text-[11px] text-white/50">{satelliteInfo.fullName}</div>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-white/40 hover:text-white/70 text-[11px] transition-colors"
        >
          \u2715
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {stats.map((stat) => (
          <div key={stat.label}>
            <div className="text-[11px] text-white/50">{stat.label}</div>
            <div className="text-[12px] text-white/80 tabular-nums">{stat.value}</div>
          </div>
        ))}
      </div>

      {satelliteInfo?.launch && (
        <div className="mt-3 pt-3 border-t border-white/[0.06]">
          <div className="text-[11px] text-white/50">LAUNCHED</div>
          <div className="text-[12px] text-white/70">{satelliteInfo.launch}</div>
        </div>
      )}

      <Link
        href={`/satellite/${noradId}`}
        className="block mt-3 text-[11px] text-[var(--asts-orange)] hover:text-[var(--asts-orange-muted)] tracking-wider transition-colors"
      >
        VIEW DETAILS &rarr;
      </Link>
    </div>
  )
}
