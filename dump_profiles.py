from populate_college_rosters import login
import requests
import json

def dump_profiles():
    auth = login()
    headers = {'Authorization': f"Bearer {auth['token']}"}
    
    # Felix Roussel (HS), Aleksandar Ivancevic (College), Michael Zheng (College)
    # Correct IDs from search hits
    p_info = [
        ('Felix Roussel', '3496353'), # ID from Step 788
        ('Aleksandar Ivancevic', '517859'), # ID from Step 857
        ('Michael Zheng', '5004523') # ID from Step 808
    ]
    
    for name, pid in p_info:
        print(f"\n--- Profile for {name} ({pid}) ---")
        try:
            res = requests.get(f"https://app.utrsports.net/api/v1/player/{pid}/profile", headers=headers, cookies=auth['cookies'])
            if res.status_code == 200:
                 print(json.dumps(res.json(), indent=2))
            else:
                 print(f"Failed: {res.status_code}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    dump_profiles()
