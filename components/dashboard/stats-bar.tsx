'use client';

import React from 'react';
import { TrendingUp, Activity, Binary, ShieldCheck, Zap, Cpu } from 'lucide-react';

const stats = [
  { label: 'Active Strategies', value: '12 Unit', trend: 'Multi-Asset', icon: Binary, color: 'text-blue-400' },
  { label: 'Avg Win Rate', value: '64.2%', trend: 'Last 30D', icon: ShieldCheck, color: 'text-[#00FF00]' },
  { label: 'Profit Factor', value: '2.14x', trend: 'All Systems', icon: TrendingUp, color: 'text-[#00FF00]' },
  { label: 'Max Drawdown', value: '-4.8%', trend: 'Var Model', icon: Activity, color: 'text-red-400' },
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
