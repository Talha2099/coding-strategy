'use client';

import React from 'react';
import { motion } from 'motion/react';
import { Target, Zap, TrendingUp, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';

const BEST_PARAMS = [
  { name: 'Donchian Window', value: '24', confidence: '0.92', icon: Target },
  { name: 'ATR Multiplier', value: '2.5x', confidence: '0.88', icon: Shield },
  { name: 'Risk / Trade', value: '1.2%', confidence: '0.95', icon: Zap },
  { name: 'Entry Threshold', value: '0.0035', confidence: '0.84', icon: TrendingUp },
];

export function OptimizationResults() {
  return (
    <div className="bg-[#151619] rounded-2xl border border-[#2A2B2F] p-5 space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
          <TrendingUp size={14} className="text-[#00FF00]" />
          Optimal Parameter Set (Bayesian)
        </h3>
        <span className="text-[9px] font-mono text-[#8E9299]">v1.2 (TPE)</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {BEST_PARAMS.map((param) => {
          const Icon = param.icon;
          return (
            <motion.div 
              key={param.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-[#0A0B0D] border border-[#2A2B2F] p-3 rounded-xl hover:border-[#00FF00]/40 transition-colors"
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon size={12} className="text-[#8E9299]" />
                <span className="text-[8px] text-[#8E9299] uppercase font-bold">{param.name}</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-white text-lg font-mono font-bold">{param.value}</span>
                <span className="text-[#00FF00] text-[8px] font-mono">{(parseFloat(param.confidence) * 100).toFixed(0)}% Conf.</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="pt-4 border-t border-[#2A2B2F]">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[9px] text-[#8E9299] uppercase font-bold">Optimization Convergence</span>
          <span className="text-white font-mono text-[9px]">Trial 42/50</span>
        </div>
        <div className="h-1 w-full bg-black/40 rounded-full overflow-hidden border border-[#2A2B2F]">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: '84%' }}
            className="h-full bg-[#00FF00] rounded-full"
          />
        </div>
      </div>

      <button className="w-full py-2 bg-[#00FF00]/10 border border-[#00FF00]/20 rounded-lg text-[#00FF00] text-[9px] font-bold uppercase hover:bg-[#00FF00]/20 transition-all">
        Relaunch Global Optimization
      </button>
    </div>
  );
}
