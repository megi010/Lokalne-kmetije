"""Ustvari prazno bazo `farm.db` po shemi iz `schema.sql`.

Zagon:  python init_db.py
Opozorilo: skripta obstoječe tabele izbriše (DROP TABLE) in jih ustvari na novo.
"""

import os

from database import get_connection

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def init_db():
    """Prebere schema.sql in ga izvede nad bazo."""
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as datoteka:
        shema = datoteka.read()

    conn = get_connection()
    try:
        conn.executescript(shema)
        conn.commit()
        print("Baza je ustvarjena (tabele: Uporabnik, Kmetija, Izdelek, "
              "Narocilo, Postavka_narocila, Ocena).")
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
