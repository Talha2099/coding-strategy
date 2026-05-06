'use client';

import React from 'react';
import { MOCK_ZONES } from '@/lib/mock-data';
import { Shield, Target, Zap, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ZoneGrid() {
  return (
    <div id="zone-grid-container" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {MOCK_ZONES.map((zone) => (
        <div 
          key={zone.id} 
          id={`zone-card-${zone.id}`}
          className="bg-[#151619] border border-[#2A2B2F] rounded-xl p-4 transition-all hover:border-[#00FF00]/30 hover:bg-[#1A1B1F]"
        >
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center gap-2">
              <div className={cn(
                "p-1.5 rounded-lg",
                zone.direction === 1 ? "bg-[#00FF00]/10" : "bg-red-500/10"
              )}>
                <Target size={14} className={zone.direction === 1 ? "text-[#00FF00]" : "text-red-500"} />
              </div>
              <div>
                <span className="text-[#8E9299] text-[10px] font-mono block uppercase tracking-wider">{zone.timeframe} • {zone.type.replace('_', ' ')}</span>
                <span className={cn(
                  "text-xs font-medium",
                  zone.direction === 1 ? "text-[#00FF00]" : "text-red-500"
                )}>
                  {zone.direction === 1 ? "DEMAND ZONE" : "SUPPLY ZONE"}
                </span>
              </div>
            </div>
            <div className={cn(
              "px-2 py-0.5 rounded text-[9px] font-mono uppercase",
              zone.state === 'fresh' ? "bg-[#00FF00]/10 text-[#00FF00]" : "bg-orange-500/10 text-orange-500"
            )}>
              {zone.state}
            </div>
          </div>

          <div className="space-y-2 mb-4">
            <div className="flex justify-between text-[11px]">
              <span className="text-[#8E9299]">Range</span>
              <span className="text-white font-mono">{zone.lowerBound.toLocaleString()} - {zone.upperBound.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-[#8E9299]">Strength</span>
              <span className="text-white font-mono">{(zone.strength * 100).toFixed(0)}%</span>
            </div>
          </div>

          <div className="w-full bg-[#2A2B2F] h-1 rounded-full overflow-hidden">
            <div 
              className={cn(
                "h-full rounded-full transition-all duration-1000",
                zone.direction === 1 ? "bg-[#00FF00]" : "bg-red-500"
              )} 
              style={{ width: `${zone.strength * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
