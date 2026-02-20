export interface SatelliteInfo {
  id: string
  name: string
  fullName: string
  launch: string
  type: 'Block 2' | 'Block 1' | 'Test'
}

export const SATELLITES_ORDERED: SatelliteInfo[] = [
  { id: '67232', name: 'FM1', fullName: 'Bluebird 7 (Block 2 FM1)', launch: '2025-12-24', type: 'Block 2' },
  { id: '61046', name: 'BB5', fullName: 'Bluebird 5 (Block 1)',     launch: '2024-09-12', type: 'Block 1' },
  { id: '61049', name: 'BB4', fullName: 'Bluebird 4 (Block 1)',     launch: '2024-09-12', type: 'Block 1' },
  { id: '61045', name: 'BB3', fullName: 'Bluebird 3 (Block 1)',     launch: '2024-09-12', type: 'Block 1' },
  { id: '61048', name: 'BB2', fullName: 'Bluebird 2 (Block 1)',     launch: '2024-09-12', type: 'Block 1' },
  { id: '61047', name: 'BB1', fullName: 'Bluebird 1 (Block 1)',     launch: '2024-09-12', type: 'Block 1' },
  { id: '53807', name: 'BW3', fullName: 'BlueWalker 3 (Test)',      launch: '2022-09-10', type: 'Test'    },
]

export const NORAD_IDS = SATELLITES_ORDERED.map((s) => s.id)
export const SATELLITE_NAMES: Record<string, string> = Object.fromEntries(
  SATELLITES_ORDERED.map((s) => [s.id, s.name])
)
export const FM1_NORAD_ID = '67232'

export function getSatelliteInfo(noradId: string): SatelliteInfo | undefined {
  return SATELLITES_ORDERED.find((s) => s.id === noradId)
}
