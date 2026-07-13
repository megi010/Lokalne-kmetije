"""Kmetijski trg - tekstovni (CLI) vmesnik.

Krmilnik za ukazno vrstico: bere vnos uporabnika, kliče funkcije iz
`model.py` in izpiše rezultat. V tem modulu ni nobene SQL poizvedbe.

Zagon:  python cli.py
"""

import sys

import model


# =====================================================================
# POMOŽNE FUNKCIJE ZA VNOS
# =====================================================================

def vnos_besedila(poziv, obvezno=True, privzeto=None):
    """Prebere niz; če je obvezen, vztraja, dokler ni neprazen.

    Če je podana `privzeto` vrednost, prazen vnos pomeni "pusti, kot je".
    """
    while True:
        vrednost = input(poziv).strip()
        if not vrednost and privzeto is not None:
            return privzeto
        if vrednost or not obvezno:
            return vrednost
        print("  Vnos je obvezen.")


def vnos_stevila(poziv, celo=True, najmanj=None, privzeto=None):
    """Prebere število in preveri, da je res število (in dovolj veliko)."""
    while True:
        besedilo = input(poziv).strip().replace(',', '.')
        if not besedilo and privzeto is not None:
            return privzeto
        try:
            vrednost = int(besedilo) if celo else float(besedilo)
        except ValueError:
            print("  Vnesti moraš število.")
            continue
        if najmanj is not None and vrednost < najmanj:
            print(f"  Vrednost mora biti vsaj {najmanj}.")
            continue
        return vrednost


def vnos_izbire(poziv, moznosti, privzeto=None):
    """Prebere vrednost iz vnaprej danega seznama možnosti."""
    print(f"  Možnosti: {', '.join(moznosti)}")
    while True:
        vrednost = input(poziv).strip()
        if not vrednost and privzeto is not None:
            return privzeto
        if vrednost in moznosti:
            return vrednost
        print("  Izbrati moraš eno od naštetih možnosti.")


def potrdi(poziv):
    """Vrne True, če uporabnik vnese 'd' (da)."""
    return input(f"{poziv} (d/n): ").strip().lower() in ('d', 'da')


def izpisi_sporocilo(uspeh, sporocilo):
    print(f"  {'✓' if uspeh else '✗'} {sporocilo}")


# =====================================================================
# PRIKAZ PODATKOV (SELECT + JOIN)
# =====================================================================

def izpis_uporabnikov():
    print("\n--- SEZNAM UPORABNIKOV ---")
    for u in model.vsi_uporabniki():
        print(f"[{u['id']}] {u['ime']} <{u['email']}> | {u['tip']} "
              f"| kmetij: {u['st_kmetij']} | naročil: {u['st_narocil']}")


def izpis_kmetij():
    print("\n--- SEZNAM KMETIJ ---")
    for k in model.vse_kmetije():
        print(f"[{k['id']}] {k['ime_kmetije']} | {k['kraj']}, {k['regija']} "
              f"| lastnik: {k['lastnik']} | izdelkov: {k['st_izdelkov']}")


def izpis_izdelkov():
    print("\n--- SEZNAM IZDELKOV ---")
    for i in model.vsi_izdelki():
        ocena = (f"{i['povprecna_ocena']}/5" if i['povprecna_ocena']
                 else "brez ocen")
        print(f"[{i['id']}] {i['ime_izdelka']} ({i['vrsta']}, {i['kolicina']}) "
              f"| {i['cena']:.2f} € | zaloga: {i['zaloga']} "
              f"| {i['ime_kmetije']} | ocena: {ocena}")


def iskanje_po_regiji():
    regija = vnos_besedila("Vnesi regijo: ")
    izdelki = model.izdelki_po_regiji(regija)
    print(f"\n--- IZDELKI V REGIJI {regija.upper()} ---")
    if not izdelki:
        print("  V tej regiji ni izdelkov.")
        return
    for i in izdelki:
        print(f"[{i['id']}] {i['ime_izdelka']} - {i['cena']:.2f} € "
              f"({i['ime_kmetije']})")


def iskanje_po_vrsti():
    vrsta = vnos_besedila("Vnesi vrsto izdelka (npr. med, sadje): ")
    izdelki = model.izdelki_po_vrsti(vrsta)
    print(f"\n--- IZDELKI VRSTE '{vrsta}' ---")
    if not izdelki:
        print("  Ni zadetkov.")
        return
    for i in izdelki:
        print(f"[{i['id']}] {i['ime_izdelka']} - {i['cena']:.2f} € "
              f"| zaloga: {i['zaloga']}")


# =====================================================================
# UPORABNIKI (INSERT)
# =====================================================================

def dodaj_uporabnika():
    """INSERT novega uporabnika (geslo se shrani zgoščeno)."""
    print("\n--- DODAJ UPORABNIKA ---")
    ime = vnos_besedila("Ime in priimek: ")
    email = vnos_besedila("E-pošta: ")
    geslo = vnos_besedila("Geslo (vsaj 5 znakov): ")
    tip = vnos_izbire("Tip: ", model.TIPI_UPORABNIKA)

    uspeh, sporocilo = model.registriraj_uporabnika(ime, email, geslo, tip)
    izpisi_sporocilo(uspeh, sporocilo)


# =====================================================================
# KMETIJE (INSERT, UPDATE, DELETE)
# =====================================================================

def dodaj_kmetijo():
    """INSERT nove kmetije - vezana je na obstoječega uporabnika."""
    print("\n--- DODAJ KMETIJO ---")
    izpis_uporabnikov()

    id_uporabnika = vnos_stevila("\nID lastnika (uporabnika): ", najmanj=1)
    if model.uporabnik_po_id(id_uporabnika) is None:
        print("  ✗ Uporabnik s tem ID-jem ne obstaja.")
        return

    uspeh, sporocilo = model.dodaj_kmetijo(
        id_uporabnika,
        vnos_besedila("Ime kmetije: "),
        vnos_besedila("Vrsta kmetije (npr. čebelarstvo): ", obvezno=False),
        vnos_besedila("Delovni čas: ", obvezno=False),
        vnos_besedila("Kraj: ", obvezno=False),
        vnos_besedila("Regija: ", obvezno=False),
        vnos_besedila("Telefon (9 števk, lahko prazno): ", obvezno=False),
        vnos_besedila("Spletna stran (lahko prazno): ", obvezno=False),
    )
    izpisi_sporocilo(uspeh, sporocilo)


def uredi_kmetijo():
    """UPDATE podatkov kmetije. Prazen vnos pusti staro vrednost."""
    print("\n--- UREDI KMETIJO ---")
    izpis_kmetij()

    id_kmetije = vnos_stevila("\nID kmetije, ki jo urejaš: ", najmanj=1)
    kmetija = model.kmetija_po_id(id_kmetije)
    if kmetija is None:
        print("  ✗ Kmetija s tem ID-jem ne obstaja.")
        return

    print("  (Prazen vnos ohrani obstoječo vrednost.)")
    uspeh, sporocilo = model.posodobi_kmetijo(
        id_kmetije,
        vnos_besedila(f"Ime [{kmetija['ime_kmetije']}]: ",
                      privzeto=kmetija['ime_kmetije']),
        vnos_besedila(f"Vrsta [{kmetija['vrsta_kmetije']}]: ",
                      obvezno=False, privzeto=kmetija['vrsta_kmetije']),
        vnos_besedila(f"Delovni čas [{kmetija['delovni_cas']}]: ",
                      obvezno=False, privzeto=kmetija['delovni_cas']),
        vnos_besedila(f"Kraj [{kmetija['kraj']}]: ",
                      obvezno=False, privzeto=kmetija['kraj']),
        vnos_besedila(f"Regija [{kmetija['regija']}]: ",
                      obvezno=False, privzeto=kmetija['regija']),
        vnos_besedila(f"Telefon [{kmetija['telefonska_stevilka']}]: ",
                      obvezno=False, privzeto=kmetija['telefonska_stevilka']),
        vnos_besedila(f"Splet [{kmetija['spletna_stran']}]: ",
                      obvezno=False, privzeto=kmetija['spletna_stran']),
    )
    izpisi_sporocilo(uspeh, sporocilo)


def izbrisi_kmetijo():
    """DELETE kmetije (skupaj z njenimi izdelki, če še niso bili naročeni)."""
    print("\n--- IZBRIŠI KMETIJO ---")
    izpis_kmetij()

    id_kmetije = vnos_stevila("\nID kmetije za brisanje: ", najmanj=1)
    kmetija = model.kmetija_po_id(id_kmetije)
    if kmetija is None:
        print("  ✗ Kmetija s tem ID-jem ne obstaja.")
        return

    if not potrdi(f"Res želiš izbrisati '{kmetija['ime_kmetije']}'?"):
        print("  Brisanje je preklicano.")
        return

    uspeh, sporocilo = model.izbrisi_kmetijo(id_kmetije)
    izpisi_sporocilo(uspeh, sporocilo)


# =====================================================================
# IZDELKI (INSERT, UPDATE, DELETE)
# =====================================================================

def dodaj_izdelek():
    """INSERT novega izdelka na izbrano kmetijo."""
    print("\n--- DODAJ IZDELEK ---")
    izpis_kmetij()

    id_kmetije = vnos_stevila("\nID kmetije: ", najmanj=1)
    if model.kmetija_po_id(id_kmetije) is None:
        print("  ✗ Kmetija s tem ID-jem ne obstaja.")
        return

    uspeh, sporocilo = model.dodaj_izdelek(
        id_kmetije,
        vnos_besedila("Ime izdelka: "),
        vnos_izbire("Vrsta: ", model.VRSTE_IZDELKOV),
        vnos_besedila("Pakiranje (npr. 500 g): ", obvezno=False),
        vnos_stevila("Cena (€): ", celo=False, najmanj=0.01),
        vnos_stevila("Zaloga: ", najmanj=0),
    )
    izpisi_sporocilo(uspeh, sporocilo)


def uredi_izdelek():
    """UPDATE izdelka: ime, vrsta, pakiranje, cena in zaloga."""
    print("\n--- UREDI IZDELEK ---")
    izpis_izdelkov()

    id_izdelka = vnos_stevila("\nID izdelka, ki ga urejaš: ", najmanj=1)
    izdelek = model.izdelek_po_id(id_izdelka)
    if izdelek is None:
        print("  ✗ Izdelek s tem ID-jem ne obstaja.")
        return

    print(f"  Urejaš: {izdelek['ime_izdelka']} "
          f"({izdelek['cena']:.2f} €, zaloga {izdelek['zaloga']})")
    print("  (Prazen vnos ohrani obstoječo vrednost.)")

    uspeh, sporocilo = model.posodobi_izdelek(
        id_izdelka,
        vnos_besedila(f"Ime [{izdelek['ime_izdelka']}]: ",
                      privzeto=izdelek['ime_izdelka']),
        vnos_izbire(f"Vrsta [{izdelek['vrsta']}]: ",
                    model.VRSTE_IZDELKOV, privzeto=izdelek['vrsta']),
        vnos_besedila(f"Pakiranje [{izdelek['kolicina']}]: ",
                      obvezno=False, privzeto=izdelek['kolicina']),
        vnos_stevila(f"Cena [{izdelek['cena']:.2f}]: ", celo=False,
                     najmanj=0.01, privzeto=izdelek['cena']),
        vnos_stevila(f"Zaloga [{izdelek['zaloga']}]: ", najmanj=0,
                     privzeto=izdelek['zaloga']),
    )
    izpisi_sporocilo(uspeh, sporocilo)


def izbrisi_izdelek():
    """DELETE izdelka (tuji ključi preprečijo brisanje že naročenih)."""
    print("\n--- IZBRIŠI IZDELEK ---")
    izpis_izdelkov()

    id_izdelka = vnos_stevila("\nID izdelka za brisanje: ", najmanj=1)
    izdelek = model.izdelek_po_id(id_izdelka)
    if izdelek is None:
        print("  ✗ Izdelek s tem ID-jem ne obstaja.")
        return

    if not potrdi(f"Res želiš izbrisati '{izdelek['ime_izdelka']}'?"):
        print("  Brisanje je preklicano.")
        return

    uspeh, sporocilo = model.izbrisi_izdelek(id_izdelka)
    izpisi_sporocilo(uspeh, sporocilo)


# =====================================================================
# OCENE (SELECT, DELETE)
# =====================================================================

def izbrisi_oceno():
    """DELETE ocene (v CLI nastopamo kot administrator)."""
    print("\n--- IZBRIŠI OCENO ---")
    izpis_izdelkov()

    id_izdelka = vnos_stevila("\nID izdelka: ", najmanj=1)
    ocene = model.ocene_izdelka(id_izdelka)
    if not ocene:
        print("  Ta izdelek še nima ocen.")
        return

    for o in ocene:
        print(f"[{o['id']}] {o['ime']}: {o['ocena']}/5 - {o['komentar']} "
              f"({o['datum']})")

    id_ocene = vnos_stevila("\nID ocene za brisanje: ", najmanj=1)
    if not potrdi("Res želiš izbrisati to oceno?"):
        print("  Brisanje je preklicano.")
        return

    uspeh, sporocilo = model.izbrisi_oceno(id_ocene, je_admin=True)
    izpisi_sporocilo(uspeh, sporocilo)


# =====================================================================
# STATISTIKA (GROUP BY, agregacije)
# =====================================================================

def statistika():
    print("\n========== STATISTIKA ==========")

    osnovna = model.statistika_osnovna()
    print(f"\nKmetij: {osnovna['kmetije']} | Izdelkov: {osnovna['izdelki']} | "
          f"Uporabnikov: {osnovna['uporabniki']} | "
          f"Naročil: {osnovna['narocila']}")

    print("\n-- Najbolje prodajani izdelki --")
    top = model.statistika_top_izdelki()
    if not top:
        print("  Ni podatkov o prodaji.")
    for p in top:
        print(f"  {p['ime_izdelka']}: {p['prodano']} kosov "
              f"({p['promet']:.2f} €)")

    print("\n-- Izdelki po regijah --")
    for r in model.statistika_po_regijah():
        povprecje = (f"{r['povprecna_cena']:.2f} €"
                     if r['povprecna_cena'] is not None else "–")
        print(f"  {r['regija']}: {r['st_izdelkov']} izdelkov "
              f"(povprečna cena {povprecje})")

    print("\n-- Povprečne ocene izdelkov --")
    ocene = model.statistika_ocene()
    if not ocene:
        print("  Ni ocen.")
    for o in ocene:
        print(f"  {o['ime_izdelka']}: {o['povprecna_ocena']}/5 "
              f"({o['st_ocen']} ocen)")

    print("\n-- Promet po kmetijah --")
    promet = model.statistika_promet_kmetij()
    if not promet:
        print("  Ni podatkov o prometu.")
    for k in promet:
        print(f"  {k['ime_kmetije']} ({k['regija']}): {k['promet']:.2f} €")


# =====================================================================
# GLAVNI MENI
# =====================================================================

MOZNOSTI = {
    '1': ("Izpiši vse kmetije", izpis_kmetij),
    '2': ("Izpiši vse izdelke", izpis_izdelkov),
    '3': ("Izpiši vse uporabnike", izpis_uporabnikov),
    '4': ("Išči izdelke po regiji", iskanje_po_regiji),
    '5': ("Išči izdelke po vrsti", iskanje_po_vrsti),
    '6': ("Dodaj uporabnika (INSERT)", dodaj_uporabnika),
    '7': ("Dodaj kmetijo (INSERT)", dodaj_kmetijo),
    '8': ("Dodaj izdelek (INSERT)", dodaj_izdelek),
    '9': ("Uredi kmetijo (UPDATE)", uredi_kmetijo),
    '10': ("Uredi izdelek (UPDATE)", uredi_izdelek),
    '11': ("Izbriši kmetijo (DELETE)", izbrisi_kmetijo),
    '12': ("Izbriši izdelek (DELETE)", izbrisi_izdelek),
    '13': ("Izbriši oceno (DELETE)", izbrisi_oceno),
    '14': ("Statistika", statistika),
}


def main():
    while True:
        print("\n===== KMETIJSKI TRG - TEKSTOVNI VMESNIK =====")
        for kljuc, (opis, _) in MOZNOSTI.items():
            print(f"  {kljuc:>2} - {opis}")
        print("   0 - Izhod")

        izbira = input("\nIzbira: ").strip()

        if izbira == '0':
            print("Nasvidenje!")
            sys.exit(0)

        if izbira in MOZNOSTI:
            try:
                MOZNOSTI[izbira][1]()
            except (KeyboardInterrupt, EOFError):
                raise
            except Exception as napaka:            # noqa: BLE001
                print(f"  ✗ Prišlo je do napake: {napaka}")
        else:
            print("  Napačna izbira, poskusi znova.")


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nNasvidenje!")
