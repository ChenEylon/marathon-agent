const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--single-process',
        ]
    }
});

let isReady = false;

client.on('qr', (qr) => {
    console.log('\n📱 Scan this QR code with WhatsApp on your phone:\n');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    isReady = true;
    console.log('✅ WhatsApp client is ready');
});

client.on('disconnected', () => {
    isReady = false;
    console.log('❌ WhatsApp client disconnected');
});

// Incoming messages → forward to Python agent
client.on('message', async (msg) => {
    if (msg.fromMe) return;
    try {
        await fetch('http://localhost:8000/incoming', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from: msg.from, body: msg.body })
        });
    } catch (e) {
        console.error('Failed to forward message to agent:', e.message);
    }
});

// POST /send  { to: "972501234567", message: "..." }
app.post('/send', async (req, res) => {
    if (!isReady) return res.status(503).json({ error: 'WhatsApp not connected' });
    const { to, message } = req.body;
    if (!to || !message) return res.status(400).json({ error: 'Missing to or message' });
    try {
        const chatId = to.includes('@c.us') ? to : `${to}@c.us`;
        await client.sendMessage(chatId, message);
        res.json({ ok: true });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.get('/health', (_, res) => res.json({ ready: isReady }));

const PORT = process.env.BRIDGE_PORT || 3000;
app.listen(PORT, () => console.log(`WhatsApp bridge listening on port ${PORT}`));

client.initialize();
