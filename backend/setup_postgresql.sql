-- PostgreSQL Database Setup Script
-- Run this script in PostgreSQL to create the database

-- Create database (run as postgres superuser)
CREATE DATABASE timesheet_db;

-- Connect to the database
\c timesheet_db

-- Tables will be created automatically by the application
-- But you can also create them manually if needed:

-- Active Timers Table
CREATE TABLE IF NOT EXISTS active_timers (
    id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL,
    employee_name VARCHAR(255) NOT NULL,
    project_id VARCHAR(255),
    project_name VARCHAR(255),
    task VARCHAR(255) NOT NULL,
    is_non_productive BOOLEAN DEFAULT FALSE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster employee lookups
CREATE INDEX IF NOT EXISTS idx_active_timers_employee_id 
ON active_timers(employee_id);

-- Time Records Table
CREATE TABLE IF NOT EXISTS time_records (
    id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL,
    employee_name VARCHAR(255) NOT NULL,
    project_id VARCHAR(255),
    project_name VARCHAR(255),
    task VARCHAR(255) NOT NULL,
    is_non_productive BOOLEAN DEFAULT FALSE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for time_records
CREATE INDEX IF NOT EXISTS idx_time_records_employee_id 
ON time_records(employee_id);

CREATE INDEX IF NOT EXISTS idx_time_records_start_time 
ON time_records(start_time);

