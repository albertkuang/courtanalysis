---
name: UTR Player Scraper
description: Scrape tennis player data from UTR Sports based on country, gender, and category.
---

# UTR Player Scraper

This skill allows you to scrape player data from UTR Sports (Universal Tennis Rating) and save it to a CSV file. It supports filtering by Country, Gender, and Category (Junior/Adult), and includes advanced performance metrics.

## Usage

The scraper is a Python script located at `scraper_analyst.py` in the root of the workspace.

### Command

```bash
python scraper_analyst.py --country=<COUNTRY_CODE> --gender=<GENDER> --category=<CATEGORY> --count=<NUMBER>
```

### Parameters

| Parameter | Description | Default | Example |
| :--- | :--- | :--- | :--- |
| `--country` | The ISO-3 country code (e.g., 'USA', 'CAN', 'FRA') or 'ALL' for worldwide. | `USA` | `--country=CAN` |
| `--gender` | Gender to filter by. 'M' for Male, 'F' for Female. | `M` | `--gender=F` |
| `--category` | Age category. 'junior' (<=18), 'adult' (>18), or 'all'. | `junior` | `--category=adult` |
| `--count` | Target number of players to scrape. | `100` | `--count=500` |

### Examples

**Scrape top 100 Junior Girls in Canada:**
```bash
python scraper_analyst.py --country=CAN --gender=F --category=junior --count=100
```

**Scrape top 50 Adult Men in France:**
```bash
python scraper_analyst.py --country=FRA --gender=M --category=adult --count=50
```

**Scrape top 200 players worldwide (Male, Junior):**
```bash
python scraper_analyst.py --country=ALL --gender=M --category=junior --count=200
```

**Scrape all major tennis countries (Female, Adult):**
```bash
python scraper_analyst.py --country=MAJOR --gender=F --category=adult --count=100
```

## Output Metrics

The script generates a CSV file with the following columns:

| Column | Description |
| :--- | :--- |
| `Rank` | Player rank in the results |
| `Name` | Player full name |
| `Singles UTR` | Current singles UTR rating |
| `Doubles UTR` | Current doubles UTR rating |
| `Peak UTR` | Highest UTR achieved |
| `Min Rating` | Lowest UTR in recent matches |
| `3-Month Trend` | UTR change over 3 months |
| `1-Year Delta` | UTR change over 1 year |
| `Win Record` | Win-Loss record (e.g., "15W-5L") |
| `Win %` | Win percentage |
| `Upset Ratio` | Wins against higher-rated opponents |
| `Avg Opp UTR` | Average opponent UTR |
| `3-Set Record` | Record in 3-set matches |
| `Recent Form (L10)` | Last 10 match results |
| `Tournaments` | Number of tournaments played |
| `vs Higher Rated` | Win % against higher-rated players |
| `Tiebreak Record` | Tiebreak win-loss record |
| `Comeback Wins` | Wins after losing first set |
| `Age` | Player age |
| `Country` | Player nationality |
| `Location` | Player location |
| `Pro Rank` | Professional ranking (if applicable) |
| `Profile URL` | UTR profile link |

## Output File

The script will generate a CSV file in the current directory with the following naming format:
`<Country>_<Category>_<Gender>_<YYYYMMDD>.csv`

Example: `CAN_junior_Female_20250127.csv`

## Requirements

- Python 3.x
- `requests` library

Install dependencies:
```bash
pip install requests
```

## Notes

- The scraper requires valid UTR credentials (hardcoded in the script)
- Rate limiting may apply for large requests
- Use `--country=MAJOR` to search all major tennis countries automatically

# College Roster Scraper

Scrape U.S. college tennis rosters by division (D1/D2/D3) and gender, utilizing UTR data.

## Usage

Script: `college_roster_scraper.py`

### Command

```bash
python college_roster_scraper.py --division=<DIVISION> --gender=<GENDER> --count=<NUMBER>
```

### Parameters

| Parameter | Description | Default | Example |
| :--- | :--- | :--- | :--- |
| `--division` | NCAA Division (D1, D2, D3), NAIA, JUCO, or ALL | `D1` | `--division=D3` |
| `--gender` | Gender: 'M' or 'F' | `M` | `--gender=F` |
| `--count` | Max players to fetch | `500` | `--count=1000` |

### Output

Generates a CSV file: `College_<Division>_<Gender>_<YYYYMMDD>.csv`

Includes standard UTR metrics plus:
- `College`: Name of the school
- `Division`: D1, D2, D3, etc.

