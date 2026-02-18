#!/bin/bash
# Run bridge with Node 20 from nvm (required for whatsapp-web.js)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20 2>/dev/null || nvm use default
exec node index.js
