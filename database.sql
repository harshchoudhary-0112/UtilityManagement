
CREATE DATABASE utility_portall;

USE utility_portall;

CREATE TABLE users (
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100),
email VARCHAR(100),
ward VARCHAR(50),
password VARCHAR(255)
);

CREATE TABLE admins (
id INT AUTO_INCREMENT PRIMARY KEY,
email VARCHAR(100),
password VARCHAR(255)
);

INSERT INTO admins VALUES (1,'admin@gmail.com','admin123');
select * from users;
select * from admins;
select * from complaints;


CREATE TABLE complaints(
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100),
ward VARCHAR(50),
category VARCHAR(100),
description TEXT
);

CREATE TABLE announcements (
id INT PRIMARY KEY AUTO_INCREMENT,
message TEXT
);

select * from announcements;

INSERT INTO announcements (message)
VALUES ('Welcome to Municipal Utility Portal');
ALTER TABLE users 
ADD reset_token VARCHAR(255),
ADD token_expiry DATETIME;

ALTER TABLE admins 
ADD reset_token VARCHAR(255),
ADD token_expiry DATETIME;

ALTER TABLE complaints
ADD COLUMN user_email VARCHAR(100),
ADD COLUMN status VARCHAR(30) DEFAULT 'Pending',
ADD COLUMN admin_reply TEXT,
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

