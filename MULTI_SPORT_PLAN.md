# Multi-Sport Support — Task Breakdown

## Context

The lads bet on 12+ sports. Non-football picks already parse and store correctly, but get no enrichment. The goal is incremental support: sport detection first, then market prices, then fixtures and auto-resulting — sport by sport.

## API Coverage Summary

| Sport | Fixtures (API-Sports) | Odds (The Odds API) | Auto-Result? |
|-------|----------------------|--------------------|----|
| Football | ✅ 100 req/day | ✅ `soccer_epl` etc. | ✅ Done |
| Rugby | ✅ 100 req/day | ✅ `rugbyunion_six_nations` | Planned |
| NFL | ✅ 100 req/day | ✅ `americanfootball_nfl` | Planned |
| NBA | ✅ 100 req/day | ✅ `basketball_nba` | Planned |
| NHL | ✅ 100 req/day | ✅ `icehockey_nhl` | Planned |
| MMA/UFC | ✅ 100 req/day | ✅ `mma_mixed_martial_arts` | Planned |
| Tennis | ❌ | ✅ Grand Slams | Prices only |
| Golf | ❌ | ✅ Majors | Prices only |
| Boxing | ❌ | ✅ `boxing_boxing` | Prices only |
| Darts | ❌ | ❌ | Manual only |
| GAA | ❌ | ❌ | Manual only |
| Horse Racing | ❌ (paid only, different data model) | ❌ | Manual only |

All API-Sports APIs share the same free tier structure (100 req/day). Each sport uses a separate API key/quota. The Odds API covers all team sports + tennis/golf/boxing within 500 req/month.

---

## Tasks

### Phase 0: Sport Detection (no API work)

**Task 0.1: Add `detect_sport()` to message parser**
- File: `src/parsers/message_parser.py`
- Add keyword-based sport detection function
- Keywords per sport (rugby, NFL, NBA, NHL, MMA, darts, GAA, horse racing, tennis, golf, boxing)
- Default → "football"
- Add tests in `tests/test_message_parser.py`

**Task 0.2: Store detected sport on picks**
- File: `src/services/pick_service.py`
- In `submit_pick()`, if enrichment didn't set `sport`, call `detect_sport()` and store it
- Ensures every pick has a sport value in the database

**Task 0.3: Add non-football team aliases**
- File: `src/db.py` (`seed_team_aliases`)
- Add rugby aliases: munster, leinster, ulster, connacht, ireland, scotland, wales, france, italy, england (rugby context)
- Add NFL/NBA/NHL common abbreviations if the lads use them
- Add `sport` column to `team_aliases` table (optional — avoids rugby "Ireland" clashing with football "Ireland")

**Task 0.4: Expand butler abbreviations**
- File: `src/butler.py` (`PICK_ABBREVIATIONS`)
- Add non-football display abbreviations used by the lads

---

### Phase 1: Generic API-Sports Client

**Task 1.1: Create `src/api/api_sports.py`**
- Generic client that works for any API-Sports product (rugby, NFL, NBA, NHL, MMA)
- Config dict maps sport → base URL + API key config name
- Functions: `get_fixtures(sport, date_str)`, `get_fixture(sport, fixture_id)`
- Same caching pattern as existing `api_football.py`
- Skip silently if API key not configured for a sport

**Task 1.2: Make `_cache_fixtures()` sport-aware**
- File: `src/services/fixture_service.py`
- Accept `sport` parameter instead of hardcoding `"football"`
- All callers pass sport explicitly

**Task 1.3: Make `fetch_daily_fixtures()` multi-sport**
- File: `src/services/fixture_service.py`
- Loop through configured sports (football + any with API keys set)
- Football still uses existing `api_football.py` (don't break what works)
- Other sports use new `api_sports.py`

**Task 1.4: Make `match_pick()` sport-aware**
- File: `src/services/match_service.py`
- Accept `sport` parameter, filter fixtures by sport
- Update LLM prompt: "This is a {sport} pick"
- Pass detected sport from `_try_enrich()` in pick_service.py

**Task 1.5: Add sport keys to The Odds API**
- File: `src/api/odds_api.py`
- Add rugby, NFL, NBA, NHL, MMA, tennis, golf, boxing sport keys
- `get_best_odds_for_selection()` accepts sport parameter

**Task 1.6: Multi-sport scheduler**
- File: `src/services/scheduler.py`
- Daily fixture fetch loops through configured sports
- Each sport fetches only if its API key is set in .env

**Task 1.7: Config entries for new sports**
- File: `src/config.py`
- Add: `API_RUGBY_KEY`, `API_NFL_KEY`, `API_NBA_KEY`, `API_NHL_KEY`, `API_MMA_KEY`
- All default to empty string (disabled)

---

### Phase 2: Auto-Resulting for Team Sports

**Task 2.1: Sport-aware pick evaluation**
- File: `src/services/auto_result_service.py`
- `_evaluate_pick()` checks fixture sport before calling BTTS/HT-FT (football-only bet types)
- Win, handicap, over/under logic works identically across all team sports

**Task 2.2: Sport-specific team name normalization**
- File: `src/services/auto_result_service.py`
- Current `_team_in_text()` strips football suffixes (" fc", " city", " united")
- Add sport-specific suffixes: rugby (" rfc", " rugby"), NFL team name patterns

**Task 2.3: MMA/UFC resulting**
- File: `src/services/auto_result_service.py`
- Individual fights, not team fixtures — fighter A beat fighter B
- Simpler logic: match fighter name to pick text, check winner

---

### Phase 3: Market Prices for Non-Fixture Sports

**Task 3.1: Odds-only enrichment path**
- File: `src/services/pick_service.py`
- For sports without fixture API (tennis, golf, boxing): skip fixture matching
- Query Odds API directly by sport for market price
- Store market_price without api_fixture_id

---

### Phase 4: Manual-Only Sports (No Code Needed)

Darts, GAA, and horse racing are handled by Phase 0 sport detection. Picks store correctly, Ed results manually. No further work unless free APIs appear.

---

## Implementation Sequence

Start with Phase 0 (zero risk). Then pick tasks from Phase 1 incrementally — start with Task 1.5 (Odds API sport keys, trivial) and Task 1.1 (generic client) as the foundation, then wire them up.

## Budget Impact

All within free tiers. See API coverage table above for per-sport quotas.
