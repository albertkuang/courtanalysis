
import requests
import tennis_db
import sys
import argparse
from config import UTR_CONFIG

CONFIG = UTR_CONFIG
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"

def force_add_player(player_id):
    # Login
    try:
        resp = requests.post(LOGIN_URL, json={"email": CONFIG['email'], "password": CONFIG['password']})
        token = resp.json().get('jwt')
        headers = {"Authorization": f"Bearer {token}"}
        cookies = resp.cookies
    except Exception as e:
        print(f"Login failed: {e}")
        return

    print(f"Fetching V2 Profile for ID {player_id}...")
    try:
        v2_url = f"https://app.utrsports.net/api/v2/player/{player_id}"
        v2 = requests.get(v2_url, headers=headers, cookies=cookies).json()
        
        if not v2 or 'id' not in v2:
            print("Profile not found or invalid ID.")
            return
            
        print(f"Found: {v2.get('displayName')} (UTR: {v2.get('singlesUtr')})")
        
        # Map to DB Schema
        player_data = {
            'player_id': str(v2.get('id')),
            'name': v2.get('displayName'),
            'country': v2.get('nationality'),
            'gender': v2.get('gender') or 'M',
            'utr_singles': v2.get('singlesUtr'),
            'utr_doubles': v2.get('doublesUtr'),
            'location': (v2.get('location') or {}).get('display'),
            'age': v2.get('age'),
            'birth_date': v2.get('birthDate')
        }
        
        if player_data['gender'] == 'Male': player_data['gender'] = 'M'
        elif player_data['gender'] == 'Female': player_data['gender'] = 'F'
        
        # Save
        tennis_db.init_db()
        conn = tennis_db.get_connection()
        tennis_db.save_player(conn, player_data)
        conn.commit()
        conn.close()
        print(f"Player {player_data['name']} saved successfully to DB.")
        
    except Exception as e:
        print(f"Error fetching/saving player: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Force Add Player by ID')
    parser.add_argument('id', help='UTR Player ID')
    args = parser.parse_args()
    
    force_add_player(args.id)
