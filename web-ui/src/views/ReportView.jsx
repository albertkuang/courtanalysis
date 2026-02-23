import React, { useState } from 'react';
import axios from 'axios';
import { FileText, Download, Loader2 } from 'lucide-react';
import { SelectFilter } from '../components/shared';

const ReportView = () => {
    const [loading, setLoading] = useState(false);
    const [params, setParams] = useState({
        country: 'ALL',
        gender: 'M',
        category: 'junior',
        minUtr: 0,
        count: 100,
        name: '',
        minAge: '',
        maxAge: ''
    });

    const generateReport = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/export', {
                params: {
                    country: params.country,
                    gender: params.gender,
                    category: params.category,
                    count: params.count,
                    name: params.name,
                    min_utr: params.minUtr,
                    min_age: params.minAge || undefined,
                    max_age: params.maxAge || undefined
                },
                responseType: 'blob', // Important
            });

            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            // Try to get filename from header or generate one
            const contentDisposition = response.headers['content-disposition'];
            let filename = 'report.xlsx';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="?([^"]+)"?/);
                if (match) filename = match[1];
            }

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);

        } catch (err) {
            console.error(err);
            alert('Failed to generate report. Checks logs or ensure data exists.');
        }
        setLoading(false);
    };

    const handleChange = (key, val) => setParams(prev => ({ ...prev, [key]: val }));

    return (
        <div className="max-w-xl mx-auto mt-10 p-8 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl animate-in fade-in zoom-in-95 duration-300">
            <div className="flex items-center gap-3 mb-6">
                <div className="bg-tennis-blue/20 p-2 rounded-lg">
                    <FileText className="w-8 h-8 text-tennis-blue" />
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-white">Export Report</h2>
                    <p className="text-slate-400 text-sm">Generate detailed Excel analysis for offline viewing.</p>
                </div>
            </div>

            <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Country</label>
                        <SelectFilter value={params.country} onChange={(v) => handleChange('country', v)} width="w-full" options={[
                            { val: 'ALL', txt: 'All Countries' }, { val: 'USA', txt: 'USA' }, { val: 'CAN', txt: 'Canada' },
                            { val: 'GBR', txt: 'UK' }, { val: 'ESP', txt: 'Spain' }, { val: 'FRA', txt: 'France' }
                        ]} />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Gender</label>
                        <SelectFilter value={params.gender} onChange={(v) => handleChange('gender', v)} width="w-full" options={[
                            { val: 'M', txt: 'Men' }, { val: 'F', txt: 'Women' }
                        ]} />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Category</label>
                        <SelectFilter value={params.category} onChange={(v) => handleChange('category', v)} width="w-full" options={[
                            { val: 'junior', txt: 'Juniors' }, { val: 'college', txt: 'College' }, { val: 'adult', txt: 'Pro' }
                        ]} />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Max Results</label>
                        <input type="number" value={params.count} onChange={(e) => handleChange('count', e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-tennis-blue focus:outline-none"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Min Age</label>
                        <input type="number" placeholder="e.g. 12" value={params.minAge} onChange={(e) => handleChange('minAge', e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-tennis-blue focus:outline-none"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Max Age</label>
                        <input type="number" placeholder="e.g. 18" value={params.maxAge} onChange={(e) => handleChange('maxAge', e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-tennis-blue focus:outline-none"
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Minimum UTR ({params.minUtr})</label>
                    <input type="range" min="0" max="16" step="0.5" value={params.minUtr} onChange={(e) => handleChange('minUtr', parseFloat(e.target.value))} className="w-full accent-tennis-blue" />
                </div>

                <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Specific Player (Optional)</label>
                    <input type="text" placeholder="Search by name..." value={params.name} onChange={(e) => handleChange('name', e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-tennis-blue focus:outline-none placeholder-slate-600"
                    />
                </div>

                <button
                    onClick={generateReport}
                    disabled={loading}
                    className="w-full mt-4 bg-gradient-to-r from-tennis-blue to-cyan-500 hover:from-cyan-500 hover:to-tennis-blue text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-tennis-blue/20 flex items-center justify-center gap-2"
                >
                    {loading ? <Loader2 className="animate-spin" /> : <Download />}
                    {loading ? 'Generating Report...' : 'Download Excel Report'}
                </button>
            </div>
        </div>
    );
};

export default ReportView;
