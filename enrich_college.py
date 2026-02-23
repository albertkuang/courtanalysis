import sqlite3
import requests
import json
import time
from import_players import login, process_player, get_v2_profile

def enrich_existing_players():
    # 1. Get Candidates from DB
    # Filter: Age 17-25 (typical college range), College Name NULL
    # Also include those with college name but is_active_college = 0? (Maybe re-check them)
    # Let's start with those missing college info.
    conn = sqlite3.connect('tennis_data.db')
    cursor = conn.cursor()
    
    print("Fetching candidates from DB...")
    # Fetch players who might be college players but are not marked as such
    # Using age range 17-26 and NULL college_name or is_active_college=0
    query = """
        SELECT player_id, name, age 
        FROM players 
        WHERE (age BETWEEN 17 AND 26) 
          AND (is_active_college = 0 OR is_active_college IS NULL)
    """
    cursor.execute(query)
    candidates = cursor.fetchall()
    print(f"Found {len(candidates)} candidates.")
    
    auth_info = login()
    
    total_updated = 0
    total_checked = 0
    
    for pid, name, age in candidates:
        total_checked += 1
        print(f"Checking {name} (ID: {pid})...", end='', flush=True)
        
        try:
            # We use process_player from import_players, but we need to mock the 'source' data structure 
            # OR we can just fetch the V2 profile directly here and update DB.
            # process_player does a lot (matches, etc). We just want college info.
            
            # Fetch V2 Profile
            v2 = get_v2_profile(auth_info, pid)
            if not v2: 
                print(" No V2 profile.")
                continue
                
            # Extract basic college info logic (copied/adapted from import_players)
            college_name = None
            college_id = None
            grad_year = None
            is_active_college = False

            # Check teams
            teams = v2.get('teams', [])
            college = next((t for t in teams if t.get('isCollege')), None)
            
            if college:
                college_name = college.get('name')
                college_id = college.get('id')
            
            if not college_name:
                 # Check schools?
                 schools = v2.get('schools', [])
                 college = next((s for s in schools if s.get('isCollege')), None)
                 if college:
                     college_name = college.get('name')
                     college_id = college.get('id')
            
            # Check grad year
            grad_year = v2.get('gradYear')
            
            # Determine Active Status
            tags = v2.get('primaryTags', []) or []
            is_college_tag = 'College' in tags
            
            from datetime import datetime
            current_year = datetime.now().year
            
            if college_name and grad_year:
                try:
                    gy_str = str(grad_year)[:4]
                    gy_int = int(gy_str)
                    if gy_int >= current_year:
                        is_active_college = True
                except: pass
            
            # Trust the Tag
            if is_college_tag and not is_active_college:
                is_active_college = True

            # Convert boolean to int
            is_active_int = 1 if is_active_college else 0
            
            # Update DB if found
            if college_name or is_active_college:
                cursor.execute("""
                    UPDATE players 
                    SET college_name = ?, college_id = ?, grad_year = ?, is_active_college = ?
                    WHERE player_id = ?
                """, (college_name, college_id, grad_year, is_active_int, pid))
                conn.commit()
                print(f" UPDATED! College: {college_name}, Active: {is_active_college}")
                total_updated += 1
            else:
                print(" No college info.")
                
        except Exception as e:
            print(f" Error: {e}")
            
        # Mild rate limit
        # time.sleep(0.1)

    conn.close()
    print(f"\n enrichment Complete. Updated {total_updated} / {total_checked} players.")

if __name__ == "__main__":
    enrich_existing_players()
