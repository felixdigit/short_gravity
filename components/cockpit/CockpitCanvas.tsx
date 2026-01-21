'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Globe, Satellite, Clock } from 'lucide-react';
import { mockSatellites } from '@/lib/mock-data';

export function CockpitCanvas() {
  return (
    <div className="grid grid-cols-1 gap-6">
      {/* Main visualization area */}
      <Card className="h-[500px]">
        <CardContent className="h-full flex flex-col items-center justify-center text-gray-500">
          <Globe className="w-24 h-24 mb-4 opacity-20" />
          <p className="text-lg font-medium">3D Orbital Visualization</p>
          <p className="text-sm mt-2">Three.js integration coming soon</p>
          <div className="mt-6 px-6 py-3 bg-gray-800 rounded-lg border border-gray-700">
            <p className="text-xs text-gray-400">
              Will display: Earth globe, satellite positions, orbital paths, coverage cones
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Info panels */}
      <div className="grid grid-cols-2 gap-6">
        {/* Tracked satellites */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-base">
              <Satellite className="w-5 h-5 mr-2" />
              Tracked Satellites
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockSatellites.map((sat) => (
                <div key={sat.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                  <div>
                    <div className="text-sm font-medium text-gray-100">{sat.name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      NORAD: {sat.norad_id} • {sat.orbit_type}
                    </div>
                  </div>
                  <div className="text-xs text-green-400">
                    {sat.operational_status}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Time controls */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-base">
              <Clock className="w-5 h-5 mr-2" />
              Time Controls
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wider">Mode</label>
                <div className="mt-2 flex space-x-2">
                  <button className="px-3 py-1.5 text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded">
                    Realtime
                  </button>
                  <button className="px-3 py-1.5 text-xs font-medium text-gray-400 hover:bg-gray-800 rounded">
                    Historical
                  </button>
                  <button className="px-3 py-1.5 text-xs font-medium text-gray-400 hover:bg-gray-800 rounded">
                    Future
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wider">Current Time</label>
                <div className="mt-2 text-sm text-gray-100 font-mono">
                  {new Date().toISOString().slice(0, 19).replace('T', ' ')} UTC
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wider">Playback Speed</label>
                <div className="mt-2 flex items-center space-x-2">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    defaultValue="50"
                    className="flex-1 h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="text-xs text-gray-400 w-8">1x</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
