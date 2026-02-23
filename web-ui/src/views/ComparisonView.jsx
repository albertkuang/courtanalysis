import React, { useState } from 'react';
import axios from 'axios';
import { Cpu, X, Loader2, TrendingUp, TrendingDown, Target, Zap } from 'lucide-react';

const ComparisonView = ({ list, onRemove }) => {
    const [simResult, setSimResult] = useState(null);
    const [simLoading, setSimLoading] = useState(false);
    const [showSim, setShowSim] = useState(false);

    const startSimulation = async () => {
        if (list.length !== 2) return;
        setSimLoading(true);
        setShowSim(true);
        setSimResult(null);
        try {
            const res = await axios.post('/api/simulate_match', {
                p1_id: list[0].player_id,
                p2_id: list[1].player_id
            });
            setSimResult(res.data.data);
        } catch (err) {
            console.error(err);
            alert("Simulation failed. Please check your AI configuration.");
            setShowSim(false);
        }
        setSimLoading(false);
    };

    return (
        <div className="max-w-6xl mx-auto p-4 md:p-6 pb-24 md:pb-6 relative h-full overflow-y-auto no-scrollbar">
            {/* Simulation Modal */}
            {showSim && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-300">
                    <div className="absolute inset-0" onClick={() => setShowSim(false)}></div>
                    <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="bg-gradient-to-r from-violet-900 via-indigo-900 to-slate-900 p-6 border-b border-indigo-500/30 flex justify-between items-center">
                            <div>
                                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                    <Cpu className="w-6 h-6 text-indigo-400 animate-pulse" /> Virtual Matchup
                                </h2>
                                <div className="text-indigo-200 text-sm font-medium tracking-wide">
                                    {list[0]?.name} <span className="text-white/30 mx-2">vs</span> {list[1]?.name}
                                </div>
                            </div>
                            <button
                                onClick={() => setShowSim(false)}
                                className="p-2 hover:bg-white/10 rounded-full text-white/50 hover:text-white transition-all"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="p-8 overflow-y-auto custom-scrollbar bg-slate-900/50">
                            {simLoading ? (
                                <div className="flex flex-col items-center justify-center py-16 text-center space-y-6">
                                    <div className="relative">
                                        <Loader2 className="w-20 h-20 animate-spin text-indigo-500 opacity-20" />
                                        <Cpu className="w-10 h-10 text-indigo-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                                    </div>
                                    <div className="space-y-2">
                                        <p className="text-xl font-bold text-white tracking-tight">AI Engine Processing...</p>
                                        <p className="text-sm text-slate-500">Comparing match histories, clutch metrics, and surface performance</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-8 text-slate-300 leading-relaxed">
                                    {simResult && simResult.report_text.split('\n').map((line, i) => {
                                        if (line.trim().startsWith('###')) {
                                            const title = line.replace(/###/g, '').trim();
                                            let icon = <Target className="w-5 h-5" />;
                                            let color = "text-white";
                                            if (title.includes('X-Factor')) { color = "text-amber-400"; icon = <Zap className="w-5 h-5" />; }
                                            if (title.includes('Prediction')) { color = "text-emerald-400"; icon = <TrendingUp className="w-5 h-5" />; }

                                            return (
                                                <h3 key={i} className={`text-xl font-bold mt-8 mb-4 border-b border-slate-800 pb-3 flex items-center gap-2 ${color}`}>
                                                    {icon} {title}
                                                </h3>
                                            );
                                        }
                                        if (line.includes('Winner:')) {
                                            const winnerName = line.replace(/\*\*/g, '').replace('Winner:', '').trim();
                                            return (
                                                <div key={i} className="bg-indigo-500/5 border border-indigo-500/20 rounded-2xl p-8 my-8 text-center shadow-2xl relative overflow-hidden group">
                                                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-50"></div>
                                                    <div className="text-xs uppercase tracking-[0.2em] text-indigo-400 font-black mb-2 opacity-80">Projected Victor</div>
                                                    <div className="text-3xl font-black text-white group-hover:scale-105 transition-transform duration-500">{winnerName}</div>
                                                </div>
                                            );
                                        }
                                        if (line.trim() === '') return null;
                                        return <p key={i} className="text-slate-400 font-medium mb-3">{line.replace(/\*\*/g, '').trim()}</p>;
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Header Actions */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
                <div>
                    <h2 className="text-3xl font-black text-white tracking-tight">Comparison Lab</h2>
                    <p className="text-slate-500 text-sm mt-1 font-medium">Head-to-head metrics and AI simulations</p>
                </div>
                {list.length === 2 && (
                    <button
                        onClick={startSimulation}
                        className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-8 rounded-xl shadow-xl shadow-indigo-500/20 flex items-center justify-center gap-3 transition-all transform hover:translate-y-[-2px] active:translate-y-[0px]"
                    >
                        <Cpu className="w-5 h-5" /> Start Simulation
                    </button>
                )}
            </div>

            {list.length === 0 ? (
                <div className="text-center text-slate-600 py-32 border-2 border-dashed border-slate-800 rounded-3xl bg-slate-900/20 flex flex-col items-center justify-center space-y-4">
                    <Target className="w-12 h-12 opacity-20" />
                    <p className="text-lg font-medium">Select players from Scout view to begin comparison</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {list.map((p) => (
                        <div key={p.player_id} className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden transition-all hover:border-slate-700/50 group">
                            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-tennis-blue/50 to-tennis-green/50"></div>

                            <div className="flex justify-between items-start mb-10">
                                <div className="min-w-0">
                                    <h3 className="text-3xl font-black text-white mb-2 truncate group-hover:text-tennis-blue transition-colors duration-300 tracking-tight">{p.name}</h3>
                                    <div className="flex items-center gap-3 text-sm text-slate-500 font-bold uppercase tracking-widest">
                                        <span>{p.country || 'N/A'}</span>
                                        <span className="w-1.5 h-1.5 rounded-full bg-slate-800"></span>
                                        <span>{p.age || '?'} YRS</span>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-4xl font-mono font-black text-tennis-green tracking-tighter">{p.utr_singles?.toFixed(2)}</div>
                                    <div className="text-[10px] text-slate-600 uppercase font-black tracking-[0.2em] mt-1">Singles UTR</div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-6 mb-10">
                                <StatItem label="Doubles UTR" value={p.utr_doubles?.toFixed(2) || '-'} />
                                <StatItem
                                    label="1Y Delta"
                                    value={(p.year_delta > 0 ? '+' : '') + (p.year_delta?.toFixed(2) || '0.00')}
                                    color={p.year_delta > 0 ? 'text-emerald-400' : 'text-rose-400'}
                                />
                                <StatItem label="Comebacks" value={p.comeback_wins || '0'} />
                                <StatItem
                                    label="T-Break W/L"
                                    value={`${p.tiebreak_wins || 0} / ${p.tiebreak_losses || 0}`}
                                    color="text-amber-400"
                                />
                            </div>

                            <div className="space-y-4 mb-10">
                                <div className="flex justify-between py-3 border-b border-slate-800/50 items-center">
                                    <span className="text-slate-500 text-xs uppercase font-black tracking-widest">College</span>
                                    <span className="text-white text-right max-w-[200px] truncate font-bold text-sm tracking-tight">{p.college || '-'}</span>
                                </div>
                                <div className="flex justify-between py-3 border-b border-slate-800/50 items-center">
                                    <span className="text-slate-500 text-xs uppercase font-black tracking-widest">Location</span>
                                    <span className="text-white text-right max-w-[200px] truncate font-bold text-sm tracking-tight">{p.location || '-'}</span>
                                </div>
                            </div>

                            <button
                                onClick={() => onRemove(p.player_id)}
                                className="w-full py-4 bg-slate-950/50 text-rose-500/70 rounded-2xl hover:bg-rose-500/10 hover:text-rose-500 transition-all text-sm font-black uppercase tracking-widest border border-slate-800 hover:border-rose-500/30"
                            >
                                Remove Player
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const StatItem = ({ label, value, color = "text-white" }) => (
    <div className="bg-slate-950/30 rounded-2xl p-4 border border-slate-800/50">
        <div className="text-[10px] text-slate-600 uppercase font-black tracking-widest mb-1">{label}</div>
        <div className={`text-lg font-mono font-black ${color}`}>{value}</div>
    </div>
);

export default ComparisonView;
