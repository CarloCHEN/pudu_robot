CREATE TABLE foxx_irvine_office_test.mnt_robot_kpi_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    calculation_date DATE NOT NULL,
    robot_sn VARCHAR(100),

    -- KPI 1: Daily Cost
    total_daily_cost DECIMAL(10,2),
    -- daily_power_cost DECIMAL(10,2),
    -- daily_water_cost DECIMAL(10,2),
    -- daily_additional_cost DECIMAL(10,2),
    -- power_consumption_kwh DECIMAL(10,3),
    -- water_consumption_liters DECIMAL(10,3),

    -- KPI 2: Hours Saved
    hours_saved_daily DECIMAL(10,2),
    -- human_hours_needed DECIMAL(10,2),
    -- robot_hours_needed DECIMAL(10,2),
    -- area_cleaned_sqm DECIMAL(10,2),

    -- KPI 3: ROI (Cumulative)
    roi_percentage DECIMAL(10,2),
    -- cumulative_savings DECIMAL(12,2),
    -- total_investment DECIMAL(12,2),
    -- days_since_deployment INT,
    payback_period_days INT,

    -- Unique constraint to prevent duplicate entries
    UNIQUE KEY unique_date_robot (calculation_date, robot_sn),
    INDEX idx_date (calculation_date),
    INDEX idx_robot (robot_sn)
);