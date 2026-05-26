

USE utility_portalll;
-- 1. Workers table
CREATE TABLE workers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mobile_number VARCHAR(15) NOT NULL,
    department VARCHAR(50) NOT NULL,
    ward VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    status ENUM('Available', 'Busy', 'On Leave', 'Inactive') DEFAULT 'Available',
    is_verified TINYINT(1) DEFAULT 0,
    profile_photo VARCHAR(255) DEFAULT NULL,
    reset_token VARCHAR(255) DEFAULT NULL,
    token_expiry DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    login_verified TINYINT DEFAULT 0
);

-- 2. Complaint-Worker Assignment
CREATE TABLE  complaint_worker_assignment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    worker_id INT NOT NULL,
    assigned_by_email VARCHAR(100),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Assigned', 'In Progress', 'Completed', 'Reassigned') DEFAULT 'Assigned',
    FOREIGN KEY (complaint_id) REFERENCES complaintss(id) ON DELETE CASCADE,
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
);

-- 3. Worker Updates (pending admin approval)
CREATE TABLE  worker_updates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    complaint_id INT NOT NULL,
    worker_id INT NOT NULL,
    update_text TEXT NOT NULL,
    proposed_status VARCHAR(30),
    admin_reviewed TINYINT(1) DEFAULT 0,
    admin_approved TINYINT(1) DEFAULT 0,
    admin_remarks TEXT,
    reviewed_by_email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL,
    FOREIGN KEY (assignment_id) REFERENCES complaint_worker_assignment(id) ON DELETE CASCADE,
    FOREIGN KEY (complaint_id) REFERENCES complaintss(id) ON DELETE CASCADE,
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
);

-- 4. Worker Notification Log
CREATE TABLE  worker_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    worker_id INT NOT NULL,
    complaint_id INT,
    notification_type ENUM('assignment', 'reassignment', 'update_approved', 'update_rejected', 'general') DEFAULT 'general',
    message TEXT,
    email_sent TINYINT(1) DEFAULT 0,
    sms_sent TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
);
ALTER TABLE workers ADD COLUMN login_verified TINYINT DEFAULT 0;
