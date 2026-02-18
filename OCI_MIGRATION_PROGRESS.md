# Oracle Cloud Migration — Progress

**Last updated:** 2026-02-17

---

## Current status

- [x] Oracle Cloud account created (Always Free, UK South London)
- [x] Instance created and **Running**
  - Image: Canonical Ubuntu 22.04 Minimal
  - Shape: VM.Standard.E2.1.Micro (AMD, 1 OCPU, 1GB RAM)
  - VCN and public subnet created
- [x] SSH key generated and saved
  - Private key: `~/Documents/Oracle/punter-bot-key.key` (or similar — check your Downloads/Oracle folder)
  - Public key: saved during instance creation

---

## Next steps (when you resume)

### 1. Add SSH access (port 22)

1. Oracle Cloud Console → **Networking** → **Virtual Cloud Networks**
2. Click your VCN
3. **Security Lists** → default security list
4. **Add Ingress Rules**
5. Set:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination port range: `22`
6. **Add Ingress Rules**

### 2. Get the public IP

1. **Compute** → **Instances**
2. Click your instance
3. Copy the **Public IP address**

### 3. Connect via SSH

```bash
chmod 600 ~/Documents/Oracle/punter-bot-key.key
ssh -i ~/Documents/Oracle/punter-bot-key.key ubuntu@<PUBLIC_IP>
```

(Use your actual key filename if different — e.g. `ssh-key-2025-02-17.key`)

### 4. Once logged in — install and deploy the bot

We'll install Node.js, Python, Chromium, copy the project, set up the venv, and run with PM2.

---

## Notes

- Instance will keep running (and consuming free-tier resources) until you stop it
- To stop the instance and avoid any charges: Compute → Instances → your instance → **Stop**
- To start again: **Start**
- The public IP may change when you stop/start — you'll need to check the new IP after restarting
