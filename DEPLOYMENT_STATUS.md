# Punter Bot OCI Deployment Status

*Last updated: 2026-02-19 (end of night session)*

## What's Working

- **Flask app** – Runs on port 5001, DB initialized, scheduler with 5 jobs
- **Health check** – Running under PM2
- **Node 20** – Bridge uses nvm's Node 20 via `run-with-node20.sh`
- **Chrome/Chromium** – System Chromium installed; all library dependencies resolved
- **Swap** – 1 GB swap configured on OCI VM
- **Puppeteer timeout patched** – Changed from 30s to 180s directly in node_modules (works!)
- **Bridge launches Chrome** – QR code generated and saved to `bridge/qr.png`
- **QR viewable** – Via SSH tunnel at http://localhost:3000/qr or `scp` download
- **Retry logic** – Bridge retries on timeout/context errors (up to 5 times)

## Current State

The bridge **starts successfully** and shows a QR code. Chrome launches (the 180s timeout patch works). However, WhatsApp rejected the QR scan with "Can't link new devices at this time. Try again later." This is a WhatsApp rate limit — too many QR codes were generated during the crash loop earlier. This should resolve itself after waiting several hours.

**Flask and health check are currently stopped** (to free RAM). Restart once bridge is linked.

## Remaining Blockers

### 1. WhatsApp QR Rate Limit

WhatsApp says "Can't link new devices at this time." Wait several hours (or until tomorrow) and try again.

### 2. Git Auth on Server

`git pull` fails — GitHub no longer accepts password auth. Need SSH key or Personal Access Token.

### 3. Puppeteer Timeout Patch is Fragile

The timeout patch is in `node_modules` and will be overwritten by `npm install`. Need a postinstall script or permanent fix.

---

## Plan for Tomorrow

### Step 1: Scan the QR Code (~5 min)

The rate limit should have cleared overnight.

```bash
# SSH into the server
ssh -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96

# Restart the bridge to get a fresh QR
pm2 restart punter-bridge

# In a SECOND terminal on your Mac, open SSH tunnel
ssh -L 3000:localhost:3000 -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96
```

Then open **http://localhost:3000/qr** in your browser. Scan with the punter bot phone (WhatsApp → Linked Devices → Link a Device).

### Step 2: Verify Connection

Watch logs for `"WhatsApp client is ready!"`:
```bash
pm2 logs punter-bridge
```

### Step 3: Restart Flask & Health Check

```bash
pm2 start punter-flask punter-health-check
pm2 status
```

### Step 4: Test the Bot

Send `!help` in the WhatsApp group.

### Step 5: Fix Git Auth on Server

```bash
# Option A – SSH (recommended)
cd ~/punter-bot
git remote set-url origin git@github.com:9tkdxzjnqy-hue/punter-bot.git
# Generate SSH key on server if needed: ssh-keygen -t ed25519
# Add public key to GitHub: Settings → SSH keys

# Option B – Personal Access Token
# GitHub → Settings → Developer settings → Personal access tokens
# Use token as password when git pull prompts
```

### Step 6: Make Timeout Patch Permanent

Add a postinstall script in `bridge/package.json`:
```json
"scripts": {
  "start": "node index.js",
  "postinstall": "sed -i 's/timeout = 30000/timeout = 180000/' node_modules/puppeteer-core/lib/cjs/puppeteer/node/BrowserLauncher.js"
}
```

---

## Key Paths & Commands

| Item | Path/Command |
|------|--------------|
| Project on OCI | `~/punter-bot` |
| SSH to server | `ssh -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96` |
| SSH tunnel for QR | `ssh -L 3000:localhost:3000 -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96` |
| PM2 config | `ecosystem.config.js` |
| Bridge | `bridge/index.js` |
| PM2 restart bridge | `pm2 restart punter-bridge` |
| PM2 logs | `pm2 logs punter-bridge` |
| PM2 status | `pm2 status` |
| View QR (tunnel) | http://localhost:3000/qr |
| Download QR | `scp -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96:~/punter-bot/bridge/qr.png /tmp/qr.png && open /tmp/qr.png` |

---

## Session Notes

- OCI instance: Ubuntu 22.04, VM.Standard.E2.1.Micro (1 GB RAM)
- Region: UK South (London)
- Bridge uses system Chromium
- Puppeteer timeout patched in node_modules (line ~76 of BrowserLauncher.js: 30000 → 180000)
