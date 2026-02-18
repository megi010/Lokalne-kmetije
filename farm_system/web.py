from flask import Flask, render_template
from database import query

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

if __name__ == '__main__':
    app.run(debug=True)
