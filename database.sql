DROP DATABASE IF EXISTS utility_portalll;
CREATE DATABASE utility_portalll;
USE utility_portalll;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    ward VARCHAR(50),
    mobile_number VARCHAR(15) NOT NULL,
    password VARCHAR(255),
    reset_token VARCHAR(255),
    token_expiry DATETIME
);

CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100),
    password VARCHAR(255),
    department VARCHAR(50),
    reset_token VARCHAR(255),
    token_expiry DATETIME
);

INSERT INTO admins (email, password, department)
VALUES
('wateradmin@gmail.com', 'admin123', 'Water'),
('electricadmin@gmail.com', 'admin123', 'Electricity');

CREATE TABLE complaintss (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    ward VARCHAR(50),
    category VARCHAR(100),
    description TEXT,
    status VARCHAR(30) DEFAULT 'Pending',
    user_email VARCHAR(100),
    admin_reply TEXT,
    department VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ward VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO announcements (ward, message)
VALUES ('all', 'Welcome to Municipal Utility Portal');