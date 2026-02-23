import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { TrendingUp, Loader2 } from 'lucide-react';
import {
    LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

const RatingChart = ({ history, playerId, player }) => {
    const [timeRange, setTimeRange] = useState('1Y');
    const [showType, setShowType] = useState('singles');
    const [rankings, setRankings] = useState([]);
    const [loadingRankings, setLoadingRankings] = useState(false);
    const [checkedForRankings, setCheckedForRankings] = useState(false);

    const isPro = String(player?.player_id || '').startsWith('sackmann') || player?.pro_rank;
    const [mode, setMode] = useState(isPro ? 'ranking' : 'utr');

    useEffect(() => {
        setRankings([]);
        setCheckedForRankings(false);
        const newIsPro = String(player?.player_id || '').startsWith('sackmann') || player?.pro_rank;
        setMode(newIsPro ? 'ranking' : 'utr');
        if (newIsPro) {
            setCheckedForRankings(true);
        }
    }, [playerId, player?.player_id, player?.pro_rank]);

    useEffect(() => {
        if (!checkedForRankings && playerId && !isPro) {
            axios.get(`/api/players/${playerId}/rankings`)
                .then(res => {
                    const data = res.data.data || [];
                    setRankings(data);
                    if (data.length > 0) {
                        setMode('ranking');
                    }
                })
                .catch(err => console.error(err))
                .finally(() => setCheckedForRankings(true));
        }
    }, [playerId, isPro, checkedForRankings]);

    useEffect(() => {
        if (mode === 'ranking' && playerId && rankings.length === 0 && checkedForRankings) {
            setLoadingRankings(true);
            axios.get(`/api/players/${playerId}/rankings`)
                .then(res => {
                    setRankings(res.data.data || []);
                })
                .catch(err => console.error(err))
                .finally(() => setLoadingRankings(false));
        }
    }, [mode, playerId, rankings.length, checkedForRankings]);

    const timeRanges = [
        { label: '3M', months: 3 },
        { label: '6M', months: 6 },
        { label: '1Y', months: 12 },
        { label: '2Y', months: 24 },
        { label: 'ALL', months: null }
    ];

    const cutoffDate = useMemo(() => {
        const selected = timeRanges.find(t => t.label === timeRange);
        if (!selected || selected.months === null) return null;
        const d = new Date();
        d.setMonth(d.getMonth() - selected.months);
        return d.toISOString().split('T')[0];
    }, [timeRange]);

    const { singlesData, doublesData, chartData, rankingData } = useMemo(() => {
        if (mode === 'ranking') {
            const filteredRankings = rankings
                .filter(r => !cutoffDate || r.date >= cutoffDate)
                .sort((a, b) => a.date.localeCompare(b.date))
                .map(r => ({ date: r.date, rank: r.rank }));
            return { singlesData: [], doublesData: [], chartData: [], rankingData: filteredRankings };
        }

        if (!history || history.length === 0) return { singlesData: [], doublesData: [], chartData: [], rankingData: [] };

        const singles = history
            .filter(h => h.type === 'singles' && (!cutoffDate || h.date >= cutoffDate))
            .map(h => ({ date: h.date, rating: h.rating }))
            .sort((a, b) => a.date.localeCompare(b.date));

        const doubles = history
            .filter(h => h.type === 'doubles' && (!cutoffDate || h.date >= cutoffDate))
            .map(h => ({ date: h.date, rating: h.rating }))
            .sort((a, b) => a.date.localeCompare(b.date));

        const allDates = [...new Set([...singles.map(s => s.date), ...doubles.map(d => d.date)])].sort();
        const merged = allDates.map(date => {
            const s = singles.find(x => x.date === date);
            const d = doubles.find(x => x.date === date);
            return { date, singles: s?.rating, doubles: d?.rating };
        });

        return { singlesData: singles, doublesData: doubles, chartData: merged, rankingData: [] };
    }, [history, cutoffDate, mode, rankings]);

    const displayData = mode === 'ranking' ? rankingData :
        showType === 'both' ? chartData :
            showType === 'singles' ? singlesData : doublesData;

    const { domainMin, domainMax } = useMemo(() => {
        if (mode === 'ranking') {
            if (rankingData.length === 0) return { domainMin: 0, domainMax: 1000 };
            const ranks = rankingData.map(r => r.rank);
            return { domainMin: Math.min(...ranks) > 10 ? Math.min(...ranks) - 5 : 1, domainMax: Math.max(...ranks) + 10 };
        }

        const allRatings = displayData.flatMap(d =>
            showType === 'both' ? [d.singles, d.doubles].filter(Boolean) : [d.rating]
        ).filter(Boolean);

        if (allRatings.length === 0) return { domainMin: 1, domainMax: 10 };
        const min = Math.min(...allRatings);
        const max = Math.max(...allRatings);
        return {
            domainMin: Math.floor(min * 2) / 2 - 0.5,
            domainMax: Math.ceil(max * 2) / 2 + 0.5
        };
    }, [displayData, showType, mode, rankingData]);

    const change = useMemo(() => {
        if (mode === 'ranking') {
            if (rankingData.length < 2) return null;
            const first = rankingData[0].rank;
            const last = rankingData[rankingData.length - 1].rank;
            return first - last;
        }
        if (showType === 'both' || !displayData || displayData.length < 2) return null;
        const first = displayData[0]?.rating;
        const last = displayData[displayData.length - 1]?.rating;
        if (first && last) return (last - first).toFixed(2);
        return null;
    }, [displayData, showType, mode, rankingData]);

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-tennis-green" />
                    {mode === 'ranking' ? 'ATP/WTA Ranking' : 'UTR Progression'}
                    {change !== null && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${parseFloat(change) > 0 ? 'bg-emerald-500/20 text-emerald-400' : parseFloat(change) < 0 ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-500/20 text-slate-400'
                            }`}>
                            {parseFloat(change) > 0 ? (mode === 'ranking' ? '▲ ' : '+') : (mode === 'ranking' ? '▼ ' : '')}{Math.abs(change)}
                        </span>
                    )}
                </h3>

                <div className="flex gap-2 flex-wrap items-center">
                    <div className="flex bg-slate-800 rounded-lg p-0.5 mr-2">
                        <button onClick={() => setMode('utr')} className={`px-2 py-1 text-xs font-medium rounded transition-colors ${mode === 'utr' ? 'bg-tennis-blue text-white' : 'text-slate-400 hover:text-white'}`}>UTR</button>
                        <button onClick={() => setMode('ranking')} className={`px-2 py-1 text-xs font-medium rounded transition-colors ${mode === 'ranking' ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-white'}`}>Rank</button>
                    </div>

                    <div className="flex bg-slate-800 rounded-lg p-0.5">
                        {timeRanges.map(t => (
                            <button
                                key={t.label}
                                onClick={() => setTimeRange(t.label)}
                                className={`px-2 py-1 text-xs font-medium rounded transition-colors ${timeRange === t.label
                                    ? 'bg-tennis-blue text-white'
                                    : 'text-slate-400 hover:text-white'
                                    }`}
                            >
                                {t.label}
                            </button>
                        ))}
                    </div>

                    {mode === 'utr' && (
                        <div className="flex bg-slate-800 rounded-lg p-0.5">
                            {[
                                { key: 'singles', label: 'S' },
                                { key: 'doubles', label: 'D' },
                                { key: 'both', label: 'S+D' }
                            ].map(t => (
                                <button
                                    key={t.key}
                                    onClick={() => setShowType(t.key)}
                                    className={`px-2 py-1 text-xs font-medium rounded transition-colors ${showType === t.key
                                        ? 'bg-tennis-green text-slate-900'
                                        : 'text-slate-400 hover:text-white'
                                        }`}
                                >
                                    {t.label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="h-56 bg-slate-950 rounded-lg border border-slate-800 p-2 relative">
                {loadingRankings && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10 rounded-lg">
                        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
                    </div>
                )}
                {displayData && displayData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={displayData}>
                            <XAxis
                                dataKey="date"
                                tick={{ fill: '#64748b', fontSize: 10 }}
                                tickFormatter={(val) => {
                                    const d = new Date(val);
                                    return `${d.getMonth() + 1}/${d.getFullYear().toString().slice(-2)}`;
                                }}
                                interval="preserveStartEnd"
                            />
                            <YAxis
                                domain={[domainMin, domainMax]}
                                reversed={mode === 'ranking'}
                                tick={{ fill: '#64748b', fontSize: 10 }}
                                tickFormatter={(val) => val.toFixed(mode === 'ranking' ? 0 : 1)}
                                width={35}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                                itemStyle={{ color: '#e2e8f0' }}
                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                                formatter={(value, name) => [
                                    mode === 'ranking' ? value : value?.toFixed(2),
                                    mode === 'ranking' ? 'Rank' : (name === 'singles' ? 'Singles' : name === 'doubles' ? 'Doubles' : 'UTR')
                                ]}
                            />
                            {mode === 'ranking' ? (
                                <Line type="monotone" dataKey="rank" stroke="#f59e0b" strokeWidth={3} dot={false} activeDot={{ r: 4, fill: '#f59e0b' }} name="Rank" connectNulls />
                            ) : showType === 'both' ? (
                                <>
                                    <Line type="monotone" dataKey="singles" stroke="#0ea5e9" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#0ea5e9' }} name="singles" connectNulls />
                                    <Line type="monotone" dataKey="doubles" stroke="#10b981" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#10b981' }} name="doubles" connectNulls />
                                    <Legend wrapperStyle={{ fontSize: '10px' }} formatter={(value) => value === 'singles' ? 'Singles' : 'Doubles'} />
                                </>
                            ) : (
                                <Line
                                    type="monotone"
                                    dataKey="rating"
                                    stroke={showType === 'singles' ? '#0ea5e9' : '#10b981'}
                                    strokeWidth={3}
                                    dot={false}
                                    activeDot={{ r: 4, fill: '#fff' }}
                                />
                            )}
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-slate-600 text-sm gap-1">
                        <span>No {mode === 'ranking' ? 'ranking' : 'UTR'} history data available</span>
                        {mode === 'ranking' && rankings.length > 0 && (
                            <span className="text-xs text-slate-500">Try selecting a longer time range (2Y or ALL)</span>
                        )}
                    </div>
                )}
            </div>

            {displayData && displayData.length > 0 && (
                <div className="flex justify-between items-center mt-3 text-xs text-slate-500">
                    <span>{displayData.length} data points</span>
                    <span>
                        {displayData[0]?.date && new Date(displayData[0].date).toLocaleDateString()} — {displayData[displayData.length - 1]?.date && new Date(displayData[displayData.length - 1].date).toLocaleDateString()}
                    </span>
                </div>
            )}
        </div>
    );
};

export default RatingChart;
