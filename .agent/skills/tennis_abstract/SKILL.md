---
name: Tennis Abstract Scraper
description: Scrape player statistics and match data from Tennis Abstract including Elo ratings, career stats, and match history.
---

# Tennis Abstract Scraper

This skill allows you to scrape player data from Tennis Abstract (tennisabstract.com) and the Match Charting Project, which provides comprehensive ATP/WTA statistics, Elo ratings, and detailed shot-by-shot match data.

## Features

- **Player Profile Data**: Elo rating, current/peak ranking, age, hand, backhand type
- **Elo Ratings**: Access to Tennis Abstract's proprietary Elo rating system
- **Match Charting Data**: Shot-by-shot statistics from 17,000+ matches
- **Player Match History**: Find all charted matches for a specific player
- **Career Statistics**: Historical performance data

## Usage

The scraper is a Python script located at `tennis_abstract_scraper.py` in the root of the workspace.

### Command

```bash
python tennis_abstract_scraper.py [options]
```

### Parameters

| Parameter | Description | Default | Example |
| :--- | :--- | :--- | :--- |
| `--player` | Player name to search for | - | `--player="Leylah Fernandez"` |
| `--gender` | Gender: 'M' for ATP, 'F' for WTA | `F` | `--gender=M` |
| `--output` | Output format: 'json' or 'csv' | `json` | `--output=csv` |
| `--elo-list` | Fetch full Elo rankings list | `false` | `--elo-list` |
| `--charted-matches` | Fetch recent charted matches | `false` | `--charted-matches` |
| `--player-matches` | Fetch charted matches for player | `false` | `--player-matches` |
| `--player-stats` | Fetch charting stats for player | `false` | `--player-stats` |
| `--limit` | Limit number of results | `100` | `--limit=50` |
| `--save` | Save output to file | - | `--save=output.csv` |

---

## Examples

### Player Profile

```bash
# Get WTA player profile
python tennis_abstract_scraper.py --player="Leylah Fernandez" --gender=F

# Get ATP player profile
python tennis_abstract_scraper.py --player="Jannik Sinner" --gender=M
```

### Elo Rankings

```bash
# WTA Elo top 50
python tennis_abstract_scraper.py --elo-list --gender=F --limit=50

# ATP Elo top 100, save to CSV
python tennis_abstract_scraper.py --elo-list --gender=M --limit=100 --save=atp_elo.csv --output=csv
```

### Match Charting Project (NEW!)

```bash
# Get recent charted ATP matches
python tennis_abstract_scraper.py --charted-matches --gender=M --limit=20

# Get all charted matches for a specific player
python tennis_abstract_scraper.py --player="Iga Swiatek" --player-matches --limit=20

# Get charting stats for a player
python tennis_abstract_scraper.py --player="Carlos Alcaraz" --gender=M --player-stats
```

---

## Output Data

### Player Profile Fields

| Field | Description |
| :--- | :--- |
| `name` | Player full name |
| `country` | Country code (e.g., CAN, USA) |
| `age` | Current age |
| `dob` | Date of birth |
| `hand` | Playing hand (L/R) |
| `backhand` | Backhand type (1=one-handed, 2=two-handed) |
| `currentRank` | Current WTA/ATP ranking |
| `peakRank` | Career-high ranking |
| `peakRankDate` | Date of peak ranking |
| `eloRating` | Tennis Abstract Elo rating |
| `eloRank` | Elo-based ranking |
| `itfId` | ITF player ID |

### Elo Rating List Fields

| Field | Description |
| :--- | :--- |
| `eloRank` | Elo rank position |
| `name` | Player name |
| `age` | Player age |
| `eloRating` | Elo rating value |
| `officialRank` | Official WTA/ATP ranking |

### Charted Match Fields

| Field | Description |
| :--- | :--- |
| `matchId` | Unique match identifier |
| `player1` | First player name |
| `player2` | Second player name |
| `date` | Match date (YYYYMMDD) |
| `tournament` | Tournament name |
| `round` | Match round (F, SF, QF, R16, etc.) |
| `surface` | Court surface (Hard, Clay, Grass) |
| `chartUrl` | Link to detailed match chart |

---

## Data Sources

### Tennis Abstract Website
- Player profiles: `https://www.tennisabstract.com/cgi-bin/wplayer.cgi?p=PlayerName`
- ATP profiles: `https://www.tennisabstract.com/cgi-bin/player.cgi?p=PlayerName`
- WTA Elo ratings: `https://tennisabstract.com/reports/wta_elo_ratings.html`
- ATP Elo ratings: `https://tennisabstract.com/reports/atp_elo_ratings.html`

### Match Charting Project (GitHub)
- ATP matches: `https://github.com/JeffSackmann/tennis_MatchChartingProject`
- WTA matches: Same repository
- 17,000+ charted matches with shot-by-shot data
- Updated regularly by volunteer contributors

---

## Sample Output

### Recent Charted Matches
```
2025-11-16  Tour Finals          F     Carlos Alcaraz vs Jannik Sinner
2025-11-15  Tour Finals          SF    Carlos Alcaraz vs Felix Auger Aliassime
2025-11-15  Tour Finals          SF    Alex De Minaur vs Jannik Sinner
```

### Player Charted Matches (Iga Swiatek)
```
2025-09-20  Seoul                QF    vs Barbora Krejcikova
2025-09-03  US Open              QF    vs Amanda Anisimova
2025-07-12  Wimbledon            F     vs Amanda Anisimova
```

---

## Notes

- Tennis Abstract data is publicly available and free
- No authentication required
- Elo ratings are updated frequently during tournaments
- Match charting data depends on volunteer contributions
- The Match Charting Project contains detailed shot-by-shot data for analysis
