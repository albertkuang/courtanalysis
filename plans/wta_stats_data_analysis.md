# WTA/ATP Statistics Data Requirements Analysis

## Overview
This document analyzes the data requirements for generating specific tennis statistics, identifies gaps in the current dataset, and provides concrete steps to populate missing data.

---

## Current Data Infrastructure

### Database Tables (tennis_data.db)
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `players` | Player profiles | player_id, name, birth_date, age, pro_rank |
| `matches` | Match results + stats | winner_id, loser_id, date, tournament, round, tourney_level, w_ace, l_ace, etc. |
| `rankings` | Historical rankings | player_id, date, rank, points |
| `sackmann_profiles` | Pro player metadata | sackmann_id, full_name, dob, tour |
| `sackmann_player_map` | ID mapping | sackmann_id → player_id |

### Available Import Scripts
| Script | Source | Data Imported |
|--------|--------|---------------|
| `import_sackmann.py` | Jeff Sackmann GitHub | ATP/WTA matches with stats |
| `import_rankings.py` | Jeff Sackmann GitHub | ATP/WTA rankings (2020s) |
| `tennis_abstract_scraper.py` | Tennis Abstract | Player profiles, Elo, birth dates |
| `update_player_ages.py` | UTR API | Birth dates, ages |

---

## Requested Statistics Analysis

### 1. WTA-1000 Consecutive Opening Matches Streak
**Stat:** Since 2009, only four have won more consecutive opening matches at WTA-1000 events than Karolina Muchova (17) – Iga Swiatek (31), Serena Williams, Victoria Azarenka (23 each) and Maria Sharapova (19)

**Data Requirements:**
| Requirement | Source | Status | Action |
|-------------|--------|--------|--------|
| WTA matches 2009-2026 | Sackmann WTA | ⚠️ Need to verify import | Run `import_sackmann.py --tour wta --start 2009 --end 2026` |
| Tournament level filter | `tourney_level = 'PM'` | ✅ Available | Query filter |
| Round identification | `round IN ('R128','R64','R32')` | ✅ Available | Query filter |
| Player ID mapping | `sackmann_player_map` | ⚠️ Verify players exist | Check specific players |

**Players to Verify:**
- Karolina Muchova
- Iga Swiatek  
- Serena Williams
- Victoria Azarenka
- Maria Sharapova

**Implementation Approach:**
```sql
-- Find opening match wins for a player at WTA-1000 events
SELECT COUNT(*) as consecutive_wins
FROM matches 
WHERE winner_id = <player_id>
  AND tourney_level = 'PM'  -- Premier Mandatory = WTA-1000
  AND date >= '2009-01-01'
  AND round IN ('R128', 'R64', 'R32')  -- Opening rounds
ORDER BY date
-- Then calculate consecutive streak logic in Python
```

---

### 2. Tier I/WTA-1000 Wins by Players Aged 40+
**Stat:** Since 1990, Vera Zvonareva (41y 154d) is now just the fourth player aged 40+ to win a Tier I/WTA-1000 main draw match after Kimiko Date, Serena Williams and Venus Williams.

**Data Requirements:**
| Requirement | Source | Status | Action |
|-------------|--------|--------|--------|
| WTA matches 1990-2026 | Sackmann WTA | ⚠️ Need import | Run `import_sackmann.py --tour wta --start 1990 --end 2026` |
| Tournament levels | `tourney_level IN ('PM','M','1')` | ✅ Available | Tier I = '1' pre-2009 |
| Player birth dates | `players.birth_date` | ⚠️ May be missing | Enrich via Tennis Abstract |
| Age calculation | match_date - birth_date | ✅ Computable | Python logic |

**Players Requiring Birth Date Enrichment:**
- Vera Zvonareva (need exact DOB for age calculation)
- Kimiko Date
- Serena Williams
- Venus Williams

**Data Enrichment Commands:**
```bash
# Option 1: Use Tennis Abstract scraper
python tennis_abstract_scraper.py --player "Vera Zvonareva" --gender F

# Option 2: Use UTR API (requires auth)
python update_player_ages.py --name "Zvonareva"
```

**Implementation Approach:**
```sql
-- Find 40+ winners at Tier I/WTA-1000 events
SELECT w.name, m.date, m.tournament, p.birth_date,
       CAST((julianday(m.date) - julianday(p.birth_date)) AS INTEGER) as age_days
FROM matches m
JOIN players w ON m.winner_id = w.player_id
JOIN players p ON m.winner_id = p.player_id
WHERE m.tourney_level IN ('PM', 'M', '1')  -- WTA-1000, Masters, Tier I
  AND p.birth_date IS NOT NULL
  AND (julianday(m.date) - julianday(p.birth_date)) > 40*365
ORDER BY age_days DESC
```

---

### 3. Sara Bejlek Career-High Ranking Win
**Stat:** Jelena Ostapenko ranked 24 is the highest ranked opponent Sara Bejlek has defeated in her career, she will feature in her second WTA-level quarterfinal after Prague 2025.

**Data Requirements:**
| Requirement | Source | Status | Action |
|-------------|--------|--------|--------|
| Sara Bejlek matches | `matches` table | ❓ Unknown | Verify player exists |
| Jelena Ostapenko matches | `matches` table | ❓ Unknown | Verify player exists |
| **Opponent rank at match time** | ❌ NOT AVAILABLE | ❌ **CRITICAL GAP** | Need new data source |
| Tournament round info | `round = 'QF'` | ✅ Available | Query filter |

**⚠️ CRITICAL DATA GAP: Ranking at Match Time**
The current `rankings` table has weekly rankings, but we need to know the opponent's rank **on the specific match date**. This requires:
1. Join `matches` with `rankings` on closest date
2. Or import match-level ranking data (some sources include winner_rank, loser_rank)

**Potential Solutions:**
1. **Sackmann match data includes rankings** - Check if `winner_rank` and `loser_rank` columns exist
2. **Date-based ranking lookup** - Find ranking closest to match date
3. **Tennis Abstract** - Has match-level rankings

**Implementation Approach (if rankings available):**
```sql
-- Find highest-ranked opponent defeated
SELECT m.date, m.tournament, l.name as opponent, 
       r.rank as opponent_rank
FROM matches m
JOIN players l ON m.loser_id = l.player_id
LEFT JOIN rankings r ON l.player_id = r.player_id 
     AND r.date = (SELECT MAX(date) FROM rankings WHERE date <= m.date AND player_id = l.player_id)
WHERE m.winner_id = <sara_bejlek_id>
ORDER BY r.rank ASC
LIMIT 1
```

---

### 4. WTA-500 Wins Since 2025
**Stat:** Since 2025, no player has registered more wins in Women's Singles WTA-500 events than Ekaterina Alexandrova (25)

**Data Requirements:**
| Requirement | Source | Status | Action |
|-------------|--------|--------|--------|
| WTA 2025-2026 matches | Sackmann WTA | ⚠️ Need import | Run import script |
| Tournament level filter | `tourney_level IN ('P','A')` | ✅ Available | WTA-500 = Premier/International |
| Player identification | Ekaterina Alexandrova | ❓ Verify exists | Check DB |

**Data Import Command:**
```bash
python import_sackmann.py --tour wta --start 2025 --end 2026
```

**Implementation Approach:**
```sql
-- Count WTA-500 wins in 2025+
SELECT w.name, COUNT(*) as wins
FROM matches m
JOIN players w ON m.winner_id = w.player_id
WHERE m.tourney_level IN ('P', 'A')  -- WTA-500 levels
  AND m.date >= '2025-01-01'
  AND m.source LIKE 'sackmann-wta%'
GROUP BY w.name
ORDER BY wins DESC
LIMIT 10
```

---

### 5. Australian Open 2026 Aces Leader (Women)
**Stat:** Elena Rybakina (47) is the player with the most aces in Women's Singles at the Australian Open 2026

**Data Requirements:**
| Requirement | Source | Status | Action |
|-------------|--------|--------|--------|
| AO 2026 WTA matches | Sackmann WTA 2026 | ⚠️ Need import | Run import script |
| Ace statistics | `w_ace`, `l_ace` columns | ✅ Available | Sum for each player |
| Player identification | Elena Rybakina | ❓ Verify exists | Check DB |

**Data Import Command:**
```bash
python import_sackmann.py --tour wta --start 2026 --end 2026
```

**Implementation Approach:**
```sql
-- Sum aces for each player at AO 2026
SELECT p.name, 
       SUM(CASE WHEN m.winner_id = p.player_id THEN m.w_ace ELSE m.l_ace END) as total_aces
FROM matches m
JOIN players p ON (m.winner_id = p.player_id OR m.loser_id = p.player_id)
WHERE m.tournament LIKE '%Australian Open%'
  AND m.date >= '2026-01-01' AND m.date < '2026-02-01'
  AND m.source LIKE 'sackmann-wta%'
GROUP BY p.name
ORDER BY total_aces DESC
```

---

### 6. Australian Open 2026 Winners Leader (Men)
**Stat:** Carlos Alcaraz is the player with the most winners in Men's Singles at the Australian Open 2026

**Data Requirements:**
| Requirement | Source | Status | Action |
|-------------|--------|--------|--------|
| AO 2026 ATP matches | Sackmann ATP 2026 | ⚠️ Need import | Run import script |
| **Winners statistics** | ❌ NOT IN SCHEMA | ❌ **IMPOSSIBLE** | Not tracked |

**⚠️ CRITICAL DATA GAP: Winners Not Tracked**
The Sackmann match statistics include:
- `w_ace`, `w_df` (aces, double faults)
- `w_svpt`, `w_1stIn`, `w_1stWon`, `w_2ndWon` (serve stats)
- `w_bpSaved`, `w_bpFaced` (break point stats)

**"Winners" (total winning shots) is NOT tracked in any available data source.**

**Alternative Stats Available:**
- Most **aces** (available)
- Most **1st serve points won** (available)
- Most **break points converted** (derivable)

**No external API currently provides "winners" statistics for matches.**

---

## Summary: Data Availability Matrix

| Statistic | Match Data | Player Data | Stats Data | Rankings | Can Generate? |
|-----------|------------|-------------|------------|----------|---------------|
| WTA-1000 Consecutive Wins | ⚠️ Need import | ✅ | N/A | N/A | ✅ After import |
| 40+ Tier I Wins | ⚠️ Need import | ⚠️ Need DOB | N/A | N/A | ✅ After enrichment |
| Bejlek Ranking Win | ✅ | ✅ | N/A | ⚠️ Need join | ⚠️ Complex query |
| WTA-500 Wins 2025+ | ⚠️ Need import | ✅ | N/A | N/A | ✅ After import |
| AO 2026 Aces | ⚠️ Need import | ✅ | ✅ | N/A | ✅ After import |
| AO 2026 Winners | ⚠️ Need import | ✅ | ❌ NOT TRACKED | N/A | ❌ **Impossible** |

---

## Action Plan: Data Import & Enrichment

### Step 1: Import Missing Match Data
```bash
# Import WTA matches (2009-2026 for WTA-1000 streaks)
python import_sackmann.py --tour wta --start 2009 --end 2026

# Import WTA matches (1990-2008 for Tier I history)
python import_sackmann.py --tour wta --start 1990 --end 2008

# Import ATP matches (2026 for AO 2026)
python import_sackmann.py --tour atp --start 2026 --end 2026
```

### Step 2: Import Rankings Data
```bash
# Import ATP/WTA rankings (for ranking-at-match-time queries)
python import_rankings.py
```

### Step 3: Enrich Player Birth Dates
```bash
# Update birth dates for specific players via Tennis Abstract
python tennis_abstract_scraper.py --player "Vera Zvonareva" --gender F
python tennis_abstract_scraper.py --player "Kimiko Date" --gender F
python tennis_abstract_scraper.py --player "Serena Williams" --gender F
python tennis_abstract_scraper.py --player "Venus Williams" --gender F

# Or batch update via UTR (requires .env credentials)
python update_player_ages.py --limit 500
```

### Step 4: Verify Player Existence
```sql
-- Check if key players exist in database
SELECT player_id, name, birth_date FROM players 
WHERE name IN ('Karolina Muchova', 'Iga Swiatek', 'Serena Williams', 
               'Victoria Azarenka', 'Maria Sharapova', 'Vera Zvonareva',
               'Kimiko Date', 'Venus Williams', 'Elena Rybakina', 
               'Ekaterina Alexandrova', 'Sara Bejlek', 'Jelena Ostapenko',
               'Carlos Alcaraz');
```

---

## External Data Sources Reference

| Source | URL | Data Available |
|--------|-----|----------------|
| Jeff Sackmann ATP | github.com/JeffSackmann/tennis_atp | Matches, rankings, player profiles |
| Jeff Sackmann WTA | github.com/JeffSackmann/tennis_wta | Matches, rankings, player profiles |
| Tennis Abstract | tennisabstract.com | Player profiles, Elo, birth dates |
| UTR API | app.utrsports.net/api | Player profiles, birth dates, UTR ratings |
| ATP Tour API | atptour.com/en/-/ajax/Ranking/GetRankings | Current rankings |
| WTA Tennis | wtatennis.com/rankings/singles | Current rankings |

---

## Conclusion

### Can Be Generated After Data Import:
1. ✅ WTA-1000 Consecutive Opening Wins
2. ✅ 40+ Tier I/WTA-1000 Wins (after birth date enrichment)
3. ✅ WTA-500 Wins Since 2025
4. ✅ AO 2026 Aces (Women)

### Can Be Generated With Complex Queries:
5. ⚠️ Sara Bejlek Ranking Win (requires ranking-to-match-date join)

### Cannot Be Generated:
6. ❌ AO 2026 Winners (Men) - "Winners" stat not tracked in any available data source

