
import argparse
import news_service
import tennis_db

def main():
    parser = argparse.ArgumentParser(description='Refresh Tennis News (Delta Update)')
    parser.add_argument('--internal-only', action='store_true', help='Only generate internal news (Tournament Winners)')
    parser.add_argument('--external-only', action='store_true', help='Only fetch external RSS news')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Refreshing Tennis News")
    print("=" * 60)
    
    # Internal
    if not args.external_only:
        try:
            print("\nUpdating Internal News...")
            news_service.generate_internal_news()
        except Exception as e:
            print(f"Error generating internal news: {e}")
            
    # External
    if not args.internal_only:
        try:
            print("\nFetcing External News...")
            news_service.fetch_external_news()
            try:
                news_service.fetch_favorites_news()
            except Exception as e:
                print(f"Error fetching favorites news: {e}")
                
        except Exception as e:
            print(f"Error fetching external news: {e}")
            
    # Stats
    conn = tennis_db.get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM news_items")
    count = c.fetchone()[0]
    c.execute("SELECT MAX(published_at) FROM news_items")
    latest = c.fetchone()[0]
    conn.close()
    
    print("\n" + "=" * 60)
    print("NEWS REFRESH COMPLETE")
    print(f"Total News Items: {count}")
    print(f"Latest Item: {latest}")
    print("=" * 60)

if __name__ == "__main__":
    main()
