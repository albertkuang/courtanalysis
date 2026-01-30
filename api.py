
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import tennis_db
from typing import List, Optional

app = FastAPI(title="CourtSide Analytics API", description="API for Tennis Player Data")

from fastapi.staticfiles import StaticFiles
import os

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files (Frontend) if built
if os.path.exists("web-ui/dist"):
    app.mount("/", StaticFiles(directory="web-ui/dist", html=True), name="static")
elif os.path.exists("../web-ui/dist"): # Fallback for dev structure
    app.mount("/", StaticFiles(directory="../web-ui/dist", html=True), name="static")

def get_db_connection():
    conn = tennis_db.get_connection()
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn

@app.get("/")
def read_root():
    return {"status": "active", "message": "Welcome to CourtSide Analytics API"}

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
    
    # If search is provided, relax category and country filters to ensure finding the specific person
    if not search:
        if country != 'ALL':
            query += " AND country = ?"
            params.append(country)
        
        if gender:
            query += " AND gender = ?"
            params.append(gender)

        # Category Logic (synced with export_players_excel.py)
        if category == 'junior':
            query += """ AND ( 
                (age IS NOT NULL AND age <= 18) OR 
                (age_group IS NOT NULL AND (age_group LIKE 'U%' OR age_group LIKE '1_-1_' OR age_group LIKE '%Junior%')) OR
                (age IS NULL AND age_group IS NULL AND utr_singles < 14.0)
            )"""
            query += " AND (college IS NULL OR college = '-' OR college LIKE '%Recruiting%')"
        elif category == 'college':
            query += " AND (college IS NOT NULL AND college != '-' AND college NOT LIKE '%Recruiting%')"
        elif category == 'adult':
            query += " AND (age IS NULL OR age > 18)"
    else:
        # Search mode: minimal filtering
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
