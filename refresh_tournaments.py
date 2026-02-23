
import argparse
import scrape_ota_tournaments
import tennis_db
from datetime import datetime, timedelta

def main():
    parser = argparse.ArgumentParser(description='Refresh OTA Tournaments (Delta Update)')
    parser.add_argument('--days-back', type=int, default=7, help='Days back to search (default: 7)')
    parser.add_argument('--days-forward', type=int, default=7, help='Days forward to search (default: 7)')
    parser.add_argument('--max', type=int, default=10, help='Max tournaments to scrape (default: 10)')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode (default: headless)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Refreshing OTA Tournaments")
    print("=" * 60)
    
    # Calculate date range for display
    start_date = (datetime.now() - timedelta(days=args.days_back)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=args.days_forward)).strftime("%Y-%m-%d")
    print(f"Searching from {start_date} to {end_date}")
    
    # Run Scraper
    scraper = scrape_ota_tournaments.OTAScraper(headless=not args.visible, db_path='tennis_data.db')
    try:
        scraper.scrape_all(
            days_back=args.days_back,
            days_forward=args.days_forward,
            max_tournaments=args.max
        )
    except Exception as e:
        print(f"Error refreshing tournaments: {e}")
    
    print("\nRefresh Complete.")

if __name__ == "__main__":
    main()
