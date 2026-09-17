import sqlite3
from datetime import datetime
import json
import random
import string

def get_connection():
    return sqlite3.connect('users.db')

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Base table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    email TEXT, username TEXT PRIMARY KEY, password TEXT, profile_pic TEXT
                )''')
                
    # Smart Migration for users table
    try: c.execute("ALTER TABLE users ADD COLUMN total_points INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE users ADD COLUMN tests_completed INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass
                
    # Saved Questions Table
    c.execute('''CREATE TABLE IF NOT EXISTS saved_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, category TEXT, 
                    question TEXT, options TEXT, answer TEXT, explanation TEXT, user_notes TEXT
                )''')
                
    # Test History Table
    c.execute('''CREATE TABLE IF NOT EXISTS test_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT,
                    domains TEXT, total_questions INTEGER, score INTEGER, accuracy INTEGER
                )''')
                
    # Smart Migration for test_history table
    try: c.execute("ALTER TABLE test_history ADD COLUMN attempted_questions INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass

    # --- NEW MULTIPLAYER CHALLENGE TABLES ---
    c.execute('''CREATE TABLE IF NOT EXISTS challenge_rooms (
                    room_code TEXT PRIMARY KEY,
                    host_username TEXT,
                    is_private BOOLEAN,
                    max_participants INTEGER,
                    show_leaderboard BOOLEAN,
                    status TEXT, -- 'waiting', 'active', 'completed'
                    quiz_data TEXT -- JSON string of the generated test
                )''')
                
    c.execute('''CREATE TABLE IF NOT EXISTS room_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_code TEXT,
                    username TEXT,
                    approval_status TEXT, -- 'approved', 'pending', 'rejected'
                    score INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT 0
                )''')

    conn.commit()
    conn.close()

# Existing Functions...
def update_user_stats(username, points_earned):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET total_points = total_points + ?, tests_completed = tests_completed + 1 WHERE username = ?", (points_earned, username))
    conn.commit()
    conn.close()

def save_test_history(username, domains, attempted_questions, total_questions, score, accuracy):
    conn = get_connection()
    c = conn.cursor()
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    domains_str = ", ".join(domains)
    c.execute("INSERT INTO test_history (username, date, domains, attempted_questions, total_questions, score, accuracy) VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (username, current_date, domains_str, attempted_questions, total_questions, score, accuracy))
    conn.commit()
    conn.close()

def get_user_stats(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT total_points, tests_completed FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    return data if data else (0, 0)
    
def get_user_history(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT date, domains, attempted_questions, total_questions, score, accuracy FROM test_history WHERE username = ? ORDER BY id DESC", (username,))
    data = c.fetchall()
    conn.close()
    return data

# --- NEW MULTIPLAYER FUNCTIONS ---
def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def create_challenge_room(host, is_private, max_part, show_leaderboard):
    conn = get_connection()
    c = conn.cursor()
    room_code = generate_room_code()
    c.execute("""
        INSERT INTO challenge_rooms (room_code, host_username, is_private, max_participants, show_leaderboard, status, quiz_data) 
        VALUES (?, ?, ?, ?, ?, 'waiting', '')
    """, (room_code, host, is_private, max_part, show_leaderboard))
    # Host auto-joins
    c.execute("INSERT INTO room_participants (room_code, username, approval_status) VALUES (?, ?, 'approved')", (room_code, host))
    conn.commit()
    conn.close()
    return room_code

def join_challenge_room(room_code, username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT is_private, max_participants FROM challenge_rooms WHERE room_code = ? AND status = 'waiting'", (room_code,))
    room = c.fetchone()
    
    if not room:
        conn.close()
        return "invalid"
        
    is_private, max_part = room
    
    c.execute("SELECT COUNT(*) FROM room_participants WHERE room_code = ? AND approval_status != 'rejected'", (room_code,))
    current_count = c.fetchone()[0]
    
    if current_count >= max_part:
        conn.close()
        return "full"
        
    c.execute("SELECT * FROM room_participants WHERE room_code = ? AND username = ?", (room_code, username))
    if c.fetchone():
        conn.close()
        return "already_joined"
        
    status = 'pending' if is_private else 'approved'
    c.execute("INSERT INTO room_participants (room_code, username, approval_status) VALUES (?, ?, ?)", (room_code, username, status))
    conn.commit()
    conn.close()
    return "joined_pending" if is_private else "joined_approved"

def get_room_participants(room_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username, approval_status FROM room_participants WHERE room_code = ?", (room_code,))
    data = c.fetchall()
    conn.close()
    return data

def update_participant_status(room_code, username, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE room_participants SET approval_status = ? WHERE room_code = ? AND username = ?", (status, room_code, username))
    conn.commit()
    conn.close()

def get_room_details(room_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT host_username, status, quiz_data FROM challenge_rooms WHERE room_code = ?", (room_code,))
    data = c.fetchone()
    conn.close()
    return data

def start_room_test(room_code, quiz_data_json):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE challenge_rooms SET status = 'active', quiz_data = ? WHERE room_code = ?", (quiz_data_json, room_code))
    conn.commit()
    conn.close()

# ==========================================
# NEW FEATURES: LIVE CHAT & LEADERBOARD
# ==========================================

def setup_new_multiplayer_features():
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Chat Table
    c.execute('''CREATE TABLE IF NOT EXISTS room_chat (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_code TEXT,
                    username TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                    
    # 2. Live Results / Leaderboard Table
    c.execute('''CREATE TABLE IF NOT EXISTS room_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_code TEXT,
                    username TEXT,
                    score INTEGER,
                    time_taken REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                    
    # 3. Add Chat Permission Column safely
    try:
        c.execute("ALTER TABLE challenge_rooms ADD COLUMN chat_allowed INTEGER DEFAULT 1")
    except Exception:
        pass # Column already exists, all good!
        
    conn.commit()
    conn.close()

# Isko yahin call kar diya taaki file import hote hi tables ban jayein
setup_new_multiplayer_features()

def update_chat_permission(room_code, is_allowed):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE challenge_rooms SET chat_allowed = ? WHERE room_code = ?", (int(is_allowed), room_code))
    conn.commit()
    conn.close()

def is_chat_allowed(room_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT chat_allowed FROM challenge_rooms WHERE room_code = ?", (room_code,))
    row = c.fetchone()
    conn.close()
    if row and row[0] is not None:
        return bool(row[0])
    return True

def add_chat_message(room_code, username, message):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO room_chat (room_code, username, message) VALUES (?, ?, ?)", (room_code, username, message))
    conn.commit()
    conn.close()

def get_room_chat(room_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username, message, timestamp FROM room_chat WHERE room_code = ? ORDER BY timestamp ASC", (room_code,))
    data = c.fetchall()
    conn.close()
    return data


def submit_room_result(room_code, username, score, time_taken):
    conn = get_connection()
    c = conn.cursor()
    # Check if user already submitted to avoid duplicates
    c.execute("SELECT id FROM room_results WHERE room_code = ? AND username = ?", (room_code, username))
    if not c.fetchone():
        c.execute("INSERT INTO room_results (room_code, username, score, time_taken) VALUES (?, ?, ?, ?)",
                  (room_code, username, score, time_taken))
        conn.commit()
    conn.close()

def get_live_leaderboard(room_code):
    conn = get_connection()
    c = conn.cursor()
    # 🏆 THE MAGIC QUERY: Pehle zyada Score wale upar, agar Score same to kam Time wala upar
    c.execute('''SELECT username, score, time_taken 
                 FROM room_results 
                 WHERE room_code = ? 
                 ORDER BY score DESC, time_taken ASC''', (room_code,))
    data = c.fetchall()
    conn.close()
    return data

def close_challenge_room(room_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM challenge_rooms WHERE room_code = ?", (room_code,))
    c.execute("DELETE FROM room_participants WHERE room_code = ?", (room_code,))
    c.execute("DELETE FROM room_chat WHERE room_code = ?", (room_code,))
    c.execute("DELETE FROM room_results WHERE room_code = ?", (room_code,))
    conn.commit()
    conn.close()

def get_room_show_leaderboard(room_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT show_leaderboard FROM challenge_rooms WHERE room_code = ?", (room_code,))
    row = c.fetchone()
    conn.close()
    if row and row[0] is not None:
        return bool(row[0])
    return True

def delete_saved_question(question_id, username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM saved_questions WHERE id = ? AND username = ?", (question_id, username))
    conn.commit()
    conn.close()