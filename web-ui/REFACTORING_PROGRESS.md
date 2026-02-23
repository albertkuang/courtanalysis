# App.jsx Refactoring Progress

## Completed Extractions

### ✅ Shared Components (src/components/shared/)
- `SelectFilter.jsx` - Dropdown filter component
- `SortableHeader.jsx` - Table header with sort controls
- `StatBadge.jsx` - Stat display badge
- `index.js` - Barrel export

### ✅ Layout Components (src/components/layout/)
- `BrandHeader.jsx` - Application logo and user menu
- `NavMenu.jsx` - Desktop navigation menu with categories
- `index.js` - Barrel export

### ✅ Player Detail Components (src/components/player/)
- `PlayerHeader.jsx` - Player profile card with UTR and metrics
- `RatingChart.jsx` - UTR/Ranking history chart with filters
- `Charts.jsx` - WinLossDonut and ClutchRadar charts
- `AnalysisComponents.jsx` - AdvancedAnalysis, HeadToHeadSection, MatchLog
- `index.js` - Barrel export

### ✅ View Components (src/views/)
- `MatchHistoryView.jsx` - Full match history with filtering and expandable stats
- `PlayerInsightsView.jsx` - Player patterns and performance insights
- `OpponentsView.jsx` - Most encountered, dominators, dominated, rivals + SocialMediaSection
- `AIPlayerViews.jsx` - GamePlan, QuarterlyReview, RecruitView (AI-powered)

## Remaining Components in App.jsx

### Large AI Views (100+ lines each)
These follow the same pattern as AIPlayerViews.jsx but are very large:
- `TrainingFocusView` (lines 4039-4172)
- `TrajectoryView` (lines 4174-4350)
- `ScholarshipView` (lines 4352-4511)
- `MentalCoachView` (lines 4513-4678)

### Dashboard/Main Views
- `RecentMatchesView` (lines 1694-1881) - Match feed with filters
- `InsightsView` (lines 3671-3833) - Dashboard insights (Comeback Kings, Risers, etc.)
- `ReportView` (lines 3835-3955) - Excel export form
- `NewsView` (lines 1090-1188) - News feed with category filters
- `FavoritesView` (lines 998-1087) - User's favorite players
- `TournamentHistoryView` (lines 1191-1588) - Tournament browser with draw viewer
- `JuniorAnalysisView` (lines 1591-1691) - ITF Junior to Pro tracking
- `ComparisonView` (lines 4680-4869) - Side-by-side player comparison
- `HighlightsSection` (lines 925-996) - Recent champions and rising stars

### Smaller Components
- `SocialMediaSection` - Already extracted to OpponentsView.jsx
- `AdvancedAnalysis` (lines 2785-2850) - Already extracted to AnalysisComponents.jsx

## Next Steps

### Option 1: Full Extraction (Recommended for long-term)
1. Extract all remaining AI views to separate files or add to AIPlayerViews.jsx
2. Extract all dashboard views to individual files
3. Create a services/api.js for centralized API calls
4. Update App.jsx imports to use extracted components
5. Implement React Router for proper navigation

### Option 2: Minimal Refactoring (Quick Win)
1. Keep App.jsx as-is but import the already-extracted components
2. Update imports at top of App.jsx
3. Test that everything still works
4. Document for future refactoring

### Option 3: Hybrid Approach (Balanced)
1. Extract the most reusable views (RecentMatchesView, NewsView, TournamentHistoryView)
2. Leave AI views in App.jsx for now (they're player-specific and less reused)
3. Update imports
4. Plan React Router migration in separate task

## Current File Structure

```
web-ui/src/
├── components/
│   ├── shared/
│   │   ├── SelectFilter.jsx
│   │   ├── SortableHeader.jsx
│   │   ├── StatBadge.jsx
│   │   └── index.js
│   ├── layout/
│   │   ├── BrandHeader.jsx
│   │   ├── NavMenu.jsx
│   │   └── index.js
│   ├── player/
│   │   ├── PlayerHeader.jsx
│   │   ├── RatingChart.jsx
│   │   ├── Charts.jsx
│   │   ├── AnalysisComponents.jsx
│   │   └── index.js
│   ├── LoginModal.jsx
│   ├── OngoingTournamentsView.jsx
│   ├── CollegeScout.jsx
│   ├── AdvancedStats.jsx
│   ├── StatsExplorer.jsx
│   ├── TennisAbstractElo.jsx
│   └── SlamPointByPoint.jsx
├── views/
│   ├── MatchHistoryView.jsx
│   ├── PlayerInsightsView.jsx
│   ├── OpponentsView.jsx
│   └── AIPlayerViews.jsx
├── context/
│   ├── AuthContext.jsx
│   └── ToastContext.jsx
├── App.jsx (still 4872 lines - needs imports updated)
├── App.css
├── index.css
└── main.jsx
```

## Recommended Immediate Action

Update App.jsx imports to use the extracted components. This will:
- Reduce App.jsx complexity by ~500 lines
- Improve code organization
- Make it easier to continue refactoring later
- Maintain current functionality

Would you like me to:
1. Update App.jsx imports to use the extracted components?
2. Extract the remaining large views?
3. Create a React Router setup?
