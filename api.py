
from fastapi import FastAPI, HTTPException, Query, status, Depends
from fastapi.middleware.cors import CORSMiddleware
import advanced_stats
import tennis_db
import analysis
import analysis_ai
import insights_generator
import sqlite3
from typing import List, Optional
import analysis_advanced
import college_service

app = FastAPI(title="CourtSide Analytics API", description="API for Tennis Player Data")

from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

load_dotenv()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTHENTICATION SETUP ---
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
import auth
from datetime import datetime, timedelta

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str = None

class GoogleLogin(BaseModel):
    token: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check existing
    c.execute("SELECT * FROM users WHERE email = ?", (user.email,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = auth.get_password_hash(user.password)
    
    try:
        c.execute("INSERT INTO users (email, hashed_password, full_name) VALUES (?, ?, ?)", 
                  (user.email, hashed_pw, user.full_name))
        conn.commit()
        user_id = c.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    
    conn.close()
    
    # Create Token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "id": user_id, "role": "user"}, expires_delta=access_token_expires
    )
    
    # MOCK EMAIL
    print(f"--- [MOCK EMAIL SERVICE] ---")
    print(f"To: {user.email}")
    print(f"Subject: Welcome to CourtSide! Please verify your email.")
    print(f"Link: http://localhost:5173/verify-email?token={access_token}") # In real app, use separate verification token
    print(f"----------------------------")
    
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user.email, "id": user_id, "name": user.full_name}}

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (form_data.username,))
    user = c.fetchone()
    conn.close()
    
    if not user or not auth.verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user['email'], "id": user['id'], "role": "user"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user['email'], "id": user['id'], "name": user['full_name']}}

@app.post("/auth/google", response_model=Token)
async def google_login(login_data: GoogleLogin):
    # Verify Google Token
    google_user = await auth.verify_google_token(login_data.token)
    email = google_user['email']
    name = google_user.get('name', '')
    google_id = google_user['sub']
    avatar = google_user.get('picture', '')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    
    if not user:
        # Create new user via Google
        c.execute("INSERT INTO users (email, full_name, google_id, avatar_url, is_verified) VALUES (?, ?, ?, ?, 1)",
                  (email, name, google_id, avatar))
        conn.commit()
        user_id = c.lastrowid
        user_data = {"email": email, "id": user_id, "name": name, "avatar": avatar}
    else:
        # Update existing user with google info if needed
        user_id = user['id']
        if not user['google_id']:
            c.execute("UPDATE users SET google_id = ?, avatar_url = ?, is_verified = 1 WHERE id = ?", (google_id, avatar, user_id))
            conn.commit()
        user_data = {"email": email, "id": user_id, "name": user['full_name'], "avatar": user['avatar_url']}
        
    conn.close()
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": email, "id": user_id, "role": "user"}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user_data}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(auth.get_current_user)):
    return current_user


def get_db_connection():
    conn = tennis_db.get_connection()
    conn.row_factory = sqlite3.Row # Access columns by name
    # Performance Optimization PRAGMAs
    try:
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -512000") # 512MB
        conn.execute("PRAGMA mmap_size = 3000000000") # 3GB
    except:
        pass
    return conn

@app.get("/")
def read_root():
    return {"status": "active", "message": "Welcome to CourtSide Analytics API"}

@app.get("/countries")
def get_countries():
    """Get all distinct countries from the players table, ordered alphabetically."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT country FROM players WHERE country IS NOT NULL AND country != '' AND country != '-' ORDER BY country")
    countries = [row['country'] for row in c.fetchall()]
    conn.close()
    return {"count": len(countries), "data": countries}

@app.get("/players")
def get_players(
    country: str = Query('ALL', description="Country code or ALL"),
    gender: str = Query(None, description="M or F"),
    category: str = Query('junior', description="junior, adult, or college"),
    division: str = Query('ALL', description="D1, D2, D3 or ALL"),
    search: str = Query(None, description="Search by name"),
    limit: int = Query(5000, description="Limit results")
):
    conn = get_db_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM players WHERE 1=1"
    params = []
    
    # 1. Basic Filters (Always Apply)
    if country != 'ALL':
        query += " AND country = ?"
        params.append(country)
    
    if gender:
        query += " AND gender = ?"
        params.append(gender)

    # 2. Category Logic (Optimized via materialized column)
    if category in ['junior', 'college', 'adult']:
        query += " AND scout_category = ?"
        params.append(category)
        if category == 'college' and division != 'ALL':
            query += " AND division = ?"
            params.append(division.upper())

    # 3. Search (Additional Filter)
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")
    
    query += " ORDER BY utr_singles DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, tuple(params))
    players = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return {"count": len(players), "data": players}

@app.get("/stats/coverage")
def get_coverage(
    country: str = Query('ALL', description="Country code or ALL"),
    gender: str = Query(None, description="M or F"),
    category: str = Query('junior', description="junior, adult, or college"),
    division: str = Query('ALL', description="D1, D2, D3 or ALL")
):
    conn = get_db_connection()
    c = conn.cursor()

    # Base WHERE clause construction (replicated from get_players)
    where_clause = "1=1"
    params = []

    # 1. Basic Filters
    if country != 'ALL':
        where_clause += " AND country = ?"
        params.append(country)
    
    if gender:
        where_clause += " AND gender = ?"
        params.append(gender)

    # 2. Category Logic (Optimized)
    if category in ['junior', 'college', 'adult']:
        where_clause += " AND scout_category = ?"
        params.append(category)
        if category == 'college' and division != 'ALL':
            where_clause += " AND division = ?"
            params.append(division.upper())

    # 1. Count Players and Match Totals from pre-aggregated data
    # This is MUCH faster than scanning the matches table
    stats_query = f"""
        SELECT COUNT(*), SUM(match_count), MIN(latest_match_date), MAX(latest_match_date)
        FROM players 
        WHERE {where_clause}
    """
    c.execute(stats_query, tuple(params))
    stats_row = c.fetchone()
    
    total_players = stats_row[0] or 0
    total_matches = stats_row[1] or 0
    min_date = stats_row[2]
    max_date = stats_row[3]

    min_year = min_date[:4] if min_date else "N/A"
    max_year = max_date[:4] if max_date else "N/A"
    years_range = f"{min_year}-{max_year}" if min_year != "N/A" else "N/A"

    conn.close()

    return {
        "total_players": total_players,
        "total_matches": total_matches,
        "years": years_range
    }

@app.get("/players/{player_id}")
def get_player_detail(player_id: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Player not found")
    return dict(row)

@app.get("/players/{player_id}/matches")
def get_player_matches(player_id: str):
    conn = get_db_connection()
    # Use existing helper from tennis_db but we need row_factory logic if re-implementing manually
    # or just use tennis_db helper if it returns dicts (it does)
    matches = tennis_db.get_player_matches(conn, player_id)
    conn.close()
    return {"count": len(matches), "data": matches}

@app.get("/players/{player_id}/history")
def get_player_history(player_id: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM utr_history WHERE player_id = ? ORDER BY date ASC", (player_id,))
    history = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"count": len(history), "data": history}

@app.get("/players/{player_id}/insights")
def get_player_insights(player_id: str, years: int = 5):
    """Get interesting patterns and insights for a player."""
    insights = insights_generator.get_player_insights(player_id, years)
    return {"count": len(insights), "data": insights}

@app.get("/players/{player_id}/analysis")
@app.get("/players/{player_id}/advanced")
def get_player_analysis(player_id: str):
    result = analysis.get_player_analysis(player_id)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"status": "success", "data": result}
    
@app.post("/players/{player_id}/game_plan")
def create_game_plan(player_id: str):
    # Route to Real AI (which falls back to mock if no key)
    result = analysis_ai.generate_game_plan_real(player_id)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"status": "success", "data": result}
    
@app.post("/players/{player_id}/quarterly_review")
def create_quarterly_review(player_id: str):
    result = analysis_ai.generate_quarterly_review(player_id)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found or Analysis failed")
    return {"status": "success", "data": result}
    
class MatchSimRequest(BaseModel):
    p1_id: str
    p2_id: str

@app.post("/simulate_match")
def simulate_match_endpoint(req: MatchSimRequest):
    result = analysis_ai.simulate_match_ai(req.p1_id, req.p2_id)
    if not result:
        raise HTTPException(status_code=400, detail="Simulation failed")
    return {"status": "success", "data": result}

@app.post("/players/{player_id}/recruiting_brief")
def create_recruiting_brief(player_id: str):
    result = analysis_ai.generate_recruiting_email(player_id)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found or Analysis failed")
    return {"status": "success", "data": result}

@app.post("/players/{player_id}/training_focus")
def create_training_focus(player_id: str, body: dict = None):
    user_context = body.get("user_context", "") if body else ""
    result = analysis_ai.generate_training_focus(player_id, user_context)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found or Analysis failed")
    return {"status": "success", "data": result}

@app.post("/players/{player_id}/trajectory")
def create_trajectory_prediction(player_id: str, body: dict = None):
    user_context = body.get("user_context", "") if body else ""
    result = analysis_ai.generate_trajectory_prediction(player_id, user_context)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found or Analysis failed")
    return {"status": "success", "data": result}

@app.post("/players/{player_id}/scholarship")
def create_scholarship_estimate(player_id: str):
    result = analysis_ai.generate_scholarship_estimate(player_id)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found or Analysis failed")
    return {"status": "success", "data": result}

@app.post("/players/{player_id}/mental_coach")
def create_mental_coach(player_id: str, body: dict = None):
    user_context = body.get("user_context", "") if body else ""
    result = analysis_ai.generate_mental_coach(player_id, user_context)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found or Analysis failed")
    return {"status": "success", "data": result}

# --- SOCIAL MEDIA ENDPOINTS ---
class SocialMediaLink(BaseModel):
    platform: str
    url: str
    username: str = None
    verified: bool = False

@app.get("/players/{player_id}/opponents")
def get_player_opponents(player_id: str):
    """Get opponent analysis for a player: most encountered, always lose to, always win against, closest matchups."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get all matches for this player
    query = """
        SELECT m.*, 
               w.name as winner_name, w.utr_singles as winner_utr_current, w.country as winner_country,
               l.name as loser_name, l.utr_singles as loser_utr_current, l.country as loser_country
        FROM matches m
        LEFT JOIN players w ON m.winner_id = w.player_id
        LEFT JOIN players l ON m.loser_id = l.player_id
        WHERE m.winner_id = ? OR m.loser_id = ?
        ORDER BY m.date DESC
    """
    c.execute(query, (player_id, player_id))
    matches = [dict(row) for row in c.fetchall()]
    conn.close()
    
    if not matches:
        return {"data": {"most_encountered": [], "always_lose": [], "always_win": [], "closest_matchups": []}}
    
    # Aggregate by opponent
    opponent_stats = {}
    for m in matches:
        is_winner = str(m['winner_id']) == str(player_id)
        if is_winner:
            opp_id = m['loser_id']
            opp_name = m['loser_name']
            opp_utr = m['loser_utr_current']
            opp_country = m['loser_country']
        else:
            opp_id = m['winner_id']
            opp_name = m['winner_name']
            opp_utr = m['winner_utr_current']
            opp_country = m['winner_country']
        
        if not opp_id:
            continue
            
        if opp_id not in opponent_stats:
            opponent_stats[opp_id] = {
                "player_id": opp_id,
                "name": opp_name or "Unknown",
                "utr_singles": opp_utr,
                "country": opp_country,
                "wins": 0,
                "losses": 0,
                "total": 0,
                "last_match": None,
                "matches": []
            }
        
        opponent_stats[opp_id]['total'] += 1
        if is_winner:
            opponent_stats[opp_id]['wins'] += 1
        else:
            opponent_stats[opp_id]['losses'] += 1
        
        # Track last match
        if not opponent_stats[opp_id]['last_match'] or m['date'] > opponent_stats[opp_id]['last_match']:
            opponent_stats[opp_id]['last_match'] = m['date']
        
        # Add match details (limit to 5 most recent per opponent)
        if len(opponent_stats[opp_id]['matches']) < 5:
            opponent_stats[opp_id]['matches'].append({
                "date": m['date'],
                "score": m['score'],
                "tournament": m['tournament'],
                "won": is_winner
            })
    
    opponents_list = list(opponent_stats.values())
    
    # Most Encountered (top 5 by total matches)
    most_encountered = sorted(opponents_list, key=lambda x: x['total'], reverse=True)[:5]
    
    # Always Lose (100% loss rate, 3+ matches)
    always_lose = sorted(
        [o for o in opponents_list if o['losses'] >= 3 and o['wins'] == 0],
        key=lambda x: x['total'], reverse=True
    )[:5]
    
    # Always Win (100% win rate, 3+ matches)
    always_win = sorted(
        [o for o in opponents_list if o['wins'] >= 3 and o['losses'] == 0],
        key=lambda x: x['total'], reverse=True
    )[:5]
    
    # Closest Matchups (4+ matches, closest to 50/50 record)
    def closeness_score(o):
        if o['total'] == 0:
            return float('inf')
        win_rate = o['wins'] / o['total']
        return abs(0.5 - win_rate)
    
    eligible_for_close = [o for o in opponents_list if o['total'] >= 4]
    closest_matchups = sorted(eligible_for_close, key=closeness_score)[:5]
    
    return {
        "data": {
            "most_encountered": most_encountered,
            "always_lose": always_lose,
            "always_win": always_win,
            "closest_matchups": closest_matchups
        }
    }

@app.get("/players/{player_id}/social_media")
def get_player_social_media(player_id: str):
    """Get all social media links for a player."""
    conn = get_db_connection()
    links = tennis_db.get_player_social_media(conn, player_id)
    conn.close()
    return {"count": len(links), "data": links}

@app.post("/players/{player_id}/social_media")
def save_player_social_media(player_id: str, link: SocialMediaLink):
    """Save or update a social media link for a player."""
    conn = get_db_connection()
    tennis_db.save_social_media(
        conn,
        player_id,
        link.platform,
        link.url,
        link.username,
        link.verified
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Saved {link.platform} link for player {player_id}"}

@app.delete("/players/{player_id}/social_media/{platform}")
def delete_player_social_media(player_id: str, platform: str):
    """Delete a social media link for a player."""
    conn = get_db_connection()
    tennis_db.delete_player_social_media(conn, player_id, platform)
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Deleted {platform} link for player {player_id}"}

@app.get("/highlights/recent_winners")
def get_recent_winners():
    """Get recent tournament winners (Matches where round is 'Final')."""
    conn = get_db_connection()
    c = conn.cursor()
    # Find matches that look like Finals
    # Note: 'Final' or 'F' or 'Championship' might be used depending on source
    query = """
        SELECT m.date, m.tournament, m.score, m.winner_id, p.name as winner_name, p.utr_singles as winner_utr
        FROM matches m
        JOIN players p ON m.winner_id = p.player_id
        WHERE (m.round LIKE '%Final%' OR m.round = 'F') 
          AND m.round NOT LIKE '%Quarter%' 
          AND m.round NOT LIKE '%Semi%'
          AND m.date IS NOT NULL
        ORDER BY m.date DESC
        LIMIT 5
    """
    c.execute(query)
    winners = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"count": len(winners), "data": winners}

@app.get("/highlights/improved_juniors")
def get_improved_juniors():
    """Get top 5 juniors with highest UTR improvement year-over-year."""
    conn = get_db_connection()
    c = conn.cursor()
    # Filter for Juniors (Age < 19 or AgeGroup U18/etc) with positive growth
    query = """
        SELECT player_id, name, country, utr_singles, year_delta, age, gender
        FROM players
        WHERE year_delta > 0 
          AND (
            (age IS NOT NULL AND age <= 18) OR 
            (age IS NULL AND age_group LIKE 'U%')
          )
        ORDER BY year_delta DESC
        LIMIT 10
    """
    c.execute(query)
    improved = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"count": len(improved), "data": improved}

@app.get("/juniors/finalists")
def get_junior_finalists(limit: int = Query(100, description="Max results")):
    """Get historical ITF Junior finalists (last 10 years)."""
    conn = get_db_connection()
    c = conn.cursor()
    query = """
        SELECT * FROM junior_finalists 
        ORDER BY date DESC 
        LIMIT ?
    """
    c.execute(query, (limit,))
    finalists = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"count": len(finalists), "data": finalists}

@app.get("/news")
def get_news(limit: int = 50, category: str = None):
    conn = get_db_connection()
    c = conn.cursor()
    query = "SELECT * FROM news_items"
    params = []
    
    if category:
        query += " WHERE category = ?"
        params.append(category)
        
    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, tuple(params))
    news = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"count": len(news), "data": news}

@app.post("/news/refresh")
def refresh_news():
    import news_service
    # Run fetchers (this might vary in duration, usually better in background task)
    news_service.generate_internal_news()
    news_service.fetch_external_news()
    news_service.fetch_favorites_news()
    return {"status": "success", "message": "News feed refreshed"}

@app.get("/tournaments")
def get_tournaments():
    conn = get_db_connection()
    c = conn.cursor()
    # Aggregate tournaments from matches table
    query = """
        SELECT tournament, COUNT(*) as match_count, MAX(date) as last_date 
        FROM matches 
        WHERE tournament IS NOT NULL 
        GROUP BY tournament 
        ORDER BY last_date DESC 
        LIMIT 100
    """
    c.execute(query)
    tournaments = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"count": len(tournaments), "data": tournaments}

def standardize_name(name, level, source):
    """Standardize tournament name based on level and source."""
    if not name or not level:
        return name
        
    name = name.strip()
    source = source or ''
    is_female = 'wta' in source.lower() or 'women' in source.lower()
    
    # Cleaning Logic
    import re
    # Remove common suffixes like " 15K", " $25,000", " $15K", " CH"
    name = re.sub(r'\s+\$?\d+(?:,\d+)?K?$', '', name, flags=re.IGNORECASE)
    if level == 'C' and name.lower().endswith(' ch'):
        name = name[:-3]
    name = name.strip()
    
    # Standardization Logic
    final_name = name
    if level in ['15', '25', '35', '50', '60', '75', '80', '100']:
        prefix = 'W' if is_female else 'M'
        target_prefix = f"{prefix}{level}"
        
        if not name.startswith(target_prefix):
            # Clean up suffix redundancy if strict mismatch
            if name.endswith(f" {prefix}{level}"):
                name = name[:-len(f" {prefix}{level}")]
            elif name.endswith(f" {level}"):
                name = name[:-len(f" {level}")]
                
            final_name = f"{target_prefix} {name}"
    
    elif level == 'C':
        if not name.lower().startswith('challenger'):
            final_name = f"Challenger {name}"
            
    return final_name

@app.get("/tournaments/list")
def get_tournament_list(search: str = Query(None, description="Search tournament name")):
    """Get list of unique tournament names."""
    conn = get_db_connection()
    c = conn.cursor()
    
    query = """
        SELECT DISTINCT m.tournament, m.tourney_level, m.source
        FROM matches m
        WHERE m.tournament IS NOT NULL 
          AND m.tournament != ''
          AND m.round = 'F'
          -- Explicitly filter for valid professional levels
          AND m.tourney_level IN ('G', 'F', 'M', 'PM', 'A', 'P', 'C', '15', '25', '35', '50', '60', '75', '80', '100')
          -- Double check to exclude UTR sources specifically if they sneak in
          AND (m.source IS NULL OR m.source NOT LIKE '%UTR%')
        ORDER BY m.tournament ASC
    """
    
    c.execute(query)
    
    # Process and Standardize Names
    raw_tournaments = [dict(row) for row in c.fetchall()]
    standardized_set = set()
    
    for t in raw_tournaments:
        final_name = standardize_name(t['tournament'], t['tourney_level'], t['source'])
        if final_name:
             standardized_set.add(final_name)
        
    conn.close()
    
    # Sort alphabetically
    tournaments = sorted(list(standardized_set))
    
    return {"count": len(tournaments), "data": tournaments}

@app.get("/tournaments/history")
def get_tournament_history(
    category: str = Query('all', description="grand_slam, masters, tour, challenger, futures, all"),
    gender: str = Query('all', description="M, F, or all"),
    year: int = Query(None, description="Filter by year"),
    search: str = Query(None, description="Search tournament name"),
    limit: int = Query(100, description="Max results")
):
    """Get tournament history with finals results."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Map category to tourney_level values
    category_map = {
        'grand_slam': ['G'],
        'masters': ['M', 'PM'],
        'tour': ['A', 'P'],
        'challenger': ['C'],
        'futures': ['10', '15', '25', '35', '40', '50', '60', '75', '80', '100', 'S', 'I'],
    }
    
    # Build query for finals
    query = """
        SELECT 
            m.tournament,
            m.date,
            m.surface,
            m.tourney_level,
            m.score,
            m.winner_id,
            m.loser_id,
            w.name as winner_name,
            l.name as finalist_name,
            m.source
        FROM matches m
        LEFT JOIN players w ON m.winner_id = w.player_id
        LEFT JOIN players l ON m.loser_id = l.player_id
        WHERE m.round = 'F'
        AND m.tourney_level IS NOT NULL
    """
    params = []
    
    # Category filter
    if category != 'all' and category in category_map:
        placeholders = ','.join(['?' for _ in category_map[category]])
        query += f" AND m.tourney_level IN ({placeholders})"
        params.extend(category_map[category])
    
    # Gender filter (based on source)
    if gender == 'M':
        query += " AND (m.source LIKE 'sackmann-atp%')"
    elif gender == 'F':
        query += " AND (m.source LIKE 'sackmann-wta%')"
    
    # Year filter
    if year:
        query += " AND strftime('%Y', m.date) = ?"
        params.append(str(year))
    
    # Search filter with Standardization Parsing
    if search:
        import re
        # Check for standardized ITF format: M15/W15 Name
        itf_match = re.match(r'^([MW])(\d+)\s+(.+)$', search)
        
        # Check for standardized Challenger format: Challenger Name
        challenger_match = re.match(r'^Challenger\s+(.+)$', search, re.IGNORECASE)
        
        if itf_match:
            # User selected "M15 Monastir"
            # Filter matches by Level=15 AND (Source implied Gender) AND Name LIKE %Monastir%
            gender_code = itf_match.group(1) # M or W
            level_code = itf_match.group(2)  # 15, 25...
            name_part = itf_match.group(3)
            
            query += " AND m.tourney_level = ?"
            params.append(level_code)
            
            if gender_code == 'M':
                query += " AND (m.source LIKE 'sackmann-atp%' OR m.source NOT LIKE 'sackmann-wta%')" # Default to M if unsure?
            else:
                query += " AND (m.source LIKE 'sackmann-wta%')"
                
            query += " AND m.tournament LIKE ?"
            params.append(f"%{name_part}%")
            
        elif challenger_match:
            # User selected "Challenger Phoenix"
            name_part = challenger_match.group(1)
            query += " AND m.tourney_level = 'C'"
            query += " AND m.tournament LIKE ?"
            params.append(f"%{name_part}%")
            
            query += " AND m.tournament LIKE ?"
            params.append(f"%{name_part}%")
            
        else:
            # Standard search
            # Special Logic for Canadian Open (Toronto/Montreal/Canada Masters)
            if 'toronto' in search.lower() or 'montreal' in search.lower():
                 query += " AND (m.tournament LIKE ? OR m.tournament = 'Canada Masters')"
                 params.append(f"%{search}%")
            else:
                 query += " AND m.tournament LIKE ?"
                 params.append(f"%{search}%")
    
    query += " ORDER BY m.date DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    
    tournaments = []
    for row in c.fetchall():
        row_dict = dict(row)
        
        # Standardize the name here too!
        row_dict['tournament'] = standardize_name(
            row_dict['tournament'], 
            row_dict.get('tourney_level'), 
            row_dict.get('source')
        )
        
        # Generate a unique tournament ID
        date_str = row_dict['date'][:10] if row_dict['date'] else ''
        tourney_name = row_dict['tournament'] or ''
        row_dict['id'] = f"{date_str}_{tourney_name.replace(' ', '_').lower()}"
        
        # Map tourney_level to category
        level = row_dict.get('tourney_level', '')
        if level == 'G':
            row_dict['category'] = 'Grand Slam'
        elif level in ['M', 'PM']:
            row_dict['category'] = 'Masters'
        elif level in ['A', 'P']:
            row_dict['category'] = 'ATP/WTA Tour'
        elif level == 'C':
            row_dict['category'] = 'Challenger'
        else:
            row_dict['category'] = 'ITF/Futures'
        
        tournaments.append(row_dict)
    
    conn.close()
    return {"count": len(tournaments), "data": tournaments}

@app.get("/tournaments/{tournament_name}/draw")
def get_tournament_draw(
    tournament_name: str,
    year: int = Query(None, description="Year of the tournament")
):
    """Get all matches from a specific tournament."""
    conn = get_db_connection()
    c = conn.cursor()
    
    query = """
        SELECT 
            m.round,
            m.date,
            m.score,
            m.winner_id,
            m.loser_id,
            w.name as winner_name,
            l.name as loser_name,
            m.surface,
            m.minutes,
            m.w_ace,
            m.l_ace
        FROM matches m
        LEFT JOIN players w ON m.winner_id = w.player_id
        LEFT JOIN players l ON m.loser_id = l.player_id
        WHERE m.tournament = ?
    """
    params = [tournament_name]
    
    if year:
        query += " AND strftime('%Y', m.date) = ?"
        params.append(str(year))
    
    # Order by round (F, SF, QF, R16, R32, etc)
    query += """
        ORDER BY 
            CASE m.round 
                WHEN 'F' THEN 1 
                WHEN 'SF' THEN 2 
                WHEN 'QF' THEN 3 
                WHEN 'R16' THEN 4 
                WHEN 'R32' THEN 5 
                WHEN 'R64' THEN 6 
                WHEN 'R128' THEN 7 
                WHEN 'RR' THEN 8
                ELSE 9 
            END,
            m.date DESC
    """
    
    c.execute(query, params)
    matches = [dict(row) for row in c.fetchall()]
    conn.close()
    
    # Group by round
    rounds = {}
    for m in matches:
        rd = m.get('round', 'Other')
        if rd not in rounds:
            rounds[rd] = []
        rounds[rd].append(m)
    
    return {"tournament": tournament_name, "year": year, "rounds": rounds, "total_matches": len(matches)}

@app.get("/tournaments/ongoing")
def get_ongoing_tournaments():
    print("Fetching ongoing tournaments...")
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get tournaments active in last 7 days
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # 1. Get List of Tournaments
    query_t = """
        SELECT tournament, MIN(date) as start_date, MAX(date) as end_date, COUNT(*) as count
        FROM matches
        WHERE date >= ? AND tournament IS NOT NULL
        GROUP BY tournament
        ORDER BY end_date DESC, count DESC
        LIMIT 20
    """
    c.execute(query_t, (cutoff,))
    tournaments = [dict(row) for row in c.fetchall()]
    
    # Helper function to determine tournament type priority
    def get_tournament_priority(name):
        name_lower = name.lower() if name else ""
        # WTA/ATP (highest priority)
        if 'wta' in name_lower or 'atp' in name_lower or 'grand slam' in name_lower:
            return 0
        # ITF (non-junior)
        if 'itf' in name_lower and 'junior' not in name_lower and 'jr' not in name_lower:
            return 1
        # ITF Junior
        if 'itf' in name_lower and ('junior' in name_lower or 'jr' in name_lower):
            return 2
        # College/NCAA
        if 'college' in name_lower or 'ncaa' in name_lower or 'university' in name_lower or 'collegiate' in name_lower:
            return 3
        # Other
        return 4
    
    results = []
    for t in tournaments:
        t_name = t['tournament']
        # 2. Get Matches for each - include player IDs for profile linking
        query_m = """
            SELECT m.match_id, m.date, m.score, 
                   m.winner_id, w.name as winner, w.utr_singles as winner_utr,
                   m.loser_id, l.name as loser, l.utr_singles as loser_utr
            FROM matches m
            JOIN players w ON m.winner_id = w.player_id
            JOIN players l ON m.loser_id = l.player_id
            WHERE m.tournament = ? AND m.date >= ?
            ORDER BY m.date DESC, m.match_id DESC
            LIMIT 50
        """
        c.execute(query_m, (t_name, cutoff))
        matches = [dict(row) for row in c.fetchall()]
        
        results.append({
            "name": t_name,
            "start_date": t['start_date'],
            "last_activity": t['end_date'],
            "match_count": t['count'],
            "matches": matches,
            "priority": get_tournament_priority(t_name)
        })
    
    # Sort by priority (WTA/ATP first, then ITF, ITF Junior, College, Other)
    from functools import cmp_to_key
    def compare_tournaments(a, b):
        if a['priority'] != b['priority']:
            return a['priority'] - b['priority']
        # Same priority: sort by last_activity descending
        if a['last_activity'] > b['last_activity']:
            return -1
        elif a['last_activity'] < b['last_activity']:
            return 1
        return 0
    
    results.sort(key=cmp_to_key(compare_tournaments))
        
    conn.close()
    return {"count": len(results), "data": results}

@app.get("/export")
def export_excel(
    country: str = Query('ALL'),
    category: str = Query('junior'),
    gender: str = Query(None),
    count: int = Query(100),
    name: str = Query(None),
    min_utr: float = Query(0.0)
):
    from fastapi.responses import FileResponse
    from export_players_excel import generate_excel_report
    import os
    
    # Generate the report
    filepath = generate_excel_report(country, category, gender, count, name, min_utr, output_dir='output')
    
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="No data found to export")
        
    return FileResponse(filepath, filename=os.path.basename(filepath), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Mount Static Files (Frontend) if built - MUST BE LAST to not intercept API routes



# --- RECENT MATCHES ENDPOINT ---

@app.get("/matches/recent")
def get_recent_matches_endpoint(
    country: str = Query(None),
    category: str = Query(None),
    gender: str = Query(None),
    days: int = Query(10, description="Days to look back")
):
    conn = get_db_connection()
    c = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    with open("api_debug.log", "a") as f:
        f.write(f"[{datetime.now()}] params: country={country}, category={category}, gender={gender}, days={days}. Cutoff={cutoff_date}\n")

    # Fetch recent matches with player details
    query = """
        SELECT m.*, 
               w.name as winner_name, w.country as winner_country, w.utr_singles as winner_utr, 
               w.age as winner_age, w.age_group as winner_age_group, w.gender as winner_gender,
               l.name as loser_name, l.country as loser_country, l.utr_singles as loser_utr,
               l.age as loser_age, l.age_group as loser_age_group, l.gender as loser_gender
        FROM matches m
        JOIN players w ON m.winner_id = w.player_id
        JOIN players l ON m.loser_id = l.player_id
        WHERE m.date >= ?
    """
    c.execute(query, (cutoff_date,))
    all_matches = [dict(row) for row in c.fetchall()]
    conn.close()

    with open("api_debug.log", "a") as f:
        f.write(f"[{datetime.now()}] Found {len(all_matches)} matches before filter.\n")

    # Helper for filtering
    def is_match_criteria(p_country, p_age, p_age_group, p_gender):
        try:
            # Country
            if country and country != 'ALL' and p_country != country:
                return False
            # Gender
            if gender and p_gender != gender:
                return False
            
            # Safe numeric conversion for age
            age_val = None
            if p_age is not None:
                try:
                    age_val = float(p_age)
                except (ValueError, TypeError):
                    pass # Ignore bad age data

            # Safe string conversion for group
            group_val = str(p_age_group) if p_age_group else ""

            # Category
            if category == 'junior':
                is_junior = (age_val is not None and age_val <= 18) or any(x in group_val for x in ['U', 'Junior', '12', '14', '16', '18'])
                if not is_junior: return False
            elif category == 'adult':
                # Determine if definitely junior
                is_junior_by_age = (age_val is not None and age_val <= 18)
                is_junior_by_group = any(x in group_val for x in ['U', 'Junior', '12', '14', '16', '18'])
                
                if is_junior_by_age or is_junior_by_group:
                    return False
                # Otherwise, treat as Adult (including unknown age)
                
            return True
        except Exception as e:
            print(f"Error in filter logic: {e}")
            return False

    filtered = []
    for m in all_matches:
        # Check if EITHER player matches criteria
        w_ok = is_match_criteria(m['winner_country'], m['winner_age'], m['winner_age_group'], m['winner_gender'])
        l_ok = is_match_criteria(m['loser_country'], m['loser_age'], m['loser_age_group'], m['loser_gender'])
        
        if w_ok or l_ok:
            # Calculate max UTR for sorting
            m['sort_utr'] = max(m['winner_utr'] or 0, m['loser_utr'] or 0)
            filtered.append(m)
            
    # Sort: Player UTR Desc, then Date Desc
    filtered.sort(key=lambda x: (x['sort_utr'], x['date']), reverse=True)
    
    # Limit to 500
    return {"count": len(filtered), "data": filtered[:500]}


# --- FAVORITES ENDPOINTS ---

@app.get("/players/{player_id}/is_favorite")
async def check_favorite(player_id: str, current_user: dict = Depends(auth.get_current_user)):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM user_favorites WHERE user_id = ? AND player_id = ?", (current_user['id'], player_id))
    exists = c.fetchone() is not None
    conn.close()
    return {"is_favorite": exists}

@app.post("/players/{player_id}/favorite")
async def toggle_favorite_alias(player_id: str, current_user: dict = Depends(auth.get_current_user)):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM user_favorites WHERE user_id = ? AND player_id = ?", (current_user['id'], player_id))
    if c.fetchone():
        c.execute("DELETE FROM user_favorites WHERE user_id = ? AND player_id = ?", (current_user['id'], player_id))
        status = "removed"
    else:
        c.execute("INSERT INTO user_favorites (user_id, player_id) VALUES (?, ?)", (current_user['id'], player_id))
        status = "added"
    conn.commit()
    conn.close()
    return {"status": "success", "action": status}

@app.post("/users/favorites/{player_id}")
def add_favorite(player_id: str, current_user: dict = Depends(auth.get_current_user)):
    conn = get_db_connection()
    user_id = current_user['id']
    try:
        conn.execute("INSERT INTO user_favorites (user_id, player_id) VALUES (?, ?)", (user_id, player_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    conn.close()
    return {"status": "success", "message": f"Added {player_id} to favorites"}

@app.delete("/users/favorites/{player_id}")
def remove_favorite(player_id: str, current_user: dict = Depends(auth.get_current_user)):
    conn = get_db_connection()
    user_id = current_user['id']
    conn.execute("DELETE FROM user_favorites WHERE user_id = ? AND player_id = ?", (user_id, player_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Removed {player_id} from favorites"}

@app.get("/users/favorites")
def get_favorites(current_user: dict = Depends(auth.get_current_user)):
    conn = get_db_connection()
    c = conn.cursor()
    # Join with players to get details
    query = """
        SELECT p.* 
        FROM user_favorites f
        JOIN players p ON f.player_id = p.player_id
        WHERE f.user_id = ?
        ORDER BY p.utr_singles DESC
    """
    c.execute(query, (current_user['id'],))
    favorites = [dict(row) for row in c.fetchall()]
    conn.close()
    return {"count": len(favorites), "data": favorites}

@app.get("/users/favorites/feed")
def get_favorites_feed(limit: int = 50, current_user: dict = Depends(auth.get_current_user)):
    conn = get_db_connection()
    c = conn.cursor()
    user_id = current_user['id']
    
    # Get recent matches for favored players
    matches_query = """
        SELECT m.*, 'match' as type, m.date as timestamp,
               w.name as winner_name, l.name as loser_name
        FROM matches m
        JOIN user_favorites f ON (m.winner_id = f.player_id OR m.loser_id = f.player_id)
        JOIN players w ON m.winner_id = w.player_id
        JOIN players l ON m.loser_id = l.player_id
        WHERE f.user_id = ?
        ORDER BY m.date DESC
        LIMIT ?
    """
    c.execute(matches_query, (user_id, limit))
    matches = [dict(row) for row in c.fetchall()]

    # Get news for favored players
    news_query = """
        SELECT n.*, 'news' as type, n.published_at as timestamp
        FROM news_items n
        JOIN user_favorites f ON n.player_id_ref = f.player_id
        WHERE f.user_id = ?
        ORDER BY n.published_at DESC
        LIMIT ?
    """
    c.execute(news_query, (user_id, limit))
    news = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    # Combine and sort
    feed = sorted(matches + news, key=lambda x: x.get('timestamp') or '', reverse=True)[:limit]
    
    return {"count": len(feed), "data": feed}

@app.get("/players/{player_id}/rankings")
def get_player_rankings(player_id: str):
    """Get historical ATP/WTA rankings for a player."""
    conn = get_db_connection()
    c = conn.cursor()
    print(f"DEBUG: Fetching rankings for {player_id}")
    
    # Try direct ID match (mapping Sackmann format to internal storage)
    sackmann_ids = [player_id]
    if player_id.startswith('sackmann-atp-'):
        sackmann_ids.append(player_id.replace('sackmann-atp-', 'atp_'))
    elif player_id.startswith('sackmann-wta-'):
        sackmann_ids.append(player_id.replace('sackmann-wta-', 'wta_'))
    elif player_id.startswith('sackmann_'):
        id_num = player_id.replace('sackmann_', '')
        sackmann_ids.append(f"atp_{id_num}")
        sackmann_ids.append(f"wta_{id_num}")
    
    # 1. Query by ID
    query = """
        SELECT date, rank, points, tours
        FROM rankings
        WHERE player_id = ?
        ORDER BY date ASC
    """
    results = None
    for s_id in sackmann_ids:
        c.execute(query, (s_id,))
        rows = c.fetchall()
        if rows:
            results = rows
            break
    
    # 2. If no results, try name match via sackmann_profiles
    if not results:
        # Get player name
        c.execute("SELECT name, country FROM players WHERE player_id = ?", (player_id,))
        player = c.fetchone()
        
        if player and player['name']:
            name = player['name']
            
            # Formats to try:
            # 1. Exact match (case-insensitive) - e.g. "Jannik SINNER" == "Jannik Sinner"
            # 2. "Last, First" swap -> "First Last"
            
            candidates = [name]
            if ',' in name:
                parts = name.split(',')
                if len(parts) == 2:
                    candidates.append(f"{parts[1].strip()} {parts[0].strip()}")
            
            rank_matches = []
            for cand in candidates:
                # Try to find profile
                c.execute("""
                    SELECT sackmann_id 
                    FROM sackmann_profiles 
                    WHERE full_name = ? COLLATE NOCASE
                """, (cand,))
                profile = c.fetchone()
                
                if profile:
                    s_id = str(profile[0])
                    print(f"DEBUG: Found Sackmann ID {s_id} for player {name}")
                    c.execute(query, (s_id,))
                    rank_matches = c.fetchall()
                    if rank_matches:
                        results = rank_matches
                        break
                else:
                    print(f"DEBUG: No profile found for candidate {cand}")
            
            # If still no match, try searching by last name only + country? 
            # Risk of false positives (e.g. "Williams", "USA"). 
            # Let's stick to full name for safety.

    rankings = [dict(row) for row in results] if results else []
    
    conn.close()
    return {"data": rankings}


# --- TENNIS ABSTRACT ELO ENDPOINTS ---

@app.get("/tennis-abstract/elo")
def get_tennis_abstract_elo(
    tour: str = Query(None, description="Tour: ATP or WTA"),
    limit: int = Query(50, description="Number of results to return")
):
    """Get Tennis Abstract Elo ratings."""
    conn = get_db_connection()
    c = conn.cursor()
    
    query = """
        SELECT elo_id, tour, player_name, elo_rank, elo_rating, official_rank, age, scraped_at
        FROM tennis_abstract_elo
    """
    params = []
    
    if tour:
        query += " WHERE tour = ?"
        params.append(tour.upper())
    
    query += " ORDER BY elo_rank ASC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    results = c.fetchall()
    conn.close()
    
    elo_list = [
        {
            'elo_id': r[0],
            'tour': r[1],
            'player_name': r[2],
            'elo_rank': r[3],
            'elo_rating': r[4],
            'official_rank': r[5],
            'age': r[6],
            'scraped_at': r[7]
        }
        for r in results
    ]
    
    return {"data": elo_list}


@app.get("/tennis-abstract/elo/{player_name}")
def get_player_tennis_abstract_elo(player_name: str):
    """Get Elo rating for a specific player."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Search by player name (case-insensitive partial match)
    c.execute("""
        SELECT elo_id, tour, player_name, elo_rank, elo_rating, official_rank, age, scraped_at
        FROM tennis_abstract_elo
        WHERE LOWER(player_name) LIKE LOWER(?)
        ORDER BY elo_rank ASC
        LIMIT 10
    """, (f"%{player_name}%",))
    
    results = c.fetchall()
    conn.close()
    
    elo_list = [
        {
            'elo_id': r[0],
            'tour': r[1],
            'player_name': r[2],
            'elo_rank': r[3],
            'elo_rating': r[4],
            'official_rank': r[5],
            'age': r[6],
            'scraped_at': r[7]
        }
        for r in results
    ]
    
    return {"data": elo_list}


# --- ADVANCED STATS ENDPOINTS ---

@app.get("/stats/records/consecutive-opening-wins")
def get_consecutive_opening_wins_record(
    level: str = Query('1000', description="Tournament level (1000, M, PM, G)")
):
    # This might be heavy if done for ALL players.
    # Ideally we'd have a pre-calculated table or cache.
    # For now, let's just implement a specific check or return a placeholder if too slow.
    # Or, we can accept a player_id to check a specific player.
    return {"message": "Not implemented for all players yet. Use specific player endpoint."}

@app.get("/players/{player_id}/stats/consecutive-opening-wins")
def get_player_consecutive_opening_wins(
    player_id: str,
    level: str = Query('1000', description="Tournament level (1000, M, PM, G)")
):
    levels = [level]
    if level == '1000':
        levels = ['M', 'PM', '1000'] # approximate mapping
    elif level == 'G':
        levels = ['G']
    elif level == 'all':
        levels = ['M', 'PM', '1000', 'G', 'A', 'P']
        
    import advanced_stats
    result = advanced_stats.get_consecutive_opening_wins(player_id, levels)
    return {"data": result}
    
@app.get("/players/{player_id}/stats/best-win")
def get_player_best_win(player_id: str):
    import advanced_stats
    result = advanced_stats.get_highest_ranked_win(player_id)
    return {"data": result}

@app.get("/players/{player_id}/stats/milestones")
def get_player_milestones(player_id: str):
    import advanced_stats
    result = advanced_stats.get_career_milestones(player_id)
    return {"data": result}

@app.get("/stats/records/oldest-winners")
def get_oldest_winners_record(
    level: str = Query('G', description="Tournament level"),
    min_age: int = 35
):
    import advanced_stats
    result = advanced_stats.get_age_records(level, min_age)
    return {"count": len(result), "data": result}


# --- STATS EXPLORER ENDPOINTS ---

import stats_engine

# stats_eng = stats_engine.TennisStatsEngine() # REMOVED: Not thread safe as singleton

@app.get("/stats/featured")
def get_featured_stats():
    """
    Get a curated list of featured stats for the homepage.
    Returns mix of interesting current statistics.
    """
    with stats_engine.TennisStatsEngine() as eng:
        results = eng.get_featured_stats()
    return {"count": len(results), "data": results}

@app.get("/stats/streaks")
def get_streak_stats(
    tour: str = Query('wta', description='ATP or WTA'),
    level: str = Query('PM', description='Tournament level - PM=WTA-1000, M=Masters'),
    start_year: int = Query(2009, description='Start year for streak calculation'),
    limit: int = Query(20, description='Max results')
):
    """Get consecutive streak records at tournament level."""
    with stats_engine.TennisStatsEngine() as eng:
        results = eng.get_consecutive_streaks(tour, level, start_year, limit)
    return {"count": len(results), "data": results}

@app.get("/stats/age-records")
def get_age_record_stats(
    tour: str = Query('wta', description='ATP or WTA'),
    min_age: int = Query(40, description='Minimum age'),
    limit: int = Query(20, description='Max results')
):
    """Get match winners above certain age at major events."""
    with stats_engine.TennisStatsEngine() as eng:
        results = eng.get_age_records(tour, min_age, None, limit)
    return {"count": len(results), "data": results}

@app.get("/stats/category-leaders")
def get_category_leaders(
    tour: str = Query('wta', description='ATP or WTA'),
    start_date: str = Query('2025-01-01', description='Start date'),
    limit: int = Query(10, description='Max results')
):
    """Get win leaders at WTA-500 level events."""
    with stats_engine.TennisStatsEngine() as eng:
        results = eng.get_category_win_leaders(tour, ['P', 'A'], start_date, limit)
    return {"count": len(results), "data": results}

@app.get("/stats/ace-leaders")
def get_ace_leaders(
    tournament: str = Query('Australian Open', description='Tournament name'),
    year: int = Query(2026, description='Year'),
    tour: str = Query('wta', description='ATP or WTA'),
    limit: int = Query(10, description='Max results')
):
    """Get ace leaders at specific tournament."""
    with stats_engine.TennisStatsEngine() as eng:
        results = eng.get_ace_leaders(tournament, year, tour, limit)
    return {"count": len(results), "data": results}

@app.get("/stats/surface-leaders")
def get_surface_leaders(
    tour: str = Query('wta', description='ATP or WTA'),
    surface: str = Query('Clay', description='Surface type'),
    min_matches: int = Query(10, description='Minimum matches'),
    start_year: int = Query(2020, description='Start year'),
    limit: int = Query(10, description='Max results')
):
    """Get players with best win percentage on a surface."""
    with stats_engine.TennisStatsEngine() as eng:
        results = eng.get_surface_leaders(tour, surface, min_matches, start_year, limit)
    return {"count": len(results), "data": results}

@app.get("/stats/grand-slam-leaders")
def get_grand_slam_leaders(
    tour: str = Query('wta', description='ATP or WTA'),
    stat_type: str = Query('aces', description='Stat type: aces or double_faults'),
    year: int = Query(2026, description='Year'),
    limit: int = Query(10, description='Max results')
):
    """Get leaders for a stat across all Grand Slams in a year."""
    with stats_engine.TennisStatsEngine() as eng:
        results = eng.get_grand_slam_leaders(tour, stat_type, year, limit)
    return {"count": len(results), "data": results}


# --- ANALYSIS & INTEGRATIONS ---

@app.get("/analysis/match_prediction")
def get_match_prediction(p1: str, p2: str):
    """Predict match outcome between two players."""
    return analysis_advanced.predict_match_outcome(p1, p2)

@app.get("/integrations/tennis_abstract/charting")
def get_charting_overview(player_name: str, gender: str = 'F'):
    """Get charting stats and matches from Tennis Abstract."""
    return analysis_advanced.fetch_player_charting_overview(player_name, gender)

@app.get("/integrations/tennis_abstract/charting/{match_id}")
def get_charting_match(match_id: str):
    """Get specific match charting data."""
    return analysis_advanced.get_match_charting(match_id)

# --- NEW: Database-backed Match Charting Endpoints ---

@app.get("/charting/matches")
def get_charted_matches(
    player_name: str = None,
    tour: str = Query(None, description="ATP or WTA"),
    surface: str = Query(None),
    year: int = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """Get charted matches from database with filters."""
    conn = get_db_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM charted_matches WHERE 1=1"
    params = []
    
    if player_name:
        query += " AND (player1 LIKE ? OR player2 LIKE ?)"
        params.extend([f"%{player_name}%", f"%{player_name}%"])
    
    if tour:
        query += " AND tour = ?"
        params.append(tour.upper())
    
    if surface:
        query += " AND surface = ?"
        params.append(surface)
    
    if year:
        query += " AND date LIKE ?"
        params.append(f"{year}%")
    
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    columns = [d[0] for d in c.description]
    matches = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    
    return {"count": len(matches), "data": matches}

@app.get("/charting/matches/{match_id}")
def get_charted_match_detail(match_id: str):
    """Get detailed info for a specific charted match."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM charted_matches WHERE match_id = ?", (match_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Charted match not found")
    
    columns = [d[0] for d in c.description]
    match_data = dict(zip(columns, row))
    
    # Get points if available
    c.execute("SELECT * FROM charted_points WHERE match_id = ? ORDER BY point_num", (match_id,))
    points_columns = [d[0] for d in c.description]
    points = [dict(zip(points_columns, row)) for row in c.fetchall()]
    
    conn.close()
    
    return {
        "match": match_data,
        "points_count": len(points),
        "points": points[:100] if len(points) > 100 else points  # Limit points in response
    }

@app.get("/charting/players/{player_name}/stats")
def get_player_charting_stats(player_name: str, tour: str = Query("WTA")):
    """Get charting stats for a specific player."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT * FROM player_charting_stats 
        WHERE player_name LIKE ? AND tour = ?
    """, (f"%{player_name}%", tour.upper()))
    
    columns = [d[0] for d in c.description]
    stats = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    
    return {"count": len(stats), "data": stats}

@app.get("/charting/players")
def search_charting_players(
    query: str = Query(None, description="Player name search"),
    tour: str = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """Search for players with charting data."""
    conn = get_db_connection()
    c = conn.cursor()
    
    sql = "SELECT player_name, tour, match_count FROM player_charting_stats WHERE 1=1"
    params = []
    
    if query:
        sql += " AND player_name LIKE ?"
        params.append(f"%{query}%")
    
    if tour:
        sql += " AND tour = ?"
        params.append(tour.upper())
    
    sql += " ORDER BY match_count DESC LIMIT ?"
    params.append(limit)
    
    c.execute(sql, params)
    columns = [d[0] for d in c.description]
    players = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    
    return {"count": len(players), "data": players}

@app.get("/charting/stats/overview")
def get_charting_overview_stats():
    """Get overview of charting data coverage."""
    conn = get_db_connection()
    c = conn.cursor()
    
    stats = {}
    
    # Count matches by tour
    c.execute("SELECT tour, COUNT(*) as count FROM charted_matches GROUP BY tour")
    stats['matches_by_tour'] = [dict(row) for row in c.fetchall()]
    
    # Count players by tour
    c.execute("SELECT tour, COUNT(*) as count FROM player_charting_stats GROUP BY tour")
    stats['players_by_tour'] = [dict(row) for row in c.fetchall()]
    
    # Total points
    c.execute("SELECT COUNT(*) as count FROM charted_points")
    row = c.fetchone()
    stats['total_points'] = row['count'] if row else 0
    
    # Recent matches
    c.execute("SELECT date, COUNT(*) as count FROM charted_matches GROUP BY date ORDER BY date DESC LIMIT 10")
    stats['recent_activity'] = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return stats

@app.get("/college/search")
def search_colleges_endpoint(query: str = None, division: str = 'D1'):
    """Search for colleges."""
    return {"data": college_service.search_colleges(query, division)}

# --- Grand Slam Point-by-Point Data Endpoints ---

@app.get("/slam/matches")
def get_slam_matches(
    tournament: str = Query(None, description="Tournament name"),
    year: int = Query(None),
    round: str = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """Get slam matches with filters."""
    conn = get_db_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM slam_matches WHERE 1=1"
    params = []
    
    if tournament:
        query += " AND tournament LIKE ?"
        params.append(f"%{tournament}%")
    
    if year:
        query += " AND year = ?"
        params.append(year)
    
    if round:
        query += " AND round = ?"
        params.append(round)
    
    query += " ORDER BY year DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    columns = [d[0] for d in c.description]
    matches = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    
    return {"count": len(matches), "data": matches}

@app.get("/slam/matches/{match_id}")
def get_slam_match_detail(match_id: str):
    """Get match detail with points."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get match
    c.execute("SELECT * FROM slam_matches WHERE match_id = ?", (match_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Slam match not found")
    
    columns = [d[0] for d in c.description]
    match_data = dict(zip(columns, row))
    
    # Get points
    c.execute("SELECT * FROM slam_points WHERE match_id = ? ORDER BY point_num", (match_id,))
    points_columns = [d[0] for d in c.description]
    points = [dict(zip(points_columns, row)) for row in c.fetchall()]
    
    conn.close()
    
    return {
        "match": match_data,
        "points_count": len(points),
        "points": points
    }

@app.get("/slam/stats/overview")
def get_slam_stats_overview():
    """Get overview of slam data coverage."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # First check if table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slam_matches'")
    table_exists = c.fetchone()
    
    stats = {}
    stats['table_exists'] = table_exists is not None
    stats['db_file'] = tennis_db.DB_FILE
    
    if table_exists:
        # Matches by tournament
        c.execute("SELECT tournament, year, COUNT(*) as count FROM slam_matches GROUP BY tournament, year ORDER BY year DESC")
        stats['matches_by_tournament'] = [dict(row) for row in c.fetchall()]
        
        # Total matches
        c.execute("SELECT COUNT(*) as count FROM slam_matches")
        row = c.fetchone()
        stats['total_matches'] = row['count'] if row else 0
        
        # Total points
        c.execute("SELECT COUNT(*) as count FROM slam_points")
        row = c.fetchone()
        stats['total_points'] = row['count'] if row else 0
    
    conn.close()
    
    return stats

@app.get("/college/{club_id}/roster")
def get_college_roster_endpoint(club_id: str, gender: str = 'M'):
    """Get roster for a college."""
    return {"data": college_service.get_roster(club_id, gender)}


# Mount Static Files (Frontend) if built - MUST BE LAST to not intercept API routes
if os.path.exists("web-ui/dist"):
    app.mount("/", StaticFiles(directory="web-ui/dist", html=True), name="static")
elif os.path.exists("../web-ui/dist"): # Fallback for dev structure
    app.mount("/", StaticFiles(directory="../web-ui/dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
