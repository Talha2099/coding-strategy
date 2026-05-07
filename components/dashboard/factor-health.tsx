'use client';

import React from 'react';
import { motion } from 'motion/react';
import { Fingerprint, TrendingUp, TrendingDown, Activity, AlertTriangle, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Factor {
  name: string;
  ic: number;
  decay: number;
  status: 'HEALTHY' | 'DEGRADING' | 'STABLE';
}

export function FactorHealth() {
  const [strategies, setStrategies] = React.useState([
    { name: 'Breakout Engine', winRate: 68.2, sharpe: 2.4, status: 'HEALTHY' },
    { name: 'Mean Reversion', winRate: 54.1, sharpe: 1.8, status: 'STABLE' },
    { name: 'Pullback Unit', winRate: 72.5, sharpe: 3.1, status: 'HEALTHY' },
    { name: 'Gap Analytics', winRate: 48.9, sharpe: 0.9, status: 'DEGRADING' },
  ]);

  return (
    <div className="bg-[#151619] rounded-2xl border border-[#2A2B2F] p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
          <Fingerprint size={14} className="text-[#00FF00]" />
          Strategy Family Health
        </h3>
        <ShieldCheck size={14} className="text-[#8E9299]" />
      </div>

      <div className="space-y-5">
        {strategies.map((strat) => (
          <div key={strat.name} className="group">
            <div className="flex justify-between items-end mb-2">
              <div className="space-y-0.5">
                <span className="text-[10px] text-white font-bold uppercase tracking-tighter">{strat.name}</span>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "text-[9px] px-1.5 py-0.5 rounded-full border",
                    strat.status === 'HEALTHY' ? "bg-[#00FF00]/10 text-[#00FF00] border-[#00FF00]/20" :
                    strat.status === 'DEGRADING' ? "bg-red-500/10 text-red-500 border-red-500/20" :
                    "bg-blue-500/10 text-blue-400 border-blue-500/20"
                  )}>
                    {strat.status}
                  </span>
                  {strat.status === 'DEGRADING' && <AlertTriangle size={10} className="text-red-500 animate-pulse" />}
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-white font-mono">WR: {strat.winRate}%</span>
                <p className={cn(
                  "text-[8px] font-mono",
                  strat.sharpe > 2.0 ? "text-[#00FF00]" : "text-gray-500"
                )}>
                  Sharpe: {strat.sharpe.toFixed(1)}
                </p>
              </div>
            </div>
            
            <div className="h-1 w-full bg-black/40 rounded-full overflow-hidden border border-[#2A2B2F]">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${strat.winRate}%` }}
                className={cn(
                  "h-full rounded-full transition-all duration-1000",
                  strat.status === 'HEALTHY' ? "bg-[#00FF00]" : 
                  strat.status === 'DEGRADING' ? "bg-red-500" : 
                  "bg-blue-400"
                )}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="pt-4 border-t border-[#2A2B2F] flex items-center justify-between">
        <span className="text-[9px] text-[#8E9299] uppercase font-mono italic">Awaiting Next Session Open...</span>
        <button className="text-[9px] font-bold text-white hover:text-[#00FF00] transition-colors uppercase">All Stats →</button>
      </div>
    </div>
  );
}
