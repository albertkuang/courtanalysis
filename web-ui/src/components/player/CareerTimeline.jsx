
import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Calendar, TrendingUp, TrendingDown, Target, Award } from 'lucide-react';
import axios from 'axios';

const CareerTimeline = ({ playerId, playerName }) => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState('1Y'); // 1Y, 3Y, ALL

    useEffect(() => {
        const fetchHistory = async () => {
            setLoading(true);
            try {
                const res = await axios.get(`/api/players/${playerId}/history`);
                if (res.data && res.data.data) {
                    processData(res.data.data);
                }
            } catch (err) {
                console.error("Failed to fetch history", err);
            }
            setLoading(false);
        };

        if (playerId) fetchHistory();
    }, [playerId]);

    const processData = (rawHistory) => {
        // Sort by date ascending
        const sorted = [...rawHistory].sort((a, b) => new Date(a.date) - new Date(b.date));

        // Filter out 0 or invalid ratings if needed
        const validData = sorted.filter(d => d.rating > 0);
        setHistory(validData);
    };

    const getFilteredData = () => {
        if (timeRange === 'ALL') return history;

        const now = new Date();
        const cutoff = new Date();
        if (timeRange === '1Y') cutoff.setFullYear(now.getFullYear() - 1);
        if (timeRange === '3Y') cutoff.setFullYear(now.getFullYear() - 3);

        return history.filter(d => new Date(d.date) >= cutoff);
    };

    const data = getFilteredData();
    if (loading) return <div className="h-64 flex items-center justify-center text-slate-500 animate-pulse">Loading Career Data...</div>;
    if (!data || data.length === 0) return <div className="h-64 flex items-center justify-center text-slate-500">No history data available.</div>;

    const startUTR = data.length > 0 ? data[0].rating : 0;
    const endUTR = data.length > 0 ? data[data.length - 1].rating : 0;
    const change = endUTR - startUTR;
    const peakUTR = Math.max(...data.map(d => d.rating));

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
            <div className="bg-slate-950/50 p-4 border-b border-slate-800 flex justify-between items-center">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-tennis-blue" /> Career Trajectory
                </h3>

                <div className="flex bg-slate-800 rounded-lg p-1">
                    {['1Y', '3Y', 'ALL'].map(range => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${timeRange === range
                                    ? 'bg-tennis-blue text-white shadow-lg'
                                    : 'text-slate-400 hover:text-white hover:bg-slate-700'
                                }`}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            <div className="p-6">
                {/* Key Metrics */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                        <div className="text-xs text-slate-500 uppercase font-bold mb-1">Current UTR</div>
                        <div className="text-2xl font-mono font-bold text-white">{endUTR.toFixed(2)}</div>
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                        <div className="text-xs text-slate-500 uppercase font-bold mb-1">Period Change</div>
                        <div className={`text-2xl font-mono font-bold flex items-center gap-1 ${change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                            {Math.abs(change).toFixed(2)}
                        </div>
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                        <div className="text-xs text-slate-500 uppercase font-bold mb-1">Peak UTR</div>
                        <div className="text-2xl font-mono font-bold text-amber-400">{peakUTR.toFixed(2)}</div>
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                        <div className="text-xs text-slate-500 uppercase font-bold mb-1">Matches</div>
                        <div className="text-2xl font-mono font-bold text-slate-300">{data.length}</div>
                    </div>
                </div>

                {/* Chart */}
                <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id="colorUtr" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                            <XAxis
                                dataKey="date"
                                tick={{ fill: '#64748b', fontSize: 10 }}
                                tickFormatter={(d) => new Date(d).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })}
                                minTickGap={30}
                            />
                            <YAxis
                                domain={['auto', 'auto']}
                                tick={{ fill: '#64748b', fontSize: 10 }}
                                tickCount={5}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }}
                                itemStyle={{ color: '#3b82f6' }}
                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                                formatter={(value) => [value.toFixed(2), "UTR"]}
                            />
                            <Area
                                type="monotone"
                                dataKey="rating"
                                stroke="#3b82f6"
                                strokeWidth={2}
                                fillOpacity={1}
                                fill="url(#colorUtr)"
                                activeDot={{ r: 6, strokeWidth: 0 }}
                            />
                            {/* Peak Line */}
                            <ReferenceLine y={peakUTR} stroke="#fbbf24" strokeDasharray="3 3" label={{ position: 'right', value: 'Peak', fill: '#fbbf24', fontSize: 10 }} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

export default CareerTimeline;
