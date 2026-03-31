# logic.py
import sqlite3
import time
import random
from pathlib import Path
import pyttsx3
import hashlib
import ctypes
import sys
import threading
import secrets
import string

DB_FILE = "typing_master.db"
SENTENCE_FILE = "sentences.txt"
PRACTICE_WORDS_FILE = "audio_words.txt"

class TypingLogic:
    def __init__(self, db_path=DB_FILE, sentence_file=SENTENCE_FILE):
        self.db_path = db_path
        self.sentence_file = sentence_file
        self.current_sentence = ""
        self.current_audio_text = ""
        self.start_time = None
        self.tts_engine = None
        self.audio_mode = "sentence"  # "word" or "sentence"
        self.seen_audio_items = []
        self.skipped_audio_items = []
        self.wrong_audio_items = []
        self._is_speaking = False
        self._desired_rate = 150
        self._tts_lock = threading.Lock()
        self._ensure_db()

    # --- DB helpers ---
    def _ensure_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                wpm REAL,
                accuracy REAL,
                time_taken REAL,
                test_type TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Users table for login
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                favorite_color TEXT DEFAULT '',
                pass_key TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Ensure favorite_color column exists on older DBs
        cur.execute("PRAGMA table_info(users)")
        user_cols = [row[1] for row in cur.fetchall()]
        if "favorite_color" not in user_cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN favorite_color TEXT DEFAULT ''")
            except Exception:
                pass
        if "pass_key" not in user_cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN pass_key TEXT DEFAULT ''")
            except Exception:
                pass
        # Ensure older DBs get missing columns added (migration)
        cur.execute("PRAGMA table_info(results)")
        existing_cols = [row[1] for row in cur.fetchall()]
        if "wpm" not in existing_cols:
            cur.execute("ALTER TABLE results ADD COLUMN wpm REAL DEFAULT 0")
        if "accuracy" not in existing_cols:
            cur.execute("ALTER TABLE results ADD COLUMN accuracy REAL DEFAULT 0")
        if "time_taken" not in existing_cols:
            cur.execute("ALTER TABLE results ADD COLUMN time_taken REAL DEFAULT 0")
        if "test_type" not in existing_cols:
            cur.execute("ALTER TABLE results ADD COLUMN test_type TEXT DEFAULT ''")
        if "created_at" not in existing_cols:
            # add created_at as text (no non-constant default allowed in ALTER TABLE for some SQLite versions)
            cur.execute("ALTER TABLE results ADD COLUMN created_at TEXT DEFAULT ''")
        conn.commit()
        conn.close()

    # --- User helpers ---
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def add_user(self, username: str, password: str) -> tuple[bool, str | None]:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            alphabet = string.ascii_uppercase + string.digits
            pass_key = "".join(secrets.choice(alphabet) for _ in range(8))
            cur.execute(
                "INSERT INTO users (username, password_hash, pass_key) VALUES (?, ?, ?)",
                (username.strip(), self._hash_password(password), pass_key)
            )
            conn.commit()
            conn.close()
            return True, pass_key
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return False, None

    def verify_user(self, username: str, password: str) -> bool:
        """Verify a user's credentials."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = ?", (username.strip(),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return False
        return row[0] == self._hash_password(password)

    def get_all_users(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT username FROM users ORDER BY username ASC")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def reset_password(self, username: str, new_password: str) -> bool:
        """Reset password for an existing user. Returns True when updated."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (self._hash_password(new_password), username.strip())
        )
        conn.commit()
        changed = cur.rowcount > 0
        conn.close()
        return changed

    def reset_password_with_passkey(self, username: str, pass_key: str, new_password: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT pass_key FROM users WHERE username = ?", (username.strip(),))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        if (row[0] or "").strip() != pass_key.strip():
            conn.close()
            return False
        cur.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (self._hash_password(new_password), username.strip())
        )
        conn.commit()
        ok = cur.rowcount > 0
        conn.close()
        return ok

    def get_pass_key(self, username: str) -> str | None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT pass_key FROM users WHERE username = ?", (username.strip(),))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def save_result(self, name, wpm, accuracy, time_taken, test_type="test"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO results (name, wpm, accuracy, time_taken, test_type) VALUES (?, ?, ?, ?, ?)",
                    (name, float(wpm), float(accuracy), float(time_taken), test_type))
        conn.commit()
        conn.close()

    def get_history(self, limit=5, name=None, test_type=None):
        """Return recent results. If name is provided, filter results to that user only."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        query = "SELECT name, wpm, accuracy, time_taken, created_at, test_type FROM results"
        params = []
        
        conditions = []
        if name:
            conditions.append("name = ?")
            params.append(name)
        if test_type and test_type != 'all':
            conditions.append("test_type = ?")
            params.append(test_type)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()
        return rows

    # --- Sentence helpers ---
    def load_sentences(self):
        p = Path(self.sentence_file)
        if not p.exists():
            return ["The quick brown fox jumps over the lazy dog."]
        lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return lines if lines else ["The quick brown fox jumps over the lazy dog."]

    def load_practice_words(self):
        p = Path(PRACTICE_WORDS_FILE)
        if not p.exists():
            return [
                "the", "and", "for", "are", "with", "you", "this", "that", "have", "will",
                "from", "they", "been", "their", "said", "each", "which", "would", "there", "could"
            ]
        tokens = []
        for ln in p.read_text(encoding="utf-8").splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith("//"):
                continue
            parts = s.split()
            for w in parts:
                if w:
                    tokens.append(w)
        return tokens if tokens else ["the", "and", "for", "are", "with"]

    def pick_audio_text(self, mode="sentence"):
        """Pick text based on mode (word or sentence)"""
        self.audio_mode = mode
        if mode == "word":
            words = self.load_practice_words()
            self.current_audio_text = random.choice(words)
        else:  # sentence mode
            sentences = self.load_sentences()
            self.current_audio_text = random.choice(sentences)
        return self.current_audio_text

    def pick_sentence(self):
        sentences = self.load_sentences()
        self.current_sentence = random.choice(sentences)
        return self.current_sentence

    # --- Timer & calculation ---
    def start_timer(self):
        self.start_time = time.time()

    def init_tts_engine(self):
        if self.tts_engine is None:
            self.tts_engine = pyttsx3.init(driverName='sapi5') if sys.platform.startswith('win') else pyttsx3.init()
            try:
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    self.tts_engine.setProperty('voice', voices[0].id)
            except Exception:
                pass
            try:
                self.tts_engine.setProperty('rate', int(self._desired_rate))
            except Exception:
                pass
        return self.tts_engine

    def speak(self, text):
        try:
            if sys.platform.startswith('win'):
                try:
                    ctypes.windll.ole32.CoInitializeEx(None, 2)
                except Exception:
                    pass
            engine = pyttsx3.init(driverName='sapi5') if sys.platform.startswith('win') else pyttsx3.init()
            try:
                voices = engine.getProperty('voices')
                if voices:
                    engine.setProperty('voice', voices[0].id)
            except Exception:
                pass
            try:
                engine.setProperty('rate', int(self._desired_rate))
            except Exception:
                pass
            try:
                engine.setProperty('volume', 1.0)
            except Exception:
                pass
            self.set_speaking_state(True)
            engine.say(text)
            engine.runAndWait()
            self.set_speaking_state(False)
            return True
        except Exception as e:
            print(f"TTS Error: {e}")
            self.set_speaking_state(False)
            return False
        finally:
            if sys.platform.startswith('win'):
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass

    def stop_speaking(self):
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception:
                pass
        self.set_speaking_state(False)

    def is_speaking(self):
        """Check if TTS engine is currently speaking"""
        if self.tts_engine:
            try:
                # This is a simple check - pyttsx3 doesn't have a direct is_speaking method
                # We'll track speaking state manually
                return getattr(self, '_is_speaking', False)
            except:
                return False
        return False

    def set_speaking_state(self, speaking):
        """Set the speaking state manually"""
        self._is_speaking = speaking

    def set_audio_speed(self, speed):
        """Set TTS engine speed (words per minute)"""
        try:
            speed = max(50, min(300, int(speed)))
            self._desired_rate = speed
            if self.tts_engine:
                self.tts_engine.setProperty('rate', speed)
            return True
        except Exception as e:
            print(f"Error setting audio speed: {e}")
            return False

    def get_audio_speed(self):
        """Get current TTS engine speed"""
        if self.tts_engine:
            try:
                return self.tts_engine.getProperty('rate')
            except:
                return int(self._desired_rate)
        return int(self._desired_rate)

    def calculate(self, typed_text):
        if not self.start_time:
            raise RuntimeError("Timer not started")
        end = time.time()
        time_taken = end - self.start_time
        time_taken = max(time_taken, 0.001)
        words = len(typed_text.split())
        wpm = (words / time_taken) * 60.0
        # accuracy by characters (compare char by char)
        total_chars = len(self.current_sentence) if self.current_sentence else 1
        correct = sum(1 for a, b in zip(typed_text, self.current_sentence) if a == b)
        accuracy = (correct / total_chars) * 100.0
        # reset timer for next test
        self.start_time = None
        return round(wpm, 2), round(accuracy, 2), round(time_taken, 2)

    def add_to_seen(self, text: str):
        self.seen_audio_items.append(text)

    def add_to_skipped(self, text: str):
        self.skipped_audio_items.append(text)

    def add_to_wrong(self, text: str):
        self.wrong_audio_items.append(text)
