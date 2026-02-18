# Punter Bot — Deployment Plan

Plan for deploying to the main group, GitHub updates, and uptime.

---

## 1. Introduction Message (When Bot Is Added)

### Behaviour
When the bot is added to a group, it sends a one-time introduction message.

### Implementation
- **Bridge:** Listen for `group_join` in whatsapp-web.js. Check if `client.info.wid._serialized` is in `notification.recipientIds` — if so, the bot was added. Call `notification.reply(introMessage)`.
- **Alternative:** On first message from a new group ID, send intro and mark group as "introduced" (e.g. in a small JSON file or DB).
- **Intro content:**
  - Who the bot is (The Betting Butler)
  - What it does (picks, results, rotation, penalties, stats)
  - How to get help (`!help`)
  - Note that features will show "no data" until the first week is set up

### Intro Message Draft
```
Good evening, gentlemen. I am The Betting Butler, at your service.

I shall assist with the weekly accumulator: collecting picks, recording results, managing the rotation, and tracking penalties. Use !help for a list of commands.

Please note — I have no data yet. Once the first week's picks and results are in, my full capabilities will be available. Until then, some commands may report that nothing is recorded.
```

---

## 2. "No Data Yet" Messaging

### Current Behaviour
- `!picks` → "No active week."
- `!leaderboard` → "No results have been recorded yet."
- `!rotation` → "No players found in the rotation."
- `!stats [player]` → Various "no data" paths

### Improvements
Make early-use messages more courteous (Butler style):

| Command      | Current                         | Proposed                                                                 |
|-------------|----------------------------------|---------------------------------------------------------------------------|
| !picks      | No active week.                 | I have no active week at present. The season will commence when picks are collected, Thursday through Friday. |
| !leaderboard| No results have been recorded yet. | I beg your pardon — no results have been recorded as yet. The leaderboard will appear once the first week's results are in. |
| !rotation   | No players found in the rotation. | The rotation has not yet been established. Once the first week is complete, I shall display who is next to place. |
| !stats      | (varies)                        | Ensure a courteous "no data" message for new deployments                  |

---

## 3. Data Reset for Fresh Start (Week 1)

**Yes — if you want next weekend to be Week 1, you need to clear the test data.**

The bot assigns week numbers sequentially within the season (calendar year). If you have Weeks 1–3 from testing, the next created week would be Week 4.

### Option A: `!resetseason` (Admin only)
Add a command that clears all weeks and related data, keeps players. Next week created will be Week 1.

### Option B: Manual reset
Delete the database file and restart:
```bash
rm data/punter_bot.db
# Restart Flask — init_db will recreate tables and seed players
```
This gives a completely fresh start: Week 1, seeded players, no history.

### Option C: SQL reset (keep players)
```sql
DELETE FROM vault;
DELETE FROM penalties;
DELETE FROM results;
DELETE FROM picks;
DELETE FROM bet_slips;
DELETE FROM rotation_queue;
DELETE FROM weeks;
```
Players are preserved. Next week = Week 1.

---

## 4. GitHub Updates

### Pre-deploy Checklist
- [ ] Ensure `.env.example` has all required vars (GROUP_CHAT_ID, ROTATION_ORDER, ADMIN_PHONES, etc.)
- [ ] Add `.env.example` note: set `TEST_MODE=false` for production
- [ ] Update README with:
  - Production vs test mode
  - Deployment section (link to this plan or DEPLOYMENT.md)
  - Note that `.wwebjs_auth` must persist across restarts
- [ ] Add `DEPLOYMENT_PLAN.md` (this file) or a shorter `DEPLOYMENT.md`
- [ ] Commit and push all changes
- [ ] Tag a release (e.g. `v0.1.0` or `v1.0.0-main-group`) for the main-group launch

### Suggested README Additions
```markdown
## Production Deployment
- Set `TEST_MODE=false` in .env
- Configure `GROUP_CHAT_ID` or `GROUP_CHAT_IDS` for your group(s)
- Ensure `ADMIN_PHONES` and `SUPERADMIN_PHONE` are set
- See DEPLOYMENT_PLAN.md for uptime and monitoring options
```

---

## 5. Uptime & Reliability

### Current State
- Stable over the weekend with the new scripts
- Survives laptop sleep (Flask + bridge recover when machine wakes)
- Auto-cleanup of stale Chrome on bridge restart
- Flask retries (3x) when bridge is reconnecting

### Options (Increasing Robustness)

#### A. Keep Running Locally (Current)
- **Pros:** Simple, no extra cost, already stable
- **Cons:** Depends on laptop being on; brief gaps during sleep/wake
- **Improvements:** Run on a machine that stays on (e.g. Raspberry Pi, old laptop, home server)

#### B. Process Manager (pm2) — **IMPLEMENTED**
- **What:** PM2 manages both Flask and the bridge; auto-restart on crash and on machine reboot
- **Setup:** `pm2 start ecosystem.config.js`; `pm2 save`; `pm2 startup`
- **Pros:** Auto-restart, logs, easy `pm2 restart all`, survives reboot
- **Status:** In use on local machine; same setup on Oracle Cloud (Phase 0.5)

#### C. systemd (Linux Server / Raspberry Pi)
- **What:** Two systemd units (flask.service, bridge.service)
- **Pros:** Starts on boot, restarts on failure, standard Linux approach
- **Example:**
  ```
  [Unit]
  Description=Punter Bot Flask
  After=network.target

  [Service]
  Type=simple
  User=punter
  WorkingDirectory=/home/punter/punter-bot
  ExecStart=/home/punter/punter-bot/venv/bin/python -m src.app
  Restart=always
  RestartSec=10
  ```

#### D. Cloud Deployment (Oracle Cloud Always Free) — **Phase 0.5**
- **What:** Run on Oracle Cloud Always Free — UK South (London) region; ARM Ampere 1 OCPU / 1GB RAM
- **Pros:** $0 permanently, independent of laptop, always on
- **Considerations:**
  - WhatsApp session: `.wwebjs_auth` must be copied or generated on the server (QR scan once)
  - Chrome/Puppeteer: headless works; may need `--no-sandbox` etc. (already in place)
  - Convert to Pay-As-You-Go after signup to prevent suspension (Always Free stays free)
  - Fallback: Amsterdam region if London ARM unavailable; AMD if ARM unavailable
- **See:** requirements_document.md §4.3, §9 Phase 0.5

#### E. Docker (Optional)
- **What:** Containerise Flask + bridge for consistent deployment
- **Pros:** Same setup on any host, easier to move between machines
- **Cons:** More setup; WhatsApp session persistence needs a volume

### Phased Approach
- **Phase 1:** Run locally (current setup). PM2 manages both processes; auto-restart on crash and reboot.
- **Phase 0.5:** Oracle Cloud Always Free for 24/7 uptime. Migrate bot to OCI; PM2 same setup on cloud. Health check + alerting (Telegram on OCI).

---

## 6. Implementation Order

| Step | Task                                      | Effort |
|------|-------------------------------------------|--------|
| 1    | Add intro message (group_join or first message) | Small  |
| 2    | Soften "no data" messages for new deployments   | Small  |
| 3    | Update README and .env.example            | Small  |
| 4    | Commit, push, tag release                 | Small  |
| 5    | Add to main group and verify intro        | Small  |
| 6    | (Optional) Set up pm2 or systemd          | Medium |
| 7    | (Optional) Move to Pi/cloud                | Medium |

---

## 7. Main Group Checklist (Day of Launch)

- [ ] Run `!resetseason` (or manual DB reset) so next weekend = Week 1
- [ ] `TEST_MODE=false` in .env
- [ ] `GROUP_CHAT_ID` or `GROUP_CHAT_IDS` set to main group
- [ ] `ADMIN_PHONES` / `SUPERADMIN_PHONE` correct
- [ ] `ROTATION_ORDER` matches the lads
- [ ] Database has players (or will be seeded)
- [ ] Bridge session valid (or QR ready for first connect)
- [ ] Add bot to group → intro message sent
- [ ] Test `!help`, `!picks` (expect "no data" style reply)
- [ ] Confirm scheduler will create first week (Wed 7PM or manual)
