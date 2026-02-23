import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Newspaper, Loader2, RefreshCw, ExternalLink, Calendar, Tag, Clock
} from 'lucide-react';

const NewsPulseView = () => {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [category, setCategory] = useState(null);

    const categories = [
        { key: null, label: 'All' },
        { key: 'atp', label: 'ATP' },
        { key: 'wta', label: 'WTA' },
        { key: 'junior', label: 'Junior' },
        { key: 'college', label: 'College' },
    ];

    useEffect(() => {
        fetchNews();
    }, [category]);

    const fetchNews = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = { limit: 50 };
            if (category) params.category = category;
            const res = await axios.get('/api/news', { params });
            setNews(res.data.data || []);
        } catch (err) {
            console.error('Error fetching news:', err);
            setError('Failed to load news. Make sure the backend is running.');
        }
        setLoading(false);
    };

    const refreshNews = async () => {
        try {
            await axios.post('/api/news/refresh');
            fetchNews();
        } catch (err) {
            console.error('Error refreshing news:', err);
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        try {
            const d = new Date(dateStr);
            const now = new Date();
            const diffMs = now - d;
            const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
            if (diffHrs < 1) return 'Just now';
            if (diffHrs < 24) return `${diffHrs}h ago`;
            const diffDays = Math.floor(diffHrs / 24);
            if (diffDays < 7) return `${diffDays}d ago`;
            return d.toLocaleDateString();
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="h-full flex flex-col animate-in fade-in duration-300">
            {/* Header */}
            <div className="p-4 md:p-6 border-b border-slate-800 bg-slate-900/50 backdrop-blur shrink-0">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Newspaper className="w-6 h-6 text-violet-400" />
                        <div>
                            <h1 className="text-xl font-bold text-white">News Pulse</h1>
                            <p className="text-xs text-slate-500 mt-0.5">Latest tennis news and updates</p>
                        </div>
                    </div>
                    <button
                        onClick={refreshNews}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 bg-violet-500/10 text-violet-400 rounded-lg hover:bg-violet-500/20 transition-colors text-sm"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>

                <div className="flex flex-wrap gap-2">
                    {categories.map(cat => (
                        <button
                            key={cat.key || 'all'}
                            onClick={() => setCategory(cat.key)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${category === cat.key
                                    ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30'
                                    : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'
                                }`}
                        >
                            {cat.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
                        <span className="mt-3 text-slate-400 text-sm">Loading news...</span>
                    </div>
                ) : error ? (
                    <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-6 text-center">
                        <p className="text-rose-400">{error}</p>
                        <button onClick={fetchNews} className="mt-3 text-sm text-tennis-blue hover:underline">
                            Try again
                        </button>
                    </div>
                ) : news.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                        <Newspaper className="w-12 h-12 mb-4 opacity-20" />
                        <p>No news articles available</p>
                        <p className="text-sm mt-1">Check back later for updates</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {news.map((item, idx) => (
                            <a
                                key={item.id || idx}
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-violet-500/50 transition-all group block"
                            >
                                {/* Image */}
                                {item.image_url && (
                                    <div className="h-40 bg-slate-800 overflow-hidden">
                                        <img
                                            src={item.image_url}
                                            alt=""
                                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                            onError={(e) => { e.target.style.display = 'none'; }}
                                        />
                                    </div>
                                )}

                                <div className="p-4">
                                    <div className="flex items-center gap-2 mb-2">
                                        {item.source && (
                                            <span className="text-[10px] uppercase font-bold bg-violet-500/20 text-violet-400 px-2 py-0.5 rounded">
                                                {item.source}
                                            </span>
                                        )}
                                        {item.category && (
                                            <span className="text-[10px] uppercase font-bold bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
                                                {item.category}
                                            </span>
                                        )}
                                        <span className="text-[10px] text-slate-500 ml-auto flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {formatDate(item.published_at)}
                                        </span>
                                    </div>

                                    <h3 className="text-white font-semibold group-hover:text-violet-400 transition-colors line-clamp-2">
                                        {item.title}
                                    </h3>

                                    {item.summary && (
                                        <p className="text-sm text-slate-400 mt-2 line-clamp-3">{item.summary}</p>
                                    )}

                                    <div className="mt-3 flex items-center gap-1 text-xs text-slate-500 group-hover:text-violet-400 transition-colors">
                                        <ExternalLink className="w-3 h-3" />
                                        <span>Read more</span>
                                    </div>
                                </div>
                            </a>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default NewsPulseView;
