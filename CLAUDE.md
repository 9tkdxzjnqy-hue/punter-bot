# Punter Bot — Claude Code Context

## What this is
A WhatsApp bot that manages a weekly accumulator betting pool for a group
of seven friends. Runs live every week. Mistakes are visible to everyone
in the group chat. Stability is the top priority.

## Three files, three jobs — do not overlap them
- `README.md` — operational: setup, running, deploying. Not for rules or architecture.
- `RULES.md` — domain source of truth: game rules, pick formats, penalties, rotation.
  Read this before implementing any game logic. Do not contradict it.
- `CLAUDE.md` (this file) — AI context: architecture map, fragile areas, constraints,
  build sequence. What Claude Code needs to work safely. Not for game rules or ops.

## Read this before touching anything
- `RULES.md` — if you are unsure what the bot should do in a given situation, read
  RULES.md first. Do not implement game logic that contradicts it.
- `src/schema.sql` — the database schema. Never modify the schema without adding a
  corresponding migration in `src/db.py`.

## Architecture
```
bridge/index.js             ← Node.js WhatsApp bridge. Do not modify unless
                              explicitly asked. Stable. Not a regression source.

src/app.py                  ← Webhook entry point. Routes messages to handlers.
                              Most dangerous file to modify — changes here affect
                              all message types. Run the full test suite before
                              and after any change here.

src/parsers/
  message_parser.py         ← Classifies incoming messages as pick / command /
                              result / general. _looks_like_pick and _parse_pick
                              are the primary regression risk. Test thoroughly
                              after any change.

src/services/               ← One service per domain concept. Business logic
                              lives here, not in app.py.
  player_service.py         ← Player lookup and alias resolution
  pick_service.py           ← Pick submission and retrieval
  rotation_service.py       ← Placer rotation and penalty queue
  result_service.py         ← Result recording and streak tracking
  penalty_service.py        ← Penalty suggestion and confirmation
  week_service.py           ← Week lifecycle and submission window
  bet_slip_service.py       ← Bet slip image validation (LLM-assisted)
  auto_result_service.py    ← Automatic result processing
  match_monitor_service.py  ← Live match events
  fixture_service.py        ← External fixture data
  scheduler.py              ← APScheduler jobs

src/butler.py               ← Message formatting. LLM personality (secondary
                              feature — do not modify unless explicitly asked).
src/llm_client.py           ← Groq API wrapper. Secondary infrastructure.
```

## Known fragile areas — read before touching

**1. Bet slip confirmation — three paths, different guards (`app.py`)**
There are three ways the bot confirms a bet is placed. Do not conflate them:

- **Image auto-detection** (`_handle_placer_bet_confirmation`, `from_image=True`):
  Only fires when the sender IS the designated next placer (`sender["id"] == next_placer["id"]`).
  LLM validates the image — all-null response is rejected before `advance_rotation`.
  Credited player is always `next_placer`, not necessarily the sender.

- **Text confirmation** (`_handle_placer_bet_confirmation`, `from_image=False`):
  Fires for any known player who sends "placed"/"sorted"/etc. No LLM gate.
  Credits `next_placer`, not the sender. Any player can confirm on behalf of placer.

- **`!slip` command** (`_cmd_slip`): Explicit delegation. Any known player replies to
  a bet slip image with `!slip`. Bypasses LLM validation — human confirmation gates
  the flow. Still runs LLM best-effort for confirmed odds.

Do not change any of these paths without reading all three and understanding
how they interact. The placer-only restriction on the image path is intentional —
see commit `f97785f`.

**2. Player alias resolution (`player_service.py` + `message_parser.py`)**
"Don", "DA", and "Declan" must all resolve to the same player.
`PLAYER_NICKNAMES` in `message_parser.py` and the alias lookup in `player_service.py`
must stay in sync. If you update one, update both. Failure here produces visible
errors when results are recorded ("I don't recognise that player: don").

**3. Rotation edge cases (`rotation_service.py`)**
Delegation, cashouts, and sole-loser penalties interact with the rotation queue in
non-obvious ways. Read `rotation_service.py` in full before modifying it. The rules
governing rotation are defined in `RULES.md`. Do not implement rotation logic from
memory — read the rules.

**4. Submission window enforcement (`week_service.py` + `app.py`)**
The window opens dynamically when the previous week is fully resulted (fallback:
Wednesday 7pm). It closes Friday 10pm strictly. The bot replies to out-of-window
picks rather than silently dropping them — this means false positives (general chat
classified as picks) produce visible responses in the group. Tighten classification
before changing window behaviour.

**5. Cumulative pick parsing (`message_parser.py` → `parse_cumulative_picks`)**
Multi-line messages with emoji prefixes are parsed as a batch. If the emoji map is
stale or a player's emoji is wrong, the batch fails silently. Test cumulative parsing
whenever player config changes.

## Constraints
- Live system. Every change must pass the full test suite before deploy.
- Do not add features unless explicitly asked. Stability first.
- Do not modify `bridge/index.js` unless explicitly asked.
- Do not modify the database schema without a corresponding migration.
- `butler.py` and `llm_client.py` are secondary infrastructure (LLM personality).
  Do not touch unless the task is specifically about personality or formatting.

## Test suite
Run with: `python3 -m pytest tests/ -v`
Run the full suite before and after any change. If adding a new behaviour, add a test.
Read `skills/test-patterns.md` before writing tests — it documents fixtures, setup
patterns, webhook testing, and LLM mocking conventions.

## Deployment
Runs on Oracle Cloud (Ubuntu 22.04) managed by PM2. See `README.md` for commands.
Use the shadow group (`SHADOW_GROUP_ID` in `.env`) to test message classification
changes before they reach the main group.

## Current build focus
Improving structural reliability so Claude Code can make changes without introducing
regressions. See `RULES.md` for domain context. Do not add new features until the
known fragile areas above are stable and tested.
