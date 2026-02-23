import requests
import time
import sys
import tennis_db
from config import UTR_CONFIG

def get_auth_token():
    try:
        auth_res = requests.post('https://app.utrsports.net/api/v1/auth/login', 
                               json={'email': UTR_CONFIG['email'], 'password': UTR_CONFIG['password']})
        if auth_res.status_code != 200:
            print(f"Login failed: {auth_res.status_code}")
            return None
        
        data = auth_res.json()
        token = data.get('jwt') or data.get('token')
        
        if not token:
            for cookie in auth_res.cookies:
                if cookie.name == 'jwt':
                    token = cookie.value
                    break
        return token
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def update_ages(limit=50, player_id=None, name_search=None):
    tennis_db.init_db()
    conn = tennis_db.get_connection()
    c = conn.cursor()
    
    # Get players needing update
    query = "SELECT player_id, name FROM players WHERE 1=1"
    params = []

    if player_id:
        query += " AND player_id = ?"
        params.append(player_id)
    elif name_search:
        query += " AND name LIKE ?"
        params.append(f"%{name_search}%")
    else:
        # Default batch mode: prioritize missing data
        query += " AND (age IS NULL OR birth_date IS NULL)"
    
    query += " LIMIT ?"
    params.append(limit)

    c.execute(query, tuple(params))
    players = c.fetchall()
    
    if not players:
        print("No players found needing age update.")
        return

    print(f"Found {len(players)} players to update...")
    
    token = get_auth_token()
    if not token:
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    updated_count = 0
    
    for pid, name in players:
        try:
            time.sleep(0.5) # Rate limit kindness
            sys.stdout.write(f"\rUpdating {name} ({pid})...")
            sys.stdout.flush()
            
            # Use V2 API which seems to have birthDate
            url = f"https://app.utrsports.net/api/v2/player/{pid}"
            res = requests.get(url, headers=headers)
            
            if res.status_code == 200:
                data = res.json()
                age = data.get('age')
                birth_date = data.get('birthDate')
                
                # Check if we got new meaningful data
                if age is not None or birth_date is not None:
                    # Update DB
                    # We need to construct a partial dict for save_player, but save_player handles partial updates if we use it cleverly
                    # actually save_player expects a dict with keys. 
                    # But save_player in tennis_db might overwrite other fields with None if we aren't careful?
                    # Let's check tennis_db.py again. 
                    # save_player uses ON CONFLICT DO UPDATE SET col=COALESCE(excluded.col, players.col)
                    # excellent! this means sending None won't overwrite existing data.
                    
                    p_data = {
                        'player_id': pid,
                        'age': age,
                        'birth_date': birth_date
                    }
                    tennis_db.save_player(conn, p_data)
                    updated_count += 1
            elif res.status_code == 404:
                print(f" Player not found on UTR.")
            else:
                print(f" Error {res.status_code}")

        except Exception as e:
            print(f" Error processing {name}: {e}")
            
    conn.commit()
    conn.close()
    print(f"\n\nUpdate complete. {updated_count} players updated.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=100, help='Max players to update')
    parser.add_argument('--id', type=str, help='Specific Player ID to update')
    parser.add_argument('--name', type=str, help='Search name to update')
    args = parser.parse_args()
    
    update_ages(args.limit, args.id, args.name)
