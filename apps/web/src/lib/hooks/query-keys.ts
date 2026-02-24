/**
 * Centralized React Query keys for data consistency.
 *
 * Using shared query keys ensures that multiple hooks accessing the same
 * data share the same cache, preventing stale data and duplicate requests.
 */

/**
 * Query key for batch TLE satellite data.
 * Used by:
 * - useTLEFreshness (for TLE age display)
 * - useMultipleSatellitePositions (for satellite positions)
 */
export function getBatchTLEQueryKey(noradIds: string[]): string[] {
  return ['satellites', 'batch-tle', noradIds.sort().join(',')]
}
