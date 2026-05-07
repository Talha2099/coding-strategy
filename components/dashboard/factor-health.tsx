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
  const [factors, setFactors] = React.useState<Factor[]>([
    { name: 'OFI Imbalance', ic: 0.14, decay: 0.01, status: 'HEALTHY' },
    { name: 'HMM Regime Sync', ic: 0.22, decay: -0.02, status: 'HEALTHY' },
    { name: 'Vola Cluster', ic: 0.08, decay: 0.04, status: 'DEGRADING' },
    { name: 'Entropy Filter', ic: 0.11, decay: 0.00, status: 'STABLE' },
  ]);

  return (
    <div className="bg-[#151619] rounded-2xl border border-[#2A2B2F] p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
          <Fingerprint size={14} className="text-[#00FF00]" />
          Alpha Factor Vitality
        </h3>
        <ShieldCheck size={14} className="text-[#8E9299]" />
      </div>

      <div className="space-y-5">
        {factors.map((factor) => (
          <div key={factor.name} className="group">
            <div className="flex justify-between items-end mb-2">
              <div className="space-y-0.5">
                <span className="text-[10px] text-white font-bold uppercase tracking-tighter">{factor.name}</span>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "text-[9px] px-1.5 py-0.5 rounded-full border",
                    factor.status === 'HEALTHY' ? "bg-[#00FF00]/10 text-[#00FF00] border-[#00FF00]/20" :
                    factor.status === 'DEGRADING' ? "bg-orange-500/10 text-orange-500 border-orange-500/20" :
                    "bg-blue-500/10 text-blue-400 border-blue-500/20"
                  )}>
                    {factor.status}
                  </span>
                  {factor.decay > 0.02 && <AlertTriangle size={10} className="text-orange-500 animate-pulse" />}
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-white font-mono">IC: {factor.ic.toFixed(2)}</span>
                <p className={cn(
                  "text-[8px] font-mono",
                  factor.decay > 0 ? "text-orange-500" : "text-[#00FF00]"
                )}>
                  Drift: {factor.decay > 0 ? '+' : ''}{(factor.decay * 100).toFixed(1)}%
                </p>
              </div>
            </div>
            
            <div className="h-1 w-full bg-black/40 rounded-full overflow-hidden border border-[#2A2B2F]">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${factor.ic * 300}%` }}
                className={cn(
                  "h-full rounded-full transition-all duration-1000",
                  factor.status === 'HEALTHY' ? "bg-[#00FF00]" : 
                  factor.status === 'DEGRADING' ? "bg-orange-500" : 
                  "bg-blue-400"
                )}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="pt-4 border-t border-[#2A2B2F] flex items-center justify-between">
        <span className="text-[9px] text-[#8E9299] uppercase font-mono italic">Recalibrating in 120s...</span>
        <button className="text-[9px] font-bold text-white hover:text-[#00FF00] transition-colors uppercase">Details →</button>
      </div>
    </div>
  );
}
