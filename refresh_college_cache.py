
import college_roster_scraper
import json
import os
import time

CACHE_FILE = 'college_data.json'

def refresh_cache():
    print("Logging in...")
    auth = college_roster_scraper.login()
    print("Logged in.")
    
    data = {}
    divisions = ['D1', 'D2', 'D3', 'NAIA', 'JUCO']
    
    for div in divisions:
        for attempt in range(3):
            try:
                print(f"Fetching {div} colleges (Attempt {attempt+1})...")
                # Fetch with a high limit to get all
                results = college_roster_scraper.search_colleges(auth, div, limit=2000)
                print(f"  Found {len(results)} colleges for {div}")
                data[div] = results
                break
            except Exception as e:
                print(f"  Error fetching {div}: {e}")
                time.sleep(5)
        
        time.sleep(2)
        
    print(f"Saving to {CACHE_FILE}...")
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    refresh_cache()
