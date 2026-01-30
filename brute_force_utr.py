import requests
import json

CONFIG = {'email': 'alberto.kuang@gmail.com', 'password': 'Spring2025'}

def try_endpoints(pid):
    resp = requests.post("https://app.utrsports.net/api/v1/auth/login", json=CONFIG)
    token = resp.json().get('jwt')
    headers = {'Authorization': f"Bearer {token}"}
    
    endpoints = [
        f"https://app.utrsports.net/api/v1/player/{pid}",
        f"https://app.utrsports.net/api/v1/player/{pid}/rating",
        f"https://app.utrsports.net/api/v1/player/{pid}/ratings",
        f"https://app.utrsports.net/api/v1/player/{pid}/historic-ratings",
        f"https://app.utrsports.net/api/v2/search/players?query={pid}",
        f"https://app.utrsports.net/api/v2/player/{pid}"
    ]
    
    for url in endpoints:
        print(f"Trying {url}...")
        try:
            r = requests.get(url, headers=headers)
            print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                # Search for 12.37 in decimal or string
                s_data = json.dumps(data)
                if "12.37" in s_data:
                    print("  !!! FOUND 12.37 !!!")
                elif "12." in s_data:
                    # Print fields that start with 12.
                    pass
        except:
            print("  Errored.")

if __name__ == "__main__":
    try_endpoints(3061144)
