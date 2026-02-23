# CourtSide Analytics - Technical Documentation

## Project Overview

A full-stack tennis analytics platform that scrapes data from Universal Tennis Rating (UTR) API and other sources to provide comprehensive player statistics, match analysis, and AI-powered insights.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB UI (React)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  React 18   │  │ TailwindCSS │  │      Recharts           │  │
│  │    Vite     │  │   Axios     │  │    Lucide Icons         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   API V1    │  │   API V2    │  │    Authentication       │  │
│  │   (api.py)  │  │  (api_v2.py)│  │  JWT + Google OAuth     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Analysis  │  │  AI Engine  │  │    Scrapers             │  │
│  │   Engine    │  │  (Gemini)   │  │  UTR / Sackmann         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ SQLite
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER (SQLite)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  players │ │ matches  │ │ rankings │ │ utr_history      │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  users   │ │ user_fav │ │  news    │ │ tennis_abstract  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Web UI Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | React 18 | UI components and state management |
| Build Tool | Vite | Fast development and optimized builds |
| Styling | TailwindCSS | Utility-first CSS framework |
| Charts | Recharts | Data visualization |
| Icons | Lucide React | Icon library |
| HTTP Client | Axios | API communication |
| State | React Context | Authentication state |

### Directory Structure

```
web-ui/
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── AdvancedStats.jsx          # Advanced statistics display
│   │   ├── CollegeScout.jsx           # College roster browser
│   │   ├── LoginModal.jsx             # Authentication modal
│   │   ├── OngoingTournamentsView.jsx # Live tournament tracker
│   │   ├── StatsExplorer.jsx          # Statistical exploration
│   │   └── TennisAbstractElo.jsx      # ELO ratings display
│   │
│   ├── pages/                # Page-level components
│   │   └── AuthPages.jsx              # Login/register pages
│   │
│   ├── context/              # React contexts
│   │   └── AuthContext.jsx            # Authentication state
│   │
│   ├── App.jsx               # Main application component
│   └── main.jsx              # Application entry point
│
├── package.json              # Dependencies
└── vite.config.js            # Vite configuration
```

### Key Components

#### App.jsx
Main application component providing:
- Player search with autocomplete
- Player profile modal with tabbed interface
- Match history with filtering
- Player insights and statistics
- Social media links
- Favorites management

#### Authentication Flow
```
┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  Login   │────▶│  JWT Auth   │────▶│  Protected   │
│  Modal   │     │  / Google   │     │   Routes     │
└──────────┘     └─────────────┘     └──────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
              ┌──────────┐          ┌──────────┐          ┌──────────┐
              │ Favorites│          │  Social  │          │   AI     │
              │ Management          │  Media   │          │ Insights │
              └──────────┘          └──────────┘          └──────────┘
```

#### Data Flow
```
User Action ──▶ Component ──▶ API Call ──▶ FastAPI ──▶ Database
                                                  │
User Display ◀── Component ◀── Response ◀─────────┘
```

---

## Backend Process

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | FastAPI | REST API endpoints |
| Database | SQLite | Data persistence |
| Auth | JWT + OAuth2 | Authentication |
| AI | Google Gemini | AI-powered insights |
| Scraping | requests | HTTP client for data fetching |

### API Architecture

#### Authentication Endpoints

```
POST   /auth/register              # User registration
POST   /auth/login                 # User login (OAuth2)
POST   /auth/google                # Google OAuth login
GET    /users/me                   # Get current user
```

#### Player Endpoints

```
GET    /players                    # List players with filters
GET    /players/{player_id}        # Get player details
GET    /players/{player_id}/matches        # Get player matches
GET    /players/{player_id}/history        # Get UTR history
GET    /players/{player_id}/analysis       # Get player analysis
GET    /players/{player_id}/insights       # Get AI-generated insights
GET    /players/{player_id}/opponents      # Get opponent analysis
GET    /players/{player_id}/rankings       # Get historical rankings
POST   /players/{player_id}/game_plan      # Generate AI game plan
POST   /players/{player_id}/quarterly_review # Generate quarterly review
```

#### Statistics Endpoints

```
GET    /stats/records/consecutive-opening-wins
GET    /stats/records/oldest-winners
GET    /stats/featured
GET    /stats/streaks
GET    /stats/age-records
GET    /stats/category-leaders
GET    /stats/ace-leaders
GET    /stats/surface-leaders
GET    /stats/grand-slam-leaders
```

#### Tennis Abstract Integration

```
GET    /tennis-abstract/elo
GET    /tennis-abstract/elo/{player_name}
GET    /charting/matches
GET    /charting/players/{player_name}/stats
```

### Data Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Processing                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                           │
│  │   Scraper    │──▶ UTR API Authentication                 │
│  │   (scraper)  │──▶ Player Profile Fetching                 │
│  └──────────────┘──▶ Match Data Retrieval                   │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                           │
│  │    Parser    │──▶ Data Normalization                     │
│  └──────────────┘──▶ Field Mapping                          │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                           │
│  │   Database   │──▶ SQLite Storage                         │
│  │   (tennis_db)│──▶ Index Creation                         │
│  └──────────────┘──▶ Data Validation                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Analysis Engine

#### Core Analysis (analysis.py)
- Player win/loss statistics
- Surface performance analysis
- Quarterly progress tracking
- Head-to-head records

#### AI Analysis (analysis_ai.py)
- Game plan generation using Gemini
- Quarterly performance reviews
- Opponent analysis
- Pattern recognition

#### Advanced Statistics (advanced_stats.py)
- Clutch performance scores
- Upset rates
- Consistency metrics
- Pressure situation analysis

---

## Data Population

### Database Schema

#### Core Tables

```sql
-- Players table
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    player_id TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    country TEXT,
    utr_rating REAL,
    college TEXT,
    college_conf TEXT,
    graduation_year INTEGER,
    birthdate TEXT,
    gender TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Matches table
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    match_id TEXT UNIQUE,
    winner_id TEXT,
    loser_id TEXT,
    event_name TEXT,
    event_date DATE,
    score TEXT,
    surface TEXT,
    round TEXT,
    winner_sets INTEGER,
    loser_sets INTEGER,
    winner_games INTEGER,
    loser_games INTEGER,
    winner_aces INTEGER,
    winner_dfs INTEGER,
    loser_aces INTEGER,
    loser_dfs INTEGER,
    -- Additional match statistics...
    FOREIGN KEY (winner_id) REFERENCES players(player_id),
    FOREIGN KEY (loser_id) REFERENCES players(player_id)
);

-- UTR History table
CREATE TABLE utr_history (
    id INTEGER PRIMARY KEY,
    player_id TEXT,
    rating REAL,
    date DATE,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

-- Rankings table
CREATE TABLE rankings (
    id INTEGER PRIMARY KEY,
    player_id TEXT,
    ranking INTEGER,
    date DATE,
    tour TEXT,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE,
    hashed_password TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMP
);

-- User Favorites table
CREATE TABLE user_favorites (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    player_id TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

### Data Population Scripts

#### 1. UTR Data Population (scraper.py)

```python
# Authentication with UTR API
def login_utr(email, password):
    """Authenticate and obtain session token"""
    response = requests.post(
        'https://app.universaltennis.com/api/v1/auth/login',
        json={'email': email, 'password': password}
    )
    return response.json()['token']

# Fetch player profile
def fetch_player_profile(player_id):
    """Retrieve player information"""
    response = requests.get(
        f'https://app.universaltennis.com/api/v2/players/{player_id}',
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()

# Fetch player matches
def fetch_player_matches(player_id):
    """Retrieve match history"""
    response = requests.get(
        f'https://app.universaltennis.com/api/v2/players/{player_id}/matches',
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()['matches']
```

#### 2. Import Scripts

**import_players.py**
- Processes player data from various sources
- Normalizes field names and data types
- Handles duplicate detection
- Updates existing records

**import_matches.py**
- Imports match results from CSV/JSON
- Validates score formats
- Links matches to players
- Calculates derived statistics

**import_rankings.py**
- Imports ATP/WTA rankings
- Historical ranking data
- Tour categorization

**import_sackmann.py**
- Imports Sackmann tennis data
- Player profile enrichment
- ID mapping between systems

#### 3. Population Scripts

**populate_college.py**
```python
def populate_college_rosters():
    """
    Process college roster data:
    1. Load college roster files
    2. Match players to UTR database
    3. Update college affiliations
    4. Create college summary statistics
    """
    pass
```

**populate_college_rosters.py**
```python
def scrape_college_rosters():
    """
    Scrape college tennis rosters:
    1. Iterate through college list
    2. Fetch roster pages
    3. Parse player information
    4. Match with UTR profiles
    """
    pass
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   UTR API   │  │  Sackmann   │  │  College Rosters        │  │
│  │             │  │   Data      │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                 │
│         ▼                ▼                     ▼                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    SCRAPERS                              │   │
│  │  scraper.py / college_roster_scraper.py / import_*.py    │   │
│  └───────────────────────────┬──────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 DATA TRANSFORMATION                       │   │
│  │  • Normalization  • Validation  • Enrichment              │   │
│  └───────────────────────────┬──────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    DATABASE (SQLite)                      │   │
│  │  tennis_data.db                                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │   │
│  │  │ players │ │ matches │ │rankings │ │ users   │        │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Update Frequency

| Data Type | Source | Update Frequency | Script |
|-----------|--------|------------------|--------|
| Player Profiles | UTR API | Daily | scraper.py |
| Match Results | UTR API | Real-time | scraper.py |
| Rankings | ATP/WTA | Weekly | import_rankings.py |
| College Rosters | College Sites | Monthly | populate_college_rosters.py |
| Sackmann Data | Sackmann | On-demand | import_sackmann.py |

---

## Configuration

### Environment Variables

```bash
# UTR API Credentials
UTR_EMAIL=your_utr_email@example.com
UTR_PASSWORD=your_utr_password

# Security
SECRET_KEY=your_jwt_secret_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id

# AI Services
GEMINI_API_KEY=your_gemini_api_key
```

### Vite Proxy Configuration

```javascript
// web-ui/vite.config.js
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
}
```

---

## Development Workflow

### Starting Development

```bash
# 1. Start backend
cd C:\work\github\tennis
python api.py
# Server runs on http://localhost:8004

# 2. Start frontend (new terminal)
cd C:\work\github\tennis\web-ui
npm run dev
# Server runs on http://localhost:5173
```

### Database Operations

```bash
# View database schema
sqlite3 tennis_data.db ".schema"

# Check player count
sqlite3 tennis_data.db "SELECT COUNT(*) FROM players;"

# Check match count
sqlite3 tennis_data.db "SELECT COUNT(*) FROM matches;"
```

---

## API Response Examples

### Player Details

```json
{
  "player_id": "12345",
  "first_name": "John",
  "last_name": "Smith",
  "country": "USA",
  "utr_rating": 12.5,
  "college": "Stanford University",
  "college_conf": "Pac-12",
  "gender": "M",
  "birthdate": "2000-05-15",
  "matches": [...],
  "stats": {
    "total_matches": 150,
    "wins": 100,
    "losses": 50,
    "win_rate": 0.67,
    "surface_stats": {...}
  }
}
```

### AI Insights

```json
{
  "player_id": "12345",
  "insights": [
    {
      "category": "Strength",
      "description": "Strong serve with 65% first serve percentage"
    },
    {
      "category": "Improvement",
      "description": "Return game has improved 15% over last quarter"
    }
  ],
  "game_plan": {
    "strengths": [...],
    "weaknesses": [...],
    "recommended_strategy": "..."
  }
}
```

---

## Deployment Considerations

### Backend
- FastAPI can be deployed with Uvicorn
- Consider using PostgreSQL for production (instead of SQLite)
- Implement Redis for caching frequently accessed data
- Set up cron jobs for regular data updates

### Frontend
- Build with `npm run build`
- Deploy static files from `dist/` folder
- Configure reverse proxy (nginx) for API routing

### Security
- Use HTTPS in production
- Store secrets in environment variables
- Implement rate limiting on API endpoints
- Regular security updates for dependencies

---

## Key Files Reference

| Purpose | File Path |
|---------|-----------|
| Main API | `api.py`, `api_v2.py` |
| Database | `tennis_db.py` |
| Authentication | `auth.py` |
| Scraper | `scraper.py` |
| Analysis | `analysis.py`, `analysis_ai.py` |
| Main UI | `web-ui/src/App.jsx` |
| Auth Context | `web-ui/src/context/AuthContext.jsx` |
| Config | `config.py`, `.env` |

---

*Documentation generated on: 2026-02-14*
