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

CREATE TABLE complaints_history (
    id INT PRIMARY KEY,
    name VARCHAR(255),
    ward VARCHAR(50),
    category VARCHAR(255),
    description TEXT,
    status VARCHAR(50),
    admin_reply TEXT,
    user_email VARCHAR(255),
    department VARCHAR(100),
    created_at DATETIME,
    resolved_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO announcements (ward, message)
VALUES ('all', 'Welcome to Municipal Utility Portal');

ALTER TABLE admins ADD COLUMN name VARCHAR(100);
UPDATE admins SET name = 'Admin' WHERE name IS NULL;
UPDATE admins SET name = 'Electrician' WHERE email = 'electricadmin@gmail.com';
UPDATE admins SET name = 'Waterman' WHERE email = 'wateradmin@gmail.com';
ALTER TABLE admins ADD COLUMN mobile_number VARCHAR(15);
UPDATE admins SET mobile_number = '9669337002' WHERE email = 'electricadmin@gmail.com';
UPDATE admins SET mobile_number = '9669337002' WHERE email = 'wateradmin@gmail.com';
ALTER TABLE complaintss ADD COLUMN is_deleted INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN is_verified TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE admins ADD COLUMN is_verified TINYINT(1) NOT NULL DEFAULT 0;
UPDATE users
SET is_verified = 1
WHERE email IN (
    'krishna@gmail.com',
    'harshchoudhary6268@gmail.com',
    'haritsharma0807@gmail.com',
    'roopesh.sharma@cdgi.edu.in',
    'dayanand.yadav@cdgi.edu.in',
    'harshchoudhar6268y@gmail.com'
);
ALTER TABLE complaintss ADD COLUMN complaint_id VARCHAR(30) UNIQUE;
delete from admins;
delete from users;
select * from users; 
select * from admins; 
delete from complaintss;
select * from complaints_history ; 
select * from announcements;