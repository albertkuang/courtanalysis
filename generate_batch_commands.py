
import sqlite3

def get_top_junior_countries():
    conn = sqlite3.connect('tennis_data.db')
    c = conn.cursor()
    
    # Query to count junior players per country
    # Using a simplified definition of junior similar to the API for consistency
    # or just filtering by age if available to keep it fast.
    # The API logic is complex, let's try a reasonable approximation:
    # Players with age <= 18 or age_group indicating junior status.
    query = """
    SELECT country, COUNT(*) as count
    FROM players
    WHERE 
        (age IS NOT NULL AND age <= 18) OR 
        (age_group LIKE 'U%' OR age_group LIKE '%Junior%') OR
        (age IS NULL AND age_group IS NULL) -- Include unknowns if they are likely juniors (often the case in bulk data)
    GROUP BY country
    HAVING country IS NOT NULL AND country != '' AND country != '-'
    ORDER BY count DESC
    LIMIT 30
    """
    
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    
    # Extract country codes
    countries = [row[0] for row in rows]
    
    # Sort alphabetically
    countries.sort()
    
    return countries

if __name__ == "__main__":
    countries = get_top_junior_countries()
    print("REM === BATCH SCRAPE COMMANDS ===")
    for country in countries:
        print(f"python scrape_matches_to_file.py --country {country} --category junior --players-only")

