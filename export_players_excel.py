
import sqlite3
import pandas as pd
import argparse
import os
import re
import sys
from datetime import datetime, timedelta
import tennis_db

# ============================================
# ARGUMENTS (Moved to main)
# ============================================


# ============================================
# HELPER FUNCTIONS
# ============================================
def clean_sheet_name(name):
    """Excel sheet names must be <= 31 chars and no special chars."""
    if not name: return "Unknown"
    clean = re.sub(r'[\\/*?:\[\]]', '', name)
    return clean[:30]

def calculate_metrics(player_id, matches, history, current_utr):
    """
    Calculate metrics from match data (offline mode).
    matches: list of match dicts
    history: list of history dicts
    current_utr: float
    """
    wins = 0
    losses = 0
    upsets = 0
    recent_form = []
    
    opponent_utrs = []
    
    # 3-set stats
    three_set_wins = 0
    three_set_losses = 0
    
    # Tiebreak stats
    tb_wins = 0
    tb_losses = 0
    
    # Comeback wins
    comeback_wins = 0
    
    # Higher rated stats
    hr_wins = 0
    hr_matches = 0
    
    # Tournaments
    tournaments = set()
    
    # Sort matches by date descending
    sorted_matches = sorted(matches, key=lambda x: x['date'] if x['date'] else '', reverse=True)
    
    for m in sorted_matches:
        is_winner = str(m['winner_id']) == str(player_id)
        is_loser = str(m['loser_id']) == str(player_id)
        
        # Determine opponent UTR
        opp_utr = m['loser_utr'] if is_winner else m['winner_utr']
        my_utr_in_match = m['winner_utr'] if is_winner else m['loser_utr']
        
        if opp_utr:
            opponent_utrs.append(opp_utr)
        
        if m['tournament']:
            tournaments.add(m['tournament'])
            
        # Analyze Score
        score = m['score']
        sets = []
        if score:
            # Simple parser for scores like "6-4 3-6 10-8" or "6-4 7-6(4)"
            # This is complex because score formats vary. simpler check first.
            try:
                # Remove brackets for TB score inside like (7)
                clean_score = re.sub(r'\(\d+\)', '', score) 
                parts = clean_score.split()
                sets = parts
            except: pass
            
        # 3-Set Record
        is_three_set = len(sets) >= 3
        
        # Tiebreak Record & Comeback
        has_tb = False
        lost_first_set = False
        
        if sets:
            # Parse first set
            try:
                s1 = sets[0]
                if '-' in s1:
                    g_w, g_l = map(int, s1.split('-')[:2])
                    if is_winner:
                        if g_w < g_l: lost_first_set = True
                    else:
                        if g_l < g_w: lost_first_set = True # 'g_w' here is set winner (opp) vs set loser (me) ? 
                        # Actually score string is rarely consistent on who is first.
                        # Usually score is written Winner-Loser.
                        # So "6-4" means match-winner won set 6-4.
                        # If I am match winner, I won 6-4.
                        # If I am match loser, I lost 6-4.
                        pass
                    
                    # Wait, if I am winner, the score is presented as MY score usually? or Match Winner score?
                    # TennisAbstract stores as Match Winner score.
                    # UTR usually stores as Match Winner score too.
                    # So if result is "6-4 3-6 6-2", Winner won S1, lost S2, won S3.
                    
                    if is_winner:
                        # Winner sets
                        # S1
                        w1, l1 = map(int, sets[0].split('-')[:2])
                        if l1 > w1: lost_first_set = True
                        
                    # Comeback only possible if I won
                    if is_winner and lost_first_set:
                        comeback_wins += 1

            except: pass
            
            # Tiebreaks
            # Heuristic: 7-6 or 6-7 or 1-0 (super TB) or score-sum=13
            for s in sets:
                try:
                    if '-' in s:
                        p1, p2 = map(int, s.split('-')[:2])
                        # Check for TB (7-6 or 6-7)
                        if (p1 == 7 and p2 == 6) or (p1 == 6 and p2 == 7):
                            if is_winner:
                                # If I am winner, did I win this set?
                                # Usually score is oriented to match winner.
                                # So "7-6" means Winner won set.
                                if p1 > p2: tb_wins += 1
                                else: tb_losses += 1
                            else:
                                # I am loser.
                                # "7-6" means Winner (opponent) won set.
                                if p1 > p2: tb_losses += 1
                                else: tb_wins += 1
                        # Super TB (10-x etc in 3rd set often replaced by 1-0)
                        # Ignoring for now for simplicity unless UTR verified
                except: pass

        if is_winner:
            wins += 1
            if is_three_set: three_set_wins += 1
            
            if opp_utr and my_utr_in_match and opp_utr > my_utr_in_match:
                upsets += 1
                
            # Higher Rated
            if opp_utr and my_utr_in_match:
                if opp_utr > my_utr_in_match:
                    hr_wins += 1
                    hr_matches += 1
                else:
                    # Lower rated win
                    pass

            recent_form.append('W')
            
        elif is_loser:
            losses += 1
            if is_three_set: three_set_losses += 1
            
            # Higher Rated stats
            if opp_utr and my_utr_in_match:
                if opp_utr > my_utr_in_match:
                    hr_matches += 1
                    
            recent_form.append('L')
            
    # Win %
    total = wins + losses
    win_pct = f"{(wins/total)*100:.1f}%" if total > 0 else "0.0%"
    
    # Recent Form (Last 10)
    last_10 = recent_form[:10]
    l10_wins = last_10.count('W')
    l10_losses = last_10.count('L')
    form_str = f"{l10_wins}W-{l10_losses}L"
    
    # Avg Opp UTR
    avg_opp_utr = "N/A"
    if opponent_utrs:
        avg_op = sum(opponent_utrs) / len(opponent_utrs)
        avg_opp_utr = f"{avg_op:.2f}"
        
    # 3-Set Record
    three_set_total = three_set_wins + three_set_losses
    three_set_str = f"{three_set_wins}W-{three_set_losses}L"
    if three_set_total > 0:
        three_set_str += f" ({int(three_set_wins/three_set_total*100)}%)"
        
    # Tiebreak Record
    # Logic above is approximate.
    tb_str = f"{tb_wins}W-{tb_losses}L"
    
    # Vs Higher Rated
    hr_str = f"{hr_wins}/{hr_matches}"
    if hr_matches > 0:
        hr_str += f" ({int(hr_wins/hr_matches*100)}%)"
    
    # --- TRENDS ---
    def get_trend(days_ago):
        target_date = datetime.now() - timedelta(days=days_ago)
        closest_diff = float('inf')
        prior_val = None
        
        if history:
            for h in history:
                try:
                    h_date_str = h['date'].replace('Z', '')
                    if 'T' in h_date_str:
                        h_date = datetime.fromisoformat(h_date_str)
                    else:
                        h_date = datetime.strptime(h_date_str, "%Y-%m-%d")
                    
                    diff = abs((h_date - target_date).total_seconds())
                    if diff < closest_diff:
                        closest_diff = diff
                        prior_val = h['rating']
                except: continue
        
        if prior_val and current_utr and closest_diff < (60 * 60 * 24 * 60): # Within 2 months
             return current_utr - prior_val
        return None

    # 1-Year Trend
    delta_1y = get_trend(365)
    trend_1y_str = f"{delta_1y:+.2f}" if delta_1y is not None else "N/A"
    
    # 3-Month Trend
    delta_3m = get_trend(90)
    trend_3m_str = f"{delta_3m:+.2f}" if delta_3m is not None else "N/A"

    return {
        'Record': f"{wins}W-{losses}L",
        'Win %': win_pct,
        'Upset Ratio': f"{upsets}/{wins} ({int(upsets/wins*100)}%)" if wins > 0 else "0/0",
        'Avg Opp UTR': avg_opp_utr,
        '3-Set Record': three_set_str,
        'Tiebreak Record': tb_str,
        'Comeback Wins': comeback_wins,
        'vs Higher Rated': hr_str,
        'Recent Form': form_str,
        'Tournaments': len(tournaments),
        '3-Month Trend': trend_3m_str,
        '1-Year Delta': trend_1y_str
    }

def get_history(conn, player_id):
    c = conn.cursor()
    c.execute("SELECT * FROM utr_history WHERE player_id = ? ORDER BY date DESC", (player_id,))
    cols = [d[0] for d in c.description]
    return [dict(zip(cols, row)) for row in c.fetchall()]

def get_filtered_players(conn, country, category, gender, count, name_filter, min_utr=0):
    """Fetch players with SQL filtering."""
    c = conn.cursor()
    
    query = "SELECT * FROM players WHERE 1=1"
    params = []
    
    if min_utr > 0:
        query += " AND utr_singles >= ?"
        params.append(min_utr)
    
    if country != 'ALL':
        query += " AND country = ?"
        params.append(country)
    
    if gender:
        query += " AND gender = ?"
        params.append(gender)
        
    if name_filter:
        query += " AND name LIKE ?"
        params.append(f"%{name_filter}%")

    # Category Filtering (Junior/Adult) logic
    if category == 'junior':
        # Include confirmed juniors (age <= 18) 
        # OR include if age_group suggests junior (e.g. U14, U16, U18, or ranges like 15-16)
        # OR include if age is missing and UTR is low (heuristic based on gender)
        query += """ AND ( 
            (age IS NOT NULL AND age <= 18) OR 
            (age_group IS NOT NULL AND (age_group LIKE 'U%' OR age_group LIKE '1_-1_' OR age_group LIKE '%Junior%')) OR
            (age IS NULL AND age_group IS NULL AND (
                (gender = 'F' AND utr_singles < 11.5) OR
                (gender = 'M' AND utr_singles < 13.5) OR
                (gender IS NULL AND utr_singles < 13.0)
            ))
        )"""
        
        # Heuristic: If age is missing to confirm, exclude those with active College (likely adults)
        query += " AND (college IS NULL OR college = '-' OR college LIKE '%Recruiting%')"
    elif category == 'college':
        # Include confirmed college players (active college name is present)
        query += " AND (college IS NOT NULL AND college != '-' AND college NOT LIKE '%Recruiting%')"
    elif category == 'adult':
        # Exclude those captured by the Junior heuristic above
        query += """ AND (
            (age IS NOT NULL AND age > 18) OR
            (age IS NULL AND (
                age_group IS NULL AND NOT (
                        (gender = 'F' AND utr_singles < 11.5) OR
                        (gender = 'M' AND utr_singles < 13.5) OR
                        (gender IS NULL AND utr_singles < 13.0)
                )
            ))
        )"""
    
    query += " ORDER BY utr_singles DESC"
    
    if count:
        query += " LIMIT ?"
        params.append(count)
        
    c.execute(query, tuple(params))
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]

# ============================================
# MAIN
# ============================================
# ============================================
# MAIN LOGIC (Refactored for API use)
# ============================================
def generate_excel_report(country, category='junior', gender=None, count=100, name_filter=None, min_utr=0, output_dir='output'):
    print(f"Exporting data...")
    print(f"Filters: Country={country}, Category={category}, Gender={gender or 'Any'}, Name={name_filter or 'Any'}, Count={count}, MinUTR={min_utr}")
    
    # Init DB to ensure migration happens if not already
    try:
        tennis_db.init_db()
    except: pass # Might be already open
    
    conn = tennis_db.get_connection()
    conn.row_factory = sqlite3.Row
    
    # Get Players
    players = get_filtered_players(conn, country, category, gender, count, name_filter, min_utr)
    print(f"Found {len(players)} matched players.")
    
    if not players:
        print("No players found.")
        return None

    # Prepare Output File
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)
    
    gender_part = f"_{gender}" if gender else ""
    cat_part = f"_{category}"
    filename = os.path.join(output_dir, f"{country or 'World'}{cat_part}{gender_part}_Detailed_{date_str}.xlsx")
    
    print(f"Writing to {filename}...")
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Create a summary sheet first
        summary_data = []
        
        for i, p in enumerate(players):
            if (i+1) % 10 == 0 or i == 0:
                print(f"Processing {i+1}/{len(players)}: {p['name'][:20]}...")
                
            p_id = p['player_id']
            matches = tennis_db.get_player_matches(conn, p_id)
            history = get_history(conn, p_id)
            
            # metrics
            metrics = calculate_metrics(p_id, matches, history, p['utr_singles'])
            
            # Profile URL
            profile_url = f"https://app.utrsports.net/profiles/{p_id}"

            # Add to summary
            summary_data.append({
                'Name': p['name'],
                'Singles UTR': p['utr_singles'],
                'Doubles UTR': p['utr_doubles'],
                'Age': p.get('age', ''),
                'Country': p.get('country', ''),
                'Gender': p.get('gender', ''),
                'College': p.get('college', ''),
                'Location': p.get('location', ''),
                'Pro Rank': p.get('pro_rank', ''),
                'Win Record': metrics['Record'],
                'Win %': metrics['Win %'],
                'Upset Ratio': metrics['Upset Ratio'],
                'Avg Opp UTR': metrics['Avg Opp UTR'],
                '3-Set Record': metrics['3-Set Record'],
                'Tiebreak Record': metrics['Tiebreak Record'],
                'Comeback Wins': metrics['Comeback Wins'],
                'vs Higher Rated': metrics['vs Higher Rated'],
                'Recent Form (L10)': metrics['Recent Form'],
                'Tournaments': metrics['Tournaments'],
                '3-Month Trend': metrics['3-Month Trend'],
                '1-Year Delta': metrics['1-Year Delta'],
                'Profile URL': profile_url
            })
            
            # --- INDIVIDUAL PLAYER SHEET ---
            sheet_name = clean_sheet_name(p['name'])
            
            # 1. Info Table
            info_dict = {
                'Metric': ['Name', 'Singles UTR', 'Doubles UTR', 'Age', 'Country', 'Gender', 'College', 'Location', 'Pro Rank',
                           'Win Record', 'Win %', 'Upset Ratio', 'Avg Opp UTR', '3-Set Record', 'Tiebreak Record', 'Comeback Wins',
                           'vs Higher Rated', 'Recent Form (L10)', 'Tournaments', '3-Month Trend', '1-Year Delta', 'Profile URL'],
                'Value': [
                    p['name'], 
                    p['utr_singles'], 
                    p['utr_doubles'], 
                    p.get('age', ''),
                    p.get('country', ''),
                    p.get('gender', ''),
                    p.get('college', ''),
                    p.get('location', ''),
                    p.get('pro_rank', ''),
                    metrics['Record'],
                    metrics['Win %'],
                    metrics['Upset Ratio'],
                    metrics['Avg Opp UTR'],
                    metrics['3-Set Record'],
                    metrics['Tiebreak Record'],
                    metrics['Comeback Wins'],
                    metrics['vs Higher Rated'],
                    metrics['Recent Form'],
                    metrics['Tournaments'],
                    metrics['3-Month Trend'],
                    metrics['1-Year Delta'],
                    profile_url
                ]
            }
            df_info = pd.DataFrame(info_dict)
            df_info.to_excel(writer, sheet_name=sheet_name, startrow=0, startcol=0, index=False)
            
            # 2. Match History Table
            if matches:
                match_rows = []
                for m in matches:
                    is_winner = str(m['winner_id']) == str(p_id)
                    result = 'Win' if is_winner else 'Loss'
                    opp_name = m['loser_name'] if is_winner else m['winner_name']
                    opp_utr = m['loser_utr'] if is_winner else m['winner_utr']
                    
                    match_rows.append({
                        'Date': m['date'][:10] if m['date'] else '',
                        'Tournament': m['tournament'],
                        'Round': m['round'],
                        'Opponent': opp_name,
                        'Opp UTR': opp_utr,
                        'Result': result,
                        'Score': m['score']
                    })
                
                df_matches = pd.DataFrame(match_rows)
                df_matches.to_excel(writer, sheet_name=sheet_name, startrow=25, startcol=0, index=False) # Moved down to accommodate longer info table
        
        # Write Summary Sheet
        df_summary = pd.DataFrame(summary_data)
        # Reorder columns to match request
        cols_order = ['Name', 'Singles UTR', 'Doubles UTR', '3-Month Trend', '1-Year Delta', 'Win Record', 'Win %', 'Upset Ratio', 'Avg Opp UTR',
                      '3-Set Record', 'Recent Form (L10)', 'Tournaments', 'vs Higher Rated', 'Tiebreak Record', 'Comeback Wins',
                      'Age', 'Country', 'Location', 'Pro Rank', 'College', 'Profile URL']
        # Filter to only existing columns
        cols_order = [c for c in cols_order if c in df_summary.columns]
        df_summary = df_summary[cols_order].sort_values(by='Singles UTR', ascending=False)
        df_summary.to_excel(writer, sheet_name='Overview', index=False)
    
    print("\nReport Generation Complete!")
    return filename

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Export Player Data to Excel')
    parser.add_argument('--country', required=True, help='ISO-3 Country Code (e.g. CAN) or ALL')
    parser.add_argument('--category', default='junior', help='junior, adult, or college (used for filtering/context)')
    parser.add_argument('--gender', default='', help='M or F (optional filter)')
    parser.add_argument('--count', type=int, default=100, help='Top N players to export (default 100)')
    parser.add_argument('--name', default='', help='Filter by partial name match')

    parser.add_argument('--min-utr', type=float, default=0, help='Minimum UTR')

    args = parser.parse_args()
    
    generate_excel_report(args.country, args.category, args.gender, args.count, args.name, args.min_utr)

if __name__ == "__main__":
    main()
