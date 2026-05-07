'use client';

import React from 'react';
import { Sidebar } from '@/components/dashboard/sidebar';
import { StatsBar } from '@/components/dashboard/stats-bar';
import { PerformanceChart } from '@/components/dashboard/performance-chart';
import { ZoneGrid } from '@/components/dashboard/zone-grid';
import { TradeTable } from '@/components/dashboard/trade-table';
import { WorkflowPipeline } from '@/components/dashboard/workflow-pipeline';
import { RegimeTracker } from '@/components/dashboard/regime-tracker';
import { FactorHealth } from '@/components/dashboard/factor-health';
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
  FlaskConical,
  Binary,
  CheckCircle2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowSimulator, SimulationStep, WORKFLOW_STAGES } from '@/src/core/utils/simulation_logic';

export default function DashboardPage() {
  const [isSimulating, setIsSimulating] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState('pipeline');
  const [riskBias, setRiskBias] = React.useState(50);
  const [regimeSensitivity, setRegimeSensitivity] = React.useState(0.8);
  const [steps, setSteps] = React.useState<SimulationStep[]>([]);
  const [logs, setLogs] = React.useState<string[]>([
    'System initialized',
    'MT5 Gateway established',
    'Deterministic SMC engine online',
    'Meta-model filter loaded: version 2.4.1'
  ]);

  const simulator = React.useMemo(() => new WorkflowSimulator(), []);

  const addLog = (msg: string) => {
    setLogs(prev => [...prev.slice(-9), `${new Date().toLocaleTimeString()} - ${msg}`]);
  };

  const runSimulation = async () => {
    if (isSimulating) return;
    
    setIsSimulating(true);
    setSteps([]);
    addLog('Initiating full-stack execution workflow...');
    
    await simulator.runStepByStep(
      { risk: riskBias, regime: regimeSensitivity },
      (step) => {
        setSteps(prev => {
          const index = prev.findIndex(s => s.id === step.id);
          if (index !== -1) {
            const next = [...prev];
            next[index] = step;
            return next;
          }
          return [...prev, step];
        });
        if (step.status === 'completed') {
          addLog(`${step.name} finalized`);
        }
      }
    );

    setTimeout(() => {
      setIsSimulating(false);
      addLog('Workflow cycle complete. Neutral status achieved.');
    }, 1000);
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
              {/* Performance Section / Pipeline View */}
              <section id="pipeline-view" className="bg-[#151619] rounded-2xl border border-[#2A2B2F] overflow-hidden">
                <div className="flex justify-between items-center bg-[#1A1B1F] p-4 border-b border-[#2A2B2F]/50">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                      <Binary size={24} className="text-white" />
                    </div>
                    <div>
                      <h2 className="text-white text-sm font-bold uppercase tracking-widest flex items-center gap-2">
                        Execution Pipeline
                      </h2>
                      <p className="text-[#8E9299] text-[10px] font-mono mt-1 italic leading-none">Automated Step-by-Step System Diagnostics</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => setSteps([])}
                      className="p-3 rounded-xl bg-[#2A2B2F]/30 border border-[#2A2B2F] text-[#8E9299] hover:text-white transition-all"
                    >
                      <RotateCcw size={16} />
                    </button>
                    <button 
                      onClick={runSimulation}
                      disabled={isSimulating}
                      id="run-simulation" 
                      className={cn(
                        "px-6 py-2 rounded-xl text-[11px] items-center gap-3 flex transition-all font-bold uppercase tracking-widest",
                        isSimulating 
                          ? "bg-[#2A2B2F] text-[#8E9299] cursor-not-allowed border border-white/5" 
                          : "bg-[#00FF00] text-black hover:bg-white hover:text-black shadow-lg shadow-[#00FF00]/5"
                      )}
                    >
                      {isSimulating ? <RefreshCw className="animate-spin" size={14} /> : <Play size={14} fill="currentColor" />}
                      {isSimulating ? "Processing..." : "Observe Workflow"}
                    </button>
                  </div>
                </div>
                
                <div className="p-8 grid grid-cols-1 md:grid-cols-12 gap-12 min-h-[500px]">
                  <div className="md:col-span-5 border-r border-[#2A2B2F]/50 pr-8">
                    <WorkflowPipeline steps={steps} />
                  </div>
                  
                  <div className="md:col-span-7 flex flex-col">
                    <div className="flex-1 rounded-2xl bg-black/40 border border-[#2A2B2F] p-8 relative flex flex-col items-center justify-center text-center overflow-hidden">
                      <div className="absolute inset-0 opacity-10 flex items-center justify-center">
                         <Cpu size={300} strokeWidth={0.5} />
                      </div>
                      
                      <AnimatePresence mode="wait">
                        {isSimulating ? (
                          <motion.div 
                            key="simulating"
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 1.1 }}
                            className="space-y-6 relative z-10"
                          >
                            <div className="w-24 h-24 rounded-full border-4 border-[#00FF00]/20 border-t-[#00FF00] animate-spin mx-auto" />
                            <div className="space-y-2">
                              <h3 className="text-[#00FF00] font-mono text-xl animate-pulse">SYSTEM_IN_LOOP</h3>
                              <p className="text-gray-500 text-xs italic">Executing mathematical abstractions onto live time-series...</p>
                            </div>
                          </motion.div>
                        ) : steps.length === WORKFLOW_STAGES.length ? (
                          <motion.div 
                            key="complete"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="space-y-4 relative z-10"
                          >
                            <div className="p-4 bg-[#00FF00]/10 rounded-full inline-block mb-4">
                              <CheckCircle2 size={48} className="text-[#00FF00]" />
                            </div>
                            <h3 className="text-white font-bold text-2xl tracking-tighter uppercase italic">Optimized Verdict</h3>
                            <div className="grid grid-cols-2 gap-4 max-w-sm mx-auto mt-6">
                              <div className="bg-[#151619] p-4 rounded-xl border border-[#2A2B2F]">
                                <span className="text-[10px] uppercase text-[#8E9299] block mb-1">Signal Score</span>
                                <span className="text-2xl text-white font-mono">0.94</span>
                              </div>
                              <div className="bg-[#151619] p-4 rounded-xl border border-[#2A2B2F]">
                                <span className="text-[10px] uppercase text-[#8E9299] block mb-1">Risk Buffer</span>
                                <span className="text-2xl text-white font-mono">1.4x</span>
                              </div>
                            </div>
                          </motion.div>
                        ) : (
                          <div className="space-y-4 relative z-10 opacity-40">
                            <Activity size={48} className="mx-auto text-gray-600" />
                            <h3 className="text-gray-400 font-bold tracking-widest uppercase">Select Action to Begin Audit</h3>
                          </div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
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

              {/* Factor Vitality Engine */}
              <section id="factors-section" className="space-y-4">
                <FactorHealth />
              </section>

              {/* Interactive Engine Controls */}
              <section id="engine-controls" className="bg-[#151619] rounded-2xl border border-[#2A2B2F] p-6 space-y-6">
                <div className="flex justify-between items-center">
                  <h3 className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
                    <Binary size={14} className="text-[#00FF00]" />
                    Interactive Engine Parameters
                  </h3>
                </div>
                
                <div className="space-y-6">
                  <div className="space-y-3">
                    <div className="flex justify-between text-[10px] font-mono uppercase">
                      <span className="text-[#8E9299]">Risk Tolerance</span>
                      <span className="text-[#00FF00]">{riskBias}%</span>
                    </div>
                    <input 
                      type="range" 
                      min="1" 
                      max="100" 
                      value={riskBias}
                      onChange={(e) => setRiskBias(parseInt(e.target.value))}
                      className="w-full h-1 bg-black rounded-lg appearance-none cursor-pointer accent-[#00FF00]"
                    />
                    <p className="text-[9px] text-gray-600 italic">Adjusts Kelly fraction capping and MC survival thresholds.</p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between text-[10px] font-mono uppercase">
                      <span className="text-[#8E9299]">Regime Sensitivity</span>
                      <span className="text-[#00FF00]">{regimeSensitivity.toFixed(2)}</span>
                    </div>
                    <input 
                      type="range" 
                      min="0" 
                      max="1" 
                      step="0.01"
                      value={regimeSensitivity}
                      onChange={(e) => setRegimeSensitivity(parseFloat(e.target.value))}
                      className="w-full h-1 bg-black rounded-lg appearance-none cursor-pointer accent-[#00FF00]"
                    />
                    <p className="text-[9px] text-gray-600 italic">Weighting of HMM states vs Microstructure OFI signals.</p>
                  </div>
                </div>

                <div className="pt-4 border-t border-[#2A2B2F] flex gap-3">
                  <button 
                    onClick={runSimulation}
                    className="flex-1 py-2 bg-white text-black text-[10px] font-bold uppercase tracking-tighter rounded-lg hover:bg-[#00FF00] transition-colors"
                  >
                    Apply & Re-simulate
                  </button>
                </div>
              </section>

              {/* Regime Tracking */}
              <section id="regime-section">
                <RegimeTracker />
              </section>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}
