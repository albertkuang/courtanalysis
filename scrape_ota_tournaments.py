"""
OTA Tournament Scraper
Scrapes tournament and match data from Ontario Tennis Association (TournamentSoftware.com)
Uses Selenium for dynamic JavaScript content
"""

import sqlite3
import time
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class OTAScraper:
    """Scraper for Ontario Tennis Association tournaments via TournamentSoftware"""
    
    BASE_URL = "https://ota.tournamentsoftware.com"
    
    def __init__(self, headless: bool = True, db_path: str = "tennis_data.db"):
        self.db_path = db_path
        self.headless = headless
        self.driver = None
        self.tournaments_scraped = 0
        self.matches_scraped = 0
        
    def _init_driver(self):
        """Initialize Edge WebDriver"""
        print("Initializing Microsoft Edge WebDriver...")
        edge_options = Options()
        if self.headless:
            edge_options.add_argument("--headless=new")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--window-size=1920,1080")
        edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Specify Edge binary path explicitly
        edge_binary_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        edge_options.binary_location = edge_binary_path
        
        try:
            # Try using webdriver_manager first
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=edge_options)
        except Exception as e:
            print(f"WebDriver Manager failed: {e}")
            print("Trying to use Edge driver from system PATH...")
            # Fallback: try without service (uses msedgedriver from PATH if available)
            try:
                self.driver = webdriver.Edge(options=edge_options)
            except Exception as e2:
                print(f"Edge driver not found in PATH: {e2}")
                print("\nTo fix this, please download the Edge driver manually:")
                print("1. Check your Edge version by going to edge://settings/help")
                print("2. Download matching driver from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/")
                print("3. Extract msedgedriver.exe to a folder in your PATH (e.g., C:\\Windows)")
                raise RuntimeError("Could not initialize WebDriver. See instructions above.")
        
        self.driver.implicitly_wait(10)
        print("WebDriver initialized successfully")
        
    def _close_driver(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def _wait_for_element(self, by: By, value: str, timeout: int = 15):
        """Wait for element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None
            
    def get_tournaments_list(self, days_back: int = 30, days_forward: int = 7) -> List[Dict]:
        """Get list of tournaments from OTA search page"""
        tournaments = []
        
        # Calculate date range
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days_forward)).strftime("%Y-%m-%d")
        
        url = f"{self.BASE_URL}/find?StartDate={start_date}&EndDate={end_date}&StatusFilterID=0"
        print(f"\nFetching tournaments from {start_date} to {end_date}")
        print(f"URL: {url}")
        
        self.driver.get(url)
        time.sleep(3)  # Wait for dynamic content
        
        # Wait for search results to load
        results_area = self._wait_for_element(By.ID, "searchResultArea", timeout=10)
        if not results_area:
            print("Could not find search results area")
            return tournaments
            
        # Scroll down to trigger lazy loading
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Find all tournament cards/items
        # TournamentSoftware uses various class names for tournament items
        tournament_elements = self.driver.find_elements(By.CSS_SELECTOR, ".media, .tournament-item, [class*='tournament']")
        
        print(f"Found {len(tournament_elements)} potential tournament elements")
        
        # OTA uses URLs like: /sport/tournament?id=2A5DD4C5-5CDC-4C03-9EDC-DAF0C839D48D
        links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/sport/tournament?id=']")
        
        print(f"Found {len(links)} tournament links with /sport/tournament?id= pattern")
        
        # Collect all tournament IDs and their info
        # Each tournament typically has 2 links: one for image (empty text), one with name
        tournament_data = {}  # id -> {name, url, date}
        
        for link in links:
            href = link.get_attribute("href") or ""
            # Extract tournament ID from URL like /sport/tournament?id=GUID
            match = re.search(r'tournament\?id=([A-F0-9-]{36})', href, re.I)
            if match:
                tournament_id = match.group(1)
                name = link.text.strip()
                
                # If we already have this tournament, update only if we have better data
                if tournament_id in tournament_data:
                    # Update name if we now have one and didn't before
                    if name and len(name) > 3 and not tournament_data[tournament_id].get("name"):
                        tournament_data[tournament_id]["name"] = name
                else:
                    # New tournament - get additional info
                    date_text = ""
                    try:
                        media_elem = link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'media')]")
                        date_elems = media_elem.find_elements(By.CSS_SELECTOR, "time")
                        if date_elems:
                            date_text = date_elems[0].get_attribute("datetime") or date_elems[0].text.strip()
                    except:
                        pass
                    
                    tournament_data[tournament_id] = {
                        "id": tournament_id,
                        "name": name if (name and len(name) > 3) else "",
                        "url": href,
                        "date": date_text
                    }
        
        # Filter to only tournaments with names
        tournaments = [t for t in tournament_data.values() if t.get("name")]
        
        print(f"Found {len(tournaments)} tournaments with valid IDs and names")
        return tournaments
        
    def get_tournament_matches(self, tournament_id: str, tournament_name: str) -> List[Dict]:
        """Get matches from a specific tournament"""
        matches = []
        
        # First, get the draws page (must use .aspx extension for OTA)
        draws_url = f"{self.BASE_URL}/sport/draws.aspx?id={tournament_id.lower()}"
        print(f"  Loading draws page: {draws_url}")
        self.driver.get(draws_url)
        time.sleep(3)
        
        # Find individual draw links (format: /sport/draw.aspx?id=GUID&draw=N)
        draw_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='draw.aspx'][href*='draw=']")
        
        print(f"  Found {len(draw_links)} individual draw links")
        
        # Extract unique draw URLs
        draws_to_visit = []
        seen_draw_ids = set()
        for link in draw_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            
            # Extract draw number from URL
            draw_match = re.search(r'draw=(\d+)', href)
            if draw_match:
                draw_id = draw_match.group(1)
                if draw_id not in seen_draw_ids:
                    seen_draw_ids.add(draw_id)
                    draw_name = text if text else f"Draw {draw_id}"
                    draws_to_visit.append({"url": href, "name": draw_name, "id": draw_id})
        
        print(f"  Will visit {len(draws_to_visit)} unique draws")
        
        # Visit each draw and extract matches
        for draw in draws_to_visit[:10]:  # Limit to first 10 draws
            draw_matches = self._get_draw_matches_v2(draw["url"], tournament_name, draw["name"])
            matches.extend(draw_matches)
            time.sleep(1)  # Be polite
            
        return matches
    
    def _get_draw_matches_v2(self, draw_url: str, tournament_name: str, draw_name: str) -> List[Dict]:
        """Extract matches from an OTA draw page (v2 - proper structure)"""
        matches = []
        
        print(f"    Scraping draw: {draw_name}")
        self.driver.get(draw_url)
        time.sleep(2)
        
        # Find all .match elements
        match_elements = self.driver.find_elements(By.CSS_SELECTOR, ".match")
        print(f"      Found {len(match_elements)} matches")
        
        for match_elem in match_elements:
            try:
                match_data = self._parse_ota_match(match_elem, tournament_name, draw_name)
                if match_data:
                    matches.append(match_data)
            except Exception as e:
                continue
        
        print(f"      Extracted {len(matches)} valid matches")
        return matches
    
    def _parse_ota_match(self, match_elem, tournament_name: str, draw_name: str) -> Optional[Dict]:
        """Parse a single OTA match element"""
        try:
            # Get the two player rows
            rows = match_elem.find_elements(By.CSS_SELECTOR, ".match__row")
            if len(rows) < 2:
                return None
            
            winner = None
            loser = None
            winner_scores = []
            loser_scores = []
            match_date = ""
            
            for row in rows[:2]:  # Only first two rows are players
                row_class = row.get_attribute("class") or ""
                is_winner = "has-won" in row_class
                
                # Get player name
                player_link = row.find_elements(By.CSS_SELECTOR, "a[href*='player']")
                if player_link:
                    player_name = player_link[0].text.strip()
                    # Remove seed/wildcard indicators like [1], [WC]
                    player_name = re.sub(r'\s*\[.*?\]', '', player_name).strip()
                else:
                    continue
                
                if is_winner:
                    winner = player_name
                else:
                    loser = player_name
            
            # If no has-won found, first player with "W" in text is winner
            if not winner and not loser:
                match_text = match_elem.text
                lines = match_text.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == 'W' and i > 0:
                        # Previous line was the winner
                        winner = re.sub(r'\s*\[.*?\]', '', lines[i-1]).strip()
                    elif line.strip() == 'W' and i < len(lines) - 1:
                        pass  # Winner was already set
            
            # Get date from footer
            try:
                date_elem = match_elem.find_element(By.CSS_SELECTOR, ".match__footer")
                date_text = date_elem.text.strip()
                # Extract date pattern like "Fri 2026-01-30 3:00 PM"
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                if date_match:
                    match_date = date_match.group(1)
            except:
                match_date = datetime.now().strftime("%Y-%m-%d")
            
            # Parse score from the full match text
            # The format is: digits separated by newlines (6, 3, 6, 1 = 6-3 6-1)
            match_text = match_elem.text
            lines = [l.strip() for l in match_text.split('\n') if l.strip()]
            
            # Find score digits (single digits 0-7, or "Retired", "Walkover")
            score_parts = []
            collecting_scores = False
            for line in lines:
                if line == 'W':
                    collecting_scores = True
                    continue
                if collecting_scores and line.isdigit() and len(line) <= 2:
                    score_parts.append(line)
                elif collecting_scores and line in ['Retired', 'Walkover', 'retired', 'walkover']:
                    score_parts = [line]
                    break
                elif collecting_scores and re.match(r'^\d{4}-\d{2}-\d{2}', line):
                    # Date line, stop
                    break
            
            # Convert score parts to score string (e.g., [6,3,6,1] -> "6-3 6-1")
            if score_parts and score_parts[0] not in ['Retired', 'Walkover', 'retired', 'walkover']:
                score_sets = []
                for i in range(0, len(score_parts), 2):
                    if i + 1 < len(score_parts):
                        score_sets.append(f"{score_parts[i]}-{score_parts[i+1]}")
                score = " ".join(score_sets)
            elif score_parts:
                score = score_parts[0]
            else:
                score = ""
            
            if winner and loser and score:
                return {
                    "winner": winner,
                    "loser": loser,
                    "score": score,
                    "tournament": tournament_name,
                    "draw": draw_name,
                    "date": match_date,
                    "source": "OTA"
                }
            
        except Exception as e:
            pass
        
        return None
        
    def _get_draw_matches(self, draw_url: str, tournament_name: str, draw_name: str) -> List[Dict]:
        """Extract matches from a draw page"""
        matches = []
        
        print(f"    Scraping draw: {draw_name}")
        self.driver.get(draw_url)
        time.sleep(2)
        
        # Look for match elements - TournamentSoftware has various structures
        # Try multiple selectors
        selectors = [
            ".match",
            "[class*='match']",
            "table tr",
            ".draw-match",
            ".result-row"
        ]
        
        for selector in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if len(elements) > 5:  # Found something
                print(f"      Found {len(elements)} elements with selector '{selector}'")
                break
        
        # Try to extract match data from tables
        tables = self.driver.find_elements(By.CSS_SELECTOR, "table")
        for table in tables:
            rows = table.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td")
                    if len(cells) >= 3:
                        # Try to extract player names and score
                        text_content = [c.text.strip() for c in cells]
                        
                        # Look for score pattern (like 6-3 6-4)
                        score_pattern = r'\d+-\d+'
                        for i, text in enumerate(text_content):
                            if re.search(score_pattern, text):
                                # Found a score, try to get player names
                                match_data = self._parse_match_row(text_content, tournament_name, draw_name)
                                if match_data:
                                    matches.append(match_data)
                                break
                except Exception as e:
                    continue
                    
        # Also try the specific TournamentSoftware match structure
        match_elements = self.driver.find_elements(By.CSS_SELECTOR, ".match, .bracket-match")
        for match_elem in match_elements:
            match_data = self._parse_match_element(match_elem, tournament_name, draw_name)
            if match_data:
                matches.append(match_data)
                
        print(f"      Extracted {len(matches)} matches from {draw_name}")
        return matches
        
    def _parse_match_row(self, row_text: List[str], tournament_name: str, draw_name: str) -> Optional[Dict]:
        """Parse a match from table row text"""
        try:
            # Common patterns:
            # [Player1] | [Score] | [Player2]
            # [Player1] | [Player2] | [Score]
            
            score_pattern = r'(\d+-\d+(?:\s+\d+-\d+)*)'
            
            # Find the score
            score = None
            score_idx = -1
            for i, text in enumerate(row_text):
                match = re.search(score_pattern, text)
                if match:
                    score = match.group(1)
                    score_idx = i
                    break
                    
            if not score:
                return None
                
            # Try to identify players
            # Remove the score from consideration
            players = [t for i, t in enumerate(row_text) if i != score_idx and len(t) > 2]
            
            if len(players) >= 2:
                # Assume first player won if they're listed first
                return {
                    "winner": players[0],
                    "loser": players[1] if len(players) > 1 else "Unknown",
                    "score": score,
                    "tournament": tournament_name,
                    "draw": draw_name,
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                
        except Exception as e:
            pass
            
        return None
        
    def _parse_match_element(self, element, tournament_name: str, draw_name: str) -> Optional[Dict]:
        """Parse a match from a match element"""
        try:
            # Get all text in the element
            text = element.text
            
            # Look for player names and scores
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            if len(lines) >= 2:
                # Look for score pattern
                score_pattern = r'(\d+-\d+)'
                scores = []
                players = []
                
                for line in lines:
                    if re.search(score_pattern, line):
                        scores.append(line)
                    elif len(line) > 2 and not line.isdigit():
                        players.append(line)
                        
                if len(players) >= 2 and scores:
                    return {
                        "winner": players[0],
                        "loser": players[1],
                        "score": " ".join(scores),
                        "tournament": tournament_name,
                        "draw": draw_name,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                    
        except Exception as e:
            pass
            
        return None
        
    def save_matches_to_db(self, matches: List[Dict]):
        """Save scraped matches to database"""
        if not matches:
            return
            
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        inserted = 0
        for match in matches:
            try:
                # Check if match already exists
                c.execute("""
                    SELECT match_id FROM matches 
                    WHERE tournament = ? AND winner_id = ? AND loser_id = ? AND score = ?
                    LIMIT 1
                """, (match["tournament"], match.get("winner_id"), match.get("loser_id"), match["score"]))
                
                if c.fetchone():
                    continue  # Already exists
                    
                # For now, we'll store the names directly since we may not have player IDs
                # You might want to add logic to match players to existing DB entries
                c.execute("""
                    INSERT OR IGNORE INTO matches 
                    (tournament, date, score, winner_id, loser_id, round, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    match["tournament"],
                    match.get("date", datetime.now().strftime("%Y-%m-%d")),
                    match["score"],
                    match.get("winner_id", match.get("winner", "Unknown")),
                    match.get("loser_id", match.get("loser", "Unknown")),
                    match.get("draw", ""),
                    "OTA_SCRAPE"
                ))
                inserted += 1
            except Exception as e:
                print(f"Error inserting match: {e}")
                
        conn.commit()
        conn.close()
        print(f"Inserted {inserted} new matches")
        self.matches_scraped += inserted
        
    def scrape_all(self, days_back: int = 30, days_forward: int = 7, max_tournaments: int = 20):
        """Main scraping function"""
        try:
            self._init_driver()
            
            print("=" * 60)
            print("OTA Tournament Scraper")
            print("=" * 60)
            
            # Get tournaments list
            tournaments = self.get_tournaments_list(days_back, days_forward)
            
            if not tournaments:
                print("No tournaments found!")
                return
                
            print(f"\nFound {len(tournaments)} tournaments to scrape")
            
            # Scrape each tournament
            for i, tournament in enumerate(tournaments[:max_tournaments]):
                print(f"\n[{i+1}/{min(len(tournaments), max_tournaments)}] {tournament['name']}")
                
                try:
                    matches = self.get_tournament_matches(tournament["id"], tournament["name"])
                    
                    if matches:
                        print(f"  Found {len(matches)} matches")
                        self.save_matches_to_db(matches)
                    else:
                        print("  No matches found")
                        
                    self.tournaments_scraped += 1
                    
                except Exception as e:
                    print(f"  Error scraping tournament: {e}")
                    
                time.sleep(2)  # Be polite between tournaments
                
            print("\n" + "=" * 60)
            print(f"Scraping complete!")
            print(f"Tournaments scraped: {self.tournaments_scraped}")
            print(f"Matches saved: {self.matches_scraped}")
            print("=" * 60)
            
        finally:
            self._close_driver()


def main():
    parser = argparse.ArgumentParser(description="Scrape OTA tournaments from TournamentSoftware.com")
    parser.add_argument("--days-back", type=int, default=30, help="Days back to search (default: 30)")
    parser.add_argument("--days-forward", type=int, default=7, help="Days forward to search (default: 7)")
    parser.add_argument("--max-tournaments", type=int, default=20, help="Max tournaments to scrape (default: 20)")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode (not headless)")
    parser.add_argument("--db", type=str, default="tennis_data.db", help="Database path")
    
    args = parser.parse_args()
    
    scraper = OTAScraper(headless=not args.visible, db_path=args.db)
    scraper.scrape_all(
        days_back=args.days_back,
        days_forward=args.days_forward,
        max_tournaments=args.max_tournaments
    )


if __name__ == "__main__":
    main()
