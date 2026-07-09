from flask import Flask, render_template, redirect, url_for
from database import query, execute #za branje in pisanje baze

app = Flask(__name__)

@app.route('/')
def index():
    # 1. Pridobimo samo 4 izdelke
    izdelki = query("""
        SELECT i.*, k.ime_kmetije 
        FROM Izdelek i 
        JOIN Kmetija k ON i.id_kmetije = k.id 
        LIMIT 4
    """)
    
    # 2. Pridobimo samo 3 kmetije
    kmetije = query("SELECT * FROM Kmetija LIMIT 3")
    
    # 3. Izračunamo statistiko (COUNT)
    st_kmetij = query("SELECT COUNT(id) AS stevilo FROM Kmetija")[0]['stevilo']
    st_izdelkov = query("SELECT COUNT(id) AS stevilo FROM Izdelek")[0]['stevilo']
    
    # Vse to pošljemo v index.html
    return render_template('index.html', 
                           izdelki=izdelki, 
                           kmetije=kmetije, 
                           st_kmetij=st_kmetij, 
                           st_izdelkov=st_izdelkov)

@app.route('/farms')
def farms():
    """Prikaže seznam vseh kmetij (alternativna pot)."""
    kmetije = query("SELECT * FROM Kmetija")
    return render_template('farms.html', kmetije=kmetije)

@app.route('/products')
def products():
    """Prikaže vse izdelke."""
    izdelki = query("""
        SELECT i.*, k.ime_kmetije 
        FROM Izdelek i 
        JOIN Kmetija k ON i.id_kmetije = k.id
    """)
    return render_template('products.html', izdelki=izdelki)

@app.route('/region/<ime_regije>')
def region(ime_regije):
    """Filtrira izdelke po regiji."""
    izdelki = query("""
        SELECT i.*, k.ime_kmetije, k.regija
        FROM Izdelek i
        JOIN Kmetija k ON i.id_kmetije = k.id
        WHERE k.regija = ?
    """, (ime_regije,))
    return render_template('products.html', izdelki=izdelki, regija=ime_regije)

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/add_to_cart/<int:id_izdelka>')
def add_to_cart(id_izdelka):
    trenutni_uporabnik_id = 2 
    # 1. KORAK: Pridobi ceno izdelka
    rezultat = query("SELECT cena FROM Izdelek WHERE id = ?", (id_izdelka,))
    cena_izdelka = rezultat[0]['cena']

    # 2. KORAK: Ali ima uporabnik že odprto košarico?
    odprto_narocilo = query("SELECT id FROM Narocilo WHERE status = 'v obdelavi' AND id_uporabnika = ?", (trenutni_uporabnik_id,))
    
    if odprto_narocilo: 
        id_narocila = odprto_narocilo[0]['id']
    else:
        id_narocila = execute("INSERT INTO Narocilo (id_uporabnika, status) VALUES (?, 'v obdelavi')", (trenutni_uporabnik_id,))

    execute("INSERT INTO Postavka_narocila (id_narocila, id_izdelka, kolicina, cena_ob_nakupu) VALUES (?, ?, 1, ?)", (id_narocila, id_izdelka, cena_izdelka))
    return redirect(url_for('products'))

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
