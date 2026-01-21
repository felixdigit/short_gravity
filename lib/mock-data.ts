import { Signal, Briefing, Entity, Satellite } from '@/types';

// Mock Entities
export const mockEntities: Entity[] = [
  {
    id: '1',
    type: 'satellite',
    name: 'Starlink-4621',
    slug: 'starlink-4621',
    description: 'SpaceX Starlink constellation satellite',
    norad_id: '54321',
    status: 'active',
  },
  {
    id: '2',
    type: 'company',
    name: 'SpaceX',
    slug: 'spacex',
    description: 'Space Exploration Technologies Corp.',
    ticker: 'PRIVATE',
    status: 'active',
  },
  {
    id: '3',
    type: 'satellite',
    name: 'OneWeb-0421',
    slug: 'oneweb-0421',
    description: 'OneWeb constellation satellite',
    norad_id: '54322',
    status: 'active',
  },
];

// Mock Satellites
export const mockSatellites: Satellite[] = [
  {
    id: '1',
    type: 'satellite',
    name: 'Starlink-4621',
    slug: 'starlink-4621',
    description: 'SpaceX Starlink constellation satellite',
    norad_id: '54321',
    status: 'active',
    orbit_type: 'LEO',
    inclination_deg: 53.2,
    apogee_km: 550,
    perigee_km: 540,
    period_min: 95.5,
    operational_status: 'operational',
  },
  {
    id: '3',
    type: 'satellite',
    name: 'OneWeb-0421',
    slug: 'oneweb-0421',
    description: 'OneWeb constellation satellite',
    norad_id: '54322',
    status: 'active',
    orbit_type: 'LEO',
    inclination_deg: 87.4,
    apogee_km: 1200,
    perigee_km: 1190,
    period_min: 109.2,
    operational_status: 'operational',
  },
];

// Mock Signals
export const mockSignals: Signal[] = [
  {
    id: '1',
    anomaly_type: 'Orbital Deviation',
    severity: 'high',
    entity_id: '1',
    entity_type: 'satellite',
    entity_name: 'Starlink-4621',
    metric_type: 'altitude_change',
    observed_value: 15.2,
    baseline_value: 0.3,
    z_score: 4.8,
    detected_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
    processed: false,
  },
  {
    id: '2',
    anomaly_type: 'Regulatory Filing',
    severity: 'medium',
    entity_id: '2',
    entity_type: 'company',
    entity_name: 'SpaceX',
    metric_type: 'sec_8k_filing',
    detected_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2h ago
    processed: true,
  },
  {
    id: '3',
    anomaly_type: 'Coverage Gap',
    severity: 'critical',
    entity_id: '3',
    entity_type: 'satellite',
    entity_name: 'OneWeb-0421',
    metric_type: 'signal_loss',
    observed_value: 0,
    baseline_value: 98.5,
    z_score: -12.3,
    detected_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(), // 15 min ago
    processed: false,
  },
  {
    id: '4',
    anomaly_type: 'Maneuver Detected',
    severity: 'low',
    entity_id: '1',
    entity_type: 'satellite',
    entity_name: 'Starlink-4621',
    metric_type: 'delta_v',
    observed_value: 2.1,
    baseline_value: 0.1,
    z_score: 3.2,
    detected_at: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(), // 5h ago
    processed: true,
  },
];

// Mock Briefings
export const mockBriefings: Briefing[] = [
  {
    id: '1',
    type: 'flash',
    title: 'Starlink-4621 Orbital Anomaly',
    content: `## Summary
Starlink-4621 (NORAD: 54321) has exhibited a significant altitude deviation (+15.2km) from baseline behavior, representing a 4.8σ anomaly.

## Key Findings
- **Altitude increase:** 15.2km above baseline (expected: ±0.3km)
- **Detection time:** ${new Date(Date.now() - 1000 * 60 * 30).toLocaleTimeString()}
- **Likely cause:** Orbital station-keeping maneuver

## Implications
- **Operational:** Normal constellation maintenance
- **Strategic:** Part of SpaceX's automated collision avoidance system
- **Investment:** No material impact expected`,
    signal_id: '1',
    created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    read: false,
  },
  {
    id: '2',
    type: 'summary',
    title: 'Daily Intelligence Brief',
    content: `## Overview
4 new signals detected across 3 entities in the past 24 hours.

## Critical Alerts
- **OneWeb-0421:** Complete signal loss detected (12.3σ deviation)
  - Last contact: ${new Date(Date.now() - 1000 * 60 * 15).toLocaleTimeString()}
  - Recommendation: Monitor for debris or deorbit maneuver

## Moderate Alerts
- **SpaceX:** SEC 8-K filing detected
  - Content: Material agreement disclosure
  - Impact: Potential new launch contracts

## Low Priority
- **Starlink-4621:** Routine orbital adjustment
  - Status: Completed successfully
  - No further action required`,
    created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    read: true,
  },
];

// Helper function to simulate real-time data
export function getRecentSignals(limit: number = 10): Signal[] {
  return mockSignals.slice(0, limit);
}

export function getUnreadBriefings(): Briefing[] {
  return mockBriefings.filter(b => !b.read);
}
