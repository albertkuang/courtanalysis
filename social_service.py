
import sqlite3
import tennis_db
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing instaloader gracefully
try:
    import instaloader
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False
    logger.warning("Instaloader not found. Instagram fetching will be disabled.")


class SocialMediaService:
    def __init__(self):
        if INSTALOADER_AVAILABLE:
            self.loader = instaloader.Instaloader()
            # Disable login requirement (limits data but works for public profiles sometimes)
            # self.loader.context.is_logged_in = False 
        else:
            self.loader = None

    def get_connection(self):
        return tennis_db.get_connection()

    def fetch_instagram_posts(self, username, limit=12):
        """
        Fetch recent posts for a public Instagram profile.
        Returns a list of dictionaries with post details.
        """
        if not INSTALOADER_AVAILABLE or not self.loader:
            return []

        posts = []
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            count = 0
            for post in profile.get_posts():
                if count >= limit:
                    break
                
                posts.append({
                    'shortcode': post.shortcode,
                    'image_url': post.url, # Note: This URL might expire
                    'caption': post.caption,
                    'posted_at': post.date_utc.isoformat(),
                    'platform': 'instagram'
                })
                count += 1
                
        except Exception as e:
            logger.error(f"Error fetching Instagram posts for {username}: {e}")
            # Fallback or error handling logic
        
        return posts

    def get_player_social_feed(self, player_id):
        """
        Get social feed for a player. 
        Checks cache first. If empty or stale (> 24h), tries to refresh.
        """
        conn = self.get_connection()
        c = conn.cursor()
        
        # Check for cached posts
        query = """
            SELECT shortcode, image_url, caption, posted_at, fetched_at
            FROM social_posts
            WHERE player_id = ? AND platform = 'instagram'
            ORDER BY posted_at DESC
            LIMIT 12
        """
        c.execute(query, (player_id,))
        rows = c.fetchall()
        
        # Decide if we need to refresh
        should_refresh = False
        if not rows:
            should_refresh = True
        else:
            last_fetched = rows[0][4] # fetched_at of the newest post in our DB (approx)
            if last_fetched:
                last_fetched_dt = datetime.fromisoformat(last_fetched)
                if datetime.now() - last_fetched_dt > timedelta(hours=24):
                    should_refresh = True
            else:
                should_refresh = True

        # If refresh needed, find the username and fetch
        if should_refresh:
            # Get Instagram handle
            c.execute("SELECT username FROM player_social_media WHERE player_id = ? AND platform = 'instagram'", (player_id,))
            row = c.fetchone()
            if row and row[0]:
                username = row[0]
                new_posts = self.fetch_instagram_posts(username)
                if new_posts:
                    self.save_posts(conn, player_id, new_posts)
                    # Re-fetch from DB
                    c.execute(query, (player_id,))
                    rows = c.fetchall()

        conn.close()
        
        return [
            {
                'shortcode': r[0],
                'image_url': r[1],
                'caption': r[2],
                'posted_at': r[3],
                'fetched_at': r[4]
            }
            for r in rows
        ]

    def save_posts(self, conn, player_id, posts):
        """Result caching to DB."""
        sql = """
            INSERT OR REPLACE INTO social_posts 
            (player_id, platform, shortcode, image_url, caption, posted_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now().isoformat()
        for p in posts:
            try:
                conn.execute(sql, (
                    player_id, 
                    p['platform'],
                    p['shortcode'],
                    p['image_url'],
                    p['caption'],
                    p['posted_at'],
                    now
                ))
            except Exception as e:
                logger.error(f"Error saving post {p['shortcode']}: {e}")
        conn.commit()

# Singleton instance
social_service = SocialMediaService()
