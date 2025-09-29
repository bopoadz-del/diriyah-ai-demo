CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY,
  name TEXT,
  drive_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY,
  project_id INTEGER,
  title TEXT,
  pinned BOOLEAN,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY,
  chat_id INTEGER,
  role TEXT,
  content TEXT,
  liked BOOLEAN,
  disliked BOOLEAN,
  copied BOOLEAN,
  read BOOLEAN,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  name TEXT,
  email TEXT,
  role TEXT
);
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  action TEXT,
  message_id INTEGER,
  timestamp TEXT
);