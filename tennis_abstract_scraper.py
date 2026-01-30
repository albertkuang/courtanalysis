#!/usr/bin/env python3
"""
Tennis Abstract Scraper
Scrapes player statistics and Elo ratings from tennisabstract.com
"""

import requests
import re
import json
import csv
import argparse
import sys
from datetime import datetime

# Constants
BASE_URL = "https://www.tennisabstract.com"
WTA_ELO_URL = f"{BASE_URL}/reports/wta_elo_ratings.html"
ATP_ELO_URL = f"{BASE_URL}/reports/atp_elo_ratings.html"

# Match Charting Project GitHub raw URLs
GITHUB_MCP_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master"
MCP_ATP_MATCHES = f"{GITHUB_MCP_BASE}/charting-m-matches.csv"
MCP_WTA_MATCHES = f"{GITHUB_MCP_BASE}/charting-w-matches.csv"
MCP_ATP_OVERVIEW = f"{GITHUB_MCP_BASE}/charting-m-stats-Overview.csv"
MCP_WTA_OVERVIEW = f"{GITHUB_MCP_BASE}/charting-w-stats-Overview.csv"


def get_player_url(player_name, gender='F'):
    """Generate Tennis Abstract URL for a player."""
    # Format name for URL (remove spaces, capitalize properly)
    formatted = player_name.replace(' ', '')
    if gender.upper() == 'F':
        return f"{BASE_URL}/cgi-bin/wplayer.cgi?p={formatted}"
    else:
        return f"{BASE_URL}/cgi-bin/player.cgi?p={formatted}"


def extract_js_variable(html, var_name):
    """Extract a JavaScript variable value from HTML."""
    # Match patterns like: var name = 'value'; or var name = 123;
    patterns = [
        rf"var\s+{var_name}\s*=\s*'([^']*)'",  # String with single quotes
        rf"var\s+{var_name}\s*=\s*\"([^\"]*)\"",  # String with double quotes
        rf"var\s+{var_name}\s*=\s*(\d+\.?\d*)",  # Number
        rf"var\s+{var_name}\s*=\s*(\d+)",  # Integer
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def scrape_player(player_name, gender='F'):
    """Scrape a player's profile from Tennis Abstract."""
    url = get_player_url(player_name, gender)
    
    print(f"Fetching: {url}")
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching player page: {e}")
        return None
    
    html = resp.text
    
    # Check if player was found
    if "Player not found" in html or len(html) < 1000:
        print(f"Player not found: {player_name}")
        return None
    
    # Extract JavaScript variables from the page
    player_data = {
        'name': extract_js_variable(html, 'fullname') or player_name,
        'country': extract_js_variable(html, 'country'),
        'currentRank': extract_js_variable(html, 'currentrank'),
        'peakRank': extract_js_variable(html, 'peakrank'),
        'peakRankDate': None,
        'dob': extract_js_variable(html, 'dob'),
        'age': None,
        'height': extract_js_variable(html, 'ht'),
        'hand': extract_js_variable(html, 'hand'),
        'backhand': extract_js_variable(html, 'backhand'),
        'eloRating': extract_js_variable(html, 'elo_rating'),
        'eloRank': extract_js_variable(html, 'elo_rank'),
        'itfId': extract_js_variable(html, 'itf_id'),
        'profileUrl': url,
        'scrapedAt': datetime.now().isoformat()
    }
    
    # Parse peak rank date
    peak_first = extract_js_variable(html, 'peakfirst')
    if peak_first and len(peak_first) == 8:
        try:
            player_data['peakRankDate'] = f"{peak_first[:4]}-{peak_first[4:6]}-{peak_first[6:]}"
        except:
            pass
    
    # Calculate age from DOB
    dob = player_data.get('dob')
    if dob and len(str(dob)) == 8:
        try:
            dob_str = str(dob)
            birth_date = datetime(int(dob_str[:4]), int(dob_str[4:6]), int(dob_str[6:]))
            today = datetime.now()
            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
            player_data['age'] = age
        except:
            pass
    
    # Convert numeric strings to proper types
    for field in ['currentRank', 'peakRank', 'height', 'eloRating', 'eloRank']:
        if player_data.get(field):
            try:
                player_data[field] = int(float(player_data[field]))
            except:
                pass
    
    # Map hand codes
    hand_map = {'L': 'Left', 'R': 'Right'}
    if player_data.get('hand') in hand_map:
        player_data['handFull'] = hand_map[player_data['hand']]
    
    # Map backhand codes
    bh_map = {'1': 'One-handed', '2': 'Two-handed'}
    if player_data.get('backhand') in bh_map:
        player_data['backhandFull'] = bh_map[player_data['backhand']]
    
    return player_data


def scrape_elo_list(gender='F', limit=100):
    """Scrape the Elo ratings list."""
    url = WTA_ELO_URL if gender.upper() == 'F' else ATP_ELO_URL
    tour = 'WTA' if gender.upper() == 'F' else 'ATP'
    
    print(f"Fetching {tour} Elo ratings from: {url}")
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching Elo list: {e}")
        return []
    
    html = resp.text
    players = []
    
    # Find the tablesorter table
    table_match = re.search(r'<table[^>]*class="tablesorter"[^>]*>(.*?)</table>', html, re.DOTALL)
    if table_match:
        table_html = table_match.group(1)
        # Extract rows
        row_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
        
        for row in row_matches[1:limit+1]:  # Skip header row
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 6:
                try:
                    # Cell 0: Elo Rank, Cell 1: Name (with link), Cell 2: Age, Cell 3: Elo Rating, Cell 5: Official Rank
                    # Extract player name from link
                    name_match = re.search(r'>([^<]+)</a>', cells[1])
                    name = name_match.group(1) if name_match else re.sub(r'<[^>]+>', '', cells[1])
                    name = name.strip().replace('&nbsp;', ' ').replace('&#160;', ' ')
                    
                    # Clean cells
                    elo_rank = int(re.sub(r'[^\d]', '', cells[0])) if cells[0] else 0
                    age_str = re.sub(r'[^\d.]', '', cells[2])
                    age = float(age_str) if age_str else None
                    elo_str = re.sub(r'[^\d.]', '', cells[3])
                    elo_rating = int(float(elo_str)) if elo_str else 0
                    
                    # Official rank is in cell 5
                    official_str = re.sub(r'[^\d]', '', cells[5]) if len(cells) > 5 else ''
                    official_rank = int(official_str) if official_str else None
                    
                    players.append({
                        'eloRank': elo_rank,
                        'name': name,
                        'age': age,
                        'eloRating': elo_rating,
                        'officialRank': official_rank
                    })
                except (ValueError, IndexError) as e:
                    continue
    
    print(f"Found {len(players)} players in Elo list")
    return players


def fetch_charting_matches(gender='F', limit=100):
    """Fetch match charting data from GitHub."""
    url = MCP_WTA_MATCHES if gender.upper() == 'F' else MCP_ATP_MATCHES
    tour = 'WTA' if gender.upper() == 'F' else 'ATP'
    
    print(f"Fetching {tour} charted matches from GitHub...")
    
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching charting data: {e}")
        return []
    
    lines = resp.text.strip().split('\n')
    if not lines:
        return []
    
    # Parse CSV header
    header = lines[0].split(',')
    matches = []
    
    for line in lines[1:limit+1]:
        try:
            values = line.split(',')
            if len(values) >= 10:
                match = {
                    'matchId': values[0],
                    'player1': values[1],
                    'player2': values[2],
                    'player1Hand': values[3],
                    'player2Hand': values[4],
                    'date': values[5],
                    'tournament': values[6],
                    'round': values[7],
                    'surface': values[10] if len(values) > 10 else '',
                    'chartedBy': values[-1] if len(values) > 14 else ''
                }
                matches.append(match)
        except (IndexError, ValueError):
            continue
    
    print(f"Found {len(matches)} charted matches")
    return matches


def fetch_player_charted_matches(player_name, gender='F', limit=50):
    """Fetch all charted matches for a specific player."""
    url = MCP_WTA_MATCHES if gender.upper() == 'F' else MCP_ATP_MATCHES
    
    print(f"Searching charted matches for {player_name}...")
    
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching charting data: {e}")
        return []
    
    lines = resp.text.strip().split('\n')
    if not lines:
        return []
    
    # Normalize player name for matching
    search_name = player_name.lower().replace(' ', '_')
    search_name_alt = player_name.lower().replace(' ', '')
    
    matches = []
    for line in lines[1:]:
        try:
            values = line.split(',')
            if len(values) >= 10:
                p1 = values[1].lower().replace(' ', '')
                p2 = values[2].lower().replace(' ', '')
                
                if search_name_alt in p1 or search_name_alt in p2:
                    match = {
                        'matchId': values[0],
                        'player1': values[1],
                        'player2': values[2],
                        'date': values[5],
                        'tournament': values[6],
                        'round': values[7],
                        'surface': values[10] if len(values) > 10 else '',
                        'chartUrl': f"{BASE_URL}/charting/{values[0]}.html"
                    }
                    matches.append(match)
                    if len(matches) >= limit:
                        break
        except (IndexError, ValueError):
            continue
    
    print(f"Found {len(matches)} charted matches for {player_name}")
    return matches


def fetch_player_charting_stats(player_name, gender='F'):
    """Fetch aggregated charting stats for a player from Overview CSV."""
    url = MCP_WTA_OVERVIEW if gender.upper() == 'F' else MCP_ATP_OVERVIEW
    
    print(f"Fetching charting stats for {player_name}...")
    
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching stats: {e}")
        return None
    
    lines = resp.text.strip().split('\n')
    if len(lines) < 2:
        return None
    
    # Parse header
    header = lines[0].split(',')
    search_name = player_name.lower().replace(' ', '')
    
    # Find player matches and aggregate stats
    player_stats = {
        'matchCount': 0,
        'aces': 0,
        'doubleFaults': 0,
        'firstServeIn': 0,
        'firstServeTotal': 0,
        'firstServeWon': 0,
        'secondServeWon': 0,
        'breakPointsSaved': 0,
        'breakPointsFaced': 0,
        'serviceGamesWon': 0,
        'serviceGamesTotal': 0,
        'returnPointsWon': 0,
        'returnPointsTotal': 0,
        'winners': 0,
        'unforcedErrors': 0
    }
    
    for line in lines[1:]:
        try:
            values = line.split(',')
            if len(values) < 3:
                continue
            
            player_col = values[1].lower().replace(' ', '')
            if search_name in player_col:
                # Found a match for this player
                player_stats['matchCount'] += 1
                
                # Parse stats (columns vary, but typical structure)
                # Column indices may need adjustment based on actual CSV structure
                try:
                    if len(values) > 5:
                        player_stats['aces'] += int(values[3]) if values[3].isdigit() else 0
                        player_stats['doubleFaults'] += int(values[4]) if values[4].isdigit() else 0
                except (ValueError, IndexError):
                    pass
        except (IndexError, ValueError):
            continue
    
    if player_stats['matchCount'] == 0:
        print(f"No charting stats found for {player_name}")
        return None
    
    print(f"Found stats from {player_stats['matchCount']} charted matches")
    return player_stats


def output_json(data, filename=None):
    """Output data as JSON."""
    json_str = json.dumps(data, indent=2, default=str)
    if filename:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"Saved to: {filename}")
    else:
        print(json_str)


def output_csv(data, filename):
    """Output data as CSV."""
    if not data:
        print("No data to export")
        return
    
    # Handle single player dict or list of players
    if isinstance(data, dict):
        data = [data]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(description='Scrape Tennis Abstract player data and match charting')
    parser.add_argument('--player', type=str, help='Player name to search')
    parser.add_argument('--gender', type=str, default='F', choices=['M', 'F'],
                        help='Gender: M for ATP, F for WTA (default: F)')
    parser.add_argument('--output', type=str, default='json', choices=['json', 'csv'],
                        help='Output format (default: json)')
    parser.add_argument('--elo-list', action='store_true',
                        help='Fetch Elo ratings list')
    parser.add_argument('--charted-matches', action='store_true',
                        help='Fetch recent charted matches from Match Charting Project')
    parser.add_argument('--player-matches', action='store_true',
                        help='Fetch charted matches for a specific player (use with --player)')
    parser.add_argument('--player-stats', action='store_true',
                        help='Fetch charting stats for a specific player (use with --player)')
    parser.add_argument('--limit', type=int, default=100,
                        help='Limit number of results (default: 100)')
    parser.add_argument('--save', type=str, help='Save output to file')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("        TENNIS ABSTRACT SCRAPER")
    print("         + Match Charting Project")
    print("=" * 60)
    
    if args.charted_matches:
        # Fetch recent charted matches
        data = fetch_charting_matches(args.gender, args.limit)
        
        if data:
            print(f"\nRecent Charted Matches ({args.limit}):")
            print("-" * 70)
            for m in data[:15]:
                date = m.get('date', '')
                if len(date) == 8:
                    date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
                print(f"  {date}  {m['tournament']:<20} {m['round']:<5} {m['player1']} vs {m['player2']}")
            
            if args.save:
                if args.output == 'csv':
                    output_csv(data, args.save)
                else:
                    output_json(data, args.save)
    
    elif args.player_matches and args.player:
        # Fetch charted matches for a player
        data = fetch_player_charted_matches(args.player, args.gender, args.limit)
        
        if data:
            print(f"\nCharted Matches for {args.player}:")
            print("-" * 70)
            for m in data[:20]:
                date = m.get('date', '')
                if len(date) == 8:
                    date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
                opp = m['player1'] if args.player.lower().replace(' ', '') not in m['player1'].lower().replace(' ', '') else m['player2']
                print(f"  {date}  {m['tournament']:<20} {m['round']:<5} vs {opp}")
            
            if args.save:
                if args.output == 'csv':
                    output_csv(data, args.save)
                else:
                    output_json(data, args.save)
    
    elif args.player_stats and args.player:
        # Fetch charting stats for a player
        data = fetch_player_charting_stats(args.player, args.gender)
        
        if data:
            print(f"\n{'=' * 50}")
            print(f"CHARTING STATS: {args.player}")
            print(f"{'=' * 50}")
            print(f"  Charted Matches:   {data.get('matchCount', 0)}")
            print(f"  Total Aces:        {data.get('aces', 0)}")
            print(f"  Total DFs:         {data.get('doubleFaults', 0)}")
            
            if args.save:
                output_json(data, args.save)
    
    elif args.elo_list:
        # Fetch Elo ratings list
        data = scrape_elo_list(args.gender, args.limit)
        
        if data:
            print(f"\nTop {min(10, len(data))} by Elo Rating:")
            print("-" * 50)
            for p in data[:10]:
                age_str = f"{p['age']:.1f}" if p.get('age') else "-"
                rank_str = f"#{p['officialRank']}" if p.get('officialRank') else "-"
                print(f"  {p['eloRank']:3}. {p['name']:<25} Age: {age_str:<5} Rank: {rank_str:<5} Elo: {p['eloRating']}")
            
            if args.save:
                if args.output == 'csv':
                    output_csv(data, args.save)
                else:
                    output_json(data, args.save)
            elif args.output == 'json':
                pass  # Already printed
    
    elif args.player:
        # Fetch single player profile
        data = scrape_player(args.player, args.gender)
        
        if data:
            print(f"\n{'=' * 50}")
            print(f"PLAYER: {data.get('name', 'Unknown')}")
            print(f"{'=' * 50}")
            print(f"  Country:      {data.get('country', '-')}")
            print(f"  Age:          {data.get('age', '-')}")
            print(f"  Hand:         {data.get('handFull', data.get('hand', '-'))}")
            print(f"  Backhand:     {data.get('backhandFull', data.get('backhand', '-'))}")
            print(f"  Height:       {data.get('height', '-')} cm")
            print(f"  Current Rank: {data.get('currentRank', '-')}")
            print(f"  Peak Rank:    {data.get('peakRank', '-')} ({data.get('peakRankDate', '-')})")
            print(f"  Elo Rating:   {data.get('eloRating', '-')}")
            print(f"  Elo Rank:     {data.get('eloRank', '-')}")
            print(f"  ITF ID:       {data.get('itfId', '-')}")
            print(f"  Profile URL:  {data.get('profileUrl', '-')}")
            
            if args.save:
                if args.output == 'csv':
                    output_csv(data, args.save)
                else:
                    output_json(data, args.save)
            elif args.output == 'json':
                print("\nJSON Output:")
                output_json(data)
    
    else:
        parser.print_help()
        print("\n" + "=" * 60)
        print("EXAMPLES:")
        print("=" * 60)
        print("\n  Player Profile:")
        print("    python tennis_abstract_scraper.py --player=\"Leylah Fernandez\" --gender=F")
        print("    python tennis_abstract_scraper.py --player=\"Jannik Sinner\" --gender=M")
        print("\n  Elo Rankings:")
        print("    python tennis_abstract_scraper.py --elo-list --gender=F --limit=50")
        print("\n  Match Charting (NEW!):")
        print("    python tennis_abstract_scraper.py --charted-matches --gender=F --limit=20")
        print("    python tennis_abstract_scraper.py --player=\"Iga Swiatek\" --player-matches")
        print("    python tennis_abstract_scraper.py --player=\"Carlos Alcaraz\" --gender=M --player-stats")


if __name__ == '__main__':
    main()
