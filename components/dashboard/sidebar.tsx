'use client';

import React from 'react';
import { 
  LayoutDashboard, 
  BarChart2, 
  Cpu, 
  Settings, 
  ShieldCheck, 
  Zap,
  ChevronRight,
  Binary
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { id: 'dashboard', label: 'Quant Monitor', icon: LayoutDashboard, active: true },
  { id: 'math-engine', label: 'Math Auditor', icon: Binary },
  { id: 'pattern-lab', label: 'Pattern Lab', icon: Cpu },
  { id: 'risk-engine', label: 'Risk Dynamics', icon: ShieldCheck },
  { id: 'settings', label: 'Engine Config', icon: Settings },
];

export function Sidebar() {
  return (
    <aside id="sidebar-nav" className="w-64 border-r border-[#2A2B2F] bg-[#0A0B0D] hidden lg:flex flex-col h-screen sticky top-0 overflow-y-auto">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-8 h-8 rounded-lg bg-[#00FF00] flex items-center justify-center">
            <Zap size={20} className="text-black fill-current" />
          </div>
          <span className="text-white font-sans font-semibold tracking-tighter text-lg">TRADERSUIT</span>
        </div>

        <nav className="space-y-1">
          <p className="text-[#8E9299] text-[10px] uppercase font-mono tracking-widest px-3 mb-3">Core Engine</p>
          {navItems.map((item) => (
            <button
              key={item.id}
              id={`nav-item-${item.id}`}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all group",
                item.active 
                  ? "bg-[#00FF00]/10 text-[#00FF00]" 
                  : "text-[#8E9299] hover:text-white hover:bg-[#151619]"
              )}
            >
              <div className="flex items-center gap-3">
                <item.icon size={18} />
                <span className="font-sans font-medium">{item.label}</span>
              </div>
              {item.active && <ChevronRight size={14} />}
            </button>
          ))}
        </nav>
      </div>

      <div className="mt-auto p-6 border-t border-[#2A2B2F]">
        <div className="bg-[#151619] rounded-xl p-4 border border-[#2A2B2F]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[#8E9299] text-[10px] uppercase font-mono tracking-tighter">API Status</span>
            <div className="w-2 h-2 rounded-full bg-[#00FF00] shadow-[0_0_8px_#00FF00]" />
          </div>
          <p className="text-white text-[11px] font-mono tracking-tighter truncate">MT5-GATEWAY-LIVE</p>
          <div className="mt-3 flex gap-1">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className={cn(
                "h-4 w-1 rounded-full",
                i < 8 ? "bg-[#00FF00]" : "bg-[#2A2B2F]"
              )} />
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
