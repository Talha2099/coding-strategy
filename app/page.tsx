'use client';

import React from 'react';
import { Sidebar } from '@/components/dashboard/sidebar';
import { StatsBar } from '@/components/dashboard/stats-bar';
import { PerformanceChart } from '@/components/dashboard/performance-chart';
import { ZoneGrid } from '@/components/dashboard/zone-grid';
import { TradeTable } from '@/components/dashboard/trade-table';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Bell, 
  Search, 
  User, 
  Play, 
  RotateCcw, 
  BarChart2, 
  Cpu, 
  Zap, 
  Activity, 
  RefreshCw,
  Terminal,
  Layers,
  FlaskConical
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function DashboardPage() {
  const [isSimulating, setIsSimulating] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState('pipeline');
  const [logs, setLogs] = React.useState<string[]>([
    'System initialized',
    'MT5 Gateway established',
    'Deterministic SMC engine online',
    'Meta-model filter loaded: version 2.4.1'
  ]);

  const addLog = (msg: string) => {
    setLogs(prev => [...prev.slice(-9), `${new Date().toLocaleTimeString()} - ${msg}`]);
  };

  const runSimulation = () => {
    setIsSimulating(true);
    addLog('Starting Backtest Simulation...');
    
    setTimeout(() => {
      addLog('Extracting Microstructure Features...');
    }, 500);

    setTimeout(() => {
      addLog('Meta-Model Filtering: 3 Candidates rejected by Risk Engine');
    }, 1200);

    setTimeout(() => {
      setIsSimulating(false);
      addLog('Backtest completed. Sharif Ratio updated: 2.45');
    }, 2000);
  };

  return (
    <div id="dashboard-root" className="min-h-screen bg-[#0A0B0D] flex overflow-x-hidden text-gray-400 font-sans">
      <Sidebar />
      
      <main className="flex-1 min-w-0 flex flex-col h-screen overflow-y-auto bg-linear-to-b from-[#0A0B0D] to-[#121317]">
        {/* Header */}
        <header id="dashboard-header" className="h-16 border-b border-[#2A2B2F] bg-[#0A0B0D]/90 backdrop-blur-xl sticky top-0 z-50 px-8 flex items-center justify-between">
          <div className="flex items-center gap-6 flex-1">
            <h1 className="text-white font-sans font-bold tracking-tighter text-xl uppercase italic">QuantPortal</h1>
            <div className="flex gap-1">
              {['Market View', 'Pipeline', 'Research'].map(tab => (
                <button 
                  key={tab}
                  className={cn(
                    "px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all",
                    activeTab === tab.toLowerCase() ? "bg-[#00FF00] text-black" : "text-[#8E9299] hover:text-white"
                  )}
                  onClick={() => setActiveTab(tab.toLowerCase())}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="hidden xl:flex items-center gap-3 px-4 py-1.5 rounded-xl bg-[#151619] border border-[#2A2B2F]">
              <Activity size={14} className="text-[#00FF00] animate-pulse" />
              <div className="flex flex-col">
                <span className="text-[9px] uppercase font-mono tracking-tighter text-[#8E9299]">Live OFI</span>
                <span className="text-white text-[11px] font-mono">+0.42</span>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#151619] border border-[#2A2B2F]">
              <div className={cn("w-2 h-2 rounded-full animate-pulse", isSimulating ? "bg-orange-500" : "bg-[#00FF00]")} />
              <span className="text-[10px] font-mono uppercase font-bold text-white tracking-wider">
                {isSimulating ? "Backtesting..." : "Standby"}
              </span>
            </div>

            <button id="system-audit-btn" className="p-2 text-[#8E9299] hover:text-white transition-colors relative bg-[#151619] border border-[#2A2B2F] rounded-lg">
              <Bell size={16} />
              <span className="absolute top-0 right-0 w-2 h-2 bg-[#00FF00] border-2 border-[#0A0B0D] rounded-full" />
            </button>
          </div>
        </header>

        {/* Content */}
        <div id="dashboard-content" className="p-8 space-y-8 max-w-[1600px] mx-auto w-full">
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <StatsBar />
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Main Area */}
            <motion.div 
              className="lg:col-span-8 space-y-8"
              initial={{ opacity: 0, scale: 0.99 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              {/* Performance Section */}
              <section id="performance-section" className="bg-[#151619] rounded-2xl border border-[#2A2B2F] p-6 space-y-6">
                <div className="flex justify-between items-center bg-[#1A1B1F] p-4 rounded-xl border border-[#2A2B2F]/50">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-[#00FF00]/10 rounded-xl">
                      <BarChart2 size={24} className="text-[#00FF00]" />
                    </div>
                    <div>
                      <h2 className="text-white text-sm font-bold uppercase tracking-widest flex items-center gap-2">
                        Equity Distribution
                      </h2>
                      <p className="text-[#8E9299] text-[10px] font-mono mt-1 italic leading-none">Simulating 1,240 historical events • OFI Neutralization active</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button id="reset-backtest" className="p-3 rounded-xl bg-[#2A2B2F]/30 border border-[#2A2B2F] text-[#8E9299] hover:text-white transition-all">
                      <RotateCcw size={16} />
                    </button>
                    <button 
                      onClick={runSimulation}
                      disabled={isSimulating}
                      id="run-simulation" 
                      className={cn(
                        "px-6 py-2 rounded-xl text-[11px] items-center gap-3 flex transition-all font-bold uppercase tracking-widest",
                        isSimulating 
                          ? "bg-[#2A2B2F] text-[#8E9299] cursor-not-allowed" 
                          : "bg-white text-black hover:bg-[#00FF00] hover:text-black shadow-lg shadow-white/5"
                      )}
                    >
                      {isSimulating ? <RefreshCw className="animate-spin" size={14} /> : <Play size={14} fill="currentColor" />}
                      {isSimulating ? "Running..." : "Initiate Research"}
                    </button>
                  </div>
                </div>
                <div className={cn("transition-all duration-500", isSimulating ? "opacity-30 blur-sm brightness-50" : "opacity-100")}>
                  <PerformanceChart />
                </div>
              </section>

              {/* Trade Candidates */}
              <section id="trades-section">
                <TradeTable />
              </section>
            </motion.div>

            {/* Sidebar Data area */}
            <motion.div 
              className="lg:col-span-4 space-y-8"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              {/* Microstructure Console */}
              <section id="micro-console" className="bg-black rounded-2xl border border-[#2A2B2F] overflow-hidden flex flex-col h-[280px]">
                <div className="bg-[#151619] px-4 py-3 border-b border-[#2A2B2F] flex items-center justify-between">
                  <span className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
                    <Terminal size={14} className="text-[#00FF00]" />
                    Engine Log
                  </span>
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-500/50" />
                    <div className="w-1.5 h-1.5 rounded-full bg-orange-500/50" />
                    <div className="w-1.5 h-1.5 rounded-full bg-[#00FF00]/50" />
                  </div>
                </div>
                <div className="p-4 flex-1 font-mono text-[10px] space-y-1.5 overflow-y-auto">
                  {logs.map((log, i) => (
                    <div key={i} className={cn(
                      "flex gap-3",
                      i === logs.length - 1 ? "text-[#00FF00]" : "text-gray-500"
                    )}>
                      <span className="opacity-30 shrink-0">[{i}]</span>
                      <span className="break-all">{log}</span>
                    </div>
                  ))}
                  <div className="animate-pulse flex gap-3 text-[#00FF00]">
                    <span className="opacity-30">[_]</span>
                    <span>_</span>
                  </div>
                </div>
              </section>

              {/* Liquidity Zones */}
              <section id="zones-section" className="space-y-4">
                <div className="flex justify-between items-center group cursor-help">
                  <h2 className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
                    <Layers size={14} />
                    Discovery Engine
                  </h2>
                  <span className="text-[#00FF00] text-[9px] font-mono tracking-tighter bg-[#00FF00]/10 px-2 py-0.5 rounded-full border border-[#00FF00]/20 group-hover:bg-[#00FF00] group-hover:text-black transition-colors">
                    SMC-RULESET-V4
                  </span>
                </div>
                <ZoneGrid />
              </section>

              {/* Research Tracking */}
              <section id="system-info" className="p-6 bg-linear-to-br from-[#151619] to-[#0A0B0D] border border-[#2A2B2F] rounded-2xl space-y-6 relative overflow-hidden">
                <div className="absolute -bottom-4 -right-4 p-4 opacity-5 pointer-events-none">
                  <FlaskConical size={120} className="text-white" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-white text-xs font-bold uppercase tracking-widest">Research Context</h3>
                  <p className="text-[10px] text-[#8E9299]">Current Experiment: <span className="text-white">OFI_META_v2</span></p>
                </div>

                <div className="space-y-4 relative z-10">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-black/40 rounded-xl border border-[#2A2B2F]">
                      <span className="text-[9px] uppercase font-mono block text-[#8E9299] mb-1">Expected EV</span>
                      <span className="text-white text-sm font-mono">+14.2 bps</span>
                    </div>
                    <div className="p-3 bg-black/40 rounded-xl border border-[#2A2B2F]">
                      <span className="text-[9px] uppercase font-mono block text-[#8E9299] mb-1">Model Fit</span>
                      <span className="text-[#00FF00] text-sm font-mono">0.88</span>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-[#2A2B2F]">
                    <div className="flex justify-between text-[11px] items-center text-[#8E9299] font-mono">
                      <span>Execution Environment</span>
                      <span className="text-white">RL-OPTIMIZED</span>
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
