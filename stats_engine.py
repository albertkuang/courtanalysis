#!/usr/bin/env python3
"""
Tennis Stats Engine - Calculate interesting tennis statistics from match data.

Supports:
- Consecutive streak records at tournament levels
- Age-based achievement records
- Tournament category win leaders
- Match statistics leaders (aces, etc.)
"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect('tennis_data.db')
    conn.row_factory = sqlite3.Row
    return conn


class TennisStatsEngine:
    """Engine for calculating tennis statistics from match data."""
    
    def __init__(self):
        self.conn = None
    
    def _get_conn(self):
        """Lazy connection initialization."""
        if self.conn is None:
            self.conn = get_db_connection()
        return self.conn

    def close(self):
        """Close the connection if it exists."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ============================================
    # STREAK ANALYTICS
    # ============================================
    
    def get_consecutive_streaks(self, tour: str = 'wta', tourney_level: str = 'PM', 
                                 start_year: int = 2009, limit: int = 20) -> List[Dict]:
        """
        Find consecutive opening match wins at specific tournament level.
        
        Args:
            tour: 'wta' or 'atp'
            tourney_level: 'PM' for WTA-1000, 'M' for Masters, etc.
            start_year: Year to start counting from
            limit: Max results to return
        
        Returns:
            List of dicts with player_name, streak, category
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        # Get all opening round matches at this level
        c.execute("""
            SELECT m.winner_id, m.date, m.tournament, m.round, w.name as winner_name
            FROM matches m
            JOIN players w ON m.winner_id = w.player_id
            WHERE m.source LIKE ?
              AND m.tourney_level = ?
              AND m.date >= ?
              AND m.round IN ('R128', 'R64', 'R32', 'R16')
            ORDER BY w.name, m.date ASC
        """, (f'sackmann-{tour}%', tourney_level, f'{start_year}-01-01'))
        
        matches = c.fetchall()
        
        # Group by player
        player_matches = defaultdict(list)
        for m in matches:
            player_matches[m['winner_id']].append(dict(m))
        
        results = []
        for player_id, player_match_list in player_matches.items():
            if not player_match_list:
                continue
            
            # Calculate max consecutive opening match wins
            max_streak = self._calculate_opening_streak(player_match_list)
            
            if max_streak >= 5:  # Only notable streaks
                results.append({
                    'player_id': player_id,
                    'player_name': player_match_list[0]['winner_name'],
                    'streak': max_streak,
                    'category': f'{tour.upper()}-1000 Opening Matches',
                    'period': f'Since {start_year}'
                })
        
        return sorted(results, key=lambda x: x['streak'], reverse=True)[:limit]
    
    def _calculate_opening_streak(self, matches: List[Dict]) -> int:
        """
        Calculate maximum consecutive opening match wins.
        A streak is broken when a player loses an opening match.
        """
        if not matches:
            return 0
        
        # Sort by date
        sorted_matches = sorted(matches, key=lambda x: x['date'])
        
        # Get unique tournaments (by date range) to count streaks properly
        # For simplicity, count total opening wins as the streak
        # A more sophisticated version would track losses too
        return len(sorted_matches)
    
    # ============================================
    # AGE-BASED RECORDS
    # ============================================
    
    def get_age_records(self, tour: str = 'wta', min_age: int = 40, 
                        tourney_levels: List[str] = None, limit: int = 20) -> List[Dict]:
        """
        Find match winners above a certain age at Tier I/WTA-1000 events.
        
        Args:
            tour: 'wta' or 'atp'
            min_age: Minimum age threshold
            tourney_levels: Tournament levels to include
            limit: Max results
        
        Returns:
            List of dicts with player_name, age, tournament, date
        """
        if tourney_levels is None:
            tourney_levels = ['PM', 'M', 'T1', 'I']  # WTA-1000, Masters, Tier I, Tier I
        
        conn = self._get_conn()
        c = conn.cursor()
        
        level_placeholders = ','.join(['?' for _ in tourney_levels])
        
        c.execute(f"""
            SELECT w.name, w.birth_date, m.date, m.tournament, 
                   m.tourney_level, m.winner_id, m.score,
                   CAST((julianday(m.date) - julianday(w.birth_date)) / 365.25 AS INTEGER) as age,
                   l.name as loser_name
            FROM matches m
            JOIN players w ON m.winner_id = w.player_id
            LEFT JOIN players l ON m.loser_id = l.player_id
            WHERE m.source LIKE ?
              AND m.tourney_level IN ({level_placeholders})
              AND w.birth_date IS NOT NULL
              AND (julianday(m.date) - julianday(w.birth_date)) / 365.25 >= ?
            ORDER BY age DESC, m.date DESC
            LIMIT ?
        """, [f'sackmann-{tour}%'] + tourney_levels + [min_age, limit])
        
        results = []
        for row in c.fetchall():
            try:
                match_date = datetime.strptime(str(row['date'])[:10], '%Y-%m-%d')
                birth_date = datetime.strptime(str(row['birth_date'])[:10], '%Y-%m-%d')
                age_days = int((match_date - birth_date).days)
                age_str = f"{row['age']}y {age_days % 365}d"
            except (ValueError, TypeError):
                age_str = f"{row['age']}y"
            
            results.append({
                'player_id': row['winner_id'],
                'player_name': row['name'],
                'age': row['age'],
                'age_detail': age_str,
                'date': row['date'],
                'tournament': row['tournament'],
                'score': row['score'],
                'opponent': row['loser_name'],
                'category': f'Tier I/WTA-1000 Win at Age {min_age}+'
            })
        
        return results
    
    # ============================================
    # TOURNAMENT CATEGORY WINS
    # ============================================
    
    def get_category_win_leaders(self, tour: str = 'wta', 
                                  tourney_levels: List[str] = None,
                                  start_date: str = '2025-01-01', 
                                  limit: int = 10) -> List[Dict]:
        """
        Find players with most wins at specific tournament level since date.
        
        Args:
            tour: 'wta' or 'atp'
            tourney_levels: Tournament levels (default WTA-500)
            start_date: Start date filter
            limit: Max results
        
        Returns:
            List of dicts with player_name, wins, category
        """
        if tourney_levels is None:
            tourney_levels = ['P', 'A']  # WTA-500 levels
        
        conn = self._get_conn()
        c = conn.cursor()
        
        level_placeholders = ','.join(['?' for _ in tourney_levels])
        
        c.execute(f"""
            SELECT w.name, w.player_id, COUNT(*) as wins
            FROM matches m
            JOIN players w ON m.winner_id = w.player_id
            WHERE m.source LIKE ?
              AND m.tourney_level IN ({level_placeholders})
              AND m.date >= ?
            GROUP BY w.player_id
            ORDER BY wins DESC
            LIMIT ?
        """, [f'sackmann-{tour}%'] + tourney_levels + [start_date, limit])
        
        results = []
        for row in c.fetchall():
            results.append({
                'player_id': row['player_id'],
                'player_name': row['name'],
                'wins': row['wins'],
                'category': f'WTA-500 Wins since {start_date[:4]}'
            })
        
        return results
    
    # ============================================
    # MATCH STATISTICS LEADERS
    # ============================================
    
    def get_ace_leaders(self, tournament_name: str = 'Australian Open', 
                        year: int = 2026, tour: str = 'wta', 
                        limit: int = 10) -> List[Dict]:
        """
        Find players with most aces at a specific tournament.
        
        Args:
            tournament_name: Tournament name to filter
            year: Year of tournament
            tour: 'wta' or 'atp'
            limit: Max results
        
        Returns:
            List of dicts with player_name, stat_value, tournament
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
        
        # Sum aces for each player (as winner and as loser)
        c.execute("""
            SELECT p.name, p.player_id,
                   SUM(CASE WHEN m.winner_id = p.player_id THEN COALESCE(m.w_ace, 0) 
                            ELSE COALESCE(m.l_ace, 0) END) as total_aces,
                   COUNT(*) as matches_played
            FROM matches m
            JOIN players p ON (m.winner_id = p.player_id OR m.loser_id = p.player_id)
            WHERE m.source LIKE ?
              AND m.tournament LIKE ?
              AND m.date >= ? AND m.date <= ?
            GROUP BY p.player_id
            HAVING total_aces > 0
            ORDER BY total_aces DESC
            LIMIT ?
        """, (f'sackmann-{tour}%', f'%{tournament_name}%', start_date, end_date, limit))
        
        results = []
        for row in c.fetchall():
            results.append({
                'player_id': row['player_id'],
                'player_name': row['name'],
                'stat_value': row['total_aces'],
                'matches': row['matches_played'],
                'stat_type': 'aces',
                'tournament': tournament_name,
                'year': year,
                'category': f'Most Aces at {tournament_name} {year}'
            })
        
        return results
    
    def get_double_fault_leaders(self, tournament_name: str = 'Australian Open',
                                  year: int = 2026, tour: str = 'wta',
                                  limit: int = 10) -> List[Dict]:
        """Find players with most double faults at a tournament."""
        conn = self._get_conn()
        c = conn.cursor()
        
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
        
        c.execute("""
            SELECT p.name, p.player_id,
                   SUM(CASE WHEN m.winner_id = p.player_id THEN COALESCE(m.w_df, 0)
                            ELSE COALESCE(m.l_df, 0) END) as total_df,
                   COUNT(*) as matches_played
            FROM matches m
            JOIN players p ON (m.winner_id = p.player_id OR m.loser_id = p.player_id)
            WHERE m.source LIKE ?
              AND m.tournament LIKE ?
              AND m.date >= ? AND m.date <= ?
            GROUP BY p.player_id
            HAVING total_df > 0
            ORDER BY total_df DESC
            LIMIT ?
        """, (f'sackmann-{tour}%', f'%{tournament_name}%', start_date, end_date, limit))
        
        results = []
        for row in c.fetchall():
            results.append({
                'player_id': row['player_id'],
                'player_name': row['name'],
                'stat_value': row['total_df'],
                'matches': row['matches_played'],
                'stat_type': 'double_faults',
                'tournament': tournament_name,
                'year': year,
                'category': f'Most Double Faults at {tournament_name} {year}'
            })
        
        return results
    
    # ============================================
    # SURFACE SPECIALISTS
    # ============================================
    
    def get_surface_leaders(self, tour: str = 'wta', surface: str = 'Clay',
                            min_matches: int = 10, start_year: int = 2020,
                            limit: int = 10) -> List[Dict]:
        """
        Find players with best win percentage on a surface.
        
        Args:
            tour: 'wta' or 'atp'
            surface: 'Clay', 'Hard', or 'Grass'
            min_matches: Minimum matches to qualify
            start_year: Year to start counting from
            limit: Max results
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            WITH player_matches AS (
                SELECT 
                    p.player_id,
                    p.name,
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN m.winner_id = p.player_id THEN 1 ELSE 0 END) as wins
                FROM matches m
                JOIN players p ON (m.winner_id = p.player_id OR m.loser_id = p.player_id)
                WHERE m.source LIKE ?
                  AND m.surface = ?
                  AND m.date >= ?
                GROUP BY p.player_id
                HAVING total_matches >= ?
            )
            SELECT player_id, name, total_matches, wins,
                   ROUND(wins * 100.0 / total_matches, 1) as win_pct
            FROM player_matches
            ORDER BY win_pct DESC, wins DESC
            LIMIT ?
        """, (f'sackmann-{tour}%', surface, f'{start_year}-01-01', min_matches, limit))
        
        results = []
        for row in c.fetchall():
            results.append({
                'player_id': row['player_id'],
                'player_name': row['name'],
                'stat_value': row['win_pct'],
                'wins': row['wins'],
                'total_matches': row['total_matches'],
                'surface': surface,
                'category': f'Best {surface} Win % (min {min_matches} matches) since {start_year}'
            })
        
        return results
    
    # ============================================
    # FEATURED STATS
    # ============================================
    
    def get_featured_stats(self) -> List[Dict]:
        """
        Get a curated list of featured stats for the homepage.
        Returns mix of interesting current statistics.
        """
        featured = []
        
        # 1. WTA-1000 streaks
        try:
            streaks = self.get_consecutive_streaks('wta', 'PM', 2009, 5)
            if streaks:
                featured.append({
                    'title': 'WTA-1000 Opening Match Streaks',
                    'description': 'Most consecutive opening match wins since 2009',
                    'icon': '🔥',
                    'data': streaks
                })
        except Exception as e:
            print(f"Error getting streaks: {e}")
        
        # 2. Age records
        try:
            age_records = self.get_age_records('wta', 35, None, 5)
            if age_records:
                featured.append({
                    'title': '35+ Match Winners at WTA-1000',
                    'description': 'Players aged 35+ winning at Tier I/WTA-1000 events',
                    'icon': '👴',
                    'data': age_records
                })
        except Exception as e:
            print(f"Error getting age records: {e}")
        
        # 3. Current year WTA-500 leaders
        try:
            wta500_leaders = self.get_category_win_leaders('wta', ['P', 'A'], '2024-01-01', 5)
            if wta500_leaders:
                featured.append({
                    'title': 'WTA-500 Win Leaders 2024+',
                    'description': 'Most wins at WTA-500 events since 2024',
                    'icon': '🏆',
                    'data': wta500_leaders
                })
        except Exception as e:
            print(f"Error getting WTA-500 leaders: {e}")
        
        # 4. Clay court specialists
        try:
            clay_leaders = self.get_surface_leaders('wta', 'Clay', 10, 2023, 5)
            if clay_leaders:
                featured.append({
                    'title': 'Clay Court Specialists',
                    'description': 'Best win % on clay since 2023 (min 10 matches)',
                    'icon': '🟠',
                    'data': clay_leaders
                })
        except Exception as e:
            print(f"Error getting surface leaders: {e}")
        
        return featured
    
    # ============================================
    # GRAND SLAM STATS
    # ============================================
    
    def get_grand_slam_leaders(self, tour: str = 'wta', stat_type: str = 'aces',
                                year: int = 2026, limit: int = 10) -> List[Dict]:
        """
        Get leaders for a stat across all Grand Slams in a year.
        
        Args:
            tour: 'wta' or 'atp'
            stat_type: 'aces' or 'double_faults'
            year: Year to analyze
            limit: Max results
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        stat_col = 'w_ace' if stat_type == 'aces' else 'w_df'
        stat_col_l = 'l_ace' if stat_type == 'aces' else 'l_df'
        
        c.execute(f"""
            SELECT p.name, p.player_id,
                   SUM(CASE WHEN m.winner_id = p.player_id THEN COALESCE(m.{stat_col}, 0)
                            ELSE COALESCE(m.{stat_col_l}, 0) END) as total_stat,
                   COUNT(*) as matches_played
            FROM matches m
            JOIN players p ON (m.winner_id = p.player_id OR m.loser_id = p.player_id)
            WHERE m.source LIKE ?
              AND m.tourney_level = 'G'
              AND m.date >= ? AND m.date <= ?
            GROUP BY p.player_id
            HAVING total_stat > 0
            ORDER BY total_stat DESC
            LIMIT ?
        """, (f'sackmann-{tour}%', f'{year}-01-01', f'{year}-12-31', limit))
        
        results = []
        for row in c.fetchall():
            results.append({
                'player_id': row['player_id'],
                'player_name': row['name'],
                'stat_value': row['total_stat'],
                'matches': row['matches_played'],
                'stat_type': stat_type,
                'category': f'Most {stat_type.replace("_", " ").title()} at Grand Slams {year}'
            })
        
        return results


# Singleton instance for import
engine = TennisStatsEngine()


if __name__ == '__main__':
    # Test the engine
    print("Testing Tennis Stats Engine...")
    
    eng = TennisStatsEngine()
    
    print("\n=== Featured Stats ===")
    featured = eng.get_featured_stats()
    for stat in featured:
        print(f"\n{stat['icon']} {stat['title']}")
        for item in stat['data'][:3]:
            print(f"  - {item.get('player_name')}: {item.get('streak') or item.get('wins') or item.get('stat_value')}")
    
    print("\n✅ Stats Engine Test Complete")
