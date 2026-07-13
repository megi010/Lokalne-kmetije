"""Sloj za dostop do podatkovne baze (nizkonivojske funkcije).

Modul ne pozna poslovne logike - ta je v `model.py`. Tu so samo
povezava, izvajanje poizvedb in transakcije.
"""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'farm.db')


def get_connection():
    """Vzpostavi povezavo z bazo in vklopi preverjanje tujih ključev."""
    conn = sqlite3.connect(DB_PATH)
    # Omogoča dostop do stolpcev po imenu (vrstica se obnaša kot slovar).
    conn.row_factory = sqlite3.Row
    # SQLite tujih ključev privzeto NE preverja - vklopiti jih moramo ročno.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=()):
    """Izvede SELECT in vrne seznam vrstic."""
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def query_one(sql, params=()):
    """Izvede SELECT in vrne prvo vrstico ali None."""
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def execute(sql, params=()):
    """Izvede INSERT/UPDATE/DELETE, potrdi spremembo in vrne id vnosa."""
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


@contextmanager
def transaction():
    """Kontekstni upravitelj za transakcijo.

    Vse spremembe znotraj bloka se potrdijo (COMMIT) samo, če se blok
    izteče brez napake. Ob kakršni koli izjemi se izvede ROLLBACK, zato
    baza nikoli ne ostane v vmesnem, nekonsistentnem stanju.

    Uporaba:
        with transaction() as conn:
            conn.execute("UPDATE Izdelek SET zaloga = zaloga - ? WHERE id = ?", ...)
            conn.execute("UPDATE Narocilo SET status = 'oddano' WHERE id = ?", ...)
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
