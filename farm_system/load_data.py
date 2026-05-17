import csv
import os
from database import execute
from datetime import datetime

def load_users_csv():
    """Uvozi uporabnike iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'users.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute(
                "INSERT INTO Uporabnik (id, ime, email, geslo, tip) VALUES (?, ?, ?, ?, ?)",
                (row['id'], row['ime'], row['email'], row['geslo'], row['tip'])
            )
    print("Users loaded")

def load_farms_csv():
    """Uvozi kmetije iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'farms.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute(
                "INSERT INTO Kmetija (id, ime_kmetije, vrsta_kmetije, delovni_cas, kraj, regija, telefonska_stevilka, spletna_stran, id_uporabnika) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row['id'], row['ime_kmetije'], row['vrsta_kmetije'], row['delovni_cas'], row['kraj'], row['regija'], row['telefonska_stevilka'], row['spletna_stran'], row['id_uporabnika'])
            )
    print("Farms loaded")

def load_products_csv():
    """Uvozi izdelke iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'products.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute(
                "INSERT INTO Izdelek (id, ime_izdelka, vrsta, kolicina, cena, zaloga, id_kmetije) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row['id'], row['ime_izdelka'], row['vrsta'], row['kolicina'], float(row['cena']), int(row['zaloga']), int(row['id_kmetije']))
            )
    print("Products loaded")

def load_orders_csv():
    """Uvozi naročila iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'orders.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            datum = datetime.strptime(row['datum'],'%Y-%m-%d').strftime('%Y-%m-%d')
            execute(
                "INSERT INTO Narocilo (id, id_uporabnika, datum, status) VALUES (?, ?, ?, ?)",
                (row['id'], row['id_uporabnika'], datum, row['status'])
            )
    print("Orders loaded")

def load_order_items_csv():
    """Uvozi postavke_naročil iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'order_items.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute(
                "INSERT INTO Postavka_narocila (id, id_narocila, id_izdelka, kolicina, cena_ob_nakupu) VALUES (?, ?, ?, ?, ?)",
                (row['id'], row['id_narocila'], row['id_izdelka'], row['kolicina'], float(row['cena_ob_nakupu']))
            )
    print("Order items loaded")

def load_reviews_csv():
    """Uvozi ocene iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'reviews.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            datum = datetime.strptime(row['datum'],'%Y-%m-%d').strftime('%Y-%m-%d')
            execute(
                "INSERT INTO Ocena (id, id_uporabnika, id_izdelka, ocena, komentar, datum) VALUES (?, ?, ?, ?, ?, ?)",
                (row['id'], row['id_uporabnika'], row['id_izdelka'], int(row['ocena']), row['komentar'], datum)
            )
    print("Reviews loaded")

if __name__ == "__main__":
    load_users_csv()
    load_farms_csv()
    load_products_csv()
    load_orders_csv()
    load_order_items_csv()
    load_reviews_csv()
