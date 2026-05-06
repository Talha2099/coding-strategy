'use client';

import React from 'react';
import { TrendingUp, Activity, BarChart3, AlertCircle } from 'lucide-react';

const stats = [
  { label: 'Total Net Profit', value: '$12,450.00', trend: '+12.5%', icon: TrendingUp, color: 'text-[#00FF00]' },
  { label: 'Sharpe Ratio', value: '2.45', trend: 'Robust', icon: BarChart3, color: 'text-blue-400' },
  { label: 'Win Rate', value: '64.2%', trend: '+2.1%', icon: Activity, color: 'text-[#00FF00]' },
  { label: 'Max Drawdown', value: '4.8%', trend: 'Low Risk', icon: AlertCircle, color: 'text-orange-400' },
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
