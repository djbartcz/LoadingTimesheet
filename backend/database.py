"""
PostgreSQL Database Connection and Setup
"""
import os
import logging
import asyncpg
from typing import Optional

# Global connection pool
pool: Optional[asyncpg.Pool] = None

async def init_db():
    """Initialize PostgreSQL connection pool and create tables"""
    global pool
    
    # Support both DATABASE_URL format and separate variables
    db_url = os.environ.get('DATABASE_URL', '')
    
    # If DATABASE_URL not set, try to build from separate variables
    if not db_url:
        db_name = os.environ.get('DB_NAME', 'timesheet_db')
        db_user = os.environ.get('DB_USER', 'postgres')
        db_password = os.environ.get('DB_PASSWORD', '')
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        
        if db_user and db_password:
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            logging.warning("Database configuration not found - PostgreSQL features disabled")
            logging.warning("Set either DATABASE_URL or DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME")
            return None
    
    if not db_url:
        logging.warning("DATABASE_URL not set - PostgreSQL features disabled")
        return None
    
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(
            db_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        
        # Create tables if they don't exist
        async with pool.acquire() as conn:
            # Create active_timers table
            await conn.execute("""
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
                )
            """)
            
            # Create index on employee_id for faster lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_timers_employee_id 
                ON active_timers(employee_id)
            """)
            
            # Create time_records table
            await conn.execute("""
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
                )
            """)
            
            # Create indexes for time_records
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_time_records_employee_id 
                ON time_records(employee_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_time_records_start_time 
                ON time_records(start_time)
            """)
        
        logging.info("PostgreSQL database initialized successfully")
        return pool
        
    except Exception as e:
        logging.error(f"Failed to initialize PostgreSQL: {e}")
        pool = None
        return None

async def close_db():
    """Close database connection pool"""
    global pool
    if pool:
        await pool.close()
        pool = None
        logging.info("PostgreSQL connection pool closed")

async def get_db():
    """Get database connection from pool"""
    if not pool:
        return None
    return await pool.acquire()

def release_db(conn):
    """Release database connection back to pool"""
    if pool and conn:
        pool.release(conn)

