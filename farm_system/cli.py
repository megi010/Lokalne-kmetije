import sys
from database import query, execute

def izpis_kmetij():
    kmetije = query("SELECT * FROM Kmetija")
    print("\nSEZNAM KMETIJ:")
    for k in kmetije:
        print(f"ID: {k['id']} | Ime: {k['ime_kmetije']} | Kraj: {k['kraj']} | Regija: {k['regija']}")

def izpis_izdelkov():
    izdelki = query("SELECT * FROM Izdelek")
    print("\nSEZNAM IZDELKOV:")
    for i in izdelki:
        print(f"ID: {i['id']} | Ime: {i['ime_izdelka']} | Cena: {i['cena']}€ | Zaloga: {i['zaloga']}")

def iskanje_po_regiji():
    regija = input("Vnesite regijo: ")
    izdelki = query("""
        SELECT i.* FROM Izdelek i
        JOIN Kmetija k ON i.id_kmetije = k.id
        WHERE k.regija LIKE ?
    """, (f"%{regija}%",))
    print(f"\nIZDELKI V REGIJI {regija}:")
    for i in izdelki:
        print(f"{i['ime_izdelka']} ({i['vrsta']}) - {i['cena']}€")

def iskanje_po_vrsti():
    vrsta = input("Vnesite vrsto izdelka: ")
    izdelki = query("SELECT * FROM Izdelek WHERE vrsta LIKE ?", (f"%{vrsta}%",))
    print(f"\nIZDELKI VRSTE {vrsta}:")
    for i in izdelki:
        print(f"{i['ime_izdelka']} - {i['cena']}€")

def dodaj_uporabnika():
    ime = input("Ime: ")
    email = input("Email: ")
    geslo = input("Geslo: ")
    tip = input("Tip (kupec / lastnik kmetije / admin): ")
    try:
        execute("INSERT INTO Uporabnik (ime, email, geslo, tip) VALUES (?, ?, ?, ?)", (ime, email, geslo, tip))
        print("Uporabnik uspešno dodan.")
    except Exception as e:
        print(f"Napaka pri dodajanju: {e}")

def statistika():
    print("\nSTATISTIKA:")
    
    # Top 5 prodajanih izdelkov (glede na Postavka_narocila)
    top_prodajani = query("""
        SELECT i.ime_izdelka, SUM(pn.kolicina) as prodano
        FROM Postavka_narocila pn
        JOIN Izdelek i ON pn.id_izdelka = i.id
        GROUP BY i.id
        ORDER BY prodano DESC
        LIMIT 5
    """)
    print("\nTop 5 prodajanih izdelkov:")
    if not top_prodajani:
        print("Ni podatkov o prodaji.")
    for p in top_prodajani:
        print(f"{p['ime_izdelka']}: {p['prodano']} kosov")

    # Število izdelkov po regijah
    po_regijah = query("""
        SELECT k.regija, COUNT(i.id) as st_izdelkov
        FROM Kmetija k
        LEFT JOIN Izdelek i ON k.id = i.id_kmetije
        GROUP BY k.regija
    """)
    print("\nŠtevilo izdelkov po regijah:")
    for r in po_regijah:
        print(f"{r['regija']}: {r['st_izdelkov']}")

    # Povprečna ocena izdelka
    povprecne_ocene = query("""
        SELECT ime_izdelka, povprecna_ocena FROM Izdelek ORDER BY povprecna_ocena DESC
    """)
    print("\nPovprečne ocene izdelkov:")
    for o in povprecne_ocene:
        print(f"{o['ime_izdelka']}: {o['povprecna_ocena']}")

def main():
    while True:
        print("\n--- LOKALNE KMETIJE CLI ---")
        print("1 – Izpiši vse kmetije")
        print("2 – Izpiši vse izdelke")
        print("3 – Išči izdelke po regiji")
        print("4 – Išči izdelke po vrsti")
        print("5 – Dodaj uporabnika")
        print("6 – Statistika")
        print("0 – Exit")
        
        izbira = input("Izbira: ")
        
        if izbira == "1":
            izpis_kmetij()
        elif izbira == "2":
            izpis_izdelkov()
        elif izbira == "3":
            iskanje_po_regiji()
        elif izbira == "4":
            iskanje_po_vrsti()
        elif izbira == "5":
            dodaj_uporabnika()
        elif izbira == "6":
            statistika()
        elif izbira == "0":
            print("Nasvidenje!")
            sys.exit()
        else:
            print("Napačna izbira.")

if __name__ == "__main__":
    main()
