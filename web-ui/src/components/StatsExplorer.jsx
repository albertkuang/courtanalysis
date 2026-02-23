import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Trophy, TrendingUp, Users, Calendar, MapPin, BarChart3,
  Loader2, RefreshCw, ChevronDown, Filter, Sparkles
} from 'lucide-react';

const API_BASE = 'http://localhost:8004';

// Stat Card Component for featured stats
const FeaturedStatCard = ({ stat }) => (
  <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 hover:border-tennis-blue/50 transition-all">
    <div className="flex items-center gap-2 mb-3">
      <span className="text-2xl">{stat.icon}</span>
      <div>
        <h3 className="text-white font-semibold">{stat.title}</h3>
        <p className="text-slate-400 text-xs">{stat.description}</p>
      </div>
    </div>
    <div className="space-y-2"> 
      {stat.data && stat.data.slice(0, 5).map((item, idx) => (
        <div key={idx} className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
          <span className="text-slate-300 text-sm">{item.player_name}</span>
          <span className="text-tennis-blue font-bold">{item.streak || item.stat_value || item.wins}</span>
        </div>
      ))}
    </div>
  </div>
);

// Data Table Component
const DataTable = ({ data, columns }) => {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400">
        No data available
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700">
            {columns.map((col) => (
              <th key={col.key} className="text-left py-3 px-4 text-xs font-medium text-slate-400 uppercase tracking-wider">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx} className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
              {columns.map((col) => (
                <td key={col.key} className="py-3 px-4 text-sm text-slate-300">
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Filter Bar Component
const FilterBar = ({ filters, onFilterChange }) => (
  <div className="flex flex-wrap gap-3 mb-6">
    {filters.map((filter) => (
      <div key={filter.key} className="flex items-center gap-2">
        <label className="text-xs text-slate-400">{filter.label}:</label>
        <select
          value={filter.value}
          onChange={(e) => onFilterChange(filter.key, e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-tennis-blue"
        >
          {filter.options.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
    ))}
  </div>
);

// Main Stats Explorer Component
const StatsExplorer = () => {
  const [activeCategory, setActiveCategory] = useState('featured');
  const [statsData, setStatsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filter states
  const [filters, setFilters] = useState({
    tour: 'wta',
    year: 2026,
    surface: 'Clay',
    minAge: 40
  });

  const categories = [
    { key: 'featured', label: 'Featured', icon: Sparkles },
    { key: 'streaks', label: 'Streaks', icon: TrendingUp },
    { key: 'age', label: 'Age Records', icon: Users },
    { key: 'wta500', label: 'WTA-500', icon: Trophy },
    { key: 'aces', label: 'Aces', icon: BarChart3 },
    { key: 'surface', label: 'Surface', icon: MapPin },
  ];

  // Fetch data based on active category
  useEffect(() => {
    fetchStats();
  }, [activeCategory, filters]);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);

    try {
      let endpoint = '';
      let params = {};

      switch (activeCategory) {
        case 'featured':
          endpoint = '/stats/featured';
          break;
        case 'streaks':
          endpoint = '/stats/streaks';
          params = { tour: filters.tour, level: 'PM', start_year: 2009 };
          break;
        case 'age':
          endpoint = '/stats/age-records';
          params = { tour: filters.tour, min_age: filters.minAge };
          break;
        case 'wta500':
          endpoint = '/stats/category-leaders';
          params = { tour: 'wta', start_date: '2025-01-01' };
          break;
        case 'aces':
          endpoint = '/stats/ace-leaders';
          params = { tournament: 'Australian Open', year: filters.year, tour: filters.tour };
          break;
        case 'surface':
          endpoint = '/stats/surface-leaders';
          params = { tour: filters.tour, surface: filters.surface };
          break;
        default:
          endpoint = '/stats/featured';
      }

      const response = await axios.get(`${API_BASE}${endpoint}`, { params });
      console.log('API Response:', response.data);
      setStatsData(response.data.data || []);
    } catch (err) {
      console.error('Error fetching stats:', err);
      setError('Failed to load statistics. Please try again.');
      setStatsData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Column definitions for different categories
  const getColumns = () => {
    switch (activeCategory) {
      case 'streaks':
        return [
          { key: 'player_name', label: 'Player' },
          { key: 'streak', label: 'Streak' },
          { key: 'category', label: 'Category' },
          { key: 'period', label: 'Period' },
        ];
      case 'age':
        return [
          { key: 'player_name', label: 'Player' },
          { key: 'age', label: 'Age' },
          { key: 'tournament', label: 'Tournament' },
          { key: 'year', label: 'Year' },
        ];
      case 'wta500':
        return [
          { key: 'player_name', label: 'Player' },
          { key: 'wins', label: 'Wins' },
          { key: 'total_matches', label: 'Matches' },
          { key: 'stat_value', label: 'Win %' },
        ];
      case 'aces':
        return [
          { key: 'player_name', label: 'Player' },
          { key: 'aces', label: 'Aces' },
          { key: 'matches', label: 'Matches' },
        ];
      case 'surface':
        return [
          { key: 'player_name', label: 'Player' },
          { key: 'wins', label: 'Wins' },
          { key: 'total_matches', label: 'Matches' },
          { key: 'stat_value', label: 'Win %' },
        ];
      default:
        return [];
    }
  };

  // Get filter options for current category
  const getFilters = () => {
    switch (activeCategory) {
      case 'streaks':
      case 'age':
        return [
          {
            key: 'tour',
            label: 'Tour',
            value: filters.tour,
            options: [
              { value: 'wta', label: 'WTA' },
              { value: 'atp', label: 'ATP' },
            ]
          }
        ];
      case 'aces':
        return [
          {
            key: 'tour',
            label: 'Tour',
            value: filters.tour,
            options: [
              { value: 'wta', label: 'WTA' },
              { value: 'atp', label: 'ATP' },
            ]
          },
          {
            key: 'year',
            label: 'Year',
            value: filters.year,
            options: [2026, 2025, 2024, 2023, 2022].map(y => ({ value: y, label: y.toString() }))
          }
        ];
      case 'surface':
        return [
          {
            key: 'tour',
            label: 'Tour',
            value: filters.tour,
            options: [
              { value: 'wta', label: 'WTA' },
              { value: 'atp', label: 'ATP' },
            ]
          },
          {
            key: 'surface',
            label: 'Surface',
            value: filters.surface,
            options: [
              { value: 'Clay', label: 'Clay' },
              { value: 'Hard', label: 'Hard' },
              { value: 'Grass', label: 'Grass' },
            ]
          }
        ];
      default:
        return [];
    }
  };

  // Check if featured data (nested structure)
  const isFeaturedData = activeCategory === 'featured' && statsData.length > 0 && statsData[0].data;

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <BarChart3 className="w-7 h-7 text-tennis-blue" />
              Stats Explorer
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Explore tennis statistics and records across tours and tournaments
            </p>
          </div>
          <button
            onClick={fetchStats}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-tennis-blue/10 text-tennis-blue rounded-lg hover:bg-tennis-blue/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Category Tabs */}
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat.key}
              onClick={() => setActiveCategory(cat.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeCategory === cat.key
                  ? 'bg-tennis-blue text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              <cat.icon className="w-4 h-4" />
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Filters */}
        {getFilters().length > 0 && (
          <FilterBar filters={getFilters()} onFilterChange={handleFilterChange} />
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-tennis-blue animate-spin" />
            <span className="ml-3 text-slate-400">Loading statistics...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-4 text-rose-400 text-center">
            {error}
          </div>
        )}

        {/* Data Display */}
        {!loading && !error && (
          <>
            {isFeaturedData ? (
              /* Featured Stats - Card Grid */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {statsData.map((stat, idx) => (
                  <FeaturedStatCard key={idx} stat={stat} />
                ))}
              </div>
            ) : (
              /* Table View for other categories */
              <div className="bg-slate-800/30 border border-slate-700 rounded-xl overflow-hidden">
                <DataTable data={statsData} columns={getColumns()} />
              </div>
            )}

            {/* Empty State */}
            {statsData.length === 0 && !loading && (
              <div className="text-center py-12">
                <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400">No statistics available for this category</p>
                <p className="text-slate-500 text-sm mt-1">
                  Try adjusting your filters or check back later
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default StatsExplorer;
