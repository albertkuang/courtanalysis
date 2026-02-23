
from fastapi import FastAPI, HTTPException, Query, status, Depends
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import tennis_db
import analysis
import analysis_ai
import advanced_stats
from typing import List, Optional

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
    search: str = Query(None, description="Search by name"),
    limit: int = 100
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

    # 2. Category Logic (Always Apply)
    if category == 'junior':
        query += """ AND ( 
            (age IS NOT NULL AND age <= 18) OR 
            (age_group IS NOT NULL AND (age_group LIKE 'U%' OR age_group LIKE '1_-1_' OR age_group LIKE '%Junior%')) OR
            (age IS NULL AND age_group IS NULL AND (
                (gender = 'F' AND utr_singles < 11.5) OR
                (gender = 'M' AND utr_singles < 13.5) OR
                (gender IS NULL AND utr_singles < 13.0)
            ))
        )"""
        query += " AND (college IS NULL OR college = '-' OR college LIKE '%Recruiting%')"
    elif category == 'college':
        query += " AND (college IS NOT NULL AND college != '-' AND college NOT LIKE '%Recruiting%')"
    elif category == 'adult':
        # Exclude those captured by the Junior heuristic above
        query += """ AND (
            (age IS NOT NULL AND age > 18) OR
            (age IS NULL AND (
                age_group IS NULL AND NOT (
                     (gender = 'F' AND utr_singles < 11.5) OR
                     (gender = 'M' AND utr_singles < 13.5) OR
                     (gender IS NULL AND utr_singles < 13.0)
                )
            ))
        )"""

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

@app.get("/players/{player_id}/analysis")
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

@app.get("/highlights/age_records")
def get_age_records(
    tourney_level: str = Query('G', description="Tournament Level (G=Grand Slam, M=Masters, etc.)"),
    min_age: int = Query(35, description="Minimum Age")
):
    """
    Get records of oldest match winners at a given level.
    """
    records = advanced_stats.get_age_records(tourney_level, min_age)
    if not records:
        return {"count": 0, "data": []}
    return {"count": len(records), "data": records}

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
    results.sort(key=lambda x: (x['priority'], x['last_activity']), reverse=False)
    # Secondary sort by last_activity descending within each priority group
    results.sort(key=lambda x: (x['priority'], -ord(x['last_activity'][0]) if x['last_activity'] else 0))
    
    # Re-sort properly: priority ascending, then last_activity descending
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

# Mount Static Files (Frontend) if built - MUST BE LAST to not intercept API routes
if os.path.exists("web-ui/dist"):
    app.mount("/", StaticFiles(directory="web-ui/dist", html=True), name="static")
elif os.path.exists("../web-ui/dist"): # Fallback for dev structure
    app.mount("/", StaticFiles(directory="../web-ui/dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
