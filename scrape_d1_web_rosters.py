import requests
from bs4 import BeautifulSoup
import csv
import re
import sys
import time
import os
import urllib3

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCE_FILE = 'd2_tennis_directory_women.md'
OUTPUT_FILE = 'd2_players_from_web_women.csv'
LOG_FILE = 'd2_scraper_log_women.txt'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

def log(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)

def get_existing_schools():
    schools = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None) # Skip header
                for row in reader:
                    if row:
                        schools.add(row[0])
        except Exception:
            pass
    return schools

def get_session():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=2)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update(HEADERS)
    session.verify = False
    return session

def get_urls_from_md():
    urls = []
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('|'):
                continue
            if 'Roster Link Pattern' in line or '---' in line:
                continue
                
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                school = parts[1]
                url_raw = parts[3]
                if school and url_raw:
                    if not url_raw.startswith('http'):
                        url = 'https://' + url_raw
                    else:
                        url = url_raw
                    urls.append((school, url))
    return urls

def extract_names(soup, school_name):
    names = set()
    
    # 1. Sidearm Sports / Common Generic 
    selectors = [
        '.sidearm-roster-player-name', 
        '.player-name', 
        '.roster-name', 
        '.roster_dgrd_full_name',
        'td[data-label="Name"]'
    ]
    
    for sel in selectors:
        elements = soup.select(sel)
        if elements:
            for el in elements:
                text = el.get_text(" ", strip=True)
                text = re.sub(r'\s+', ' ', text).strip()
                if text and len(text) > 2 and text.lower() != "name":
                    names.add(text)
            if len(names) > 0:
                break 
    
    # Fallback: Look for ANY table with a "Name" header
    if not names:
        tables = soup.find_all('table')
        for tbl in tables:
            # Check headers
            header_row = tbl.find('tr')
            if not header_row:
                continue
                
            header_cells = header_row.find_all(['th', 'td'])
            headers = [c.get_text(strip=True).lower() for c in header_cells]
            
            # Find name column index
            name_idx = -1
            for i, h in enumerate(headers):
                if h in ['name', 'full name', 'player', 'student-athlete', 'roster']:
                    name_idx = i
                    break
            
            if name_idx == -1: 
                continue
                
            # Iterate rows
            rows = tbl.find_all('tr')
            for row in rows[1:]: # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) > name_idx:
                    txt = cols[name_idx].get_text(" ", strip=True)
                    if "\n" in txt:
                        txt = txt.split("\n")[0]
                    txt = re.sub(r'^\d+\s*', '', txt)
                    
                    if txt and len(txt) > 3 and txt.lower() not in ['name', 'team', 'totals']:
                        names.add(txt)
    # Strategy 3: Look for links to player profiles (common in Sidearm grids)
    if not names:
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            # Virginia pattern: /sports/mten/roster/player/stiles-brockett
            # General Sidearm: /roster/player/
            if '/roster/player/' in href or '/roster/' in href and '/player/' in href:
                # Often the link text is the name, or headers inside
                txt = link.get_text(" ", strip=True)
                # Clean up
                txt = re.sub(r'\s+', ' ', txt).strip()
                # Ignore "View Bio" or similar
                if txt and len(txt) > 3 and "Bio" not in txt and "Stats" not in txt:
                    names.add(txt)

    # Cleanup names
    cleaned_names = []
    for n in names:
        n = re.sub(r'\d+', '', n) 
        n = n.replace('Full Bio', '').replace('View Bio', '').strip()
        if ' ' in n and len(n) < 50:
             cleaned_names.append(n)
             
    return cleaned_names

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scrape d2 Tennis Rosters')
    parser.add_argument('--school', type=str, help='Filter by school name (partial match)', default=None)
    args = parser.parse_args()

    urls = get_urls_from_md()
    existing_schools = get_existing_schools()
    
    # Filter if argument provided
    if args.school:
        urls = [u for u in urls if args.school.lower() in u[0].lower()]
        # If forcing a school, ignore whether it was already scraped
        # existing_schools = set() 
    
    log(f"Found {len(urls)} schools to scrape.")
    if not args.school:
        log(f"Skipping {len(existing_schools)} schools already scraped.")
    
    mode = 'a' if os.path.exists(OUTPUT_FILE) else 'w'
    
    with open(OUTPUT_FILE, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if mode == 'w':
            writer.writerow(['School', 'Player Name', 'Source URL'])
        
        session = get_session()
        
        for i, (school, url) in enumerate(urls):
            if not args.school and school in existing_schools:
                continue
                
            log(f"[{i+1}/{len(urls)}] Scraping {school} ({url})...")
            
            try:
                resp = session.get(url, timeout=15)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    players = extract_names(soup, school)
                    
                    if players:
                        log(f"  -> Found {len(players)} players.")
                        for p in players:
                            writer.writerow([school, p, url])
                    else:
                        log(f"  -> No players found (parsing failed or empty page).")
                else:
                    log(f"  -> Failed (Status {resp.status_code})")
                    
            except Exception as e:
                log(f"  -> Error: {str(e)[:100]}")
            
            f.flush()
            time.sleep(1.0) 

if __name__ == "__main__":
    main()
