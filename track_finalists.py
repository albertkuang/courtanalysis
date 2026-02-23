import pandas as pd
import os
import sqlite3
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def main():
    input_file = "itf_junior_finalists_10years_jsonl.csv"
    output_file = "finalist_career_tracking.csv"
    summary_file = "itf_finals_summary.md"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # 1. Clean Data
    # Ensure year is numeric
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    
    # 2. Extract Unique Finalists (Winners and Losers)
    winners = df[['winner_id', 'winner_name', 'winner_utr', 'winner_rank', 'winner_dob', 'winner_college']].rename(columns={
        'winner_id': 'id', 'winner_name': 'name', 'winner_utr': 'utr', 'winner_rank': 'junior_rank', 'winner_dob': 'dob', 'winner_college': 'college'
    })
    winners['role'] = 'Winner'
    
    losers = df[['loser_id', 'loser_name', 'loser_utr', 'loser_rank', 'loser_dob', 'loser_college']].rename(columns={
        'loser_id': 'id', 'loser_name': 'name', 'loser_utr': 'utr', 'loser_rank': 'junior_rank', 'loser_dob': 'dob', 'loser_college': 'college'
    })
    losers['role'] = 'Finalist'
    
    all_finalists = pd.concat([winners, losers])
    
    # Drop duplicates
    unique_players = all_finalists.drop_duplicates(subset=['id']).copy()
    unique_players['id'] = unique_players['id'].astype(str).str.replace('.0', '', regex=False)
    # Initialize pro_rank as NaN
    unique_players['pro_rank'] = pd.NA

    
    # 3. Enrich with DB Rankings
    db_path = "tennis_data.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            
            # Check for map table
            map_check = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='sackmann_player_map'", conn)
            
            if not map_check.empty:
                print("Loading player map from DB...")
                # Fetch player_name too
                player_map = pd.read_sql("SELECT player_id, sackmann_id, player_name as db_name FROM sackmann_player_map WHERE player_id IS NOT NULL", conn)
                player_map['player_id'] = player_map['player_id'].astype(str)
                player_map['sackmann_id'] = player_map['sackmann_id'].astype(str)
                
                print("Loading latest rankings from DB...")
                # Find latest date
                max_date_df = pd.read_sql("SELECT MAX(date) as d FROM rankings", conn)
                if not max_date_df.empty and max_date_df.iloc[0]['d']:
                    max_date = max_date_df.iloc[0]['d']
                    print(f"Using rankings from: {max_date}")
                    
                    rankings = pd.read_sql(f"SELECT player_id, rank FROM rankings WHERE date = '{max_date}'", conn)
                    
                    # Extract numeric ID from rankings.player_id (e.g. 'atp_104925' -> '104925')
                    def extract_id(pid):
                        parts = pid.split('_')
                        return parts[-1] if len(parts) > 1 else pid
                        
                    rankings['sackmann_id'] = rankings['player_id'].apply(extract_id).astype(str)
                    
                    # Merge map with rankings to get UTR_ID -> Rank
                    # map: player_id (UTR) -> sackmann_id
                    # rankings: sackmann_id -> rank
                    
                    mapped_ranks = player_map.merge(rankings[['sackmann_id', 'rank']], on='sackmann_id', how='inner')
                    # Keep one rank per player
                    mapped_ranks = mapped_ranks.drop_duplicates(subset=['player_id'])
                    
                    print(f"Found rankings for {len(mapped_ranks)} mapped players.")
                    
                    # Merge with unique_players to check names
                    merged = unique_players.merge(mapped_ranks[['player_id', 'rank', 'db_name']], left_on='id', right_on='player_id', how='left')
                    
                    # Validate names
                    valid_ranks = []
                    for idx, row in merged.iterrows():
                        if pd.notna(row['rank']) and pd.notna(row['db_name']):
                            sim = similar(row['name'], row['db_name'])
                            if sim >= 0.6: # Threshold
                                valid_ranks.append(row['rank'])
                            else:
                                valid_ranks.append(pd.NA)
                        else:
                            valid_ranks.append(pd.NA)
                            
                    merged['pro_rank'] = valid_ranks
                    
                    # Merge back to unique_players
                    unique_players['pro_rank'] = merged['pro_rank']
                    
                    # UTR Sanity Check
                    # If rank is high (<= 1000) but UTR is low (< 10), it's likely a bad map/data error
                    # Ensure UTR is float
                    unique_players['utr'] = pd.to_numeric(unique_players['utr'], errors='coerce')
                    
                    mask_bad_utr = (unique_players['pro_rank'] <= 1000) & (unique_players['utr'] < 10.0)
                    bad_utr_count = mask_bad_utr.sum()
                    print(f"Removed {bad_utr_count} ranks due to low UTR (< 10.0) for top 1000 players.")
                    
                    unique_players.loc[mask_bad_utr, 'pro_rank'] = pd.NA
                    
                    # Count verified
                    verified_count = unique_players['pro_rank'].notna().sum()
                    print(f"Verified {verified_count} pro rankings after name validation and UTR sanity check.")
                    
            conn.close()
        except Exception as e:
            print(f"Database error: {e}")
    else:
        print("Database not found, skipping enrichment.")

    # 4. Analyze Pro Rankings
    unique_players['pro_rank'] = pd.to_numeric(unique_players['pro_rank'], errors='coerce')
    
    has_rank = unique_players[unique_players['pro_rank'].notna()]
    print(f"Players with current Pro Rank: {len(has_rank)} ({len(has_rank)/len(unique_players)*100:.1f}%)")
    
    top_100 = has_rank[has_rank['pro_rank'] <= 100]
    top_500 = has_rank[has_rank['pro_rank'] <= 500]
    
    print(f"Top 100 Pro: {len(top_100)}")
    print(f"Top 500 Pro: {len(top_500)}")
    
    # 5. College Recruitment
    has_college = unique_players[unique_players['college'].notna() & (unique_players['college'] != 'None')]
    print(f"Players with College Listed: {len(has_college)}")
    
    # 6. Export Tracking Sheet
    tracking_df = unique_players.sort_values(by='pro_rank', ascending=True)
    tracking_df.to_csv(output_file, index=False)
    print(f"Saved career tracking data to {output_file}")
    
    # 7. Generate Summary
    with open(summary_file, "w") as f:
        f.write("# ITF Junior Finals Analysis (Last 10 Years)\n\n")
        f.write(f"- **Total Finals Analyzed**: {len(df)}\n")
        f.write(f"- **Unique Finalists**: {len(unique_players)}\n")
        f.write(f"- **Players with Pro Rank**: {len(has_rank)} ({len(has_rank)/len(unique_players)*100:.1f}%)\n")
        f.write(f"- **Top 100 Players**: {len(top_100)}\n")
        f.write(f"- **Top 500 Players**: {len(top_500)}\n")
        f.write(f"- **College Commits**: {len(has_college)}\n\n")
        
        f.write("## Top 50 Pro Players from Junior Finalists\n")
        f.write("| Rank | Name | UTR | DOB | College |\n")
        f.write("|---|---|---|---|---|\n")
        
        for _, p in tracking_df.head(50).iterrows():
            r = f"{p['pro_rank']:.0f}" if pd.notna(p['pro_rank']) else "-"
            c = p['college'] if pd.notna(p['college']) else "-"
            dob = p['dob'].split('T')[0] if pd.notna(p['dob']) and 'T' in str(p['dob']) else str(p['dob'])
            f.write(f"| {r} | {p['name']} | {p['utr']} | {dob} | {c} |\n")

if __name__ == "__main__":
    main()
