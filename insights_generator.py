#!/usr/bin/env python3
"""
Insights Generator - Detects interesting patterns in player match history.

Generates facts like:
- "0-3 against players aged 37+ in the last 5 years"
- "7-0 on clay this season"
- "Lost 4 straight to Top 50 players"
"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import tennis_db


def get_player_insights(player_id: str, years: int = 5):
    """
    Generate insights for a player based on their match history.
    
    Returns a list of insight objects with category, title, description, 
    emoji, win/loss ratio, and supporting matches.
    """
    conn = sqlite3.connect(tennis_db.DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Calculate date threshold
    cutoff_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')
    
    # Fetch recent matches with opponent details
    c.execute("""
        SELECT m.*, 
               w.name as winner_name, w.age as winner_age, w.country as winner_country,
               l.name as loser_name, l.age as loser_age, l.country as loser_country
        FROM matches m
        LEFT JOIN players w ON m.winner_id = w.player_id
        LEFT JOIN players l ON m.loser_id = l.player_id
        WHERE (m.winner_id = ? OR m.loser_id = ?)
        AND m.date >= ?
        ORDER BY m.date DESC
    """, (player_id, player_id, cutoff_date))
    
    matches = [dict(row) for row in c.fetchall()]
    conn.close()
    
    if not matches:
        return []
    
    insights = []
    
    # Run all pattern detectors
    insights.extend(find_age_patterns(player_id, matches))
    insights.extend(find_surface_patterns(player_id, matches))
    insights.extend(find_country_patterns(player_id, matches))
    insights.extend(find_set_patterns(player_id, matches))
    insights.extend(find_streak_patterns(player_id, matches))
    insights.extend(find_round_patterns(player_id, matches))
    
    # Sort by interest score (0% or 100% win rates are most interesting)
    insights.sort(key=lambda x: (x['total_matches'], abs(x['win_pct'] - 50)), reverse=True)
    
    return insights[:10]  # Return top 10 insights


def is_interesting(wins, losses, min_matches=3):
    """Determine if a pattern is interesting enough to show."""
    total = wins + losses
    if total < min_matches:
        return False
    # Perfect or anti-perfect records are interesting
    if wins == 0 or losses == 0:
        return True
    # Close matchups with enough data are interesting
    if total >= 4:
        win_pct = wins / total
        if win_pct <= 0.25 or win_pct >= 0.75:
            return True
    return False


def format_match_list(matches, player_id):
    """Format matches into a list for display."""
    result = []
    for m in matches[:5]:  # Limit to 5 matches
        is_win = str(m.get('winner_id')) == str(player_id)
        opponent_name = m.get('loser_name') if is_win else m.get('winner_name')
        opponent_age = m.get('loser_age') if is_win else m.get('winner_age')
        
        result.append({
            'date': m.get('date', '')[:10],
            'opponent': opponent_name or 'Unknown',
            'opponent_age': opponent_age,
            'result': 'W' if is_win else 'L',
            'score': m.get('score', ''),
            'tournament': m.get('tournament', ''),
            'surface': m.get('surface', ''),
        })
    return result


def find_age_patterns(player_id, matches):
    """Find patterns against different age groups."""
    insights = []
    
    age_buckets = {
        '37+': {'min': 37, 'max': 100, 'emoji': '👴', 'label': 'Veterans (37+)'},
        'under_21': {'min': 0, 'max': 20, 'emoji': '🧒', 'label': 'Young Guns (Under 21)'},
    }
    
    for bucket_key, bucket_info in age_buckets.items():
        bucket_matches = []
        wins = 0
        losses = 0
        
        for m in matches:
            is_win = str(m.get('winner_id')) == str(player_id)
            opponent_age = m.get('loser_age') if is_win else m.get('winner_age')
            
            if opponent_age and bucket_info['min'] <= opponent_age <= bucket_info['max']:
                bucket_matches.append(m)
                if is_win:
                    wins += 1
                else:
                    losses += 1
        
        if is_interesting(wins, losses):
            insights.append({
                'category': 'age',
                'emoji': bucket_info['emoji'],
                'title': f"vs {bucket_info['label']}",
                'description': f"{wins}-{losses} against players aged {bucket_key.replace('under_', 'under ').replace('+', '+')}",
                'wins': wins,
                'losses': losses,
                'total_matches': wins + losses,
                'win_pct': round(100 * wins / (wins + losses), 1) if (wins + losses) > 0 else 0,
                'matches': format_match_list(bucket_matches, player_id),
            })
    
    return insights


def find_surface_patterns(player_id, matches):
    """Find patterns on different surfaces."""
    insights = []
    
    surfaces = {
        'Hard': {'emoji': '🔵', 'label': 'Hard Courts'},
        'Clay': {'emoji': '🟠', 'label': 'Clay Courts'},
        'Grass': {'emoji': '🟢', 'label': 'Grass Courts'},
    }
    
    for surface, info in surfaces.items():
        surface_matches = [m for m in matches if m.get('surface') == surface]
        wins = sum(1 for m in surface_matches if str(m.get('winner_id')) == str(player_id))
        losses = len(surface_matches) - wins
        
        if is_interesting(wins, losses, min_matches=5):
            insights.append({
                'category': 'surface',
                'emoji': info['emoji'],
                'title': f"on {info['label']}",
                'description': f"{wins}-{losses} on {surface.lower()} courts",
                'wins': wins,
                'losses': losses,
                'total_matches': wins + losses,
                'win_pct': round(100 * wins / (wins + losses), 1) if (wins + losses) > 0 else 0,
                'matches': format_match_list(surface_matches, player_id),
            })
    
    return insights


def find_country_patterns(player_id, matches):
    """Find patterns against players from specific countries."""
    insights = []
    
    country_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'matches': []})
    
    for m in matches:
        is_win = str(m.get('winner_id')) == str(player_id)
        opponent_country = m.get('loser_country') if is_win else m.get('winner_country')
        
        if opponent_country:
            country_stats[opponent_country]['matches'].append(m)
            if is_win:
                country_stats[opponent_country]['wins'] += 1
            else:
                country_stats[opponent_country]['losses'] += 1
    
    for country, stats in country_stats.items():
        if is_interesting(stats['wins'], stats['losses'], min_matches=4):
            insights.append({
                'category': 'country',
                'emoji': '🌍',
                'title': f"vs {country} Players",
                'description': f"{stats['wins']}-{stats['losses']} against {country} opponents",
                'wins': stats['wins'],
                'losses': stats['losses'],
                'total_matches': stats['wins'] + stats['losses'],
                'win_pct': round(100 * stats['wins'] / (stats['wins'] + stats['losses']), 1),
                'matches': format_match_list(stats['matches'], player_id),
            })
    
    return insights


def find_set_patterns(player_id, matches):
    """Find patterns based on set scores (e.g., losing first set)."""
    insights = []
    
    lost_first_set = {'wins': 0, 'losses': 0, 'matches': []}
    
    for m in matches:
        score = m.get('score', '')
        if not score or score == 'W/O':
            continue
        
        is_win = str(m.get('winner_id')) == str(player_id)
        
        # Parse first set
        sets = score.split()
        if not sets:
            continue
            
        first_set = sets[0]
        # Check if player lost first set
        try:
            parts = first_set.replace('(', '-').replace(')', '').split('-')
            if len(parts) >= 2:
                s1, s2 = int(parts[0]), int(parts[1])
                player_lost_first = (is_win and s1 < s2) or (not is_win and s1 > s2)
                
                if player_lost_first:
                    lost_first_set['matches'].append(m)
                    if is_win:
                        lost_first_set['wins'] += 1
                    else:
                        lost_first_set['losses'] += 1
        except (ValueError, IndexError):
            continue
    
    if is_interesting(lost_first_set['wins'], lost_first_set['losses'], min_matches=5):
        wins, losses = lost_first_set['wins'], lost_first_set['losses']
        insights.append({
            'category': 'set',
            'emoji': '🎯',
            'title': 'After Losing 1st Set',
            'description': f"{wins}-{losses} when losing the first set",
            'wins': wins,
            'losses': losses,
            'total_matches': wins + losses,
            'win_pct': round(100 * wins / (wins + losses), 1) if (wins + losses) > 0 else 0,
            'matches': format_match_list(lost_first_set['matches'], player_id),
        })
    
    return insights


def find_streak_patterns(player_id, matches):
    """Find current winning/losing streaks."""
    insights = []
    
    if not matches:
        return insights
    
    # Check current streak (matches are already sorted by date DESC)
    streak = 0
    streak_type = None
    streak_matches = []
    
    for m in matches:
        is_win = str(m.get('winner_id')) == str(player_id)
        
        if streak_type is None:
            streak_type = 'W' if is_win else 'L'
            streak = 1
            streak_matches = [m]
        elif (is_win and streak_type == 'W') or (not is_win and streak_type == 'L'):
            streak += 1
            streak_matches.append(m)
        else:
            break
    
    if streak >= 5:
        if streak_type == 'W':
            insights.append({
                'category': 'streak',
                'emoji': '🔥',
                'title': 'Hot Streak',
                'description': f"Won {streak} consecutive matches",
                'wins': streak,
                'losses': 0,
                'total_matches': streak,
                'win_pct': 100,
                'matches': format_match_list(streak_matches, player_id),
            })
        else:
            insights.append({
                'category': 'streak',
                'emoji': '❄️',
                'title': 'Cold Streak',
                'description': f"Lost {streak} consecutive matches",
                'wins': 0,
                'losses': streak,
                'total_matches': streak,
                'win_pct': 0,
                'matches': format_match_list(streak_matches, player_id),
            })
    
    return insights


def find_round_patterns(player_id, matches):
    """Find patterns in specific tournament rounds."""
    insights = []
    
    rounds = {
        'F': {'label': 'Finals', 'emoji': '🏆'},
        'SF': {'label': 'Semifinals', 'emoji': '🥈'},
        'QF': {'label': 'Quarterfinals', 'emoji': '🎖️'},
    }
    
    for round_code, info in rounds.items():
        round_matches = [m for m in matches if m.get('round') == round_code]
        wins = sum(1 for m in round_matches if str(m.get('winner_id')) == str(player_id))
        losses = len(round_matches) - wins
        
        if is_interesting(wins, losses, min_matches=3):
            insights.append({
                'category': 'round',
                'emoji': info['emoji'],
                'title': f"in {info['label']}",
                'description': f"{wins}-{losses} in {info['label'].lower()}",
                'wins': wins,
                'losses': losses,
                'total_matches': wins + losses,
                'win_pct': round(100 * wins / (wins + losses), 1) if (wins + losses) > 0 else 0,
                'matches': format_match_list(round_matches, player_id),
            })
    
    return insights


if __name__ == '__main__':
    # Test with a sample player
    import sys
    player_id = sys.argv[1] if len(sys.argv) > 1 else 'test'
    
    insights = get_player_insights(player_id)
    
    print(f"\n=== Insights for player {player_id} ===\n")
    for insight in insights:
        print(f"{insight['emoji']} {insight['title']}")
        print(f"   {insight['description']}")
        print(f"   Win Rate: {insight['win_pct']}%")
        for m in insight['matches'][:3]:
            print(f"   {'✅' if m['result'] == 'W' else '❌'} {m['opponent']} at {m['tournament']}")
        print()
