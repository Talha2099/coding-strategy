'use client';

import React from 'react';
import { MOCK_TRADES } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { ArrowUpRight, ArrowDownRight, MoreVertical, ExternalLink } from 'lucide-react';

export function TradeTable() {
  return (
    <div id="trade-table-container" className="bg-[#151619] border border-[#2A2B2F] rounded-xl overflow-hidden">
      <div className="p-4 border-bottom border-[#2A2B2F] flex justify-between items-center bg-[#1A1B1F]">
        <h3 className="text-white text-xs font-medium uppercase tracking-wider font-sans">Recent Trade Candidates</h3>
        <button id="view-all-trades" className="text-[#8E9299] hover:text-white text-[10px] font-mono flex items-center gap-1 transition-colors">
          View Audit Log <ExternalLink size={10} />
        </button>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-[#2A2B2F]">
              <th className="px-4 py-3 text-[#8E9299] font-mono italic text-[10px] uppercase tracking-wider">Strategy / Regime</th>
              <th className="px-4 py-3 text-[#8E9299] font-mono italic text-[10px] uppercase tracking-wider">Entry Detail</th>
              <th className="px-4 py-3 text-[#8E9299] font-mono italic text-[10px] uppercase tracking-wider">Risk / Reward</th>
              <th className="px-4 py-3 text-[#8E9299] font-mono italic text-[10px] uppercase tracking-wider">Conf. Score</th>
              <th className="px-4 py-3 text-[#8E9299] font-mono italic text-[10px] uppercase tracking-wider">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#2A2B2F]">
            {MOCK_TRADES.map((trade) => (
              <tr 
                key={trade.id} 
                id={`trade-row-${trade.id}`}
                className="hover:bg-[#1A1B1F] transition-colors group cursor-pointer"
              >
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center",
                      trade.side === 1 ? "bg-[#00FF00]/10" : "bg-red-500/10"
                    )}>
                      {trade.side === 1 ? <ArrowUpRight className="text-[#00FF00]" size={16} /> : <ArrowDownRight className="text-red-500" size={16} />}
                    </div>
                    <div>
                      <p className="text-white text-sm font-medium">{trade.symbol}</p>
                      <p className="text-[#8E9299] text-[10px] font-mono truncate max-w-[150px]">{trade.strategyName} | {trade.regime}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <p className="text-white text-xs font-mono">{trade.entryPrice.toLocaleString()}</p>
                  <p className="text-[#8E9299] text-[10px]">{format(new Date(trade.entryTime), 'MMM dd, HH:mm')}</p>
                </td>
                <td className="px-4 py-4">
                  <p className="text-white text-[10px] font-mono">SL: <span className="text-red-400/80">{trade.stopLoss.toLocaleString()}</span></p>
                  <p className="text-white text-[10px] font-mono">TP: <span className="text-[#00FF00]/80">{trade.takeProfit.toLocaleString()}</span></p>
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-2">
                    <div className="w-12 h-1.5 bg-[#2A2B2F] rounded-full overflow-hidden">
                      <div 
                        className={cn(
                          "h-full rounded-full transition-all",
                          trade.probability > 0.75 ? "bg-[#00FF00]" : "bg-[#8E9299]"
                        )} 
                        style={{ width: `${trade.probability * 100}%` }}
                      />
                    </div>
                    <span className="text-white text-[10px] font-mono">{(trade.probability * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <span className={cn(
                    "px-2 py-0.5 rounded-md text-[10px] font-mono uppercase",
                    trade.status === 'executed' ? "bg-[#00FF00]/10 text-[#00FF00]" :
                    trade.status === 'closed' ? "bg-blue-500/10 text-blue-400" :
                    trade.status === 'pending' ? "bg-orange-500/10 text-orange-400" :
                    "bg-[#8E9299]/10 text-[#8E9299]"
                  )}>
                    {trade.status}
                  </span>
                </td>
                <td className="px-4 py-4 text-right">
                  <button className="text-[#8E9299] group-hover:text-white transition-colors p-1">
                    <MoreVertical size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
