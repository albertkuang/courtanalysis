"""
Regenerate 2025-2026 ranking data with realistic rank variations.
Since real 2025-2026 data isn't available from public sources, this script:
1. Clears all 2025+ mock data
2. Regenerates with proper rank recalculation based on point variations

This creates more realistic ranking charts where ranks change over time.
"""
import sqlite3
from datetime import datetime, timedelta
import random

def get_db_connection():
    conn = sqlite3.connect('tennis_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def main():
    print("=" * 60)
    print("Regenerating 2025-2026 Rankings with Realistic Variations")
    print("=" * 60)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Step 1: Delete existing 2025+ data
    print("\n[1] Deleting existing 2025+ mock data...")
    c.execute("DELETE FROM rankings WHERE date >= '2025-01-01'")
    deleted = c.rowcount
    conn.commit()
    print(f"    Deleted {deleted} rows")
    
    # Step 2: Get base data from end of 2024
    print("\n[2] Loading base data from 2024-12-30...")
    c.execute("""
        SELECT player_id, rank, points, tours 
        FROM rankings 
        WHERE date = '2024-12-30'
        ORDER BY rank ASC
    """)
    base_data = [dict(r) for r in c.fetchall()]
    print(f"    Found {len(base_data)} players")
    
    # Separate ATP and WTA
    atp_players = [p for p in base_data if p['player_id'].startswith('atp_')]
    wta_players = [p for p in base_data if p['player_id'].startswith('wta_')]
    
    print(f"    ATP: {len(atp_players)}, WTA: {len(wta_players)}")
    
    # Step 3: Generate weekly rankings for 2025-2026
    print("\n[3] Generating weekly rankings with rank variations...")
    
    # Generate all Mondays from Jan 2025 to Feb 2026
    start_date = datetime(2025, 1, 6)
    end_date = datetime(2026, 2, 9)
    
    weeks = []
    current = start_date
    while current <= end_date:
        weeks.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=7)
    
    print(f"    Generating {len(weeks)} weeks of data")
    
    total_imported = 0
    
    for tour_name, players in [('ATP', atp_players), ('WTA', wta_players)]:
        print(f"\n    Processing {tour_name}...")
        
        # Keep track of current points for each player
        player_points = {p['player_id']: p['points'] for p in players}
        
        for week_idx, week_date in enumerate(weeks):
            # Apply random point changes
            for player_id in player_points:
                # Random weekly point change: -50 to +100 (slightly positive bias for activity)
                change = random.randint(-50, 100)
                # Also add some larger swings occasionally (tournament results)
                if random.random() < 0.1:  # 10% chance of big change
                    change += random.randint(-200, 400)
                
                player_points[player_id] = max(0, player_points[player_id] + change)
            
            # Sort players by points to get new rankings
            sorted_players = sorted(player_points.items(), key=lambda x: x[1], reverse=True)
            
            # Insert rankings for this week
            for new_rank, (player_id, points) in enumerate(sorted_players, 1):
                rank_id = f"{week_date.replace('-', '')}_{player_id}"
                
                c.execute("""
                    INSERT INTO rankings (rank_id, date, player_id, rank, points, tours)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (rank_id, week_date, player_id, new_rank, points))
                total_imported += 1
            
            # Commit every week
            conn.commit()
            
            if week_idx % 10 == 0:
                print(f"      Week {week_idx + 1}/{len(weeks)}: {week_date}")
    
    # Final stats
    c.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM rankings")
    stats = c.fetchone()
    
    print("\n" + "=" * 60)
    print("REGENERATION COMPLETE")
    print(f"Total rankings generated: {total_imported:,}")
    print(f"Rankings table spans: {stats[0]} to {stats[1]}")
    print(f"Total entries: {stats[2]:,}")
    print("=" * 60)
    
    # Verify Gabriel Diallo's data
    print("\nVerifying Gabriel Diallo's rankings:")
    c.execute("""
        SELECT date, rank, points 
        FROM rankings 
        WHERE player_id = 'atp_209113' 
        ORDER BY date DESC 
        LIMIT 10
    """)
    for r in c.fetchall():
        print(f"  {r[0]}: Rank {r[1]}, Points {r[2]}")
    
    conn.close()

if __name__ == "__main__":
    main()
