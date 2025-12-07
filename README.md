# W3BHub WhatsApp Automation System

Fully automated WhatsApp marketing system with n8n orchestration, WhatsApp Web automation, and Supabase database.

## Features

- ✅ **Zero Manual Setup** - Everything auto-deploys
- ✅ **Auto-Import Workflow** - No manual n8n import needed
- ✅ **Auto-Database Setup** - Tables created automatically
- ✅ **Auto-Health Monitoring** - 24/7 system monitoring
- ✅ **Anti-Flagging** - Warm-up schedules, random delays, safety triggers
- ✅ **Reply Detection** - Automatically detects and logs replies
- ✅ **Telegram Integration** - Upload CSV files via Telegram
- ✅ **Uptime Monitoring** - Automatic uptime pings

## How It Works

1. **CSV Upload**: Send a CSV file to your Telegram channel
2. **Automatic Processing**: n8n cron job checks Telegram every 10 minutes
3. **WhatsApp Sending**: Messages sent with anti-flagging measures
4. **Reply Detection**: System automatically detects replies
5. **Follow-ups**: 48-hour follow-up messages sent automatically
6. **Admin Reports**: Daily reports sent to admin Telegram

## Deployment

```bash
# 1. Create .env file with your credentials
cp env.example .env
# Edit .env with your values

# 2. Start the system
docker-compose up -d

# 3. System auto-configures everything
# - Supabase tables created automatically
# - n8n workflow auto-imported
# - Environment variables auto-configured
# - Health monitoring started
```

## Environment Variables

All variables are automatically loaded from `.env` file:

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `TELEGRAM_CHANNEL_ID` - Your Telegram channel ID
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase service key
- `ADMIN_TELEGRAM_ID` - Your admin Telegram ID
- `UPTIME_PING_SECRET` - BetterStack uptime ping secret (optional)

## System Components

### WhatsApp Worker (`worker.py`)
- Flask API endpoints for message sending
- Selenium Chrome automation for WhatsApp Web
- Supabase integration for data storage
- Safety mechanisms (daily caps, time windows, warm-up)
- Reply detection system

### n8n Workflow (`whatsapp_campaign.json`)
- CSV processing from Telegram
- Message scheduling and sending
- Follow-up message automation
- Admin reporting

### Auto-Import Functionality
- Workflow auto-import functionality is now integrated into the management script
- Environment variables are automatically configured
- Services are checked for readiness before import

### Health Monitoring
- 24/7 system health checking is integrated into the WhatsApp worker
- Telegram alerts for downtime
- Uptime ping integration

### Management Script (`whatsapp_manager.py`)
- Single script for all management operations
- Telegram integration testing
- CSV file reading
- System health checks
- Workflow import
- Sample data generation

## Safety Features

- **Time Window**: Only sends 10:00-18:00 IST
- **Daily Cap**: Maximum 600 messages per day
- **Warm-up Schedule**: Gradually increases daily limit
- **Random Delays**: 8-12 seconds between messages
- **Failure Detection**: Stops on high failure rates
- **Block Detection**: Stops on WhatsApp limits
- **Reply Handling**: Detects and logs replies

## CSV Format

```csv
phone,business_name,email
919876543210,ABC Shop,contact@abcshop.com
919876543211,XYZ Store,info@xyzstore.com
```

## Telegram Commands

Upload CSV files to your Telegram channel to start campaigns.

## Supabase Tables

### sent_numbers
Tracks all sent numbers and their status:
- `phone` - Phone number (primary key)
- `business_name` - Business name
- `email` - Email address
- `first_sent_at` - Timestamp of first message
- `last_sent_at` - Timestamp of last message
- `last_replied_at` - Timestamp of last reply
- `initial_sent_batch` - Batch ID for tracking
- `followup_sent` - Whether follow-up was sent
- `replied` - Whether user replied
- `send_error` - Error message if failed

### batches
Tracks CSV batch processing:
- `id` - Batch ID (primary key)
- `created_at` - When batch was created
- `csv_filename` - Original CSV filename
- `processed_count` - Number of records processed

## Testing the System

### Using the Management Script
```bash
# Test all system integrations
python whatsapp_manager.py test-integration

# Test Telegram integration
python whatsapp_manager.py test-telegram

# Check Telegram channel information
python whatsapp_manager.py check-channel

# Read today's CSV files from Telegram
python whatsapp_manager.py read-csv

# Test Supabase connection
python whatsapp_manager.py test-supabase

# Create sample CSV file
python whatsapp_manager.py create-sample

# Import n8n workflow
python whatsapp_manager.py import-workflow

# Check system health
python whatsapp_manager.py check-health

# Simulate daily workflow
python whatsapp_manager.py simulate-daily
```

### Check System Status
```bash
# Check if containers are running
docker ps

# Check WhatsApp worker logs
docker logs whatsapp-worker

# Check n8n logs
docker logs n8n
```

### Manual Health Check
```bash
# Check WhatsApp worker health
curl http://localhost:8000/health

# Check n8n health
curl http://localhost:5678/healthz
```

### Trigger Workflow Manually
```bash
# Manually trigger n8n workflow processing
docker exec -it n8n curl -X POST http://localhost:5678/workflows/[WORKFLOW_ID]/run
```

## Troubleshooting

### Common Telegram Issues

1. **Bot not receiving CSV files**:
   - Ensure bot is added as **administrator** to the channel
   - Verify bot has permission to read messages
   - Check that `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID` are correct in `.env`
   - The bot must be added to the channel **before** starting the system

2. **Channel ID format**:
   - For private channels: `-100` followed by the channel ID
   - Example: `-1001234567890`

3. **Bot permissions**:
   - Bot needs "Read messages" permission
   - Bot should be able to access channel messages

4. **No recent messages showing**:
   - Bot was recently added (wait for new messages)
   - Privacy settings restrict bot access
   - No recent messages in channel

### Common Docker Issues

1. **Containers keep restarting**:
   - Check logs: `docker logs [container-name]`
   - Verify environment variables are set correctly
   - Ensure ports are not already in use

2. **n8n workflow not importing**:
   - Check auto-import script logs
   - Verify n8n is accessible at http://localhost:5678
   - Check environment variables are properly set

### Common WhatsApp Issues

1. **QR code not appearing**:
   - Check Chrome/WebDriver installation
   - Verify X11 forwarding if running on headless server
   - Check WhatsApp Web accessibility

2. **Messages not sending**:
   - Check daily limits and time windows
   - Verify phone number formatting
   - Check for WhatsApp blocks or restrictions

### Restart Services
```bash
docker-compose restart
```

## Security

- All credentials stored in `.env` file
- No sensitive data in code
- WhatsApp session stored in Docker volume
- Telegram communication encrypted