import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'farm.db')

def get_connection():
    """Vzpostavi povezavo z SQLite bazo."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Omogoča dostop do podatkov po imenih stolpcev
    conn.execute("PRAGMA foreign_keys = ON")   
    return conn

def query(sql, params=()):
    """Izvede SQL SELECT poizvedbo in vrne rezultate."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        result = cursor.fetchall()
        return result
    finally:
        conn.close()

def execute(sql, params=()):
    """Izvede SQL ukaz (INSERT, UPDATE, DELETE) in potrdi spremembe."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
