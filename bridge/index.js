require("dotenv").config({ path: require("path").resolve(__dirname, "../.env") });
const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const express = require("express");
const http = require("http");

// Config
const FLASK_URL = process.env.FLASK_URL || "http://127.0.0.1:5001";
const BRIDGE_PORT = parseInt(process.env.BRIDGE_PORT || "3000", 10);
const GROUP_CHAT_ID = process.env.GROUP_CHAT_ID || "";

// WhatsApp client with persistent local auth
const client = new Client({
  authStrategy: new LocalAuth(),
  puppeteer: {
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
});

// Display QR code for authentication
client.on("qr", (qr) => {
  console.log("Scan this QR code to authenticate:");
  qrcode.generate(qr, { small: true });
});

client.on("ready", () => {
  console.log("WhatsApp client is ready!");
  console.log(`Monitoring group: ${GROUP_CHAT_ID}`);
});

client.on("authenticated", () => {
  console.log("Authenticated successfully.");
});

client.on("auth_failure", (msg) => {
  console.error("Authentication failed:", msg);
});

client.on("disconnected", (reason) => {
  console.log("Client disconnected:", reason);
  // Attempt reconnect after 10 seconds
  setTimeout(() => {
    console.log("Attempting reconnection...");
    client.initialize();
  }, 10000);
});

// Helper to POST JSON to Flask using Node built-in http
function postToFlask(path, data) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, FLASK_URL);
    const body = JSON.stringify(data);

    const req = http.request(
      {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
        },
        timeout: 10000,
      },
      (res) => {
        let responseData = "";
        res.on("data", (chunk) => (responseData += chunk));
        res.on("end", () => {
          try {
            resolve(JSON.parse(responseData));
          } catch {
            resolve(null);
          }
        });
      }
    );

    req.on("error", (err) => {
      console.error(`Flask connection error: ${err.message}`);
      resolve(null);
    });

    req.on("timeout", () => {
      req.destroy();
      console.error("Flask request timed out");
      resolve(null);
    });

    req.write(body);
    req.end();
  });
}

// Track messages sent by the bot to avoid processing them as input
const botSentMessages = new Set();

// Forward incoming group messages to Flask backend
// Use message_create to capture all messages including your own
client.on("message_create", async (message) => {
  try {
    // Skip messages sent by the bot via /send endpoint
    if (botSentMessages.has(message.body)) {
      botSentMessages.delete(message.body);
      return;
    }

    const chat = await message.getChat();

    // Only process group messages
    if (!chat.isGroup) return;

    const groupId = chat.id._serialized;

    // Only process messages from our target group
    if (groupId !== GROUP_CHAT_ID) return;

    let sender = "Unknown";
    let senderPhone = "";
    try {
      const contact = await message.getContact();
      sender = contact.pushname || contact.name || "Unknown";
      senderPhone = contact.id ? contact.id._serialized : "";
    } catch {
      // For own messages, fall back to client info
      sender = (client.info && client.info.pushname) || message.author || "Unknown";
      senderPhone = message.author || (client.info ? client.info.wid._serialized : "");
    }

    const payload = {
      sender: sender,
      sender_phone: senderPhone,
      body: message.body || "",
      group_id: groupId,
      timestamp: message.timestamp,
      has_media: message.hasMedia,
      message_id: message.id ? message.id._serialized : "",
    };

    console.log(`[${chat.name}] ${sender}: ${(message.body || "").slice(0, 80)}`);

    const result = await postToFlask("/webhook", payload);
    if (result && result.action === "replied") {
      console.log(`Bot replied: ${result.reply.slice(0, 80)}`);
    }
  } catch (err) {
    console.error("Error processing message:", err.message);
  }
});

// Express server for receiving send requests from Flask
const app = express();
app.use(express.json());

app.post("/send", async (req, res) => {
  const { chat_id, message } = req.body;

  if (!chat_id || !message) {
    return res.status(400).json({ error: "chat_id and message required" });
  }

  try {
    botSentMessages.add(message);
    await client.sendMessage(chat_id, message);
    console.log(`Sent message to ${chat_id}: ${message.slice(0, 80)}`);
    res.json({ status: "sent" });
  } catch (err) {
    console.error("Failed to send message:", err.message);
    res.status(500).json({ error: err.message });
  }
});

app.get("/health", (req, res) => {
  const state = client.info ? "connected" : "disconnected";
  res.json({ status: "ok", whatsapp: state });
});

app.get("/group-members", async (req, res) => {
  try {
    const chat = await client.getChatById(GROUP_CHAT_ID);
    const participants = chat.participants || [];
    const members = [];
    for (const p of participants) {
      try {
        const contact = await client.getContactById(p.id._serialized);
        members.push({
          phone: p.id._serialized,
          name: contact.pushname || contact.name || "Unknown",
        });
      } catch {
        members.push({ phone: p.id._serialized, name: "Unknown" });
      }
    }
    res.json({ members });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Start everything
app.listen(BRIDGE_PORT, () => {
  console.log(`Bridge HTTP server listening on port ${BRIDGE_PORT}`);
});

console.log("Initializing WhatsApp client...");
client.initialize();
