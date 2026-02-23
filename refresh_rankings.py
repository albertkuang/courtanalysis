
import argparse
import import_rankings_current
import tennis_db
import sys

def main():
    parser = argparse.ArgumentParser(description='Refresh ATP/WTA Rankings (Delta Update)')
    parser.add_argument('--mock', action='store_true', help='Generate mock 2025 data (for dev)')
    parser.add_argument('--force', action='store_true', help='Force update even if recent data exists')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Refreshing Rankings Data")
    print("=" * 60)
    
    conn = tennis_db.get_connection()
    c = conn.cursor()
    
    # Check latest date
    c.execute("SELECT MAX(date) FROM rankings")
    latest = c.fetchone()[0]
    print(f"Current latest date: {latest}")
    
    if args.mock:
        print("Using Mock Data Generator...")
        import_rankings_current.generate_mock_2025_data(conn)
    else:
        # Real scraping (User might want this, but currently commented out in original script)
        # We can try to enable it if requested, but for now let's stick to what's available.
        # The original script has scrape_atp_rankings() but it's not called by default.
        print("Scraping Real Data...")
        try:
            atp_rankings = import_rankings_current.scrape_atp_rankings()
            if atp_rankings:
                # We need a date and tour prefix. 
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                import_rankings_current.import_scraped_rankings(conn, atp_rankings, "ATP", today)
            
            wta_rankings = import_rankings_current.scrape_wta_rankings()
            if wta_rankings:
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                import_rankings_current.import_scraped_rankings(conn, wta_rankings, "WTA", today)
        except Exception as e:
            print(f"Error scraping real data: {e}")

    conn.close()
    print("\nRefresh Complete.")

if __name__ == "__main__":
    main()
