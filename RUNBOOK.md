# W3BHub WhatsApp Automation System - Runbook

## How to Run the Application

1. Create .env file with your credentials:
   ```bash
   cp env.example .env
   # Edit .env with your values
   ```

2. Start the system:
   ```bash
   docker-compose up -d
   ```

## Required Environment Variables

- TELEGRAM_BOT_TOKEN - Your Telegram bot token
- TELEGRAM_CHANNEL_ID - Your Telegram channel ID  
- SUPABASE_URL - Your Supabase project URL
- SUPABASE_KEY - Your Supabase service key
- ADMIN_TELEGRAM_ID - Your admin Telegram ID

## Debugging Commands

Check if containers are running:
```bash
docker ps
```

Check WhatsApp worker logs:
```bash
docker logs whatsapp-worker
```

Check n8n logs:
```bash
docker logs n8n
```

Check WhatsApp worker health:
```bash
curl http://localhost:8000/health
```

Check n8n health:
```bash
curl http://localhost:5678/healthz
```

## Support

For assistance with setup or troubleshooting, message WebHub on WhatsApp:
https://wa.me/message/XDA2UCEQCOILO1