
import React, { useState, useEffect } from 'react';
import { Camera, ExternalLink, Instagram, Loader2 } from 'lucide-react';
import axios from 'axios';

const PlayerSocialFeed = ({ playerId, playerName }) => {
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState('loading'); // loading, success, empty, error
    const [provider, setProvider] = useState(null);
    const [isConnected, setIsConnected] = useState(true);

    useEffect(() => {
        const fetchFeed = async () => {
            setLoading(true);
            try {
                const res = await axios.get(`/api/players/${playerId}/social`);
                const { data, status: apiStatus, connected } = res.data;

                setIsConnected(connected);

                if (data && data.length > 0) {
                    setPosts(data);
                    setStatus('success');
                } else {
                    setStatus('empty');
                }
            } catch (err) {
                console.error("Failed to fetch social feed", err);
                setStatus('error');
            }
            setLoading(false);
        };

        if (playerId) {
            fetchFeed();
        }
    }, [playerId]);

    const handlePostClick = (shortcode) => {
        window.open(`https://www.instagram.com/p/${shortcode}/`, '_blank');
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-slate-500">
                <Loader2 className="w-8 h-8 animate-spin mb-2" />
                <span className="text-sm">Loading social feed...</span>
            </div>
        );
    }

    if (!isConnected) {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center">
                <Instagram className="w-8 h-8 text-pink-500 mx-auto mb-3" />
                <h3 className="text-white font-medium mb-1">Instagram Feed Unavailable</h3>
                <p className="text-slate-400 text-sm mb-4">
                    The Instagram integration is currently not configured or unavailable.
                </p>
                <a
                    href={`https://www.instagram.com/explore/tags/${playerName.replace(/\s+/g, '')}/`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-pink-600 hover:bg-pink-500 text-white rounded-lg transition-colors text-sm font-bold"
                >
                    <ExternalLink className="w-4 h-4" />
                    View on Instagram
                </a>
            </div>
        );
    }

    if (status === 'empty' || status === 'error') {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center">
                <Camera className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <h3 className="text-white font-medium mb-1">No Recent Posts</h3>
                <p className="text-slate-400 text-sm mb-4">
                    We couldn't find any recent Instagram posts for this player.
                </p>
                <a
                    href={`https://www.instagram.com/explore/tags/${playerName.replace(/\s+/g, '')}/`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors text-sm font-bold"
                >
                    <Instagram className="w-4 h-4" />
                    Search Instagram
                </a>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Instagram className="w-5 h-5 text-pink-500" />
                    <h3 className="text-white font-bold">Recent Updates</h3>
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {posts.map((post) => (
                    <div
                        key={post.shortcode}
                        className="group relative aspect-square bg-slate-900 rounded-lg overflow-hidden cursor-pointer border border-slate-800 hover:border-pink-500/50 transition-all"
                        onClick={() => handlePostClick(post.shortcode)}
                    >
                        <img
                            src={post.image_url}
                            alt={post.caption || "Instagram Post"}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.parentElement.classList.add('flex', 'items-center', 'justify-center');
                                e.target.parentElement.innerHTML = '<span class="text-xs text-slate-600">Image Expired</span>';
                            }}
                        />
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                            {post.caption && (
                                <p className="text-white text-xs line-clamp-2 mb-1">
                                    {post.caption}
                                </p>
                            )}
                            <div className="flex items-center gap-1 text-[10px] text-slate-300">
                                <ExternalLink className="w-3 h-3" />
                                <span>View Post</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default PlayerSocialFeed;
