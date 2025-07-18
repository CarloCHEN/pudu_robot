-- Track individual robot investments
CREATE TABLE foxx_irvine_office_test.mnt_robot_investment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    robot_sn VARCHAR(100) UNIQUE NOT NULL,
    purchase_price DECIMAL(12,2) NOT NULL,
    purchase_date DATE NOT NULL,
    expected_lifespan_years INT DEFAULT 5,
    annual_maintenance_cost DECIMAL(10,2) DEFAULT 0,
    deployment_date DATE,  -- When robot started operating
    status ENUM('active', 'retired', 'maintenance') DEFAULT 'active',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_status (status),
    INDEX idx_deployment (deployment_date)
);