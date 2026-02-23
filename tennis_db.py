import sqlite3
import os
from datetime import datetime

DB_FILE = 'tennis_data.db'

def get_connection():
    """Get a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE, timeout=30.0)

def init_db():
    """Initialize the database tables."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    
    # Players table
    c.execute('''
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        name TEXT,
        college TEXT,
        country TEXT,
        gender TEXT,
        utr_singles REAL,
        utr_doubles REAL,
        age INTEGER,
        updated_at TIMESTAMP
    )
    ''')
    
    # Users table for Auth
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT,
        full_name TEXT,
        is_verified BOOLEAN DEFAULT 0,
        google_id TEXT,
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Migration: Check if age column exists, if not add it
    c.execute("PRAGMA table_info(players)")
    columns = [row[1] for row in c.fetchall()]
    
    player_cols = [
        ('age', 'INTEGER'),
        ('location', 'TEXT'),
        ('pro_rank', 'TEXT'),
        ('age_group', 'TEXT'),
        ('birth_date', 'TEXT'),
        ('college_name', 'TEXT'),
        ('college_id', 'TEXT'),
        ('grad_year', 'TEXT'),
        ('is_active_college', 'BOOLEAN DEFAULT 0'),
        ('comeback_wins', 'INTEGER DEFAULT 0'),
        ('year_delta', 'REAL DEFAULT 0.0'),
        ('tiebreak_wins', 'INTEGER DEFAULT 0'),
        ('tiebreak_losses', 'INTEGER DEFAULT 0'),
        ('three_set_wins', 'INTEGER DEFAULT 0'),
        ('three_set_losses', 'INTEGER DEFAULT 0')
    ]
    
    for col_name, col_type in player_cols:
        if col_name not in columns:
            print(f"Migrating DB: Adding '{col_name}' column to players table...")
            c.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_type}")

    
    # Matches table
    # Using specific source_match_id to prevent duplicates from same source
    c.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        date TEXT,
        winner_id TEXT,
        loser_id TEXT,
        score TEXT,
        tournament TEXT,
        round TEXT,
        source TEXT,
        winner_utr REAL,
        loser_utr REAL,
        processed_player_id TEXT, 
        FOREIGN KEY (winner_id) REFERENCES players (player_id),
        FOREIGN KEY (loser_id) REFERENCES players (player_id)
    )
    ''')
    
    # UTR History table
    c.execute('''
    CREATE TABLE IF NOT EXISTS utr_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT,
        date TEXT,
        rating REAL,
        type TEXT,
        FOREIGN KEY (player_id) REFERENCES players (player_id),
        UNIQUE(player_id, date, type)
    )
    ''')
    
    # Social Media Links table
    c.execute('''
    CREATE TABLE IF NOT EXISTS player_social_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        url TEXT NOT NULL,
        username TEXT,
        verified BOOLEAN DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players (player_id),
        UNIQUE(player_id, platform)
    )
    ''')
    
    # News Items Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS news_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        summary TEXT,
        url TEXT,
        source TEXT,
        image_url TEXT,
        published_at TIMESTAMP,
        category TEXT,
        is_internal BOOLEAN DEFAULT 0,
        player_id_ref TEXT,
        UNIQUE(url)
    )
    ''')



    # Social Media Posts Cache Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS social_posts (
        post_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT,
        platform TEXT, -- 'instagram'
        shortcode TEXT UNIQUE,
        image_url TEXT,
        caption TEXT,
        posted_at TIMESTAMP,
        fetched_at TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players (player_id)
    )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_social_posts_player ON social_posts (player_id, posted_at DESC)')

    # Historical Rankings Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS rankings (
        rank_id TEXT PRIMARY KEY,
        date TEXT,
        player_id TEXT,
        rank INTEGER,
        points INTEGER,
        tours INTEGER,
        FOREIGN KEY (player_id) REFERENCES players (player_id)
    )
    ''')
    
    # Sackmann Profiles Table (for linking)
    c.execute('''
    CREATE TABLE IF NOT EXISTS sackmann_profiles (
        sackmann_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        full_name TEXT,
        country TEXT,
        dob TEXT,
        tour TEXT
    )
    ''')

    # User Favorites Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        player_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (player_id) REFERENCES players (player_id),
        UNIQUE(user_id, player_id)
    )
    ''')
    
    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches (winner_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_matches_loser ON matches (loser_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_history_player ON utr_history (player_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_social_player ON player_social_media (player_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_news_date ON news_items (published_at)')

    
    # Sackmann Player Map Table (for matching Sackmann IDs to our player IDs)
    c.execute('''
    CREATE TABLE IF NOT EXISTS sackmann_player_map (
        sackmann_id INTEGER PRIMARY KEY,
        player_id TEXT,
        player_name TEXT,
        matched_by TEXT,
        country TEXT,
        FOREIGN KEY (player_id) REFERENCES players (player_id)
    )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sackmann_player ON sackmann_player_map (player_id)')
    
    # Tennis Abstract Elo Ratings table
    c.execute('''
    CREATE TABLE IF NOT EXISTS tennis_abstract_elo (
        elo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tour TEXT,  -- 'ATP' or 'WTA'
        player_name TEXT,
        elo_rank INTEGER,
        elo_rating INTEGER,
        official_rank INTEGER,
        age REAL,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_elo_tour ON tennis_abstract_elo(tour, elo_rank)')
    
    # Migration: Add match statistics columns for Sackmann data
    c.execute("PRAGMA table_info(matches)")
    match_cols = [row[1] for row in c.fetchall()]
    
    stats_columns = [
        ('surface', 'TEXT'),
        ('best_of', 'INTEGER'),
        ('minutes', 'INTEGER'),
        ('tourney_level', 'TEXT'),
        # Winner stats
        ('w_ace', 'INTEGER'),
        ('w_df', 'INTEGER'),
        ('w_svpt', 'INTEGER'),
        ('w_1stIn', 'INTEGER'),
        ('w_1stWon', 'INTEGER'),
        ('w_2ndWon', 'INTEGER'),
        ('w_SvGms', 'INTEGER'),
        ('w_bpSaved', 'INTEGER'),
        ('w_bpFaced', 'INTEGER'),
        # Loser stats
        ('l_ace', 'INTEGER'),
        ('l_df', 'INTEGER'),
        ('l_svpt', 'INTEGER'),
        ('l_1stIn', 'INTEGER'),
        ('l_1stWon', 'INTEGER'),
        ('l_2ndWon', 'INTEGER'),
        ('l_SvGms', 'INTEGER'),
        ('l_bpSaved', 'INTEGER'),
        ('l_bpFaced', 'INTEGER'),
    ]
    
    for col_name, col_type in stats_columns:
        if col_name not in match_cols:
            print(f"Migrating DB: Adding '{col_name}' column to matches table...")
            c.execute(f"ALTER TABLE matches ADD COLUMN {col_name} {col_type}")
    
    conn.commit()
    conn.close()
    print(f"Database {DB_FILE} initialized.")

def save_player(conn, player_data):
    """
    Upsert player data.
    player_data: dict with keys matching table columns
    """
    sql = '''
    INSERT INTO players (player_id, name, college, country, gender, utr_singles, utr_doubles, age, birth_date, location, pro_rank, age_group, comeback_wins, year_delta, tiebreak_wins, tiebreak_losses, three_set_wins, three_set_losses, college_name, college_id, grad_year, is_active_college, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(player_id) DO UPDATE SET
        name=COALESCE(excluded.name, players.name),
        college=COALESCE(excluded.college, players.college),
        country=COALESCE(excluded.country, players.country),
        gender=COALESCE(excluded.gender, players.gender),
        utr_singles=COALESCE(excluded.utr_singles, players.utr_singles),
        utr_doubles=COALESCE(excluded.utr_doubles, players.utr_doubles),
        age=COALESCE(excluded.age, players.age),
        birth_date=COALESCE(excluded.birth_date, players.birth_date),
        location=COALESCE(excluded.location, players.location),
        pro_rank=COALESCE(excluded.pro_rank, players.pro_rank),
        age_group=COALESCE(excluded.age_group, players.age_group),
        comeback_wins=COALESCE(excluded.comeback_wins, players.comeback_wins),
        year_delta=COALESCE(excluded.year_delta, players.year_delta),
        tiebreak_wins=COALESCE(excluded.tiebreak_wins, players.tiebreak_wins),
        tiebreak_losses=COALESCE(excluded.tiebreak_losses, players.tiebreak_losses),
        three_set_wins=COALESCE(excluded.three_set_wins, players.three_set_wins),
        three_set_losses=COALESCE(excluded.three_set_losses, players.three_set_losses),
        college_name=COALESCE(excluded.college_name, players.college_name),
        college_id=COALESCE(excluded.college_id, players.college_id),
        grad_year=COALESCE(excluded.grad_year, players.grad_year),
        is_active_college=COALESCE(excluded.is_active_college, players.is_active_college),
        updated_at=excluded.updated_at
    '''
    
    params = (
        str(player_data.get('player_id')),
        player_data.get('name'),
        player_data.get('college'),
        player_data.get('country'),
        player_data.get('gender'),
        player_data.get('utr_singles'),
        player_data.get('utr_doubles'),
        player_data.get('age'),
        player_data.get('birth_date'),
        player_data.get('location'),
        player_data.get('pro_rank'),
        player_data.get('age_group'),
        player_data.get('comeback_wins'),
        player_data.get('year_delta'),
        player_data.get('tiebreak_wins'),
        player_data.get('tiebreak_losses'),
        player_data.get('three_set_wins'),
        player_data.get('three_set_losses'),
        player_data.get('college_name'),
        player_data.get('college_id'),
        player_data.get('grad_year'),
        1 if player_data.get('is_active_college') else 0,
        datetime.now().isoformat()
    )
    
    try:
        conn.execute(sql, params)
    except Exception as e:
        print(f"Error saving player {player_data.get('name')}: {e}")

def save_match(conn, match_data, overwrite=True):
    """
    Insert match data.
    match_data: dict with keys matching table columns
    overwrite: If True, replace existing match. If False, ignore if exists.
    """
    # Auto-create missing players to satisfy foreign keys and populate DB
    winner_id = str(match_data.get('winner_id'))
    loser_id = str(match_data.get('loser_id'))
    winner_name = match_data.get('winner_name', 'Unknown')
    loser_name = match_data.get('loser_name', 'Unknown')
    winner_utr = match_data.get('winner_utr')
    loser_utr = match_data.get('loser_utr')
    
    # Minimal player insert (ignore if exists)
    player_sql = "INSERT OR IGNORE INTO players (player_id, name, utr_singles, updated_at) VALUES (?, ?, ?, ?)"
    try:
        conn.execute(player_sql, (winner_id, winner_name, winner_utr, datetime.now().isoformat()))
        conn.execute(player_sql, (loser_id, loser_name, loser_utr, datetime.now().isoformat()))
    except Exception as e:
        print(f"Warning: Failed to auto-create players for match: {e}")

    # Determine conflict resolution
    conflict_action = "REPLACE" if overwrite else "IGNORE"

    sql = f'''
    INSERT OR {conflict_action} INTO matches (match_id, date, winner_id, loser_id, score, tournament, round, source, winner_utr, loser_utr, processed_player_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    params = (
        str(match_data.get('match_id')),
        match_data.get('date'),
        str(match_data.get('winner_id')),
        str(match_data.get('loser_id')),
        match_data.get('score'),
        match_data.get('tournament'),
        match_data.get('round'),
        match_data.get('source'),
        match_data.get('winner_utr'),
        match_data.get('loser_utr'),
        str(match_data.get('processed_player_id'))
    )
    
    try:
        conn.execute(sql, params)
        # Check if row was inserted (changes returns 1 if inserted, 0 if ignored)
        return conn.total_changes
    except Exception as e:
        print(f"Error saving match {match_data.get('match_id')}: {e}")
        return 0

def save_history(conn, history_data, overwrite=True):
    """
    Insert history record.
    history_data: dict with keys matching table columns
    overwrite: If True, replace existing record. If False, ignore.
    """
    conflict_action = "REPLACE" if overwrite else "IGNORE"
    
    sql = f'''
    INSERT OR {conflict_action} INTO utr_history (player_id, date, rating, type)
    VALUES (?, ?, ?, ?)
    '''
    
    params = (
        str(history_data.get('player_id')),
        history_data.get('date'),
        history_data.get('rating'),
        history_data.get('type')
    )
    
    try:
        cursor = conn.execute(sql, params)
        return cursor.rowcount
    except Exception as e:
        print(f"Error saving history for {history_data.get('player_id')}: {e}")
        return 0

def get_players_by_name(conn, name_query):

    """Find players matching name."""
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE name LIKE ?", (f"%{name_query}%",))
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]

def get_players_by_country(conn, country_code):
    """Find players by country."""
    c = conn.cursor()
    # If country is 'ALL', return all
    if country_code == 'ALL':
        c.execute("SELECT * FROM players")
    else:
        c.execute("SELECT * FROM players WHERE country = ?", (country_code,))
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]

def get_players_for_refresh(conn, country=None, days_old=1, limit=100, min_utr=0, max_utr=17, force_update=False):
    """
    Get players who haven't been updated in X days.
    force_update: If True, ignore updated_at timestamp.
    min_utr: Only return players with utr_singles >= min_utr.
    max_utr: Only return players with utr_singles <= max_utr.
    """
    c = conn.cursor()
    
    query = "SELECT * FROM players WHERE 1=1"
    params = []
    
    if country and country != 'ALL':
        query += " AND country = ?"
        params.append(country)
        
    if min_utr > 0:
        query += " AND utr_singles >= ?"
        params.append(min_utr)

    if max_utr < 17:
        query += " AND utr_singles <= ?"
        params.append(max_utr)
        
    if not force_update:
        # Check updated_at (or if null)
        # SQLite 'now' is in UTC, updated_at is ISO string
        # We'll fetch rows where updated_at < (now - days) OR updated_at IS NULL
        query += f" AND (updated_at IS NULL OR julianday('now') - julianday(updated_at) > ?)" 
        params.append(days_old)
    
    query += " ORDER BY updated_at ASC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]

def get_player_matches(conn, player_id, year=None, limit=100, offset=0):
    """
    Get matches for a player with optional pagination and year filtering.
    Uses UNION approach for much better performance (130x faster than OR).
    """
    import time
    _start = time.time()
    c = conn.cursor()
    
    # Column list (explicit to avoid SELECT * overhead)
    cols = '''match_id, date, winner_id, loser_id, score, tournament, round, source,
              winner_utr, loser_utr, surface, best_of, minutes,
              w_ace, w_df, w_svpt, w_1stIn, w_1stWon, w_2ndWon, w_SvGms, w_bpSaved, w_bpFaced,
              l_ace, l_df, l_svpt, l_1stIn, l_1stWon, l_2ndWon, l_SvGms, l_bpSaved, l_bpFaced'''
    
    # Use UNION for much better index utilization
    query = f'''
        SELECT {cols} FROM (
            SELECT {cols} FROM matches WHERE winner_id = ?
            UNION ALL
            SELECT {cols} FROM matches WHERE loser_id = ?
        )
    '''
    params = [player_id, player_id]
    
    # Add year filter if specified
    if year:
        query += ' WHERE date >= ? AND date < ?'
        params.extend([f'{year}-01-01', f'{int(year)+1}-01-01'])
    
    # Add ordering and pagination
    query += ' ORDER BY date DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    c.execute(query, params)
    
    # Get column names
    columns = [d[0] for d in c.description]
    matches = [dict(zip(columns, row)) for row in c.fetchall()]
    
    # Batch fetch player names to avoid JOIN overhead
    if matches:
        player_ids = set()
        for m in matches:
            if m.get('winner_id'):
                player_ids.add(m['winner_id'])
            if m.get('loser_id'):
                player_ids.add(m['loser_id'])
        
        if player_ids:
            placeholders = ','.join(['?'] * len(player_ids))
            # Include stats columns for player detail
            c.execute(f'''SELECT player_id, name, utr_singles, age, age_group, gender,
                          comeback_wins, tiebreak_wins, tiebreak_losses, three_set_wins, three_set_losses 
                          FROM players WHERE player_id IN ({placeholders})''', list(player_ids))
            player_data = {row[0]: {
                'name': row[1], 
                'utr_singles': row[2],
                'age': row[3],
                'age_group': row[4],
                'gender': row[5],
                'comeback_wins': row[6],
                'tiebreak_wins': row[7],
                'tiebreak_losses': row[8],
                'three_set_wins': row[9],
                'three_set_losses': row[10]
            } for row in c.fetchall()}
            
            for m in matches:
                winner_id = m.get('winner_id')
                loser_id = m.get('loser_id')
                if winner_id and winner_id in player_data:
                    p = player_data[winner_id]
                    m['winner_name'] = p['name']
                    m['winner_utr'] = p['utr_singles']
                    m['winner_age'] = p['age']
                    m['winner_age_group'] = p['age_group']
                    m['winner_gender'] = p['gender']
                    m['winner_comeback_wins'] = p['comeback_wins']
                    m['winner_tiebreak_wins'] = p['tiebreak_wins']
                    m['winner_tiebreak_losses'] = p['tiebreak_losses']
                    m['winner_three_set_wins'] = p['three_set_wins']
                    m['winner_three_set_losses'] = p['three_set_losses']
                if loser_id and loser_id in player_data:
                    p = player_data[loser_id]
                    m['loser_name'] = p['name']
                    m['loser_utr'] = p['utr_singles']
                    m['loser_age'] = p['age']
                    m['loser_age_group'] = p['age_group']
                    m['loser_gender'] = p['gender']
                    m['loser_comeback_wins'] = p['comeback_wins']
                    m['loser_tiebreak_wins'] = p['tiebreak_wins']
                    m['loser_tiebreak_losses'] = p['tiebreak_losses']
                    m['loser_three_set_wins'] = p['three_set_wins']
                    m['loser_three_set_losses'] = p['three_set_losses']
    
    print(f"get_player_matches: player={player_id}, year={year}, limit={limit}, offset={offset}, found={len(matches)}, time={time.time()-_start:.3f}s")
    return matches


def get_player_matches_count(conn, player_id, year=None):
    """
    Get total count of matches for a player (for pagination info).
    
    Args:
        conn: Database connection
        player_id: The player's ID
        year: Optional year to filter matches
    
    Returns:
        Total count of matches
    """
    c = conn.cursor()
    
    query = '''
        SELECT COUNT(*) FROM matches m
        WHERE (m.winner_id = ? OR m.loser_id = ?)
    '''
    params = [player_id, player_id]
    
    if year:
        query += ' AND m.date >= ? AND m.date < ?'
        params.extend([f'{year}-01-01', f'{int(year)+1}-01-01'])
    
    c.execute(query, params)
    return c.fetchone()[0]


def get_player_match_years(conn, player_id):
    """
    Get all years that a player has matches for.
    
    Args:
        conn: Database connection
        player_id: The player's ID
    
    Returns:
        List of years (as strings) sorted descending
    """
    c = conn.cursor()
    
    # Extract year from date and get unique years
    c.execute('''
        SELECT DISTINCT substr(date, 1, 4) as year
        FROM matches
        WHERE (winner_id = ? OR loser_id = ?)
        AND date IS NOT NULL
        ORDER BY year DESC
    ''', (player_id, player_id))
    
    return [row[0] for row in c.fetchall()]


def save_social_media(conn, player_id, platform, url, username=None, verified=False):
    """
    Save or update a social media link for a player.
    """
    sql = '''
    INSERT INTO player_social_media (player_id, platform, url, username, verified, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(player_id, platform) DO UPDATE SET
        url=excluded.url,
        username=excluded.username,
        verified=excluded.verified,
        updated_at=excluded.updated_at
    '''
    try:
        conn.execute(sql, (
            str(player_id),
            platform.lower(),
            url,
            username,
            1 if verified else 0,
            datetime.now().isoformat()
        ))
    except Exception as e:
        print(f"Error saving social media for {player_id}: {e}")


def get_player_social_media(conn, player_id):
    """Get all social media links for a player."""
    c = conn.cursor()
    c.execute('''
        SELECT platform, url, username, verified, updated_at
        FROM player_social_media
        WHERE player_id = ?
        ORDER BY platform
    ''', (str(player_id),))
    
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]


def delete_player_social_media(conn, player_id, platform=None):
    """Delete social media link(s) for a player."""
    if platform:
        conn.execute('DELETE FROM player_social_media WHERE player_id = ? AND platform = ?', 
                     (str(player_id), platform.lower()))
    else:
        conn.execute('DELETE FROM player_social_media WHERE player_id = ?', (str(player_id),))

def get_match_stats(conn, player_id, year=None):
    """
    Get aggregated match stats for a player (Wins, Losses, Aces, DFs).
    Efficiently sums stats using SQL.
    """
    c = conn.cursor()
    
    # Base query
    query = """
        SELECT 
            SUM(CASE WHEN winner_id = ? THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN loser_id = ? THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN winner_id = ? THEN w_ace ELSE l_ace END) as total_aces,
            SUM(CASE WHEN winner_id = ? THEN w_df ELSE l_df END) as total_dfs
        FROM matches 
        WHERE (winner_id = ? OR loser_id = ?)
    """
    params = [player_id, player_id, player_id, player_id, player_id, player_id]
    
    # Year filter
    if year:
        query += " AND date LIKE ?"
        params.append(f"{year}%")
        
    c.execute(query, params)
    row = c.fetchone()
    
    if row:
        wins = row[0] or 0
        losses = row[1] or 0
        return {
            "wins": wins,
            "losses": losses,
            "winPct": round((wins / (wins + losses)) * 100) if (wins + losses) > 0 else 0,
            "totalAces": row[2] or 0,
            "totalDfs": row[3] or 0
        }
    return {"wins": 0, "losses": 0, "winPct": 0, "totalAces": 0, "totalDfs": 0}

if __name__ == "__main__":
    init_db()
