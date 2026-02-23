import sqlite3
import tennis_db
import feedparser
from datetime import datetime
import time
import requests
import re

# Use the same database as the rest of the app
DB_FILE = tennis_db.DB_FILE

def get_connection():
    return tennis_db.get_connection()

# --- Internal News Generators ---

def generate_internal_news():
    """Scan matches and players for interesting events and create news items."""
    conn = get_connection()
    c = conn.cursor()
    
    print("Generating internal news...")
    
    # 1. Recent Winners (Last 7 days)
    # Find matches that are 'Finals' and happened recently
    query = """
        SELECT m.date, m.tournament, m.score, m.winner_id, p.name as winner_name
        FROM matches m
        JOIN players p ON m.winner_id = p.player_id
        WHERE (m.round LIKE '%Final%' OR m.round = 'F') 
          AND m.round NOT LIKE '%Quarter%' 
          AND m.round NOT LIKE '%Semi%'
          AND m.date >= date('now', '-7 days')
    """
    c.execute(query)
    winners = c.fetchall()
    
    for row in winners:
        date, tournament, score, pid, name = row
        title = f"{name} wins {tournament}!"
        summary = f"{name} captured the title at {tournament} with a {score} victory in the final."
        url = f"/player/{pid}" # Internal link structure
        
        # Unique ID for internal items to prevent dupes: "internal_winner_{match_date}_{pid}"
        # We store this in 'url' since it has a UNIQUE constraint, but we might want a real url.
        # Let's use a unique source_id approach or just check existence.
        # Actually URL is unique. Let's make a fake permalink.
        fake_url = f"internal://winner/{pid}/{date}/{tournament.replace(' ', '_')}"
        
        save_news_item(conn, {
            'title': title,
            'summary': summary,
            'url': fake_url,
            'source': 'CourtSide Analytics',
            'image_url': None, # We could generate a placeholder
            'published_at': date,
            'category': 'Tournament Result',
            'is_internal': 1,
            'player_id_ref': pid
        })

    # 2. Big Movers (UTR Delta > 1.0 in last year for Juniors)
    # This is static, so we only want to generate it if it's "New". 
    # Hard to track "New" movement without a history log trigger. 
    # For now, let's skip "Movement News" to avoid spam, or finding a way to track "Recent" jumps.
    
    conn.commit()
    conn.close()


# --- External RSS Fetcher ---

# Specific high-quality feeds
LEGACY_RSS_FEEDS = [
    {
        'url': 'https://zootennis.blogspot.com/feeds/posts/default?alt=rss', 
        'source': 'ZooTennis',
        'category': 'Junior/College'
    }
]

# Google News Topics to track
TOPICS = [
    {'query': 'ATP Tennis', 'category': 'ATP Tour'},
    {'query': 'WTA Tennis', 'category': 'WTA Tour'},
    {'query': 'College Tennis', 'category': 'College'},
    {'query': 'ITF Tennis', 'category': 'ITF'},
    {'query': 'US Open Tennis', 'category': 'Major Events'},
    {'query': 'ITF Junior Tennis', 'category': 'ITF Junior'},
    {'query': 'USTA Junior Tennis', 'category': 'ITF Junior'},
    {'query': 'Tennis Europe Junior', 'category': 'ITF Junior'},
    {'query': 'Junior Orange Bowl Tennis', 'category': 'ITF Junior'},
    {'query': 'Les Petits As', 'category': 'ITF Junior'},
    {'query': 'Eddie Herr Tennis', 'category': 'ITF Junior'},
    {'query': 'ITF World Tennis Tour Juniors', 'category': 'ITF Junior'},
    {'query': 'USTA National Campus', 'category': 'ITF Junior'},
    {'query': 'College Tennis Recruitment', 'category': 'Junior/College'},
    {'query': 'ITF J500', 'category': 'ITF Junior'},
    {'query': 'ITF J300', 'category': 'ITF Junior'},
    {'query': 'ITF J200', 'category': 'ITF Junior'}
]

def fetch_external_news():
    """Fetch and parse RSS feeds from Google News Topics and legacy sources."""
    conn = get_connection()
    from urllib.parse import quote
    
    print("Fetching external news...")
    
    # 1. Fetch Legacy Feeds
    for feed_info in LEGACY_RSS_FEEDS:
        try:
            print(f"Polling {feed_info['source']}...")
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries[:3]:
                save_rss_entry(conn, entry, feed_info['source'], feed_info['category'])
        except Exception as e:
            print(f"Failed to fetch {feed_info['source']}: {e}")

    # 2. Fetch Google News Topics
    for topic in TOPICS:
        try:
            print(f"Polling Topic: {topic['query']}...")
            # Append when:7d to force recent news
            search_query = topic['query'] + " when:7d"
            encoded_query = quote(search_query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]: # Top 10 per topic
                # Source often inside title "Title - Source"
                source = "Google News"
                title = entry.title
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source = parts[1]
                
                # Dedupe: skip if title is too short or weird
                if len(title) < 10: continue

                save_rss_entry(conn, entry, source, topic['category'], title_override=title)
                
        except Exception as e:
             print(f"Failed to fetch topic {topic['query']}: {e}")

    conn.commit()
    conn.close()

def save_rss_entry(conn, entry, source_name, category, title_override=None):
    """Helper to parse and save a single RSS entry."""
    title = title_override or entry.title
    link = entry.link
    
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed)).isoformat()
    else:
        pub_date = datetime.now().isoformat()
    
    summary = entry.get('summary', '') or entry.get('description', '')
    # Clean summary
    clean_summary = re.sub('<[^<]+?>', '', summary)[:250]
    if len(clean_summary) == 250: clean_summary += "..."
    
    # Image extraction attempt
    image_url = None
    if 'media_content' in entry:
        image_url = entry.media_content[0]['url']
    elif 'media_thumbnail' in entry:
        image_url = entry.media_thumbnail[0]['url']
        
    save_news_item(conn, {
        'title': title,
        'summary': clean_summary,
        'url': link,
        'source': source_name,
        'image_url': image_url,
        'published_at': pub_date,
        'category': category,
        'is_internal': 0,
        'player_id_ref': None
    })


def save_news_item(conn, item):
    """Insert news item if URL doesn't exist."""
    sql = """
    INSERT OR IGNORE INTO news_items 
    (title, summary, url, source, image_url, published_at, category, is_internal, player_id_ref)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        conn.execute(sql, (
            item['title'],
            item['summary'],
            item['url'],
            item['source'],
            item['image_url'],
            item['published_at'], 
            item['category'],
            item['is_internal'],
            item['player_id_ref']
        ))
    except Exception as e:
        print(f"Error saving news: {e}")


def fetch_favorites_news():
    """Fetch news for all players that are marked as favorites by any user using Google News RSS."""
    conn = get_connection()
    c = conn.cursor()
    
    # Get all unique favorited players
    print("Fetching news for favorite players...")
    query = """
        SELECT DISTINCT p.player_id, p.name 
        FROM user_favorites f
        JOIN players p ON f.player_id = p.player_id
    """
    c.execute(query)
    favorites = c.fetchall()
    
    conn.close() # Close and reopen inside loop or helper to manage scope if needed, but here simple is fine.
    # actually better to keep open or pass to save_news_item. save_news_item opens its own execution/helper? 
    # Current save_news_item takes `conn`. So let's keep `conn` open.
    
    # Re-open for writing
    conn = get_connection()
    
    from urllib.parse import quote
    
    for pid, name in favorites:
        try:
            # Construct Google News RSS Search Query
            search_query = f'"{name}" tennis'
            encoded_query = quote(search_query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            print(f"Searching news for {name}...")
            feed = feedparser.parse(rss_url)
            
            count = 0
            for entry in feed.entries[:3]: # Limit to top 3 per player to avoid clutter
                title = entry.title
                link = entry.link
                
                # Google News RSS dates are standard RFC822, feedparser handles them well usually
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed)).isoformat()
                else:
                    pub_date = datetime.now().isoformat()
                
                summary = entry.get('summary', '') or entry.get('description', '')
                clean_summary = re.sub('<[^<]+?>', '', summary)[:200]
                if clean_summary: clean_summary += "..."
                
                # Image: Google RSS often doesn't give good images, maybe try to match source or leave generic
                image_url = None 
                
                save_news_item(conn, {
                    'title': title,
                    'summary': clean_summary,
                    'url': link,
                    'source': 'Google News', # Or split title "Title - Source"
                    'image_url': image_url,
                    'published_at': pub_date,
                    'category': 'Player News',
                    'is_internal': 0,
                    'player_id_ref': pid
                })
                count += 1
            print(f"  Found {count} items.")
            
        except Exception as e:
            print(f"Error fetching news for {name}: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    generate_internal_news()
    fetch_external_news()
    fetch_favorites_news()
