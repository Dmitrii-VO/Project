-- PostgreSQL Performance Optimization Migration
-- Adding advanced indexes, partitioning, and performance enhancements
-- Version: 2.0
-- Date: 2025-01-01

-- Create partial indexes for better performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_offers_active_budget 
ON offers(budget_total DESC, created_at DESC) 
WHERE status IN ('active', 'matching');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_responses_pending_recent 
ON offer_responses(created_at DESC) 
WHERE status = 'pending';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_channels_verified_by_category 
ON channels(category, subscriber_count DESC) 
WHERE is_verified = true AND is_active = true;

-- Create composite indexes for complex queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_placements_stats 
ON offer_placements(status, placement_start, views_count, clicks_count);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_user_type_date 
ON payments(user_id, payment_type, created_at DESC);

-- Create GIN indexes for JSONB columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_data_gin 
ON analytics_events USING GIN (event_data);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_data_gin 
ON notifications USING GIN (data);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_details_gin 
ON security_audit_logs USING GIN (details);

-- Partitioning for analytics_events table (by month)
CREATE TABLE IF NOT EXISTS analytics_events_template (
    LIKE analytics_events INCLUDING ALL
);

-- Create function for automatic partitioning
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I 
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
                   
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (created_at)',
                   'idx_' || partition_name || '_created_at', partition_name);
END;
$$ LANGUAGE plpgsql;

-- Convert analytics_events to partitioned table
DO $$
BEGIN
    -- Only partition if not already partitioned
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'analytics_events' AND c.relkind = 'p'
    ) THEN
        -- Create partitioned table
        ALTER TABLE analytics_events RENAME TO analytics_events_old;
        
        CREATE TABLE analytics_events (
            LIKE analytics_events_old INCLUDING ALL
        ) PARTITION BY RANGE (created_at);
        
        -- Create partitions for current year
        PERFORM create_monthly_partition('analytics_events', date_trunc('month', CURRENT_DATE - interval '2 months'));
        PERFORM create_monthly_partition('analytics_events', date_trunc('month', CURRENT_DATE - interval '1 month'));
        PERFORM create_monthly_partition('analytics_events', date_trunc('month', CURRENT_DATE));
        PERFORM create_monthly_partition('analytics_events', date_trunc('month', CURRENT_DATE + interval '1 month'));
        
        -- Migrate data
        INSERT INTO analytics_events SELECT * FROM analytics_events_old;
        
        -- Drop old table
        DROP TABLE analytics_events_old;
    END IF;
END $$;

-- Create materialized views for dashboard analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_offer_stats AS
SELECT 
    date_trunc('day', created_at) as date,
    COUNT(*) as total_offers,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_offers,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_offers,
    AVG(COALESCE(budget_total, price)) as avg_budget,
    SUM(COALESCE(budget_total, price)) as total_budget
FROM offers
WHERE created_at >= CURRENT_DATE - interval '90 days'
GROUP BY date_trunc('day', created_at)
ORDER BY date;

CREATE MATERIALIZED VIEW IF NOT EXISTS channel_performance_stats AS
SELECT 
    c.id,
    c.title,
    c.category,
    c.subscriber_count,
    COUNT(DISTINCT r.id) as total_responses,
    COUNT(DISTINCT CASE WHEN r.status = 'accepted' THEN r.id END) as accepted_responses,
    COUNT(DISTINCT p.id) as total_placements,
    COALESCE(AVG(p.views_count), 0) as avg_views,
    COALESCE(AVG(p.clicks_count), 0) as avg_clicks,
    COALESCE(AVG(p.engagement_rate), 0) as avg_engagement,
    MAX(r.created_at) as last_response_date
FROM channels c
LEFT JOIN offer_responses r ON c.id = r.channel_id
LEFT JOIN offer_placements p ON r.id = p.response_id
WHERE c.is_active = true
GROUP BY c.id, c.title, c.category, c.subscriber_count;

-- Create unique indexes on materialized views
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_offer_stats(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_perf_id ON channel_performance_stats(id);

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_offer_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY channel_performance_stats;
END;
$$ LANGUAGE plpgsql;

-- Create function for database maintenance
CREATE OR REPLACE FUNCTION maintain_database()
RETURNS void AS $$
BEGIN
    -- Update table statistics
    ANALYZE users, channels, offers, offer_responses, offer_placements, payments;
    
    -- Clean old notifications (older than 30 days)
    DELETE FROM notifications 
    WHERE created_at < CURRENT_DATE - interval '30 days' AND is_read = true;
    
    -- Clean old analytics events (older than 1 year)
    DELETE FROM analytics_events 
    WHERE created_at < CURRENT_DATE - interval '1 year';
    
    -- Clean expired user sessions
    DELETE FROM user_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP;
    
    -- Clean old audit logs (older than 6 months, keep only high risk)
    DELETE FROM security_audit_logs 
    WHERE timestamp < CURRENT_DATE - interval '6 months' 
    AND risk_level IN ('low', 'medium');
    
    -- Refresh materialized views
    PERFORM refresh_analytics_views();
END;
$$ LANGUAGE plpgsql;

-- Create function for automatic partition creation
CREATE OR REPLACE FUNCTION create_next_month_partitions()
RETURNS void AS $$
BEGIN
    -- Create partition for next month
    PERFORM create_monthly_partition('analytics_events', 
                                   date_trunc('month', CURRENT_DATE + interval '2 months'));
END;
$$ LANGUAGE plpgsql;

-- Enhanced stored procedures
CREATE OR REPLACE FUNCTION get_user_dashboard_stats(p_user_id INTEGER)
RETURNS TABLE(
    total_channels INTEGER,
    verified_channels INTEGER,
    total_offers INTEGER,
    active_offers INTEGER,
    total_responses INTEGER,
    pending_responses INTEGER,
    total_placements INTEGER,
    active_placements INTEGER,
    total_earnings DECIMAL(10,2),
    pending_payments DECIMAL(10,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH user_stats AS (
        SELECT 
            u.id,
            COUNT(DISTINCT c.id) as channels_count,
            COUNT(DISTINCT CASE WHEN c.is_verified THEN c.id END) as verified_count,
            COUNT(DISTINCT o.id) as offers_count,
            COUNT(DISTINCT CASE WHEN o.status IN ('active', 'matching') THEN o.id END) as active_offers_count,
            COUNT(DISTINCT r.id) as responses_count,
            COUNT(DISTINCT CASE WHEN r.status = 'pending' THEN r.id END) as pending_count,
            COUNT(DISTINCT p.id) as placements_count,
            COUNT(DISTINCT CASE WHEN p.status = 'active' THEN p.id END) as active_placements_count,
            COALESCE(SUM(CASE WHEN pay.payment_type = 'payout' AND pay.status = 'completed' THEN pay.amount END), 0) as earnings,
            COALESCE(SUM(CASE WHEN pay.payment_type = 'payout' AND pay.status = 'pending' THEN pay.amount END), 0) as pending
        FROM users u
        LEFT JOIN channels c ON u.id = c.owner_id
        LEFT JOIN offers o ON u.id = o.created_by
        LEFT JOIN offer_responses r ON c.id = r.channel_id
        LEFT JOIN offer_placements p ON r.id = p.response_id
        LEFT JOIN payments pay ON u.id = pay.user_id
        WHERE u.id = p_user_id
        GROUP BY u.id
    )
    SELECT 
        channels_count::INTEGER,
        verified_count::INTEGER,
        offers_count::INTEGER,
        active_offers_count::INTEGER,
        responses_count::INTEGER,
        pending_count::INTEGER,
        placements_count::INTEGER,
        active_placements_count::INTEGER,
        earnings,
        pending
    FROM user_stats;
END;
$$ LANGUAGE plpgsql;

-- Create function for offer matching algorithm
CREATE OR REPLACE FUNCTION find_matching_channels(
    p_offer_id INTEGER,
    p_limit INTEGER DEFAULT 10
) RETURNS TABLE(
    channel_id INTEGER,
    channel_title VARCHAR(255),
    channel_username VARCHAR(255),
    subscriber_count INTEGER,
    match_score DECIMAL(3,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH offer_info AS (
        SELECT category, target_audience, COALESCE(budget_total, price) as budget
        FROM offers WHERE id = p_offer_id
    ),
    channel_scores AS (
        SELECT 
            c.id,
            c.title,
            c.username,
            c.subscriber_count,
            -- Calculate match score based on category, budget, and performance
            (
                CASE WHEN c.category = oi.category THEN 0.4 ELSE 0.0 END +
                CASE WHEN c.subscriber_count >= 1000 THEN 0.3 ELSE c.subscriber_count::DECIMAL / 1000 * 0.3 END +
                CASE WHEN cps.avg_engagement >= 5.0 THEN 0.3 ELSE cps.avg_engagement / 5.0 * 0.3 END
            ) as score
        FROM channels c
        CROSS JOIN offer_info oi
        LEFT JOIN channel_performance_stats cps ON c.id = cps.id
        WHERE c.is_verified = true 
        AND c.is_active = true
        AND c.price_per_post <= oi.budget
        AND NOT EXISTS (
            SELECT 1 FROM offer_responses r 
            WHERE r.offer_id = p_offer_id AND r.channel_id = c.id
        )
    )
    SELECT 
        cs.id,
        cs.title,
        cs.username,
        cs.subscriber_count,
        cs.score
    FROM channel_scores cs
    WHERE cs.score > 0.2
    ORDER BY cs.score DESC, cs.subscriber_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Add configuration for automatic maintenance
INSERT INTO pg_settings_custom (name, setting, description) VALUES
('maintenance.auto_analyze', 'on', 'Enable automatic analyze'),
('maintenance.auto_vacuum', 'on', 'Enable automatic vacuum')
ON CONFLICT (name) DO UPDATE SET setting = EXCLUDED.setting;

-- Create table for custom settings if not exists
CREATE TABLE IF NOT EXISTS pg_settings_custom (
    name VARCHAR(100) PRIMARY KEY,
    setting VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert migration record
INSERT INTO migration_history (version, applied_at, description) 
VALUES ('002', CURRENT_TIMESTAMP, 'Performance optimizations and partitioning')
ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

COMMIT;