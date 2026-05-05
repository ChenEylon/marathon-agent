# Marathon Agent

AI-powered marathon training agent. Sends daily workout instructions via WhatsApp, adapts based on Strava activity, Garmin HRV, and training load.

## Setup

### 1. Fill in config.yaml
```yaml
user:
  phone: "972501234567"     # Your number with country code, no +
  marathon_date: "2027-01-10"
```

### 2. Install Python dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install Node.js dependencies (WhatsApp bridge)
```bash
cd whatsapp-bridge
npm install
```

### 4. Start the WhatsApp bridge
```bash
cd whatsapp-bridge
node index.js
# Scan the QR code with your phone
```

### 5. Start the agent (new terminal)
```bash
source venv/bin/activate
python agent/main.py
```

## Project structure
```
marathon-agent/
├── agent/
│   ├── main.py              # Entry point (FastAPI + scheduler)
│   ├── scheduler.py         # APScheduler setup
│   ├── config.py            # Config loader
│   ├── whatsapp_client.py   # HTTP client → Node.js bridge
│   └── handlers/
│       └── morning.py       # 7:30 AM daily message
├── whatsapp-bridge/
│   └── index.js             # whatsapp-web.js + Express bridge
├── config.yaml              # Your preferences (edit this)
└── requirements.txt
```

## Build phases
- [x] Phase 1 — WhatsApp bridge + 7:30 AM scheduler
- [ ] Phase 2 — Strava webhook integration
- [ ] Phase 3 — Garmin HRV integration
- [ ] Phase 4 — Google Calendar deadlines
- [ ] Phase 5 — Training plan database + adaptation engine
- [ ] Phase 6 — Cloud deployment (Oracle Free Tier)
