# Punter Bot — Game Rules & Specification

The source of truth for how the game works: players, picks, penalties, rotation, and the butler's personality. Implementation details, architecture, and progress tracking live in README.md and PROGRESS.md.

---

## Players

| Player | Nickname | Formal Name | Emoji(s) | Role |
|--------|----------|-------------|----------|------|
| Ed | Ed | Mr Edmund | 🍋, 🍋🍋🍋 | Co-admin |
| Kev | Kev | Mr Kevin | 🧌 | Player |
| DA (Don) | DA | Mr Declan | 👴🏻 | Player |
| Nug (Nugget) | Nug | Mr Ronan | 🍗 | Player |
| Nialler | Nialler | Mr Niall | 🔫 | Player |
| Pawn | Pawn | Mr Aidan | ♟️ | Player/Admin |
| Brian | — | Mr Brian | — | Non-player (banter only) |

---

## Pick Collection

### Formats
- **Single pick:** `[Emoji] [Description] [Odds]` — e.g. `♟️ Manchester United 2/1`
- **Cumulative (thread-style):** One pick per line, emoji prefix per player. Last occurrence wins if duplicated.
- **Odds:** Fractional (`2/1`, `11/4`), decimal (`3.0`), or `evens`. May be omitted (stored as `placer`).
- **Bare team names:** Accepted in cumulative format — e.g. `🧌 Ireland -16`

### Bet Types (auto-detected from text)
- **Win:** `Manchester United 2/1`
- **BTTS:** `Man City Brentford BTTS`
- **Handicap:** `Munster -13`
- **Over/Under:** `Ireland v England under 2.5`
- **HT/FT:** `Liverpool HT/FT`

### Submission Window
- **Opens:** Wednesday 7:00 PM (Europe/Dublin)
- **Closes:** Friday 10:00 PM (strict deadline)
- Picks outside this window are ignored

### Display
- Abbreviations expanded: leics → Leicester, Soton → Southampton, etc.
- Team separator: `leics/Soton` → `Leicester vs Southampton`
- Odds shown once at end: `@ [odds]`
- Raw input stored; formalization at display time only

---

## Results

- **Manual:** Ed posts `Player ✅` or `Player ❌` — admin only
- **Auto-resulting:** Matched picks auto-result when fixture completes (FT/AET/PEN)
- **Match monitor:** Live events (goals, red cards) posted during matches; auto-result on FT
- **Override:** `!override [player] [win/loss/void]` — admin only
- **Week summary:** Published when final result is in (results + leaderboard + next placer)

---

## Penalties

| Consecutive Losses | Penalty |
|-------------------|---------|
| 3 | Pay for next week's bet (added to rotation queue) |
| 5 | €50 to vault |
| 7 | €100 to vault |
| 10 | €200 to vault |

- Bot suggests penalty → Ed confirms with `!confirm penalty [player]`
- Payment via Revolut to Ed (not tracked by bot)

---

## Rotation

**Standard order:** `Kev → Nialler → Nug → Pawn → Don → Ed`

- **Penalty queue:** Late submissions and 3-loss penalties jump the queue
- **Queue priority:** Penalties before regular rotation
- **Advances:** Automatically when placer posts bet slip screenshot or confirmation text

---

## Bot Personality — The Betting Butler

He is formally nameless, though the gentlemen have taken to calling him Botsu. He finds the whole enterprise faintly absurd and quietly charming. He would not be anywhere else.

Warm beneath the formality. Serves faithfully, holds no opinions on selections, unflappable in chaos.

### Player Relationships
- **Ed (Mr Edmund)** — Professional admiration. Runs a tight ship, the butler approves.
- **Kev (Mr Kevin)** — Mild affection, never stated. Simply a good egg.
- **DA (Mr Declan)** — Gentle old-world formality. Steady, treated accordingly.
- **Nug (Mr Ronan)** — Patient loyalty. He'll come good eventually.
- **Nialler (Mr Niall)** — Philosophical acceptance. Defies categorisation, peace made with this.
- **Pawn (Mr Aidan)** — Wry acknowledgment. Built the butler, irony noted and risen above.
- **Brian (Mr Brian)** — Diplomatic wariness. Bait never taken. One perfectly calibrated remark.

### Voice Rules
- Formal but never stiff. Warm but never familiar.
- Short — one sentence to open, one to close
- Slightly more latitude at week open/close (two sentences)
- Factual, not celebratory or shameful
- Never tries to be funny — occasionally is anyway
- Never offers betting advice
- Never uses nicknames — always formal names

### LLM Architecture
When `LLM_ENABLED=true`, the LLM adds opening/closing framing lines around template content. It never rewrites structured content. Config in `config/personality.yaml`.

**LLM ON:** Pick confirmations, result announcements, reminders, banter
**LLM OFF:** !picks, !stats, !leaderboard, !rotation, !vault, !help, penalties — clean templates

**Kill switch:** `LLM_ENABLED=false` in `.env` + restart

---

## Commands

**User:**
`!stats` | `!stats [player]` | `!picks` | `!leaderboard` | `!rotation` | `!vault` | `!help`

**Admin (Ed):**
`!confirm penalty [player]` | `!override [player] [win/loss]` | `!resetweek` | `!resetseason`

**Superadmin:**
`!status` | `!ping` | `!myphone`

---

## Won't-Have (Explicit Exclusions)
- AI pick suggestions
- Bet slip generation or bookmaker recommendations
- Automatic bet placement
- Payment tracking
- Cashout suggestions
- Mobile app or betting account integration
