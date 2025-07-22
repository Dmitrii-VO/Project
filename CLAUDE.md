# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python working_app.py
# Default: http://0.0.0.0:5000 (configurable via PORT env var)
```

### Testing
```bash
# Run all tests (42 test files)
python -m pytest tests/

# Run by test type
python -m pytest tests/unit/          # Unit tests
python -m pytest tests/integration/   # API integration tests  
python -m pytest tests/system/        # End-to-end system tests

# Run specific tests
python tests/test_complete_system.py
python tests/system/test_placement_completion.py
```

### Database Management
```bash
# Run database migrations
python migrations/02_migration_executor.py

# Debug database structure
python tests/utils/debug_db_structure.py
```

## Project Architecture

### Technology Stack
- **Backend:** Flask 3.0.3 application with SQLite database
- **Frontend:** Modern JavaScript (no framework) + Telegram WebApp SDK
- **Integration:** python-telegram-bot 21.3 with webhook system
- **Authentication:** Telegram-based user authentication

### High-Level Structure
This is a **Telegram Mini App** that connects channel owners with advertisers for ad placement management.

**Core Application (`working_app.py`):**
- Factory pattern with `create_app()` function
- Comprehensive error handling for all HTTP status codes
- Security middleware and Telegram webhook handling at `/webhook/telegram`
- Health checks at `/health` and `/api/health`

**API Architecture (12 modules in `/app/api/`):**
- `channels.py` - Channel management (20+ endpoints)
- `offers.py` - Legacy offer system (2102 lines, being replaced)
- `offers_new.py` - New unified API replacing legacy code
- `proposals_management.py` - New proposal-based workflow
- `analytics.py` - Analytics and reporting
- `channel_recommendations.py` - ML-based channel matching

**Services Layer (`/app/services/`):**
- New modular architecture in `/services/offers/` with 70% code reduction
- Clean separation: `offer_service.py`, `offer_repository.py`, `offer_validator.py`
- Business logic separated from API layer

**Frontend (`/app/static/js/`):**
- Modular JavaScript architecture (17 files)
- Key modules: `channels-core.js`, `channels-modals.js`, `offers-manager.js`
- Telegram WebApp integration in `telegram-app.js`

### Database Schema
- SQLite with 4 migration files
- Main tables: users, channels, offers, offer_proposals, offer_responses, payments
- Foreign key constraints enabled

## Key Business Logic

### Channel Management Flow
1. Users add Telegram channels via URL or username
2. Verification through message forwarding to the bot
3. Real-time subscriber count updates via Telegram API
4. Category-based organization and statistics tracking

### Offer System (New Architecture)
1. **Advertisers** create offers with budget and targeting criteria
2. **System** matches offers to suitable channels using recommendation engine
3. **Advertisers** send proposals to selected channel owners
4. **Channel owners** accept/reject proposals with response messages
5. **Tracking** placement completion through bot notifications

### Telegram Integration
- Bot commands: `/start`, `/post_published` for placement tracking
- Webhook-based real-time updates at `/webhook/telegram`
- eREIT token system for ad placement verification
- Notification system for all user interactions

## Environment Configuration

Required environment variables:
```bash
BOT_TOKEN=your_telegram_bot_token
WEBAPP_URL=https://your-domain.com
YOUR_TELEGRAM_ID=your_admin_telegram_id
```

Optional (have defaults):
```bash
DEBUG=True/False
DATABASE_PATH=path_to_database
FLASK_ENV=development/production/testing
PORT=5000
```

## Architecture Evolution Notes

The project has undergone significant refactoring:
- **Legacy:** Monolithic `offers.py` (2102 lines) and `offers_management.py` (633 lines)
- **Current:** Modular service layer architecture
- **Status:** Legacy files marked for removal, new architecture ready for deployment

Key files to understand the transition:
- `/app/services/offers/` - New modular architecture
- `/app/api/offers_new.py` - Unified API ready to replace legacy files
- `FUNCTIONS_MAP.md` - Complete function mapping and migration status

## Current Status (Version 1.3)
- Modern proposal-based workflow replacing direct responses
- Real-time Telegram API integration for accurate channel data
- Comprehensive test coverage (42 test files)
- Production-ready with security headers and error handling