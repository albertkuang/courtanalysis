import college_roster_scraper
from config import UTR_CONFIG
import logging
import os
import datetime

# Configure logging
logging.basicConfig(
    filename='college_service.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Auth helper
def get_auth(force_refresh=False):
    # We might need to cache login?
    # For now, login on request (slow) or use a singleton.
    # college_roster_scraper.login() returns tokens.
    if not hasattr(get_auth, 'cache'):
        get_auth.cache = None
        
    # Check if cached and valid? (Simulate for now, simple login)
    if not force_refresh and get_auth.cache:
        return get_auth.cache
        
    try:
        logging.info("Authenticating with UTR...")
        auth = college_roster_scraper.login()
        get_auth.cache = auth
        logging.info("Authentication successful")
        return auth
    except Exception as e:
        logging.error(f"Auth failed: {e}")
        return {}

import json

# Cache for college data
COLLEGE_CACHE_FILE = 'college_data.json'
COLLEGE_CACHE = {}

def load_cache():
    global COLLEGE_CACHE
    if os.path.exists(COLLEGE_CACHE_FILE):
        try:
            with open(COLLEGE_CACHE_FILE, 'r') as f:
                COLLEGE_CACHE = json.load(f)
            logging.info(f"Loaded college cache with {sum(len(v) for v in COLLEGE_CACHE.values())} entries.")
        except Exception as e:
            logging.error(f"Failed to load college cache: {e}")

# Load cache on module import
load_cache()

def search_colleges(query, division='D1', gender='M'):
    """
    Search colleges by name/division. Uses local cache if available.
    """
    logging.info(f"Searching colleges: query='{query}', division='{division}', gender='{gender}'")
    
    # Reload cache if empty (maybe first run or file just created)
    if not COLLEGE_CACHE:
        load_cache()

    # Optimized Cache Search
    if division in COLLEGE_CACHE:
        cached_list = COLLEGE_CACHE[division]
        
        # If no query, return full cached list (fast!)
        if not query or not query.strip():
            logging.info(f"Returning {len(cached_list)} cached results for {division}")
            # Ensure division field is present
            for c in cached_list:
                if 'division' not in c: c['division'] = division
            return cached_list
            
        # If query, filter local cache first
        q_lower = query.lower()
        matches = [c for c in cached_list if q_lower in c.get('name', '').lower()]
        
        if matches:
            logging.info(f"Found {len(matches)} cached matches for '{query}' in {division}")
            return matches
            
    # Fallback to live API if not in cache or no matches found (and we want to be sure)
    # But usually cache is authoritative for the dropdown use case.
    # We will only fallback if cache is missing for this division.
    
    # Retry logic for auth failures
    for attempt in range(2):
        force_refresh = (attempt > 0)
        if attempt > 0:
            logging.info("Retrying with fresh auth...")
            
        try:
            auth = get_auth(force_refresh=force_refresh)
            
            if query:
                # Utilize the specific finder
                hit = college_roster_scraper.find_college_by_name(auth, query, preferred_gender=gender)
                if hit:
                    logging.info(f"Found direct match: {hit['name']}")
                    return [hit]
                
                # Fallback: Try searching generally and filtering
                logging.info(f"Direct match not found for '{query}', trying broader search...")
                results = []
                # Fallback logic simplified - just searching across divisions is messy without gender context sometimes
                # But kept for robustness
                for div in ['D1', 'D2', 'D3', 'NAIA', 'JUCO']:
                    try:
                        res = college_roster_scraper.search_colleges(auth, div, limit=20) 
                        for r in res:
                            if query.lower() in r.get('name', '').lower():
                                if 'division' not in r: r['division'] = div
                                results.append(r)
                    except Exception as e:
                        logging.warning(f"Error searching division {div}: {e}")
                        continue
                    if len(results) >= 5: break 
                
                logging.info(f"Broad search found {len(results)} results")
                return results
            
            # No query, just search by division
            # Increased limit to populate full dropdown
            results = college_roster_scraper.search_colleges(auth, division, limit=1000)
            return results
            
        except Exception as e:
            logging.error(f"Error in search_colleges (attempt {attempt+1}): {e}")
            if attempt == 0:
                continue
            return []
    return []

def get_roster(club_id, gender='M'):
    """
    Get roster for a college.
    """
    logging.info(f"Fetching roster for club_id={club_id}, gender={gender}")
    
    # Retry logic for auth failures
    for attempt in range(2):
        force_refresh = (attempt > 0)
        auth = get_auth(force_refresh=force_refresh)
        
        try:
            roster = college_roster_scraper.get_college_roster(auth, club_id, gender)
            logging.info(f"Fetched {len(roster)} players")
            return roster
        except Exception as e:
            logging.error(f"Error fetching roster (attempt {attempt+1}): {e}")
            if attempt == 0:
                logging.info("Retrying with fresh auth...")
                continue
            return []
    return []
