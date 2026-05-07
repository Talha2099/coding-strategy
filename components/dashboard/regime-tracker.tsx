'use client';

import React from 'react';
import { motion } from 'motion/react';
import { TrendingUp, TrendingDown, RefreshCw, BarChart2, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

export function RegimeTracker() {
  const [data, setData] = React.useState({
    regime: 'MEAN_REVERSION',
    vol: 0.0012,
    prob: [0.1, 0.1, 0.7, 0.1], // TrendUp, TrendDown, Range, Toxic
    timestamp: new Date()
  });

  React.useEffect(() => {
    const interval = setInterval(() => {
      setData(prev => ({
        ...prev,
        vol: prev.vol + (Math.random() - 0.5) * 0.0001,
        prob: prev.prob.map(p => Math.max(0.05, Math.min(0.8, p + (Math.random() - 0.5) * 0.05))),
        timestamp: new Date()
      }));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const regimes = ['TREND_UP', 'TREND_DN', 'RANGE', 'TOXIC'];

  return (
    <div className="bg-[#151619] rounded-2xl border border-[#2A2B2F] p-5 space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
          <BarChart2 size={14} className="text-[#00FF00]" />
          Regime Audit
        </h3>
        <span className="text-[9px] font-mono text-[#8E9299]">{data.timestamp.toLocaleTimeString()}</span>
      </div>

      <div className="space-y-4">
        {regimes.map((name, i) => (
          <div key={name} className="space-y-1.5">
            <div className="flex justify-between text-[9px] font-mono uppercase">
              <span className={cn(data.prob[i] > 0.5 ? "text-[#00FF00]" : "text-[#8E9299]")}>
                {name}
              </span>
              <span className="text-white">{(data.prob[i] * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1 bg-black/40 rounded-full overflow-hidden border border-[#2A2B2F]">
              <motion.div 
                initial={false}
                animate={{ width: `${data.prob[i] * 100}%` }}
                className={cn(
                  "h-full transition-colors",
                  data.prob[i] > 0.5 ? "bg-[#00FF00]" : "bg-[#8E9299]/30"
                )}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="pt-4 border-t border-[#2A2B2F] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={12} className="text-[#00FF00]" />
          <span className="text-[10px] text-[#8E9299] uppercase font-bold">Inst. Vol</span>
        </div>
        <span className="text-white font-mono text-xs">{(data.vol * 10000).toFixed(2)} bps</span>
      </div>
    </div>
  );
}
