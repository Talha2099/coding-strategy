'use client';

import React from 'react';
import { TrendingUp, Activity, Binary, ShieldCheck, Zap, Cpu } from 'lucide-react';

const stats = [
  { label: 'GARCH(1,1) Vol', value: '0.0012', trend: 'Forecasted', icon: Activity, color: 'text-blue-400' },
  { label: 'HMM Confidence', value: '88.4%', trend: 'State: RANGE', icon: Cpu, color: 'text-[#00FF00]' },
  { label: 'Kelly Fraction', value: '0.12x', trend: 'Risk Capped', icon: ShieldCheck, color: 'text-orange-400' },
  { label: 'Exp. Return', value: '+14.2 bps', trend: 'MC Filtered', icon: Zap, color: 'text-[#00FF00]' },
];

export function StatsBar() {
  return (
    <div id="stats-bar-container" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, i) => (
        <div 
          key={i} 
          id={`stat-card-${i}`}
          className="bg-[#151619] border border-[#2A2B2F] rounded-xl p-4 flex flex-col justify-between"
        >
          <div className="flex justify-between items-start mb-2">
            <span className="text-[#8E9299] text-[10px] uppercase font-mono tracking-widest">{stat.label}</span>
            <stat.icon size={16} className={stat.color} />
          </div>
          <div className="flex items-end justify-between">
            <span className="text-white text-xl font-light font-sans tracking-tight">{stat.value}</span>
            <span className={`text-[10px] font-mono ${stat.color}`}>{stat.trend}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
