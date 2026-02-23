#!/usr/bin/env python3
"""
Import Tennis Abstract Elo ratings into the database.
Scrapes Elo ratings from tennisabstract.com and stores them in the database.
"""

import requests
import re
import sqlite3
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, '.')
import tennis_db

# Constants
BASE_URL = "https://www.tennisabstract.com"
WTA_ELO_URL = f"{BASE_URL}/reports/wta_elo_ratings.html"
ATP_ELO_URL = f"{BASE_URL}/reports/atp_elo_ratings.html"


def scrape_elo_list(gender='F', limit=200):
    """Scrape the Elo ratings list from Tennis Abstract."""
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
                        'tour': tour,
                        'player_name': name,
                        'elo_rank': elo_rank,
                        'age': age,
                        'elo_rating': elo_rating,
                        'official_rank': official_rank
                    })
                except (ValueError, IndexError) as e:
                    continue
    
    print(f"Found {len(players)} players in Elo list")
    return players


def import_elo_to_db(players, tour):
    """Import Elo ratings into the database."""
    conn = tennis_db.get_connection()
    c = conn.cursor()
    
    # Clear existing data for this tour
    c.execute("DELETE FROM tennis_abstract_elo WHERE tour = ?", (tour,))
    print(f"Cleared existing {tour} Elo data")
    
    # Insert new data
    imported = 0
    for p in players:
        try:
            c.execute("""
                INSERT INTO tennis_abstract_elo 
                (tour, player_name, elo_rank, elo_rating, official_rank, age, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                p['tour'],
                p['player_name'],
                p['elo_rank'],
                p['elo_rating'],
                p['official_rank'],
                p['age'],
                datetime.now()
            ))
            imported += 1
        except Exception as e:
            print(f"Error inserting {p['player_name']}: {e}")
    
    conn.commit()
    conn.close()
    print(f"Imported {imported} {tour} Elo ratings")
    return imported


def get_latest_elo(tour, limit=50):
    """Get the latest Elo rankings from the database."""
    conn = tennis_db.get_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT elo_rank, player_name, elo_rating, official_rank, age, scraped_at
        FROM tennis_abstract_elo
        WHERE tour = ?
        ORDER BY elo_rank ASC
        LIMIT ?
    """, (tour, limit))
    
    results = c.fetchall()
    conn.close()
    
    return [
        {
            'elo_rank': r[0],
            'player_name': r[1],
            'elo_rating': r[2],
            'official_rank': r[3],
            'age': r[4],
            'scraped_at': r[5]
        }
        for r in results
    ]


def main():
    print("=" * 60)
    print("  TENNIS ABSTRACT ELO RATINGS IMPORTER")
    print("=" * 60)
    
    total_imported = 0
    
    # Scrape and import ATP Elo
    print("\n--- Fetching ATP Elo Ratings ---")
    atp_players = scrape_elo_list('M', 200)
    if atp_players:
        total_imported += import_elo_to_db(atp_players, 'ATP')
    
    # Scrape and import WTA Elo
    print("\n--- Fetching WTA Elo Ratings ---")
    wta_players = scrape_elo_list('F', 200)
    if wta_players:
        total_imported += import_elo_to_db(wta_players, 'WTA')
    
    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Total Elo ratings imported: {total_imported}")
    
    # Show sample data
    print("\n--- Sample ATP Elo (Top 10) ---")
    atp_latest = get_latest_elo('ATP', 10)
    for p in atp_latest:
        print(f"  #{p['elo_rank']:3} {p['player_name']:<25} Elo: {p['elo_rating']:<5} Official: #{p['official_rank']}")
    
    print("\n--- Sample WTA Elo (Top 10) ---")
    wta_latest = get_latest_elo('WTA', 10)
    for p in wta_latest:
        print(f"  #{p['elo_rank']:3} {p['player_name']:<25} Elo: {p['elo_rating']:<5} Official: #{p['official_rank']}")


if __name__ == "__main__":
    main()
