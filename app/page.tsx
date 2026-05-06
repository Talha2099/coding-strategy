'use client';

import React from 'react';
import { Sidebar } from '@/components/dashboard/sidebar';
import { StatsBar } from '@/components/dashboard/stats-bar';
import { PerformanceChart } from '@/components/dashboard/performance-chart';
import { ZoneGrid } from '@/components/dashboard/zone-grid';
import { TradeTable } from '@/components/dashboard/trade-table';
import { motion, AnimatePresence } from 'motion/react';
import { Bell, Search, User, Play, RotateCcw, BarChart2, Cpu, Zap, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function DashboardPage() {
  const [isSimulating, setIsSimulating] = React.useState(false);

  const runSimulation = () => {
    setIsSimulating(true);
    setTimeout(() => setIsSimulating(false), 2000);
  };

  return (
    <div id="dashboard-root" className="min-h-screen bg-[#0A0B0D] flex overflow-x-hidden">
      <Sidebar />
      
      <main className="flex-1 min-w-0 flex flex-col h-screen overflow-y-auto font-sans">
        {/* Header */}
        <header id="dashboard-header" className="h-16 border-b border-[#2A2B2F] bg-[#0A0B0D]/80 backdrop-blur-md sticky top-0 z-50 px-8 flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            <h1 className="text-white font-sans font-medium tracking-tight text-lg">Strategy Dashboard</h1>
            <div className="relative max-w-md w-full hidden md:block uppercase tracking-widest text-[9px] font-mono text-[#8E9299]">
              Live Engine Control Panel v5.2
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#151619] border border-[#2A2B2F]">
              <div className={cn("w-1.5 h-1.5 rounded-full animate-pulse", isSimulating ? "bg-orange-500" : "bg-[#00FF00]")} />
              <span className="text-[10px] font-mono uppercase">{isSimulating ? "Processing..." : "System Idle"}</span>
            </div>
            <button id="system-audit-btn" className="p-2 text-[#8E9299] hover:text-white transition-colors relative">
              <Bell size={18} />
              <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-blue-500 rounded-full" />
            </button>
            <div className="h-8 w-[1px] bg-[#2A2B2F]" />
            <div className="flex items-center gap-3 pl-2">
              <div className="text-right hidden sm:block">
                <p className="text-white text-xs font-medium font-sans tracking-tight">Aqeela Shahid</p>
                <p className="text-[#8E9299] text-[10px] font-mono opacity-60">Senior Quant Analyst</p>
              </div>
              <div className="w-8 h-8 rounded-full bg-linear-to-br from-[#1A1B1F] to-[#2A2B2F] border border-[#2A2B2F] overflow-hidden flex items-center justify-center">
                <User size={16} className="text-[#8E9299]" />
              </div>
            </div>
          </div>
        </header>

        {/* Content */}
        <div id="dashboard-content" className="p-8 space-y-8 max-w-7xl mx-auto w-full">
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <StatsBar />
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <motion.div 
              className="lg:col-span-2 space-y-8"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <section id="performance-section" className="space-y-4">
                <div className="flex justify-between items-end">
                  <div>
                    <h2 className="text-white text-xs font-bold uppercase tracking-widest font-sans flex items-center gap-2">
                      <BarChart2 size={14} className="text-[#00FF00]" />
                      Equity Performance
                    </h2>
                    <p className="text-[#8E9299] text-[10px] font-mono mt-1">Simulated backtest results • 50 interval window</p>
                  </div>
                  <div className="flex gap-2">
                    <button id="reset-backtest" className="px-4 py-2 rounded-lg bg-[#151619] border border-[#2A2B2F] text-[#8E9299] hover:text-white text-[10px] items-center gap-2 flex transition-all uppercase tracking-widest font-mono">
                      <RotateCcw size={12} />
                    </button>
                    <button 
                      onClick={runSimulation}
                      disabled={isSimulating}
                      id="run-simulation" 
                      className={cn(
                        "px-6 py-2 rounded-lg text-[10px] items-center gap-2 flex transition-all font-bold uppercase tracking-widest",
                        isSimulating 
                          ? "bg-[#2A2B2F] text-[#8E9299] cursor-not-allowed" 
                          : "bg-[#00FF00] text-black hover:bg-[#00CC00] hover:shadow-[0_0_15px_rgba(0,255,0,0.3)]"
                      )}
                    >
                      {isSimulating ? "Simulating..." : <><Play size={10} fill="black" /> Run Backtest</>}
                    </button>
                  </div>
                </div>
                <div className={cn("transition-opacity duration-300", isSimulating ? "opacity-40" : "opacity-100")}>
                  <PerformanceChart />
                </div>
              </section>

              <section id="trades-section" className="space-y-4">
                <TradeTable />
              </section>
            </motion.div>

            <motion.div 
              className="space-y-8"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <section id="zones-section" className="space-y-5">
                <div className="flex justify-between items-end pb-2 border-b border-[#2A2B2F]">
                  <h2 className="text-white text-xs font-bold uppercase tracking-widest font-sans">Active S/D Zones</h2>
                  <span className="text-[#00FF00] text-[9px] font-mono tracking-tighter bg-[#00FF00]/5 px-2 py-0.5 rounded border border-[#00FF00]/10">SCANNING LIVE</span>
                </div>
                <div className="flex flex-col gap-4">
                  <ZoneGrid />
                </div>
              </section>

              <section id="system-info" className="p-6 bg-[#151619] border border-[#2A2B2F] rounded-xl space-y-5 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                  <Cpu size={48} className="text-white" />
                </div>
                <h3 className="text-white text-xs font-bold uppercase tracking-widest font-sans">Quant Engine Specs</h3>
                <div className="space-y-4">
                  <div className="flex justify-between text-[11px] items-center">
                    <span className="text-[#8E9299] flex items-center gap-2"><Zap size={12} /> MT5 Connector</span>
                    <span className="text-[#00FF00] font-mono bg-[#00FF00]/5 px-1.5 py-0.5 rounded">ACTIVE</span>
                  </div>
                  <div className="flex justify-between text-[11px] items-center">
                    <span className="text-[#8E9299] flex items-center gap-2"><Cpu size={12} /> LLM Analyzer</span>
                    <span className="text-blue-400 font-mono bg-blue-400/5 px-1.5 py-0.5 rounded">GEMINI-3 PRO</span>
                  </div>
                  <div className="flex justify-between text-[11px] items-center">
                    <span className="text-[#8E9299] flex items-center gap-2"><Activity size={12} /> RL Env</span>
                    <span className="text-white font-mono bg-white/5 px-1.5 py-0.5 rounded">SB3</span>
                  </div>
                  <div className="pt-2 border-t border-[#2A2B2F]">
                    <div className="flex justify-between text-[10px] mt-1">
                      <span className="text-[#8E9299] uppercase tracking-tighter">Last Heatmap Update</span>
                      <span className="text-[#8E9299] font-mono">14s ago</span>
                    </div>
                  </div>
                </div>
              </section>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}
