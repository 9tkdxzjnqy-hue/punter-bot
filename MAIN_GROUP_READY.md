# Main Group — Ready Checklist

Pre-launch verification against requirements and deployment plan.

---

## ✅ Implemented & Ready

| Item | Status | Notes |
|------|--------|-------|
| Pick collection (single + cumulative) | ✅ | Fractional/decimal odds, bare team names, replacement |
| Result recording (Player ✅/❌) | ✅ | Admin-only, word-boundary matching (Aidan ≠ DA) |
| Rotation management | ✅ | ROTATION_ORDER, penalty queue |
| Penalty tracking (3/5/7/10 loss) | ✅ | Suggest + confirm flow |
| !override | ✅ | Admin only |
| !resetweek | ✅ | Resets current or last completed week |
| !resetseason | ✅ | Fresh start, next week = Week 1 |
| Week summary on final result | ✅ | Results + leaderboard + next placer (no Monday recap) |
| No-data messages | ✅ | Courteous Butler-style |
| Intro on group add | ✅ | group_join → intro message |
| Restart scripts | ✅ | start.sh, restart.sh, auto-cleanup Chrome |
| TEST_MODE | ✅ | Set false for production |

---

## ⚠️ Before Adding to Main Group

### 1. .env Configuration
- [ ] `TEST_MODE=false`
- [ ] `GROUP_CHAT_ID` = main group ID **or** `GROUP_CHAT_IDS` = main group ID (comma-separated if multiple)
- [ ] `ADMIN_PHONES` or `ADMIN_PHONE` = Ed's WhatsApp ID (format: `353XXXXXXXXX@c.us`)
- [ ] `SUPERADMIN_PHONE` = your WhatsApp ID (for !myphone, !status)
- [ ] `ROTATION_ORDER` = e.g. `Kev,Nialler,Nug,Pawn,DA,Ed` (matches the lads)
- [ ] `API_FOOTBALL_KEY` = API-Football key ([sign up](https://www.api-football.com/), free: 100 req/day)
- [ ] `ODDS_API_KEY` = The Odds API key ([sign up](https://the-odds-api.com/), free: 500 req/month)

### 2. Data Reset
- [ ] Run `!resetseason` in the test group (or after switching to main) so next weekend = Week 1
- [ ] Or: delete `data/punter_bot.db` and restart for full reset (players will re-seed)

### 3. Group ID
If moving from test group to main:
- Update `GROUP_CHAT_ID` or `GROUP_CHAT_IDS` with the **main** group ID
- Get it from bridge logs when you first message the main group, or use !myphone in a group to see IDs in logs

### 4. Bridge Session
- [ ] Bridge already authenticated (`.wwebjs_auth` exists) — no QR needed
- [ ] Or: be ready to scan QR when bridge starts (if new machine/session)

### 5. First Week
- Scheduler creates Week 1 on **Wednesday 7PM** (Europe/Dublin)
- Or: trigger manually by ensuring no open week exists and waiting for Wed 7PM

---

## Launch Steps

1. **Update .env** with main group ID and admin phones
2. **Run `!resetseason`** (in test group first, or after adding to main)
3. **Restart** Flask and bridge: `./scripts/restart.sh` then `./scripts/start.sh`
4. **Add bot** to main group → intro message should send automatically
5. **Test** `!help` and `!picks` (expect courteous "no data" reply)
6. **Wednesday 7PM** — scheduler creates Week 1
7. **Thursday 7PM** — first reminder goes out

---

## Requirements Coverage

| Requirement | Implementation |
|-------------|----------------|
| Pick collection Thu–Fri | ✅ Scheduler reminders, cumulative format |
| Result entry (Ed posts) | ✅ Player ✅/❌, admin-only |
| Rotation + penalties | ✅ ROTATION_ORDER, streak penalties |
| Override capability | ✅ !override, !resetweek, !resetseason |
| Butler personality | ✅ Formal addressing, courteous messages |
| Week summary | ✅ On final result (no separate Monday recap) |

---

## Implemented but Not Yet Deployed (Phase 2)

- API-Football fixture caching + pick enrichment (sport, competition, event)
- Three-tier pick matching (alias → fuzzy → LLM)
- Auto-resulting from completed fixtures (win, BTTS, over/under, HT/FT)
- The Odds API market price lookup on pick submission
- Group isolation (test/main groups share DB safely)

## Not Yet Implemented (Phase 3+)

- Bet slip image reading (Groq Vision → odds/stake/return)
- Match start validation (warn on picks for kicked-off matches)
- DM reminders to missing players
- Historical analytics / Punter Wrapped
