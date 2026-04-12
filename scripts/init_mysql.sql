-- 初始化数据库脚本
-- 在MySQL容器启动时自动执行

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS internship_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权（如果不存在）
CREATE USER IF NOT EXISTS 'internship'@'%' IDENTIFIED BY 'intern123';
GRANT ALL PRIVILEGES ON internship_db.* TO 'internship'@'%';
FLUSH PRIVILEGES;

-- 切换到新创建的数据库
USE internship_db;

-- 可选：创建一些初始表（注意：后端应用会通过SQLAlchemy创建表）
-- 这里可以留空，因为后端会通过init_db()创建表