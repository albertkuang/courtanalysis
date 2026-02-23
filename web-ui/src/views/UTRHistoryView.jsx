import React, { useMemo } from 'react';
import { History, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const UTRHistoryView = ({ history }) => {
    const sortedHistory = useMemo(() => {
        if (!history || history.length === 0) return [];
        return [...history]
            .filter(h => h.type === 'singles')
            .sort((a, b) => b.date.localeCompare(a.date));
    }, [history]);

    const stats = useMemo(() => {
        if (!history || history.length < 2) return { singlesChange: 0 };

        const singles = history.filter(h => h.type === 'singles').sort((a, b) => a.date.localeCompare(b.date));

        const sChange = singles.length >= 2 ? (singles[singles.length - 1].rating - singles[0].rating).toFixed(2) : 0;

        return { singlesChange: sChange };
    }, [history]);

    if (!history || history.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-slate-800 rounded-2xl bg-slate-900/30">
                <History className="w-12 h-12 text-slate-600 mb-4" />
                <h3 className="text-lg font-bold text-slate-400">No UTR History</h3>
                <p className="text-slate-500 text-sm mt-2">No historical rating data found for this player.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            {/* Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 max-w-sm">
                    <div className="text-xs text-slate-500 uppercase font-bold mb-1">Singles Growth</div>
                    <div className="flex items-center gap-2">
                        <div className={`text-2xl font-mono font-bold ${parseFloat(stats.singlesChange) > 0 ? 'text-emerald-400' : parseFloat(stats.singlesChange) < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                            {parseFloat(stats.singlesChange) > 0 ? '+' : ''}{stats.singlesChange}
                        </div>
                        {parseFloat(stats.singlesChange) !== 0 && (
                            parseFloat(stats.singlesChange) > 0 ? <TrendingUp className="w-5 h-5 text-emerald-500" /> : <TrendingDown className="w-5 h-5 text-rose-500" />
                        )}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1 uppercase tracking-wider">All-time trend</div>
                </div>
            </div>

            {/* History Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
                    <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                        <History className="w-4 h-4 text-tennis-blue" /> Historical Weekly Singles UTR
                    </h3>
                    <span className="text-xs text-slate-500">{sortedHistory.length} updates</span>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs text-slate-500 uppercase bg-slate-950/50 border-b border-slate-800">
                            <tr>
                                <th className="px-6 py-3 font-bold">Date</th>
                                <th className="px-6 py-3 font-bold">Rating</th>
                                <th className="px-6 py-3 font-bold">Change</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {sortedHistory.map((h, idx) => {
                                // Find previous rating to calculate change
                                const prev = sortedHistory[idx + 1];
                                const change = prev ? (h.rating - prev.rating).toFixed(2) : null;

                                return (
                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                        <td className="px-6 py-4 font-medium text-slate-300">
                                            {new Date(h.date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                                        </td>
                                        <td className="px-6 py-4 font-mono font-bold text-white">
                                            {h.rating.toFixed(2)}
                                        </td>
                                        <td className="px-6 py-4">
                                            {change !== null ? (
                                                <div className={`flex items-center gap-1 font-mono text-xs ${parseFloat(change) > 0 ? 'text-emerald-400' : parseFloat(change) < 0 ? 'text-rose-400' : 'text-slate-500'
                                                    }`}>
                                                    {parseFloat(change) > 0 ? '+' : ''}{change}
                                                </div>
                                            ) : (
                                                <Minus className="w-3 h-3 text-slate-700" />
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default UTRHistoryView;
