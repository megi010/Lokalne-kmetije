import csv
import os
from database import execute

def load_users_csv():
    """Uvozi uporabnike iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'users.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute(
                "INSERT INTO Uporabnik (ime, email, geslo, tip) VALUES (?, ?, ?, ?)",
                (row['ime'], row['email'], row['geslo'], row['tip'])
            )
    print("Users loaded")

def load_farms_csv():
    """Uvozi kmetije iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'farms.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute(
                "INSERT INTO Kmetija (ime_kmetije, vrsta_kmetije, kraj, regija, telefonska_stevilka, spletna_stran, id_uporabnika) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row['ime_kmetije'], row['vrsta_kmetije'], row['kraj'], row['regija'], row['telefonska_stevilka'], row['spletna_stran'], row['id_uporabnika'])
            )
    print("Farms loaded")

def load_products_csv():
    """Uvozi izdelke iz CSV datoteke."""
    path = os.path.join(os.path.dirname(__file__), 'data', 'products.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute(
                "INSERT INTO Izdelek (ime_izdelka, vrsta, kolicina, cena, zaloga, id_kmetije, povprecna_ocena) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row['ime_izdelka'], row['vrsta'], row['kolicina'], float(row['cena']), int(row['zaloga']), int(row['id_kmetije']), float(row['povprecna_ocena']))
            )
    print("Products loaded")

if __name__ == "__main__":
    load_users_csv()
    load_farms_csv()
    load_products_csv()
