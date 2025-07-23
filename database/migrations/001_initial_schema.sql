-- PostgreSQL Migration Script - Initial Schema
-- Migrating from SQLite to PostgreSQL for Telegram Mini App
-- Version: 1.0
-- Date: 2025-01-01

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(20),
    balance DECIMAL(10,2) DEFAULT 0.00,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    language_code VARCHAR(10) DEFAULT 'ru',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    CONSTRAINT users_telegram_id_check CHECK (telegram_id > 0),
    CONSTRAINT users_balance_check CHECK (balance >= 0)
);

-- Create channels table
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    description TEXT,
    category VARCHAR(50) DEFAULT 'other',
    subscriber_count INTEGER DEFAULT 0,
    price_per_post DECIMAL(10,2) DEFAULT 0.00,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    verification_code VARCHAR(10),
    verification_expires_at TIMESTAMP WITH TIME ZONE,
    last_stats_update TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT channels_subscriber_count_check CHECK (subscriber_count >= 0),
    CONSTRAINT channels_price_check CHECK (price_per_post >= 0),
    CONSTRAINT channels_username_unique UNIQUE (username)
);

-- Create offers table
CREATE TABLE IF NOT EXISTS offers (
    id SERIAL PRIMARY KEY,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    advertiser_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_audience TEXT,
    budget_total DECIMAL(10,2),
    price DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'RUB',
    status VARCHAR(50) DEFAULT 'draft',
    category VARCHAR(50) DEFAULT 'other',
    placement_type VARCHAR(50) DEFAULT 'post',
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT offers_budget_check CHECK (budget_total >= 0 OR budget_total IS NULL),
    CONSTRAINT offers_price_check CHECK (price >= 0 OR price IS NULL),
    CONSTRAINT offers_dates_check CHECK (start_date IS NULL OR end_date IS NULL OR start_date <= end_date)
);

-- Create offer_responses table (previously offer_proposals)
CREATE TABLE IF NOT EXISTS offer_responses (
    id SERIAL PRIMARY KEY,
    offer_id INTEGER NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    channel_id INTEGER NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    response_message TEXT,
    proposed_price DECIMAL(10,2),
    counter_offers_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT offer_responses_price_check CHECK (proposed_price >= 0 OR proposed_price IS NULL),
    CONSTRAINT offer_responses_counter_offers_check CHECK (counter_offers_count >= 0),
    CONSTRAINT offer_responses_unique UNIQUE (offer_id, channel_id)
);

-- Create offer_placements table
CREATE TABLE IF NOT EXISTS offer_placements (
    id SERIAL PRIMARY KEY,
    response_id INTEGER NOT NULL REFERENCES offer_responses(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending_placement',
    post_url VARCHAR(500),
    placement_start TIMESTAMP WITH TIME ZONE,
    placement_end TIMESTAMP WITH TIME ZONE,
    views_count INTEGER DEFAULT 0,
    clicks_count INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT placements_counts_check CHECK (views_count >= 0 AND clicks_count >= 0),
    CONSTRAINT placements_engagement_check CHECK (engagement_rate >= 0 AND engagement_rate <= 100)
);

-- Create payments table
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    offer_id INTEGER REFERENCES offers(id) ON DELETE SET NULL,
    placement_id INTEGER REFERENCES offer_placements(id) ON DELETE SET NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    payment_type VARCHAR(50) NOT NULL, -- 'deposit', 'withdrawal', 'escrow', 'payout'
    status VARCHAR(50) DEFAULT 'pending',
    provider VARCHAR(50), -- 'telegram_payments', 'bank_card', etc.
    provider_payment_id VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT payments_amount_check CHECK (amount > 0)
);

-- Create analytics_events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    channel_id INTEGER REFERENCES channels(id) ON DELETE SET NULL,
    offer_id INTEGER REFERENCES offers(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for analytics queries
    CONSTRAINT analytics_events_type_check CHECK (event_type != '')
);

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT notifications_title_check CHECK (title != ''),
    CONSTRAINT notifications_message_check CHECK (message != '')
);

-- Create user_sessions table for auth tracking
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Constraints
    CONSTRAINT sessions_expires_check CHECK (expires_at > created_at)
);

-- Create security audit logs table
CREATE TABLE IF NOT EXISTS security_audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    risk_level VARCHAR(20) DEFAULT 'low',
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for security queries
    CONSTRAINT audit_action_check CHECK (action != '')
);

-- Create indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_channels_owner_id ON channels(owner_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_channels_username ON channels(username) WHERE username IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_channels_category ON channels(category);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_channels_verified_active ON channels(is_verified, is_active);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_offers_created_by ON offers(created_by);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_offers_advertiser_id ON offers(advertiser_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_offers_status ON offers(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_offers_category ON offers(category);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_offers_dates ON offers(start_date, end_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_offers_created_at ON offers(created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_responses_offer_id ON offer_responses(offer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_responses_channel_id ON offer_responses(channel_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_responses_user_id ON offer_responses(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_responses_status ON offer_responses(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_responses_created_at ON offer_responses(created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_placements_response_id ON offer_placements(response_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_placements_status ON offer_placements(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_placements_dates ON offer_placements(placement_start, placement_end);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_offer_id ON payments(offer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_type_status ON payments(payment_type, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_created_at ON payments(created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_user_id ON analytics_events(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_session_id ON analytics_events(session_id) WHERE session_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_type ON notifications(notification_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active ON user_sessions(is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user_id ON security_audit_logs(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_action ON security_audit_logs(action);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_timestamp ON security_audit_logs(timestamp);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_risk ON security_audit_logs(risk_level);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channels_updated_at BEFORE UPDATE ON channels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offers_updated_at BEFORE UPDATE ON offers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_responses_updated_at BEFORE UPDATE ON offer_responses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_placements_updated_at BEFORE UPDATE ON offer_placements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE OR REPLACE VIEW active_offers AS
SELECT 
    o.*,
    u.first_name as creator_name,
    u.telegram_id as creator_telegram_id,
    COUNT(r.id) as response_count
FROM offers o
LEFT JOIN users u ON o.created_by = u.id
LEFT JOIN offer_responses r ON o.id = r.offer_id
WHERE o.status IN ('active', 'matching', 'started')
GROUP BY o.id, u.first_name, u.telegram_id;

CREATE OR REPLACE VIEW channel_stats AS
SELECT 
    c.*,
    u.first_name as owner_name,
    u.telegram_id as owner_telegram_id,
    COUNT(DISTINCT r.id) as total_responses,
    COUNT(DISTINCT CASE WHEN r.status = 'accepted' THEN r.id END) as accepted_responses,
    COUNT(DISTINCT p.id) as total_placements,
    COALESCE(SUM(CASE WHEN p.status = 'active' THEN 1 END), 0) as active_placements
FROM channels c
LEFT JOIN users u ON c.owner_id = u.id
LEFT JOIN offer_responses r ON c.id = r.channel_id
LEFT JOIN offer_placements p ON r.id = p.response_id
WHERE c.is_active = true
GROUP BY c.id, u.first_name, u.telegram_id;

-- Create stored procedures for common operations
CREATE OR REPLACE FUNCTION create_offer_response(
    p_offer_id INTEGER,
    p_channel_id INTEGER,
    p_user_id INTEGER,
    p_response_message TEXT DEFAULT NULL,
    p_proposed_price DECIMAL(10,2) DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    response_id INTEGER;
BEGIN
    INSERT INTO offer_responses (
        offer_id, channel_id, user_id, 
        response_message, proposed_price,
        expires_at
    ) VALUES (
        p_offer_id, p_channel_id, p_user_id,
        p_response_message, p_proposed_price,
        CURRENT_TIMESTAMP + INTERVAL '24 hours'
    ) RETURNING id INTO response_id;
    
    RETURN response_id;
END;
$$ LANGUAGE plpgsql;

-- Insert migration record
INSERT INTO migration_history (version, applied_at, description) 
VALUES ('001', CURRENT_TIMESTAMP, 'Initial schema migration from SQLite to PostgreSQL')
ON CONFLICT (version) DO NOTHING;

-- Create migration_history table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_history (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

COMMIT;