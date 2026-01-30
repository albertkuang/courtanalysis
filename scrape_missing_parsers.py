import requests
from bs4 import BeautifulSoup
import csv
import re
import urllib3

urllib3.disable_warnings()

FAILED_SCHOOLS = [
    'Temple', 'Tulsa', 'UAB', 'UTSA', 'East Carolina', 'Dayton', 'Fordham', 
    'George Mason', 'SMU', 'Virginia', 'Virginia Tech', 'Arizona State', 
    'Baylor', 'BYU', 'TCU', 'Portland State', 'Purdue', 'USC', 'Wisconsin', 
    'Campbell', 'College of Charleston', 'Hampton', 'Hofstra', 'Jacksonville State', 
    'Liberty', 'Middle Tennessee', 'IU Indy', 'Quinnipiac', 'A&M-Corpus Christi', 
    'Drake', 'Appalachian State', 'Eastern Kentucky'
]

MD_FILE = 'd1_tennis_directory.md'
OUTPUT_FILE = 'd1_players_v2.csv'

HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}

def get_urls():
    urls = {}
    with open(MD_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4 and parts[1] in FAILED_SCHOOLS:
                u = parts[3]
                if not u.startswith('http'): u = 'https://' + u
                urls[parts[1]] = u
    return urls

def aggressive_extract(soup):
    names = set()
    # 1. Try standard classes again (maybe they were 403 before?)
    # ... (same selectors as before)
    
    # 2. Look for ANY link that looks like a player bio
    # href="/sports/mens-tennis/roster/john-doe/123"
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'roster' in href and re.search(r'/\d+$', href): # Ends in ID
            # Text might be name
            txt = a.get_text(strip=True)
            if txt and len(txt) > 3:
                names.add(txt)
    
    # 3. Look for table cells that contain "Year" or "Class" in the row, then assume another cell is Name
    # This is risky.
    
    return list(names)

def main():
    school_urls = get_urls()
    print(f"Loaded {len(school_urls)} URLs to retry.")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['School', 'Player Name', 'Source URL'])
        
        for school, url in school_urls.items():
            print(f"Retrying {school}...")
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    names = aggressive_extract(soup)
                    if names:
                        print(f"  -> Found {len(names)} names!")
                        for n in names:
                            writer.writerow([school, n, url])
                    else:
                        print("  -> Still no names.")
                else:
                    print(f"  -> Failed: {resp.status_code}")
            except Exception as e:
                print(f"  -> Error: {e}")

if __name__ == "__main__":
    main()
