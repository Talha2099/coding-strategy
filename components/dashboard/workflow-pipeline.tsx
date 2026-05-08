'use client';

import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, Circle, Loader2, Activity, ShieldCheck, Zap, Cpu, Search, Database, Fingerprint, Binary } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SimulationStep, WORKFLOW_STAGES } from '@/src/core/utils/simulation_logic';

interface Props {
  steps: SimulationStep[];
}

const STAGE_ICONS: Record<string, any> = {
  ingest: Database,
  technical: Activity,
  regime: Search,
  router: Fingerprint,
  backtest: Database,
  analytics: Cpu,
  optimization: Binary,
  risk: ShieldCheck,
  exec: Zap,
};

export function WorkflowPipeline({ steps }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-white text-xs font-bold uppercase tracking-widest flex items-center gap-2">
          <Zap size={14} className="text-[#00FF00]" />
          Execution Pipeline
        </h3>
        <span className="text-[9px] font-mono text-[#8E9299]">v4.0.2 Stable</span>
      </div>

      <div className="space-y-3 relative">
        <div className="absolute left-[17px] top-6 bottom-6 w-[1px] bg-[#2A2B2F]" />
        
        {WORKFLOW_STAGES.map((stage) => {
          const step = steps.find(s => s.id === stage.id);
          const status = step?.status || 'pending';
          const Icon = STAGE_ICONS[stage.id] || Circle;

          return (
            <motion.div 
              key={stage.id}
              initial={false}
              animate={{ opacity: status === 'pending' ? 0.3 : 1 }}
              className={cn(
                "relative flex items-start gap-4 p-3 rounded-xl border border-transparent transition-all",
                status === 'processing' && "bg-[#00FF00]/5 border-[#00FF00]/20 shadow-[0_0_20px_rgba(0,255,0,0.05)]",
                status === 'completed' && "bg-[#2A2B2F]/20"
              )}
            >
              <div className="relative z-10 mt-1">
                {status === 'completed' ? (
                  <div className="bg-[#00FF00] text-black rounded-full p-1">
                    <CheckCircle2 size={12} />
                  </div>
                ) : status === 'processing' ? (
                  <div className="bg-[#00FF00] text-black rounded-full p-1 animate-spin">
                    <Loader2 size={12} />
                  </div>
                ) : (
                  <div className="bg-[#1A1B1F] border border-[#2A2B2F] text-[#8E9299] rounded-full p-1">
                    <Circle size={12} />
                  </div>
                )}
              </div>

              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className={cn(
                    "text-[10px] uppercase font-bold tracking-wider",
                    status === 'processing' ? "text-[#00FF00]" : "text-white"
                  )}>
                    {stage.name}
                  </span>
                  {status === 'completed' && (
                    <span className="text-[9px] font-mono text-[#00FF00]">OK</span>
                  )}
                </div>

                <AnimatePresence mode="wait">
                  {status === 'processing' ? (
                    <motion.p 
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="text-[9px] text-[#8E9299] italic"
                    >
                      Analyzing high-frequency streams...
                    </motion.p>
                  ) : status === 'completed' && step?.data ? (
                    <motion.div 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-wrap gap-2 mt-1"
                    >
                      {Object.entries(step.data).map(([key, val]) => (
                        <div key={key} className="px-2 py-0.5 rounded bg-black/40 border border-[#2A2B2F] text-[8px] font-mono whitespace-nowrap">
                          <span className="opacity-40 uppercase">{key}:</span> {val as string}
                        </div>
                      ))}
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              </div>

              <div className={cn(
                "p-2 rounded-lg bg-[#1A1B1F] border border-[#2A2B2F]",
                status === 'processing' && "border-[#00FF00]/40 text-[#00FF00]"
              )}>
                <Icon size={14} />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
