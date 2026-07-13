"""Kmetijski trg - spletni vmesnik (glavni program).

Krmilnik (controller): sprejme zahtevo, pokliče funkcijo iz `model.py` in
izriše predlogo. V tem modulu ni nobene SQL poizvedbe.

Vse spremembe baze gredo prek metode POST, ki ji sledi preusmeritev
(vzorec POST/Redirect/GET), da osvežitev strani ne ponovi transakcije.

Zagon:  python web.py   ->  http://127.0.0.1:5000
"""

from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)

import model

app = Flask(__name__)
# Ključ za podpisovanje sej (piškotkov). V pravi aplikaciji bi ga brali iz
# okoljske spremenljivke, za seminarsko nalogo zadošča konstanta.
app.secret_key = 'kmetijski-trg-skrivni-kljuc-2026'


# =====================================================================
# POMOŽNE FUNKCIJE IN DEKORATORJI
# =====================================================================

def prijavljen_uporabnik():
    """Vrne id prijavljenega uporabnika ali None."""
    return session.get('uporabnik_id')


def je_admin():
    return session.get('uporabnik_tip') == model.TIP_ADMIN


def je_lastnik():
    """Lastnik kmetije ali admin - oba lahko upravljata kmetije in izdelke."""
    return session.get('uporabnik_tip') in (model.TIP_LASTNIK, model.TIP_ADMIN)


def zahtevaj_prijavo(funkcija):
    """Dekorator: pot je dostopna samo prijavljenim uporabnikom."""
    @wraps(funkcija)
    def ovoj(*args, **kwargs):
        if not prijavljen_uporabnik():
            flash("Za ta korak se moraš najprej prijaviti.", "opozorilo")
            return redirect(url_for('prijava', naprej=request.path))
        return funkcija(*args, **kwargs)
    return ovoj


def zahtevaj_lastnika(funkcija):
    """Dekorator: pot je dostopna samo lastnikom kmetij in administratorjem."""
    @wraps(funkcija)
    def ovoj(*args, **kwargs):
        if not prijavljen_uporabnik():
            flash("Za ta korak se moraš najprej prijaviti.", "opozorilo")
            return redirect(url_for('prijava', naprej=request.path))
        if not je_lastnik():
            flash("Ta del je namenjen lastnikom kmetij.", "napaka")
            return redirect(url_for('domov'))
        return funkcija(*args, **kwargs)
    return ovoj


def zahtevaj_admina(funkcija):
    """Dekorator: pot je dostopna samo administratorju."""
    @wraps(funkcija)
    def ovoj(*args, **kwargs):
        if not je_admin():
            flash("Ta del je namenjen administratorju.", "napaka")
            return redirect(url_for('domov'))
        return funkcija(*args, **kwargs)
    return ovoj


def sme_do_kmetije(id_kmetije):
    """Kmetijo sme urejati njen lastnik ali administrator."""
    return je_admin() or model.je_lastnik_kmetije(id_kmetije,
                                                  prijavljen_uporabnik())


def sme_do_izdelka(id_izdelka):
    """Izdelek sme urejati lastnik pripadajoče kmetije ali administrator."""
    return je_admin() or model.je_lastnik_izdelka(id_izdelka,
                                                  prijavljen_uporabnik())


@app.context_processor
def skupne_spremenljivke():
    """Spremenljivke, ki so na voljo v vseh predlogah (npr. v navigaciji)."""
    id_uporabnika = prijavljen_uporabnik()
    return {
        'uporabnik_ime': session.get('uporabnik_ime'),
        'uporabnik_tip': session.get('uporabnik_tip'),
        'kosov_v_kosarici': (model.stevilo_v_kosarici(id_uporabnika)
                             if id_uporabnika else 0),
        'status_opis': model.STATUS_OPIS,
    }


# =====================================================================
# JAVNE STRANI (SELECT)
# =====================================================================

@app.route('/')
def domov():
    """Začetna stran: najnovejši izdelki, kmetije in osnovna statistika."""
    return render_template(
        'index.html',
        izdelki=model.izdelki_omejeno(4),
        kmetije=model.kmetije_omejeno(3),
        statistika=model.statistika_osnovna(),
    )


@app.route('/kmetije')
def kmetije():
    """Seznam vseh kmetij."""
    return render_template('farms.html', kmetije=model.vse_kmetije())


@app.route('/kmetija/<int:id_kmetije>')
def kmetija(id_kmetije):
    """Podrobnosti kmetije in vsi njeni izdelki."""
    podatki = model.kmetija_po_id(id_kmetije)
    if podatki is None:
        abort(404)

    return render_template(
        'farm.html',
        kmetija=podatki,
        izdelki=model.izdelki_kmetije(id_kmetije),
        sme_urejati=prijavljen_uporabnik() is not None
        and sme_do_kmetije(id_kmetije),
    )


@app.route('/izdelki')
def izdelki():
    """Vsi izdelki z iskanjem po imenu, vrsti ali kmetiji."""
    iskanje = (request.args.get('q') or '').strip()
    seznam = model.izdelki_iskanje(iskanje) if iskanje else model.vsi_izdelki()
    return render_template(
        'products.html',
        izdelki=seznam,
        iskanje=iskanje,
        regije=model.vse_regije(),
    )


@app.route('/regija/<ime_regije>')
def regija(ime_regije):
    """Izdelki, filtrirani po regiji kmetije."""
    return render_template(
        'products.html',
        izdelki=model.izdelki_po_regiji(ime_regije),
        regija=ime_regije,
        regije=model.vse_regije(),
    )


@app.route('/izdelek/<int:id_izdelka>')
def izdelek(id_izdelka):
    """Podrobnosti izdelka: kmetija, povprečna ocena in vse ocene."""
    podatki = model.izdelek_po_id(id_izdelka)
    if podatki is None:
        abort(404)

    id_uporabnika = prijavljen_uporabnik()
    return render_template(
        'product.html',
        izdelek=podatki,
        kmetija=model.kmetija_po_id(podatki['id_kmetije']),
        ocene=model.ocene_izdelka(id_izdelka),
        moja_ocena=(model.ocena_uporabnika(id_uporabnika, id_izdelka)
                    if id_uporabnika else None),
        sme_urejati=id_uporabnika is not None and sme_do_izdelka(id_izdelka),
    )


@app.route('/statistika')
def statistika():
    """Agregirani pregled tržnice (GROUP BY, SUM, AVG, HAVING)."""
    return render_template(
        'stats.html',
        osnovna=model.statistika_osnovna(),
        top_izdelki=model.statistika_top_izdelki(),
        po_regijah=model.statistika_po_regijah(),
        ocene=model.statistika_ocene(),
        promet=model.statistika_promet_kmetij(),
    )


# =====================================================================
# PRIJAVA, REGISTRACIJA, ODJAVA, PROFIL (seje + zgoščena gesla)
# =====================================================================

@app.route('/prijava', methods=['GET', 'POST'])
def prijava():
    if request.method == 'POST':
        uporabnik = model.preveri_prijavo(
            request.form.get('email'),
            request.form.get('geslo')
        )
        if uporabnik is None:
            flash("Napačna e-pošta ali geslo.", "napaka")
            return render_template('login.html'), 401

        session['uporabnik_id'] = uporabnik['id']
        session['uporabnik_ime'] = uporabnik['ime']
        session['uporabnik_tip'] = uporabnik['tip']
        flash(f"Pozdravljen(a), {uporabnik['ime']}!", "uspeh")

        naprej = request.args.get('naprej')
        return redirect(naprej if naprej and naprej.startswith('/')
                        else url_for('domov'))

    return render_template('login.html')


@app.route('/registracija', methods=['GET', 'POST'])
def registracija():
    if request.method == 'POST':
        uspeh, sporocilo = model.registriraj_uporabnika(
            request.form.get('ime'),
            request.form.get('email'),
            request.form.get('geslo'),
            request.form.get('tip', model.TIP_KUPEC),
        )
        flash(sporocilo, "uspeh" if uspeh else "napaka")
        if uspeh:
            return redirect(url_for('prijava'))

    return render_template('register.html')


@app.route('/odjava')
def odjava():
    session.clear()
    flash("Odjava je uspela. Se vidimo!", "uspeh")
    return redirect(url_for('domov'))


@app.route('/profil')
@zahtevaj_prijavo
def profil():
    """Pregled in urejanje lastnega uporabniškega računa."""
    return render_template(
        'profile.html',
        uporabnik=model.uporabnik_po_id(prijavljen_uporabnik()),
    )


@app.route('/profil/uredi', methods=['POST'])
@zahtevaj_prijavo
def uredi_profil():
    """UPDATE imena in e-pošte."""
    uspeh, sporocilo = model.posodobi_profil(
        prijavljen_uporabnik(),
        request.form.get('ime'),
        request.form.get('email'),
    )
    if uspeh:
        session['uporabnik_ime'] = request.form.get('ime', '').strip()
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('profil'))


@app.route('/profil/geslo', methods=['POST'])
@zahtevaj_prijavo
def zamenjaj_geslo():
    """UPDATE gesla (shrani se zgoščeno)."""
    uspeh, sporocilo = model.spremeni_geslo(
        prijavljen_uporabnik(),
        request.form.get('staro_geslo'),
        request.form.get('novo_geslo'),
        request.form.get('ponovitev'),
    )
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('profil'))


# =====================================================================
# KOŠARICA (INSERT, UPDATE, DELETE)
# =====================================================================

@app.route('/kosarica')
@zahtevaj_prijavo
def kosarica():
    postavke, skupna_cena = model.vsebina_kosarice(prijavljen_uporabnik())
    return render_template('cart.html', postavke=postavke,
                           skupna_cena=skupna_cena)


@app.route('/kosarica/dodaj/<int:id_izdelka>', methods=['POST'])
@zahtevaj_prijavo
def dodaj_v_kosarico(id_izdelka):
    uspeh, sporocilo = model.dodaj_v_kosarico(
        prijavljen_uporabnik(),
        id_izdelka,
        request.form.get('kolicina', 1),
    )
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    # Vrnemo se na stran, s katere je uporabnik prišel.
    nazaj = request.form.get('nazaj')
    return redirect(nazaj if nazaj and nazaj.startswith('/')
                    else url_for('izdelki'))


@app.route('/kosarica/posodobi/<int:id_postavke>', methods=['POST'])
@zahtevaj_prijavo
def posodobi_kosarico(id_postavke):
    uspeh, sporocilo = model.posodobi_kolicino(
        id_postavke,
        prijavljen_uporabnik(),
        request.form.get('kolicina'),
    )
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('kosarica'))


@app.route('/kosarica/odstrani/<int:id_postavke>', methods=['POST'])
@zahtevaj_prijavo
def odstrani_iz_kosarice(id_postavke):
    uspeh, sporocilo = model.odstrani_iz_kosarice(
        id_postavke, prijavljen_uporabnik()
    )
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('kosarica'))


@app.route('/kosarica/oddaj', methods=['POST'])
@zahtevaj_prijavo
def oddaj_narocilo():
    """Oddaja naročila: zaloga se zmanjša in status spremeni v eni transakciji."""
    uspeh, sporocilo = model.oddaj_narocilo(prijavljen_uporabnik())
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('moja_narocila') if uspeh else url_for('kosarica'))


# =====================================================================
# NAROČILA KUPCA
# =====================================================================

@app.route('/moja-narocila')
@zahtevaj_prijavo
def moja_narocila():
    narocila = model.narocila_uporabnika(prijavljen_uporabnik())
    postavke = {n['id']: model.postavke_narocila(n['id']) for n in narocila}
    return render_template('orders.html', narocila=narocila, postavke=postavke)


@app.route('/narocilo/<int:id_narocila>/preklici', methods=['POST'])
@zahtevaj_prijavo
def preklici_narocilo(id_narocila):
    uspeh, sporocilo = model.preklici_narocilo(id_narocila,
                                               prijavljen_uporabnik())
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('moja_narocila'))


# =====================================================================
# NADZORNA PLOŠČA LASTNIKA KMETIJE
# =====================================================================

@app.route('/moja-kmetija')
@zahtevaj_lastnika
def moja_kmetija():
    """Pregled lastnikovih kmetij, njihovih izdelkov in prejetih naročil."""
    id_uporabnika = prijavljen_uporabnik()
    kmetije_seznam = model.kmetije_uporabnika(id_uporabnika)
    izdelki_po_kmetiji = {
        k['id']: model.izdelki_kmetije(k['id']) for k in kmetije_seznam
    }
    narocila = model.narocila_za_lastnika(id_uporabnika)
    postavke = {
        n['id']: model.postavke_narocila_lastnika(n['id'], id_uporabnika)
        for n in narocila
    }

    return render_template(
        'dashboard.html',
        kmetije=kmetije_seznam,
        izdelki_po_kmetiji=izdelki_po_kmetiji,
        narocila=narocila,
        postavke=postavke,
    )


@app.route('/narocilo/<int:id_narocila>/zakljuci', methods=['POST'])
@zahtevaj_lastnika
def zakljuci_narocilo(id_narocila):
    """UPDATE statusa v 'zakljuceno' (kupec je izdelke prevzel)."""
    uspeh, sporocilo = model.zakljuci_narocilo(id_narocila,
                                               prijavljen_uporabnik())
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('moja_kmetija'))


# =====================================================================
# UPRAVLJANJE KMETIJ (INSERT, UPDATE, DELETE)
# =====================================================================

@app.route('/kmetija/nova', methods=['GET', 'POST'])
@zahtevaj_lastnika
def nova_kmetija():
    """INSERT nove kmetije."""
    if request.method == 'POST':
        uspeh, sporocilo = model.dodaj_kmetijo(
            prijavljen_uporabnik(),
            request.form.get('ime_kmetije'),
            request.form.get('vrsta_kmetije'),
            request.form.get('delovni_cas'),
            request.form.get('kraj'),
            request.form.get('regija'),
            request.form.get('telefonska_stevilka'),
            request.form.get('spletna_stran'),
        )
        flash(sporocilo, "uspeh" if uspeh else "napaka")
        if uspeh:
            return redirect(url_for('moja_kmetija'))
        # Ob napaki vrnemo obrazec z že vnesenimi podatki.
        return render_template('farm_form.html', kmetija=request.form,
                               naslov="Dodaj kmetijo")

    return render_template('farm_form.html', kmetija=None,
                           naslov="Dodaj kmetijo")


@app.route('/kmetija/<int:id_kmetije>/uredi', methods=['GET', 'POST'])
@zahtevaj_lastnika
def uredi_kmetijo(id_kmetije):
    """UPDATE podatkov kmetije (samo lastnik ali admin)."""
    podatki = model.kmetija_po_id(id_kmetije)
    if podatki is None:
        abort(404)
    if not sme_do_kmetije(id_kmetije):
        flash("Urejaš lahko samo svoje kmetije.", "napaka")
        return redirect(url_for('moja_kmetija'))

    if request.method == 'POST':
        uspeh, sporocilo = model.posodobi_kmetijo(
            id_kmetije,
            request.form.get('ime_kmetije'),
            request.form.get('vrsta_kmetije'),
            request.form.get('delovni_cas'),
            request.form.get('kraj'),
            request.form.get('regija'),
            request.form.get('telefonska_stevilka'),
            request.form.get('spletna_stran'),
        )
        flash(sporocilo, "uspeh" if uspeh else "napaka")
        if uspeh:
            return redirect(url_for('kmetija', id_kmetije=id_kmetije))
        return render_template('farm_form.html', kmetija=request.form,
                               naslov=f"Uredi: {podatki['ime_kmetije']}")

    return render_template('farm_form.html', kmetija=podatki,
                           naslov=f"Uredi: {podatki['ime_kmetije']}")


@app.route('/kmetija/<int:id_kmetije>/izbrisi', methods=['POST'])
@zahtevaj_lastnika
def izbrisi_kmetijo(id_kmetije):
    """DELETE kmetije (zavrnjeno, če so bili njeni izdelki že naročeni)."""
    if not sme_do_kmetije(id_kmetije):
        flash("Brisati smeš samo svoje kmetije.", "napaka")
        return redirect(url_for('moja_kmetija'))

    uspeh, sporocilo = model.izbrisi_kmetijo(id_kmetije)
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('moja_kmetija'))


# =====================================================================
# UPRAVLJANJE IZDELKOV (INSERT, UPDATE, DELETE)
# =====================================================================

@app.route('/kmetija/<int:id_kmetije>/izdelek/nov', methods=['GET', 'POST'])
@zahtevaj_lastnika
def nov_izdelek(id_kmetije):
    """INSERT novega izdelka na kmetijo prijavljenega lastnika."""
    podatki_kmetije = model.kmetija_po_id(id_kmetije)
    if podatki_kmetije is None:
        abort(404)
    if not sme_do_kmetije(id_kmetije):
        flash("Izdelke lahko dodajaš samo svojim kmetijam.", "napaka")
        return redirect(url_for('moja_kmetija'))

    if request.method == 'POST':
        uspeh, sporocilo = model.dodaj_izdelek(
            id_kmetije,
            request.form.get('ime_izdelka'),
            request.form.get('vrsta'),
            request.form.get('kolicina'),
            request.form.get('cena'),
            request.form.get('zaloga'),
        )
        flash(sporocilo, "uspeh" if uspeh else "napaka")
        if uspeh:
            return redirect(url_for('kmetija', id_kmetije=id_kmetije))
        return render_template('product_form.html', izdelek=request.form,
                               kmetija=podatki_kmetije,
                               vrste=model.VRSTE_IZDELKOV,
                               naslov="Dodaj izdelek")

    return render_template('product_form.html', izdelek=None,
                           kmetija=podatki_kmetije,
                           vrste=model.VRSTE_IZDELKOV,
                           naslov="Dodaj izdelek")


@app.route('/izdelek/<int:id_izdelka>/uredi', methods=['GET', 'POST'])
@zahtevaj_lastnika
def uredi_izdelek(id_izdelka):
    """UPDATE izdelka (ime, vrsta, pakiranje, cena, zaloga)."""
    podatki = model.izdelek_po_id(id_izdelka)
    if podatki is None:
        abort(404)
    if not sme_do_izdelka(id_izdelka):
        flash("Urejaš lahko samo izdelke svojih kmetij.", "napaka")
        return redirect(url_for('izdelek', id_izdelka=id_izdelka))

    podatki_kmetije = model.kmetija_po_id(podatki['id_kmetije'])

    if request.method == 'POST':
        uspeh, sporocilo = model.posodobi_izdelek(
            id_izdelka,
            request.form.get('ime_izdelka'),
            request.form.get('vrsta'),
            request.form.get('kolicina'),
            request.form.get('cena'),
            request.form.get('zaloga'),
        )
        flash(sporocilo, "uspeh" if uspeh else "napaka")
        if uspeh:
            return redirect(url_for('izdelek', id_izdelka=id_izdelka))
        return render_template('product_form.html', izdelek=request.form,
                               kmetija=podatki_kmetije,
                               vrste=model.VRSTE_IZDELKOV,
                               naslov=f"Uredi: {podatki['ime_izdelka']}")

    return render_template('product_form.html', izdelek=podatki,
                           kmetija=podatki_kmetije,
                           vrste=model.VRSTE_IZDELKOV,
                           naslov=f"Uredi: {podatki['ime_izdelka']}")


@app.route('/izdelek/<int:id_izdelka>/izbrisi', methods=['POST'])
@zahtevaj_lastnika
def izbrisi_izdelek(id_izdelka):
    """DELETE izdelka (zavrnjeno, če je bil izdelek že naročen)."""
    if not sme_do_izdelka(id_izdelka):
        flash("Brisati smeš samo izdelke svojih kmetij.", "napaka")
        return redirect(url_for('izdelek', id_izdelka=id_izdelka))

    uspeh, sporocilo = model.izbrisi_izdelek(id_izdelka)
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('izdelki') if uspeh
                    else url_for('izdelek', id_izdelka=id_izdelka))


# =====================================================================
# OCENE (INSERT, UPDATE, DELETE)
# =====================================================================

@app.route('/izdelek/<int:id_izdelka>/oceni', methods=['POST'])
@zahtevaj_prijavo
def oceni_izdelek(id_izdelka):
    uspeh, sporocilo = model.dodaj_oceno(
        prijavljen_uporabnik(),
        id_izdelka,
        request.form.get('ocena'),
        request.form.get('komentar'),
    )
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('izdelek', id_izdelka=id_izdelka))


@app.route('/ocena/<int:id_ocene>/izbrisi', methods=['POST'])
@zahtevaj_prijavo
def izbrisi_oceno(id_ocene):
    """DELETE svoje ocene (administrator lahko izbriše katero koli)."""
    uspeh, sporocilo = model.izbrisi_oceno(
        id_ocene, prijavljen_uporabnik(), je_admin()
    )
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    id_izdelka = request.form.get('id_izdelka')
    if id_izdelka and id_izdelka.isdigit():
        return redirect(url_for('izdelek', id_izdelka=int(id_izdelka)))
    return redirect(url_for('izdelki'))


# =====================================================================
# ADMINISTRACIJA UPORABNIKOV (SELECT, UPDATE, DELETE)
# =====================================================================

@app.route('/admin')
@zahtevaj_prijavo
@zahtevaj_admina
def admin():
    """Pregled vseh uporabnikov s številom kmetij in naročil."""
    return render_template(
        'admin.html',
        uporabniki=model.vsi_uporabniki(),
        tipi=model.TIPI_UPORABNIKA,
    )


@app.route('/admin/uporabnik/<int:id_uporabnika>/tip', methods=['POST'])
@zahtevaj_prijavo
@zahtevaj_admina
def spremeni_tip(id_uporabnika):
    """UPDATE tipa uporabnika."""
    uspeh, sporocilo = model.spremeni_tip_uporabnika(
        id_uporabnika, request.form.get('tip')
    )
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('admin'))


@app.route('/admin/uporabnik/<int:id_uporabnika>/izbrisi', methods=['POST'])
@zahtevaj_prijavo
@zahtevaj_admina
def izbrisi_uporabnika(id_uporabnika):
    """DELETE uporabnika (zavrnjeno, če ima kmetijo ali naročila)."""
    if id_uporabnika == prijavljen_uporabnik():
        flash("Lastnega računa ne moreš izbrisati.", "napaka")
        return redirect(url_for('admin'))

    uspeh, sporocilo = model.izbrisi_uporabnika(id_uporabnika)
    flash(sporocilo, "uspeh" if uspeh else "napaka")
    return redirect(url_for('admin'))


# =====================================================================
# NAPAKE
# =====================================================================

@app.errorhandler(404)
def stran_ne_obstaja(_napaka):
    return render_template('404.html'), 404


@app.errorhandler(500)
def napaka_streznika(_napaka):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
