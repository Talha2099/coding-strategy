'use client';

import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { MOCK_PERFORMANCE } from '@/lib/mock-data';

export function PerformanceChart() {
  return (
    <div id="performance-chart-container" className="h-[300px] w-full bg-[#151619] rounded-xl p-4 border border-[#2A2B2F] shadow-2xl relative overflow-hidden">
      <div className="absolute top-4 left-4 z-10">
        <h3 className="text-[#8E9299] text-[10px] uppercase tracking-[1px] font-mono">Performance Equity Curve</h3>
        <p className="text-white text-xl font-light font-sans tracking-tight">$12,450.00 <span className="text-[#00FF00] text-xs font-mono ml-2">+4.2%</span></p>
      </div>
      
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={MOCK_PERFORMANCE} margin={{ top: 60, right: 0, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00FF00" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#00FF00" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2A2B2F" />
          <XAxis 
            dataKey="time" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#8E9299', fontSize: 10, fontFamily: 'monospace' }}
            minTickGap={30}
          />
          <YAxis 
            hide 
            domain={['dataMin - 100', 'dataMax + 100']}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#151619', border: '1px solid #2A2B2F', borderRadius: '8px', fontSize: '12px', color: '#fff' }}
            itemStyle={{ color: '#00FF00' }}
          />
          <Area 
            type="monotone" 
            dataKey="equity" 
            stroke="#00FF00" 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#colorEquity)" 
            isAnimationActive={true}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
