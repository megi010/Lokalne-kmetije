"""Model: vsa poslovna logika in vse SQL poizvedbe aplikacije.

To je edini modul, ki vsebuje SQL. Spletni vmesnik (`web.py`) in tekstovni
vmesnik (`cli.py`) sta samo krmilnika (controller) - kličeta funkcije od tu
in prikažeta rezultat.

Vse funkcije, ki spreminjajo bazo, vrnejo par `(uspeh, sporocilo)`, da lahko
oba vmesnika napake obravnavata enako.
"""

import re

from werkzeug.security import check_password_hash, generate_password_hash

from database import execute, query, query_one, transaction

# Statusi naročila (uporabljeni tudi v CHECK omejitvi v schema.sql).
STATUS_KOSARICA = 'kosarica'
STATUS_ODDANO = 'oddano'
STATUS_ZAKLJUCENO = 'zakljuceno'
STATUS_PREKLICANO = 'preklicano'

STATUS_OPIS = {
    STATUS_KOSARICA: 'V košarici',
    STATUS_ODDANO: 'Oddano',
    STATUS_ZAKLJUCENO: 'Zaključeno',
    STATUS_PREKLICANO: 'Preklicano',
}

TIP_KUPEC = 'kupec'
TIP_LASTNIK = 'lastnik kmetije'
TIP_ADMIN = 'admin'
TIPI_UPORABNIKA = (TIP_KUPEC, TIP_LASTNIK, TIP_ADMIN)

# Vrste izdelkov, ki jih ponudi spustni meni v obrazcih.
VRSTE_IZDELKOV = (
    'med', 'sadje', 'zelenjava', 'mlečni izdelki', 'jajca',
    'mesni izdelki', 'pijača', 'ostalo',
)

# Telefonska številka: natanko 9 števk (enako preverja CHECK v schema.sql).
_TELEFON_VZOREC = re.compile(r'^\d{9}$')


# =====================================================================
# UPORABNIKI (INSERT, SELECT, UPDATE, DELETE + zgoščena gesla)
# =====================================================================

def vsi_uporabniki():
    """Vsi uporabniki s številom kmetij in naročil (LEFT JOIN + COUNT)."""
    return query("""
        SELECT u.id,
               u.ime,
               u.email,
               u.tip,
               COUNT(DISTINCT k.id) AS st_kmetij,
               COUNT(DISTINCT n.id) AS st_narocil
        FROM Uporabnik u
        LEFT JOIN Kmetija k ON k.id_uporabnika = u.id
        LEFT JOIN Narocilo n ON n.id_uporabnika = u.id
                            AND n.status <> 'kosarica'
        GROUP BY u.id
        ORDER BY u.id
    """)


def uporabnik_po_id(id_uporabnika):
    return query_one(
        "SELECT id, ime, email, tip FROM Uporabnik WHERE id = ?",
        (id_uporabnika,)
    )


def uporabnik_po_emailu(email):
    return query_one("SELECT * FROM Uporabnik WHERE email = ?", (email,))


def _preveri_email(email):
    """Groba oblikovna kontrola e-poštnega naslova."""
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email or ''))


def registriraj_uporabnika(ime, email, geslo, tip):
    """INSERT novega uporabnika z zgoščenim geslom."""
    ime = (ime or '').strip()
    email = (email or '').strip().lower()

    if not ime or not email or not geslo:
        return False, "Ime, e-pošta in geslo so obvezni."
    if not _preveri_email(email):
        return False, "E-poštni naslov ni veljaven."
    if len(geslo) < 4:
        return False, "Geslo mora imeti vsaj 4 znake."
    if tip not in TIPI_UPORABNIKA:
        return False, f"Tip mora biti eden od: {', '.join(TIPI_UPORABNIKA)}."
    if uporabnik_po_emailu(email):
        return False, "Uporabnik s to e-pošto že obstaja."

    execute(
        "INSERT INTO Uporabnik (ime, email, geslo, tip) VALUES (?, ?, ?, ?)",
        (ime, email, generate_password_hash(geslo), tip)
    )
    return True, f"Uporabnik {ime} je bil uspešno dodan."


def preveri_prijavo(email, geslo):
    """Preveri e-pošto in geslo. Vrne vrstico uporabnika ali None."""
    uporabnik = uporabnik_po_emailu((email or '').strip().lower())
    if uporabnik and check_password_hash(uporabnik['geslo'], geslo or ''):
        return uporabnik
    return None


def posodobi_profil(id_uporabnika, ime, email):
    """UPDATE imena in e-pošte prijavljenega uporabnika."""
    ime = (ime or '').strip()
    email = (email or '').strip().lower()

    if not ime or not email:
        return False, "Ime in e-pošta sta obvezna."
    if not _preveri_email(email):
        return False, "E-poštni naslov ni veljaven."

    zaseden = uporabnik_po_emailu(email)
    if zaseden and zaseden['id'] != id_uporabnika:
        return False, "To e-pošto že uporablja drug uporabnik."

    execute(
        "UPDATE Uporabnik SET ime = ?, email = ? WHERE id = ?",
        (ime, email, id_uporabnika)
    )
    return True, "Profil je posodobljen."


def spremeni_geslo(id_uporabnika, staro_geslo, novo_geslo, ponovitev):
    """UPDATE gesla (v bazo se shrani zgoščeno)."""
    uporabnik = query_one(
        "SELECT * FROM Uporabnik WHERE id = ?", (id_uporabnika,)
    )
    if uporabnik is None:
        return False, "Uporabnik ne obstaja."
    if not check_password_hash(uporabnik['geslo'], staro_geslo or ''):
        return False, "Staro geslo ni pravilno."
    if len(novo_geslo or '') < 4:
        return False, "Novo geslo mora imeti vsaj 4 znake."
    if novo_geslo != ponovitev:
        return False, "Novi gesli se ne ujemata."

    execute(
        "UPDATE Uporabnik SET geslo = ? WHERE id = ?",
        (generate_password_hash(novo_geslo), id_uporabnika)
    )
    return True, "Geslo je spremenjeno."


def spremeni_tip_uporabnika(id_uporabnika, tip):
    """UPDATE tipa uporabnika (na voljo samo administratorju)."""
    if tip not in TIPI_UPORABNIKA:
        return False, "Neveljaven tip uporabnika."
    if uporabnik_po_id(id_uporabnika) is None:
        return False, "Uporabnik ne obstaja."

    execute("UPDATE Uporabnik SET tip = ? WHERE id = ?", (tip, id_uporabnika))
    return True, "Tip uporabnika je spremenjen."


def izbrisi_uporabnika(id_uporabnika):
    """DELETE uporabnika.

    Tuja ključa z ON DELETE RESTRICT preprečita brisanje uporabnika, ki ima
    kmetijo ali naročilo. Namesto da bi pustili SQLite vreči izjemo, razlog
    razložimo vnaprej.
    """
    if uporabnik_po_id(id_uporabnika) is None:
        return False, "Uporabnik ne obstaja."

    kmetij = query_one(
        "SELECT COUNT(*) AS st FROM Kmetija WHERE id_uporabnika = ?",
        (id_uporabnika,)
    )['st']
    if kmetij:
        return False, (f"Uporabnika ni mogoče izbrisati: je lastnik {kmetij} "
                       "kmetij(e). Najprej izbriši ali prenesi kmetije.")

    narocil = query_one(
        "SELECT COUNT(*) AS st FROM Narocilo WHERE id_uporabnika = ?",
        (id_uporabnika,)
    )['st']
    if narocil:
        return False, ("Uporabnika ni mogoče izbrisati, ker ima zgodovino "
                       "naročil, ki je kmetije ne smejo izgubiti.")

    execute("DELETE FROM Uporabnik WHERE id = ?", (id_uporabnika,))
    return True, "Uporabnik je izbrisan."


# =====================================================================
# KMETIJE (INSERT, SELECT, UPDATE, DELETE, JOIN, GROUP BY)
# =====================================================================

_KMETIJE_SELECT = """
    SELECT k.*,
           u.ime AS lastnik,
           COUNT(i.id) AS st_izdelkov
    FROM Kmetija k
    JOIN Uporabnik u ON u.id = k.id_uporabnika
    LEFT JOIN Izdelek i ON i.id_kmetije = k.id
"""


def vse_kmetije():
    """Kmetije z imenom lastnika in številom izdelkov (JOIN + GROUP BY)."""
    return query(_KMETIJE_SELECT + " GROUP BY k.id ORDER BY k.ime_kmetije")


def kmetije_omejeno(stevilo):
    return query(
        _KMETIJE_SELECT + " GROUP BY k.id ORDER BY k.id DESC LIMIT ?",
        (stevilo,)
    )


def kmetija_po_id(id_kmetije):
    return query_one(
        _KMETIJE_SELECT + " WHERE k.id = ? GROUP BY k.id", (id_kmetije,)
    )


def kmetije_uporabnika(id_uporabnika):
    """Kmetije, ki jih upravlja dani lastnik."""
    return query(
        _KMETIJE_SELECT + " WHERE k.id_uporabnika = ? GROUP BY k.id "
                          "ORDER BY k.ime_kmetije",
        (id_uporabnika,)
    )


def je_lastnik_kmetije(id_kmetije, id_uporabnika):
    """True, če dani uporabnik upravlja to kmetijo."""
    return query_one(
        "SELECT 1 FROM Kmetija WHERE id = ? AND id_uporabnika = ?",
        (id_kmetije, id_uporabnika)
    ) is not None


def _preveri_kmetijo(ime_kmetije, telefon, spletna_stran):
    """Skupno preverjanje vnosa za INSERT in UPDATE kmetije."""
    if not (ime_kmetije or '').strip():
        return False, "Ime kmetije je obvezno."

    if telefon and not _TELEFON_VZOREC.match(telefon):
        return False, ("Telefonska številka mora imeti natanko 9 števk "
                       "(npr. 041123456).")

    if spletna_stran and not spletna_stran.startswith(('http://', 'https://')):
        return False, "Spletna stran se mora začeti s http:// ali https://."

    return True, ""


def _ocisti_telefon(telefon):
    """Odstrani presledke in vezaje, da uporabnik lahko piše '041 123 456'."""
    return (telefon or '').replace(' ', '').replace('-', '').replace('/', '').strip()


def dodaj_kmetijo(id_uporabnika, ime_kmetije, vrsta_kmetije, delovni_cas,
                  kraj, regija, telefon, spletna_stran):
    """INSERT nove kmetije; lastnik je uporabnik, ki jo dodaja."""
    telefon = _ocisti_telefon(telefon)
    spletna_stran = (spletna_stran or '').strip()

    veljavno, napaka = _preveri_kmetijo(ime_kmetije, telefon, spletna_stran)
    if not veljavno:
        return False, napaka

    id_kmetije = execute("""
        INSERT INTO Kmetija (ime_kmetije, vrsta_kmetije, delovni_cas, kraj,
                             regija, telefonska_stevilka, spletna_stran,
                             id_uporabnika)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ime_kmetije.strip(), (vrsta_kmetije or '').strip(),
          (delovni_cas or '').strip(), (kraj or '').strip(),
          (regija or '').strip(), telefon or None, spletna_stran or None,
          id_uporabnika))

    return True, f"Kmetija {ime_kmetije.strip()} je dodana (ID {id_kmetije})."


def posodobi_kmetijo(id_kmetije, ime_kmetije, vrsta_kmetije, delovni_cas,
                     kraj, regija, telefon, spletna_stran):
    """UPDATE podatkov kmetije."""
    if kmetija_po_id(id_kmetije) is None:
        return False, "Kmetija ne obstaja."

    telefon = _ocisti_telefon(telefon)
    spletna_stran = (spletna_stran or '').strip()

    veljavno, napaka = _preveri_kmetijo(ime_kmetije, telefon, spletna_stran)
    if not veljavno:
        return False, napaka

    execute("""
        UPDATE Kmetija
        SET ime_kmetije = ?, vrsta_kmetije = ?, delovni_cas = ?, kraj = ?,
            regija = ?, telefonska_stevilka = ?, spletna_stran = ?
        WHERE id = ?
    """, (ime_kmetije.strip(), (vrsta_kmetije or '').strip(),
          (delovni_cas or '').strip(), (kraj or '').strip(),
          (regija or '').strip(), telefon or None, spletna_stran or None,
          id_kmetije))

    return True, "Podatki kmetije so posodobljeni."


def izbrisi_kmetijo(id_kmetije):
    """DELETE kmetije.

    Izdelki kmetije se izbrišejo skupaj z njo (ON DELETE CASCADE), zato
    brisanje zavrnemo, če je bil kateri koli izdelek že naročen - s tem bi
    izgubili zgodovino nakupov.
    """
    kmetija = kmetija_po_id(id_kmetije)
    if kmetija is None:
        return False, "Kmetija ne obstaja."

    naroceno = query_one("""
        SELECT COUNT(*) AS st
        FROM Postavka_narocila pn
        JOIN Izdelek i ON i.id = pn.id_izdelka
        WHERE i.id_kmetije = ?
    """, (id_kmetije,))['st']
    if naroceno:
        return False, ("Kmetije ni mogoče izbrisati, ker so bili njeni izdelki "
                       "že naročeni. Namesto tega izdelkom nastavi zalogo na 0.")

    execute("DELETE FROM Kmetija WHERE id = ?", (id_kmetije,))
    return True, f"Kmetija {kmetija['ime_kmetije']} je izbrisana."


def vse_regije():
    return [v['regija'] for v in query(
        "SELECT DISTINCT regija FROM Kmetija "
        "WHERE regija IS NOT NULL AND regija <> '' ORDER BY regija"
    )]


# =====================================================================
# IZDELKI (INSERT, SELECT, UPDATE, DELETE, JOIN, GROUP BY, AVG)
# =====================================================================

_IZDELKI_SELECT = """
    SELECT i.*,
           k.ime_kmetije,
           k.regija,
           k.id_uporabnika AS id_lastnika,
           ROUND(AVG(o.ocena), 1) AS povprecna_ocena,
           COUNT(o.id) AS st_ocen
    FROM Izdelek i
    JOIN Kmetija k ON k.id = i.id_kmetije
    LEFT JOIN Ocena o ON o.id_izdelka = i.id
"""


def vsi_izdelki():
    return query(_IZDELKI_SELECT + " GROUP BY i.id ORDER BY i.ime_izdelka")


def izdelki_omejeno(stevilo):
    return query(
        _IZDELKI_SELECT + " GROUP BY i.id ORDER BY i.id DESC LIMIT ?",
        (stevilo,)
    )


def izdelki_po_regiji(regija):
    return query(
        _IZDELKI_SELECT + " WHERE k.regija = ? GROUP BY i.id "
                          "ORDER BY i.ime_izdelka",
        (regija,)
    )


def izdelki_po_vrsti(vrsta):
    return query(
        _IZDELKI_SELECT + " WHERE i.vrsta LIKE ? GROUP BY i.id "
                          "ORDER BY i.ime_izdelka",
        (f"%{vrsta}%",)
    )


def izdelki_iskanje(niz):
    return query(
        _IZDELKI_SELECT + """
        WHERE i.ime_izdelka LIKE ? OR i.vrsta LIKE ? OR k.ime_kmetije LIKE ?
        GROUP BY i.id
        ORDER BY i.ime_izdelka
        """,
        (f"%{niz}%", f"%{niz}%", f"%{niz}%")
    )


def izdelek_po_id(id_izdelka):
    return query_one(
        _IZDELKI_SELECT + " WHERE i.id = ? GROUP BY i.id", (id_izdelka,)
    )


def izdelki_kmetije(id_kmetije):
    return query(
        _IZDELKI_SELECT + " WHERE k.id = ? GROUP BY i.id "
                          "ORDER BY i.ime_izdelka",
        (id_kmetije,)
    )


def je_lastnik_izdelka(id_izdelka, id_uporabnika):
    """True, če izdelek pripada kmetiji, ki jo upravlja dani uporabnik."""
    return query_one("""
        SELECT 1
        FROM Izdelek i
        JOIN Kmetija k ON k.id = i.id_kmetije
        WHERE i.id = ? AND k.id_uporabnika = ?
    """, (id_izdelka, id_uporabnika)) is not None


def _preveri_izdelek(ime_izdelka, cena, zaloga):
    """Skupno preverjanje vnosa za INSERT in UPDATE izdelka.

    Vrne (uspeh, sporocilo, cena, zaloga).
    """
    if not (ime_izdelka or '').strip():
        return False, "Ime izdelka je obvezno.", None, None

    try:
        cena = float(str(cena).replace(',', '.'))
        zaloga = int(zaloga)
    except (TypeError, ValueError):
        return False, "Cena mora biti število, zaloga pa celo število.", None, None

    if cena <= 0:
        return False, "Cena mora biti večja od 0.", None, None
    if zaloga < 0:
        return False, "Zaloga ne more biti negativna.", None, None

    return True, "", cena, zaloga


def dodaj_izdelek(id_kmetije, ime_izdelka, vrsta, kolicina, cena, zaloga):
    """INSERT novega izdelka na izbrano kmetijo."""
    if kmetija_po_id(id_kmetije) is None:
        return False, "Kmetija ne obstaja."

    veljavno, napaka, cena, zaloga = _preveri_izdelek(ime_izdelka, cena, zaloga)
    if not veljavno:
        return False, napaka

    id_izdelka = execute("""
        INSERT INTO Izdelek (ime_izdelka, vrsta, kolicina, cena, zaloga,
                             id_kmetije)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ime_izdelka.strip(), (vrsta or '').strip(),
          (kolicina or '').strip(), cena, zaloga, id_kmetije))

    return True, f"Izdelek {ime_izdelka.strip()} je dodan (ID {id_izdelka})."


def posodobi_izdelek(id_izdelka, ime_izdelka, vrsta, kolicina, cena, zaloga):
    """UPDATE vseh podatkov izdelka."""
    if izdelek_po_id(id_izdelka) is None:
        return False, "Izdelek s tem ID-jem ne obstaja."

    veljavno, napaka, cena, zaloga = _preveri_izdelek(ime_izdelka, cena, zaloga)
    if not veljavno:
        return False, napaka

    execute("""
        UPDATE Izdelek
        SET ime_izdelka = ?, vrsta = ?, kolicina = ?, cena = ?, zaloga = ?
        WHERE id = ?
    """, (ime_izdelka.strip(), (vrsta or '').strip(),
          (kolicina or '').strip(), cena, zaloga, id_izdelka))

    return True, "Izdelek je posodobljen."


def izbrisi_izdelek(id_izdelka):
    """DELETE izdelka.

    Zaradi ON DELETE RESTRICT na Postavka_narocila brisanje ne uspe, če je
    bil izdelek že kdaj naročen - zgodovine nakupov namreč ne smemo uničiti.
    """
    if izdelek_po_id(id_izdelka) is None:
        return False, "Izdelek s tem ID-jem ne obstaja."

    naroceno = query_one(
        "SELECT COUNT(*) AS st FROM Postavka_narocila WHERE id_izdelka = ?",
        (id_izdelka,)
    )['st']
    if naroceno:
        return False, ("Izdelka ni mogoče izbrisati, ker je vezan na obstoječa "
                       "naročila. Namesto brisanja mu nastavi zalogo na 0.")

    execute("DELETE FROM Izdelek WHERE id = ?", (id_izdelka,))
    return True, "Izdelek je izbrisan."


# =====================================================================
# KOŠARICA IN NAROČILA (INSERT, UPDATE, DELETE, transakcija)
# =====================================================================

def odprta_kosarica(id_uporabnika):
    """Vrne odprto naročilo (košarico) uporabnika ali None."""
    return query_one(
        "SELECT * FROM Narocilo WHERE id_uporabnika = ? AND status = ?",
        (id_uporabnika, STATUS_KOSARICA)
    )


def _ustvari_kosarico(id_uporabnika):
    return execute(
        "INSERT INTO Narocilo (id_uporabnika, status) VALUES (?, ?)",
        (id_uporabnika, STATUS_KOSARICA)
    )


def dodaj_v_kosarico(id_uporabnika, id_izdelka, kolicina=1):
    """Doda izdelek v košarico ali poveča količino obstoječe postavke."""
    try:
        kolicina = int(kolicina)
    except (TypeError, ValueError):
        return False, "Količina mora biti celo število."
    if kolicina < 1:
        return False, "Količina mora biti vsaj 1."

    izdelek = query_one("SELECT * FROM Izdelek WHERE id = ?", (id_izdelka,))
    if izdelek is None:
        return False, "Izdelek ne obstaja."

    kosarica = odprta_kosarica(id_uporabnika)
    id_narocila = kosarica['id'] if kosarica else _ustvari_kosarico(id_uporabnika)

    obstojeca = query_one(
        "SELECT * FROM Postavka_narocila WHERE id_narocila = ? AND id_izdelka = ?",
        (id_narocila, id_izdelka)
    )
    ze_v_kosarici = obstojeca['kolicina'] if obstojeca else 0

    if ze_v_kosarici + kolicina > izdelek['zaloga']:
        return False, (
            f"Na zalogi je le {izdelek['zaloga']} kosov izdelka "
            f"{izdelek['ime_izdelka']} (v košarici jih imaš že {ze_v_kosarici})."
        )

    if obstojeca:
        # UPDATE: izdelek je že v košarici, zato le povečamo količino.
        execute(
            "UPDATE Postavka_narocila SET kolicina = kolicina + ? WHERE id = ?",
            (kolicina, obstojeca['id'])
        )
    else:
        # INSERT: novo postavko shranimo skupaj s trenutno ceno izdelka.
        execute("""
            INSERT INTO Postavka_narocila
                (id_narocila, id_izdelka, kolicina, cena_ob_nakupu)
            VALUES (?, ?, ?, ?)
        """, (id_narocila, id_izdelka, kolicina, izdelek['cena']))

    return True, f"{izdelek['ime_izdelka']} je dodan v košarico."


def postavke_narocila(id_narocila):
    """Postavke naročila skupaj z izdelkom in kmetijo (JOIN)."""
    return query("""
        SELECT pn.id,
               pn.kolicina,
               pn.cena_ob_nakupu,
               pn.kolicina * pn.cena_ob_nakupu AS skupaj,
               i.id AS id_izdelka,
               i.ime_izdelka,
               i.vrsta,
               i.zaloga,
               k.ime_kmetije
        FROM Postavka_narocila pn
        JOIN Izdelek i ON i.id = pn.id_izdelka
        JOIN Kmetija k ON k.id = i.id_kmetije
        WHERE pn.id_narocila = ?
        ORDER BY pn.id
    """, (id_narocila,))


def vsebina_kosarice(id_uporabnika):
    """Vrne (postavke, skupna_cena) za odprto košarico uporabnika."""
    kosarica = odprta_kosarica(id_uporabnika)
    if not kosarica:
        return [], 0.0
    postavke = postavke_narocila(kosarica['id'])
    skupaj = sum(p['skupaj'] for p in postavke)
    return postavke, skupaj


def stevilo_v_kosarici(id_uporabnika):
    """Skupno število kosov v košarici (za značko v navigaciji)."""
    vrstica = query_one("""
        SELECT COALESCE(SUM(pn.kolicina), 0) AS kosov
        FROM Narocilo n
        LEFT JOIN Postavka_narocila pn ON pn.id_narocila = n.id
        WHERE n.id_uporabnika = ? AND n.status = ?
    """, (id_uporabnika, STATUS_KOSARICA))
    return vrstica['kosov'] if vrstica else 0


def _postavka_uporabnika(id_postavke, id_uporabnika):
    """Zaščita: postavka mora pripadati odprti košarici tega uporabnika."""
    return query_one("""
        SELECT pn.*, i.zaloga, i.ime_izdelka
        FROM Postavka_narocila pn
        JOIN Narocilo n ON n.id = pn.id_narocila
        JOIN Izdelek i ON i.id = pn.id_izdelka
        WHERE pn.id = ? AND n.id_uporabnika = ? AND n.status = ?
    """, (id_postavke, id_uporabnika, STATUS_KOSARICA))


def posodobi_kolicino(id_postavke, id_uporabnika, kolicina):
    """UPDATE količine postavke v košarici."""
    try:
        kolicina = int(kolicina)
    except (TypeError, ValueError):
        return False, "Količina mora biti celo število."

    postavka = _postavka_uporabnika(id_postavke, id_uporabnika)
    if postavka is None:
        return False, "Postavka ni v tvoji košarici."
    if kolicina < 1:
        return False, ("Količina mora biti vsaj 1. "
                       "Za odstranitev uporabi gumb Odstrani.")
    if kolicina > postavka['zaloga']:
        return False, f"Na zalogi je le {postavka['zaloga']} kosov."

    execute(
        "UPDATE Postavka_narocila SET kolicina = ? WHERE id = ?",
        (kolicina, id_postavke)
    )
    return True, "Količina je posodobljena."


def odstrani_iz_kosarice(id_postavke, id_uporabnika):
    """DELETE postavke iz košarice."""
    postavka = _postavka_uporabnika(id_postavke, id_uporabnika)
    if postavka is None:
        return False, "Postavka ni v tvoji košarici."

    execute("DELETE FROM Postavka_narocila WHERE id = ?", (id_postavke,))
    return True, f"{postavka['ime_izdelka']} je odstranjen iz košarice."


def oddaj_narocilo(id_uporabnika):
    """Odda naročilo v ENI TRANSAKCIJI.

    Koraki (vsi uspejo ali pa noben):
      1. ponovno preveri zalogo vsake postavke,
      2. zmanjša zalogo izdelkov (UPDATE),
      3. naročilu nastavi status 'oddano' in datum (UPDATE).

    Če katera koli postavka nima dovolj zaloge, se izvede ROLLBACK in
    zaloga nobenega izdelka se ne spremeni.
    """
    kosarica = odprta_kosarica(id_uporabnika)
    if not kosarica:
        return False, "Tvoja košarica je prazna."

    postavke = postavke_narocila(kosarica['id'])
    if not postavke:
        return False, "Tvoja košarica je prazna."

    try:
        with transaction() as conn:
            for p in postavke:
                trenutna = conn.execute(
                    "SELECT zaloga FROM Izdelek WHERE id = ?", (p['id_izdelka'],)
                ).fetchone()['zaloga']

                if p['kolicina'] > trenutna:
                    raise ValueError(
                        f"Izdelka {p['ime_izdelka']} je na zalogi le {trenutna} "
                        f"kosov, v košarici pa jih imaš {p['kolicina']}."
                    )

                conn.execute(
                    "UPDATE Izdelek SET zaloga = zaloga - ? WHERE id = ?",
                    (p['kolicina'], p['id_izdelka'])
                )

            conn.execute(
                "UPDATE Narocilo SET status = ?, datum = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (STATUS_ODDANO, kosarica['id'])
            )
    except ValueError as napaka:
        return False, str(napaka)

    return True, f"Naročilo #{kosarica['id']} je bilo uspešno oddano."


def narocila_uporabnika(id_uporabnika):
    """Zgodovina naročil kupca z zneskom (LEFT JOIN + GROUP BY + SUM)."""
    return query("""
        SELECT n.id,
               n.datum,
               n.status,
               COUNT(pn.id) AS st_postavk,
               COALESCE(SUM(pn.kolicina * pn.cena_ob_nakupu), 0) AS znesek
        FROM Narocilo n
        LEFT JOIN Postavka_narocila pn ON pn.id_narocila = n.id
        WHERE n.id_uporabnika = ? AND n.status <> ?
        GROUP BY n.id
        ORDER BY n.datum DESC, n.id DESC
    """, (id_uporabnika, STATUS_KOSARICA))


def preklici_narocilo(id_narocila, id_uporabnika):
    """UPDATE statusa v 'preklicano' in vračilo zaloge (transakcija)."""
    narocilo = query_one(
        "SELECT * FROM Narocilo WHERE id = ? AND id_uporabnika = ?",
        (id_narocila, id_uporabnika)
    )
    if narocilo is None:
        return False, "Naročilo ne obstaja."
    if narocilo['status'] != STATUS_ODDANO:
        return False, "Prekličeš lahko samo oddana naročila."

    with transaction() as conn:
        for p in postavke_narocila(id_narocila):
            conn.execute(
                "UPDATE Izdelek SET zaloga = zaloga + ? WHERE id = ?",
                (p['kolicina'], p['id_izdelka'])
            )
        conn.execute(
            "UPDATE Narocilo SET status = ? WHERE id = ?",
            (STATUS_PREKLICANO, id_narocila)
        )
    return True, f"Naročilo #{id_narocila} je preklicano, zaloga je vrnjena."


# =====================================================================
# NAROČILA Z VIDIKA LASTNIKA KMETIJE
# =====================================================================

def narocila_za_lastnika(id_uporabnika):
    """Naročila, ki vsebujejo izdelke s kmetij tega lastnika.

    Znesek je seštet samo po postavkah, ki pripadajo njegovim kmetijam
    (JOIN čez pet tabel + GROUP BY + SUM).
    """
    return query("""
        SELECT n.id,
               n.datum,
               n.status,
               u.ime AS kupec,
               COUNT(pn.id) AS st_postavk,
               ROUND(SUM(pn.kolicina * pn.cena_ob_nakupu), 2) AS znesek
        FROM Narocilo n
        JOIN Uporabnik u ON u.id = n.id_uporabnika
        JOIN Postavka_narocila pn ON pn.id_narocila = n.id
        JOIN Izdelek i ON i.id = pn.id_izdelka
        JOIN Kmetija k ON k.id = i.id_kmetije
        WHERE k.id_uporabnika = ? AND n.status <> ?
        GROUP BY n.id
        ORDER BY n.datum DESC, n.id DESC
    """, (id_uporabnika, STATUS_KOSARICA))


def postavke_narocila_lastnika(id_narocila, id_uporabnika):
    """Samo tiste postavke naročila, ki pripadajo kmetijam tega lastnika."""
    return query("""
        SELECT pn.kolicina,
               pn.cena_ob_nakupu,
               pn.kolicina * pn.cena_ob_nakupu AS skupaj,
               i.ime_izdelka,
               k.ime_kmetije
        FROM Postavka_narocila pn
        JOIN Izdelek i ON i.id = pn.id_izdelka
        JOIN Kmetija k ON k.id = i.id_kmetije
        WHERE pn.id_narocila = ? AND k.id_uporabnika = ?
        ORDER BY pn.id
    """, (id_narocila, id_uporabnika))


def zakljuci_narocilo(id_narocila, id_uporabnika):
    """UPDATE statusa v 'zakljuceno' - kupec je izdelke prevzel.

    Sme ga izvesti samo lastnik kmetije, katere izdelek je v naročilu.
    """
    narocilo = query_one("SELECT * FROM Narocilo WHERE id = ?", (id_narocila,))
    if narocilo is None:
        return False, "Naročilo ne obstaja."
    if narocilo['status'] != STATUS_ODDANO:
        return False, "Zaključiš lahko samo oddana naročila."
    if not postavke_narocila_lastnika(id_narocila, id_uporabnika):
        return False, "To naročilo ne vsebuje izdelkov s tvojih kmetij."

    execute(
        "UPDATE Narocilo SET status = ? WHERE id = ?",
        (STATUS_ZAKLJUCENO, id_narocila)
    )
    return True, f"Naročilo #{id_narocila} je zaključeno."


# =====================================================================
# OCENE (INSERT, UPDATE, DELETE, SELECT, AVG)
# =====================================================================

def ocene_izdelka(id_izdelka):
    return query("""
        SELECT o.id, o.ocena, o.komentar, o.datum, o.id_uporabnika, u.ime
        FROM Ocena o
        JOIN Uporabnik u ON u.id = o.id_uporabnika
        WHERE o.id_izdelka = ?
        ORDER BY o.datum DESC, o.id DESC
    """, (id_izdelka,))


def ocena_uporabnika(id_uporabnika, id_izdelka):
    """Obstoječa ocena tega uporabnika za ta izdelek (ali None)."""
    return query_one(
        "SELECT * FROM Ocena WHERE id_uporabnika = ? AND id_izdelka = ?",
        (id_uporabnika, id_izdelka)
    )


def dodaj_oceno(id_uporabnika, id_izdelka, ocena, komentar):
    """INSERT nove ocene oz. UPDATE obstoječe (UNIQUE uporabnik + izdelek)."""
    try:
        ocena = int(ocena)
    except (TypeError, ValueError):
        return False, "Ocena mora biti število med 1 in 5."
    if not 1 <= ocena <= 5:
        return False, "Ocena mora biti med 1 in 5."
    if izdelek_po_id(id_izdelka) is None:
        return False, "Izdelek ne obstaja."

    ze_ocenil = ocena_uporabnika(id_uporabnika, id_izdelka)
    if ze_ocenil:
        execute(
            "UPDATE Ocena SET ocena = ?, komentar = ?, "
            "datum = CURRENT_TIMESTAMP WHERE id = ?",
            (ocena, (komentar or '').strip(), ze_ocenil['id'])
        )
        return True, "Tvoja ocena je posodobljena."

    execute("""
        INSERT INTO Ocena (id_uporabnika, id_izdelka, ocena, komentar)
        VALUES (?, ?, ?, ?)
    """, (id_uporabnika, id_izdelka, ocena, (komentar or '').strip()))
    return True, "Hvala za oceno!"


def izbrisi_oceno(id_ocene, id_uporabnika=None, je_admin=False):
    """DELETE ocene. Uporabnik lahko izbriše svojo oceno, admin katero koli."""
    ocena = query_one("SELECT * FROM Ocena WHERE id = ?", (id_ocene,))
    if ocena is None:
        return False, "Ocena ne obstaja."
    if not je_admin and ocena['id_uporabnika'] != id_uporabnika:
        return False, "Brisati smeš samo svoje ocene."

    execute("DELETE FROM Ocena WHERE id = ?", (id_ocene,))
    return True, "Ocena je izbrisana."


# =====================================================================
# STATISTIKA (GROUP BY, agregacije, HAVING)
# =====================================================================

def statistika_osnovna():
    """Osnovni števci za začetno stran."""
    return {
        'kmetije': query_one("SELECT COUNT(*) AS st FROM Kmetija")['st'],
        'izdelki': query_one("SELECT COUNT(*) AS st FROM Izdelek")['st'],
        'uporabniki': query_one("SELECT COUNT(*) AS st FROM Uporabnik")['st'],
        'narocila': query_one(
            "SELECT COUNT(*) AS st FROM Narocilo WHERE status <> ?",
            (STATUS_KOSARICA,)
        )['st'],
    }


def statistika_top_izdelki(limit=5):
    """Najbolje prodajani izdelki (SUM + GROUP BY + ORDER BY)."""
    return query("""
        SELECT i.ime_izdelka,
               SUM(pn.kolicina) AS prodano,
               ROUND(SUM(pn.kolicina * pn.cena_ob_nakupu), 2) AS promet
        FROM Postavka_narocila pn
        JOIN Izdelek i ON i.id = pn.id_izdelka
        JOIN Narocilo n ON n.id = pn.id_narocila
        WHERE n.status IN (?, ?)
        GROUP BY i.id
        ORDER BY prodano DESC
        LIMIT ?
    """, (STATUS_ODDANO, STATUS_ZAKLJUCENO, limit))


def statistika_po_regijah():
    """Število izdelkov in povprečna cena po regijah (LEFT JOIN + GROUP BY)."""
    return query("""
        SELECT k.regija,
               COUNT(i.id) AS st_izdelkov,
               ROUND(AVG(i.cena), 2) AS povprecna_cena
        FROM Kmetija k
        LEFT JOIN Izdelek i ON i.id_kmetije = k.id
        GROUP BY k.regija
        ORDER BY st_izdelkov DESC
    """)


def statistika_ocene():
    """Povprečne ocene izdelkov (AVG + GROUP BY + HAVING)."""
    return query("""
        SELECT i.ime_izdelka,
               ROUND(AVG(o.ocena), 2) AS povprecna_ocena,
               COUNT(o.id) AS st_ocen
        FROM Izdelek i
        JOIN Ocena o ON o.id_izdelka = i.id
        GROUP BY i.id
        HAVING COUNT(o.id) > 0
        ORDER BY povprecna_ocena DESC
    """)


def statistika_promet_kmetij():
    """Promet po kmetijah (LEFT JOIN čez štiri tabele + SUM)."""
    return query("""
        SELECT k.ime_kmetije,
               k.regija,
               ROUND(COALESCE(SUM(pn.kolicina * pn.cena_ob_nakupu), 0), 2) AS promet
        FROM Kmetija k
        LEFT JOIN Izdelek i ON i.id_kmetije = k.id
        LEFT JOIN Postavka_narocila pn ON pn.id_izdelka = i.id
        LEFT JOIN Narocilo n ON n.id = pn.id_narocila
            AND n.status IN ('oddano', 'zakljuceno')
        GROUP BY k.id
        ORDER BY promet DESC
    """)
