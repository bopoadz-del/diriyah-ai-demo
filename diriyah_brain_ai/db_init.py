import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect("diriyah.db")
    c = conn.cursor()
    
    # Create tables
    c.execute("""CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT, role TEXT)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS projects
                 (id INTEGER PRIMARY KEY, name TEXT, folder_id TEXT)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY, type TEXT, detail TEXT, project_id INTEGER)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS whatsapp_groups
                 (id INTEGER PRIMARY KEY, user_id INTEGER, project_id INTEGER, group_id TEXT)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS teams_connections
                 (id INTEGER PRIMARY KEY, user_id INTEGER, project TEXT, channel_id TEXT)""")
    
    # Insert sample data
    c.execute("INSERT OR IGNORE INTO users (username, role) VALUES ('admin', 'admin')")
    c.execute("INSERT OR IGNORE INTO users (username, role) VALUES ('engineer', 'engineer')")
    
    c.execute("INSERT OR IGNORE INTO projects (name, folder_id) VALUES ('Heritage Resort', 'heritage')")
    c.execute("INSERT OR IGNORE INTO projects (name, folder_id) VALUES ('Infrastructure', 'infra')")
    
    c.execute("INSERT OR IGNORE INTO alerts (type, detail, project_id) VALUES ('Delay', 'Task A is behind schedule', 1)")
    c.execute("INSERT OR IGNORE INTO alerts (type, detail, project_id) VALUES ('Budget', 'Overrun in section B', 1)")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")


