from flask import Flask, render_template, redirect, url_for
from database import query, execute #za branje in pisanje baze

app = Flask(__name__)

@app.route('/')
def index():
    """Prikaže seznam vseh kmetij."""
    kmetije = query("SELECT * FROM Kmetija")
    return render_template('index.html', kmetije=kmetije)

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

@app.route('/add_to_cart/<int:id_izdelka>')
def add_to_cart(id_izdelka):
    """Doda izdelek v kosarico"""
    trenutni_uporabnik_id = 2
    izdelki = query("""
        SELECT cena
        FROM Izdelek
        WHERE id = ?
    """, (id_izdelka,))
    cena_izdelka = izdelki[0]['cena']
    return render_template('products.html', izdelki=izdelki, id=id_izdelka)

if __name__ == '__main__':
    app.run(debug=True)
