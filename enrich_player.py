import sqlite3
import requests
import json
from config import UTR_CONFIG

LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"

def login():
    session = requests.Session()
    headers = {"Content-Type": "application/json"}
    response = session.post(LOGIN_URL, json={
        "email": UTR_CONFIG['email'],
        "password": UTR_CONFIG['password']
    }, headers=headers)
    token = response.json().get('jwt') or response.json().get('token')
    return token, session.cookies

def enrich_player(player_id, division=None):
    token, cookies = login()
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Fetching profile for {player_id}...")
    res = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}/profile", headers=headers, cookies=cookies)
    if res.status_code != 200:
        print(f"Failed to fetch profile: {res.status_code}")
        return
    
    data = res.json()
    name = data.get('displayName')
    
    # Try multiple sources for college name
    col_details = data.get('playerCollegeDetails')
    col_obj = data.get('playerCollege')
    
    college_name = None
    if col_obj and col_obj.get('name'):
        college_name = col_obj.get('name')
    elif col_details and col_details.get('name'):
        college_name = col_details.get('name')
    
    if not college_name:
        # Check description as last resort
        desc = data.get('descriptionShort', '')
        if 'University' in desc or 'College' in desc:
            college_name = desc
    
    if not college_name:
        print(f"No college details found for {name}")
        return
    
    print(f"Found college: {college_name} for {name}")
    
    conn = sqlite3.connect('tennis_data.db')
    c = conn.cursor()
    
    # Update player
    if division:
        c.execute("UPDATE players SET college_name = ?, is_active_college = 1, division = ? WHERE player_id = ?", (college_name, division.upper(), player_id))
    else:
        c.execute("UPDATE players SET college_name = ?, is_active_college = 1 WHERE player_id = ?", (college_name, player_id))
    
    if c.rowcount == 0:
        print(f"Player {player_id} not found in database. Inserting...")
        # (Simplified insert - ideally we want more data but for now)
        c.execute("INSERT INTO players (player_id, name, college_name, is_active_college, division) VALUES (?, ?, ?, 1, ?)", 
                  (player_id, name, college_name, division.upper() if division else None))
    
    conn.commit()
    conn.close()
    print("Updated successfully.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: py enrich_player.py <player_id> [division]")
        sys.exit(1)
    
    pid = sys.argv[1]
    div = sys.argv[2] if len(sys.argv) > 2 else None
    enrich_player(pid, div)
