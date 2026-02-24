"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import type { SatelliteData } from "@shortgravity/ui";
import { getCoverageRadiusKm, propagateOrbitPath } from "@shortgravity/core";
import { useTerminalData } from "@/lib/providers/TerminalDataProvider";
import { useTerminalStore } from "@/lib/stores/terminal-store";

const Globe3D = dynamic(
  () =>
    import("@shortgravity/ui/components/earth/Globe3D").then((mod) => ({
      default: mod.Globe3D,
    })),
  { ssr: false }
);

export function GlobeWidget({ className }: { className?: string }) {
  const { satellites } = useTerminalData();
  const store = useTerminalStore();

  const globeSatellites: SatelliteData[] = satellites.map((s) => ({
    noradId: s.noradId,
    name: s.name,
    latitude: s.latitude,
    longitude: s.longitude,
    altitude: s.altitude,
    inclination: s.inclination,
    raan: undefined,
    tle: s.tle,
  }));

  // ACL: pre-compute coverage radii (core → UI boundary)
  const coverageRadii = useMemo(() => {
    const radii: Record<string, number> = {};
    for (const s of satellites) {
      radii[s.noradId] = getCoverageRadiusKm(s.altitude);
    }
    return radii;
  }, [satellites]);

  // ACL: pre-compute orbit paths from TLE data (core → UI boundary)
  const orbitPaths = useMemo(() => {
    const paths: Record<string, { lat: number; lon: number; alt: number }[]> =
      {};
    for (const s of satellites) {
      if (s.tle) {
        paths[s.noradId] = propagateOrbitPath(s.tle.line1, s.tle.line2, 180);
      }
    }
    return paths;
  }, [satellites]);

  return (
    <Globe3D
      className={className}
      satellites={globeSatellites}
      selectedSatellite={store.selectedSatellite ?? undefined}
      onSelectSatellite={(noradId) =>
        noradId
          ? store.toggleSatelliteCard(noradId)
          : store.deselectSatellite()
      }
      showOrbits={store.showOrbits}
      showCoverage={store.showCoverage}
      useDotMarkers={store.useDotMarkers}
      coverageRadii={coverageRadii}
      orbitPaths={orbitPaths}
    />
  );
}
