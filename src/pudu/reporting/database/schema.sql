-- src/pudu/reporting/database/schema.sql
-- Database schema for robot management reporting system

-- Report schedules table
CREATE TABLE mnt_report_schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    report_config JSON NOT NULL,
    schedule_frequency ENUM('immediate', 'daily', 'weekly', 'monthly') NOT NULL,
    eventbridge_rule_name VARCHAR(255),
    eventbridge_rule_arn VARCHAR(500),
    last_run_time DATETIME NULL,
    next_run_time DATETIME NULL,
    status ENUM('active', 'paused', 'deleted') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    INDEX idx_customer_status (customer_id, status),
    INDEX idx_next_run_time (next_run_time),
    INDEX idx_rule_name (eventbridge_rule_name),

    -- JSON validation for report_config
    CONSTRAINT chk_report_config_valid
        CHECK (JSON_VALID(report_config)),

    -- Ensure rule name is unique when active
    UNIQUE KEY uniq_active_rule (eventbridge_rule_name, status)
);

-- Report execution history table
CREATE TABLE mnt_report_execution_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    schedule_id INT NULL,
    report_config JSON NOT NULL,
    execution_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'failed', 'partial') NOT NULL,
    execution_time_seconds DECIMAL(10, 3),
    robots_included INT DEFAULT 0,
    records_processed INT DEFAULT 0,
    storage_url VARCHAR(1000) NULL,
    delivery_method ENUM('in-app', 'email') NOT NULL,
    delivery_status ENUM('success', 'failed', 'partial') NOT NULL,
    error_message TEXT NULL,
    metadata JSON NULL,

    INDEX idx_customer_time (customer_id, execution_time),
    INDEX idx_schedule_id (schedule_id),
    INDEX idx_status (status),
    INDEX idx_delivery_method (delivery_method),

    FOREIGN KEY (schedule_id) REFERENCES mnt_report_schedules(id) ON DELETE SET NULL,

    CONSTRAINT chk_report_config_valid_history
        CHECK (JSON_VALID(report_config)),
    CONSTRAINT chk_metadata_valid
        CHECK (metadata IS NULL OR JSON_VALID(metadata))
);

-- Report delivery tracking table
CREATE TABLE mnt_report_deliveries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    execution_history_id INT NOT NULL,
    customer_id VARCHAR(255) NOT NULL,
    delivery_method ENUM('in-app', 'email') NOT NULL,
    recipient VARCHAR(255) NULL, -- Email address for email delivery
    delivery_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('sent', 'failed', 'bounced', 'opened') NOT NULL,
    message_id VARCHAR(255) NULL, -- SES message ID for emails
    error_message TEXT NULL,

    INDEX idx_customer_time (customer_id, delivery_time),
    INDEX idx_execution_history (execution_history_id),
    INDEX idx_delivery_method (delivery_method),
    INDEX idx_recipient (recipient),
    INDEX idx_status (status),

    FOREIGN KEY (execution_history_id) REFERENCES mnt_report_execution_history(id) ON DELETE CASCADE
);

-- Report templates table (for future extensibility)
CREATE TABLE mnt_report_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL UNIQUE,
    template_type ENUM('robot_performance', 'cost_analysis', 'maintenance', 'custom') NOT NULL,
    description TEXT,
    template_config JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_template_type (template_type),
    INDEX idx_is_active (is_active),

    CONSTRAINT chk_template_config_valid
        CHECK (JSON_VALID(template_config))
);

-- Insert default robot performance template
INSERT INTO mnt_report_templates (
    template_name,
    template_type,
    description,
    template_config,
    created_by
) VALUES (
    'Robot Performance Report',
    'robot_performance',
    'Standard robot performance analysis template with fleet status, task analysis, charging performance, and event monitoring',
    JSON_OBJECT(
        'sections', JSON_ARRAY('robot_status', 'cleaning_tasks', 'charging_tasks', 'performance', 'cost_analysis'),
        'detail_levels', JSON_ARRAY('summary', 'detailed', 'comprehensive'),
        'supported_charts', JSON_ARRAY('status_distribution', 'task_completion', 'charging_trends', 'event_analysis')
    ),
    'system'
);

-- Customer report preferences table
CREATE TABLE mnt_customer_report_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL UNIQUE,
    default_detail_level ENUM('summary', 'detailed', 'comprehensive') DEFAULT 'detailed',
    default_delivery_method ENUM('in-app', 'email') DEFAULT 'in-app',
    default_email_recipients JSON NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    notification_preferences JSON NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_customer_id (customer_id),

    CONSTRAINT chk_email_recipients_valid
        CHECK (default_email_recipients IS NULL OR JSON_VALID(default_email_recipients)),
    CONSTRAINT chk_notification_preferences_valid
        CHECK (notification_preferences IS NULL OR JSON_VALID(notification_preferences))
);

-- Report access logs (for audit and analytics)
CREATE TABLE mnt_report_access_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    report_url VARCHAR(1000) NOT NULL,
    access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_method ENUM('direct', 'email_link', 'dashboard') NOT NULL,
    user_agent TEXT NULL,
    ip_address VARCHAR(45) NULL,

    INDEX idx_customer_time (customer_id, access_time),
    INDEX idx_access_method (access_method),
    INDEX idx_report_url (report_url(255))
);

-- Views for reporting and analytics

-- Active schedules summary view
CREATE VIEW vw_active_report_schedules AS
SELECT
    rs.id,
    rs.customer_id,
    rs.schedule_frequency,
    rs.next_run_time,
    rs.eventbridge_rule_name,
    JSON_UNQUOTE(JSON_EXTRACT(rs.report_config, '$.detailLevel')) as detail_level,
    JSON_UNQUOTE(JSON_EXTRACT(rs.report_config, '$.delivery')) as delivery_method,
    rs.created_at,
    COALESCE(erh.last_execution, 'Never') as last_execution,
    CASE
        WHEN rs.next_run_time < NOW() THEN 'Overdue'
        WHEN rs.next_run_time < DATE_ADD(NOW(), INTERVAL 1 HOUR) THEN 'Due Soon'
        ELSE 'Scheduled'
    END as schedule_status
FROM mnt_report_schedules rs
LEFT JOIN (
    SELECT
        schedule_id,
        MAX(execution_time) as last_execution
    FROM mnt_report_execution_history
    GROUP BY schedule_id
) erh ON rs.id = erh.schedule_id
WHERE rs.status = 'active';

-- Customer report summary view
CREATE VIEW vw_customer_report_summary AS
SELECT
    erh.customer_id,
    COUNT(*) as total_reports,
    COUNT(CASE WHEN erh.status = 'success' THEN 1 END) as successful_reports,
    COUNT(CASE WHEN erh.status = 'failed' THEN 1 END) as failed_reports,
    AVG(erh.execution_time_seconds) as avg_execution_time,
    MAX(erh.execution_time) as last_report_time,
    SUM(erh.robots_included) as total_robots_analyzed,
    SUM(erh.records_processed) as total_records_processed
FROM mnt_report_execution_history erh
WHERE erh.execution_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY erh.customer_id;

-- Recent report activity view
CREATE VIEW vw_recent_report_activity AS
SELECT
    erh.id,
    erh.customer_id,
    erh.execution_time,
    erh.status,
    erh.delivery_method,
    erh.robots_included,
    erh.records_processed,
    erh.execution_time_seconds,
    erh.storage_url,
    rs.schedule_frequency,
    JSON_UNQUOTE(JSON_EXTRACT(erh.report_config, '$.detailLevel')) as detail_level,
    CASE
        WHEN rs.id IS NOT NULL THEN 'Scheduled'
        ELSE 'On-Demand'
    END as report_type
FROM mnt_report_execution_history erh
LEFT JOIN mnt_report_schedules rs ON erh.schedule_id = rs.id
WHERE erh.execution_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY erh.execution_time DESC;

-- Indexes for performance optimization
CREATE INDEX idx_execution_history_customer_time ON mnt_report_execution_history(customer_id, execution_time);
CREATE INDEX idx_schedules_next_run ON mnt_report_schedules(next_run_time, status);
CREATE INDEX idx_deliveries_status_time ON mnt_report_deliveries(status, delivery_time);

-- Initial data for testing (optional)
-- INSERT INTO mnt_customer_report_preferences (customer_id, default_detail_level, default_delivery_method, timezone)
-- VALUES ('test-customer-123', 'detailed', 'email', 'America/New_York');