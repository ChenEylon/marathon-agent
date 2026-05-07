const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const express = require('express');
const path = require('path');
const pino = require('pino');

const app = express();
app.use(express.json());

const AUTH_FOLDER = path.join(__dirname, 'baileys_auth');

let sock = null;
let isReady = false;
let currentQR = null;

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_FOLDER);
    const { version } = await fetchLatestBaileysVersion();

    sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: true,
        browser: ['Marathon Agent', 'Chrome', '1.0'],
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
        if (qr) {
            currentQR = qr;
            console.log('\n📱 Scan this QR code with WhatsApp on your phone:');
            console.log(`Or open in browser: http://YOUR_SERVER_IP:3000/qr\n`);
        }
        if (connection === 'open') {
            isReady = true;
            currentQR = null;
            console.log('✅ WhatsApp client is ready');
        }
        if (connection === 'close') {
            isReady = false;
            const code = lastDisconnect?.error?.output?.statusCode;
            console.log(`❌ WhatsApp disconnected (${code})`);
            if (code !== DisconnectReason.loggedOut) {
                console.log('Reconnecting...');
                connectToWhatsApp();
            }
        }
    });

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;
        for (const msg of messages) {
            if (!msg.message) continue;
            const body = msg.message?.conversation
                || msg.message?.extendedTextMessage?.text
                || '';
            if (!body) continue;
            try {
                await fetch('http://localhost:8000/incoming', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ from: msg.key.remoteJid, body })
                });
            } catch (e) {
                console.error('Failed to forward message to agent:', e.message);
            }
        }
    });
}

// POST /send  { to: "972501234567", message: "..." }
app.post('/send', async (req, res) => {
    if (!isReady || !sock) return res.status(503).json({ error: 'WhatsApp not connected' });
    const { to, message } = req.body;
    if (!to || !message) return res.status(400).json({ error: 'Missing to or message' });
    try {
        const jid = to.includes('@') ? to : `${to}@s.whatsapp.net`;
        await sock.sendMessage(jid, { text: message });
        res.json({ ok: true });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.get('/health', (_, res) => res.json({ ready: isReady }));

app.get('/qr', async (req, res) => {
    if (isReady) return res.send('<h2>✅ WhatsApp already connected!</h2>');
    if (!currentQR) return res.send('<h2>⏳ QR not ready yet — refresh in a few seconds</h2>');
    const img = await QRCode.toDataURL(currentQR);
    res.send(`<html><body style="display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;font-family:sans-serif;background:#f0f2f5"><h2>Scan with WhatsApp</h2><img src="${img}" style="width:300px;height:300px;border-radius:12px"><p style="color:#666">Refresh page if expired</p></body></html>`);
});

const PORT = process.env.BRIDGE_PORT || 3000;
app.listen(PORT, () => console.log(`WhatsApp bridge listening on port ${PORT}`));

connectToWhatsApp();
