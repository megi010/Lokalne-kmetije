"""Napolni bazo z začetnim stanjem iz CSV datotek v mapi `data/`.

Zagon:  python load_data.py   (po `python init_db.py`)

Gesla iz `users.csv` so v CSV zapisana v čistopisu (samo za testne podatke),
ob uvozu pa jih zgostimo (hash), tako da v bazi golega gesla nikoli ni.
"""

import csv
import os
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash

from database import get_connection

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _preberi_csv(ime_datoteke):
    """Vrne vrstice CSV datoteke kot seznam slovarjev."""
    pot = os.path.join(DATA_DIR, ime_datoteke)
    with open(pot, mode='r', encoding='utf-8-sig', newline='') as datoteka:
        return list(csv.DictReader(datoteka))


def _datum(niz):
    """Preveri, ali je datum v obliki YYYY-MM-DD, in ga vrne normaliziranega."""
    return datetime.strptime(niz.strip(), '%Y-%m-%d').strftime('%Y-%m-%d')


def nalozi_podatke():
    """Uvozi vse CSV datoteke v eni transakciji."""
    conn = get_connection()
    try:
        with conn:  # samodejni COMMIT ob uspehu oz. ROLLBACK ob napaki
            for v in _preberi_csv('users.csv'):
                conn.execute(
                    "INSERT INTO Uporabnik (id, ime, email, geslo, tip) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (int(v['id']), v['ime'].strip(), v['email'].strip().lower(),
                     generate_password_hash(v['geslo'].strip()), v['tip'].strip())
                )
            print("Uporabniki so uvoženi (gesla so zgoščena).")

            for v in _preberi_csv('farms.csv'):
                conn.execute(
                    "INSERT INTO Kmetija (id, ime_kmetije, vrsta_kmetije, "
                    "delovni_cas, kraj, regija, telefonska_stevilka, "
                    "spletna_stran, id_uporabnika) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (int(v['id']), v['ime_kmetije'].strip(),
                     v['vrsta_kmetije'].strip(), v['delovni_cas'].strip(),
                     v['kraj'].strip(), v['regija'].strip(),
                     v['telefonska_stevilka'].strip(), v['spletna_stran'].strip(),
                     int(v['id_uporabnika']))
                )
            print("Kmetije so uvožene.")

            for v in _preberi_csv('products.csv'):
                conn.execute(
                    "INSERT INTO Izdelek (id, ime_izdelka, vrsta, kolicina, "
                    "cena, zaloga, id_kmetije) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (int(v['id']), v['ime_izdelka'].strip(), v['vrsta'].strip(),
                     v['kolicina'].strip(), float(v['cena']), int(v['zaloga']),
                     int(v['id_kmetije']))
                )
            print("Izdelki so uvoženi.")

            for v in _preberi_csv('orders.csv'):
                conn.execute(
                    "INSERT INTO Narocilo (id, id_uporabnika, datum, status) "
                    "VALUES (?, ?, ?, ?)",
                    (int(v['id']), int(v['id_uporabnika']),
                     _datum(v['datum']), v['status'].strip())
                )
            print("Naročila so uvožena.")

            for v in _preberi_csv('order_items.csv'):
                conn.execute(
                    "INSERT INTO Postavka_narocila (id, id_narocila, id_izdelka, "
                    "kolicina, cena_ob_nakupu) VALUES (?, ?, ?, ?, ?)",
                    (int(v['id']), int(v['id_narocila']), int(v['id_izdelka']),
                     int(v['kolicina']), float(v['cena_ob_nakupu']))
                )
            print("Postavke naročil so uvožene.")

            for v in _preberi_csv('reviews.csv'):
                conn.execute(
                    "INSERT INTO Ocena (id, id_uporabnika, id_izdelka, ocena, "
                    "komentar, datum) VALUES (?, ?, ?, ?, ?, ?)",
                    (int(v['id']), int(v['id_uporabnika']), int(v['id_izdelka']),
                     int(v['ocena']), v['komentar'].strip(), _datum(v['datum']))
                )
            print("Ocene so uvožene.")

        print("\nZačetno stanje baze je uspešno naloženo.")

    except sqlite3.IntegrityError as napaka:
        print(f"\nNapaka pri uvozu (kršena omejitev v bazi): {napaka}")
        print("Vsi vnosi so bili razveljavljeni (ROLLBACK).")
    except (ValueError, KeyError) as napaka:
        print(f"\nNapaka v CSV podatkih: {napaka}")
        print("Vsi vnosi so bili razveljavljeni (ROLLBACK).")
    finally:
        conn.close()


if __name__ == '__main__':
    nalozi_podatke()
