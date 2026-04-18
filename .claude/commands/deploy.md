Deploy the latest changes to the production server.

## Steps

1. Push local commits to origin:
```bash
git push
```

2. Pull and restart all PM2 processes on the server:
```bash
ssh -i ~/Documents/Oracle/ssh-key-2026-02-18.key ubuntu@193.123.179.96 "cd ~/punter-bot && git pull && pm2 restart all --update-env"
```

Run these two commands in sequence and report the output. If either fails, stop and report the error.
