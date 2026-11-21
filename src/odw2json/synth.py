"""Generate synthetic documents with new layouts and exact gold JSON.

The generator uses only the public conventions of the organizer. It does not
use the rules of the extractors. Thus the score shows how the rules work on
layouts that the team did not see.

Run: PYTHONPATH=src python -m odw2json.synth --n 20 --seed 1 [--errors] [--type przelew]
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import re
import textwrap
from collections import Counter, defaultdict

MONTHS = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]  # fmt: skip

# --- random data ----------------------------------------------------------

MALE = {  # nominative: (genitive, dative)
    "Jan": ("Jana", "Janowi"), "Piotr": ("Piotra", "Piotrowi"), "Tomasz": ("Tomasza", "Tomaszowi"),
    "Marek": ("Marka", "Markowi"), "Paweł": ("Pawła", "Pawłowi"), "Michał": ("Michała", "Michałowi"),
    "Krzysztof": ("Krzysztofa", "Krzysztofowi"), "Andrzej": ("Andrzeja", "Andrzejowi"),
    "Marcin": ("Marcina", "Marcinowi"), "Łukasz": ("Łukasza", "Łukaszowi"), "Adam": ("Adama", "Adamowi"),
    "Rafał": ("Rafała", "Rafałowi"), "Grzegorz": ("Grzegorza", "Grzegorzowi"), "Jacek": ("Jacka", "Jackowi"),
    "Robert": ("Roberta", "Robertowi"), "Wojciech": ("Wojciecha", "Wojciechowi"),
    "Jakub": ("Jakuba", "Jakubowi"), "Dariusz": ("Dariusza", "Dariuszowi"), "Mateusz": ("Mateusza", "Mateuszowi"),
}  # fmt: skip
FEMALE = {  # nominative: (genitive, dative, accusative)
    "Anna": ("Anny", "Annie", "Annę"), "Katarzyna": ("Katarzyny", "Katarzynie", "Katarzynę"),
    "Joanna": ("Joanny", "Joannie", "Joannę"), "Agnieszka": ("Agnieszki", "Agnieszce", "Agnieszkę"),
    "Magdalena": ("Magdaleny", "Magdalenie", "Magdalenę"), "Ewa": ("Ewy", "Ewie", "Ewę"),
    "Maria": ("Marii", "Marii", "Marię"), "Monika": ("Moniki", "Monice", "Monikę"),
    "Barbara": ("Barbary", "Barbarze", "Barbarę"), "Aleksandra": ("Aleksandry", "Aleksandrze", "Aleksandrę"),
    "Natalia": ("Natalii", "Natalii", "Natalię"), "Beata": ("Beaty", "Beacie", "Beatę"),
    "Justyna": ("Justyny", "Justynie", "Justynę"), "Małgorzata": ("Małgorzaty", "Małgorzacie", "Małgorzatę"),
    "Karolina": ("Karoliny", "Karolinie", "Karolinę"),
}  # fmt: skip
ADJ_STEMS = [
    "Kowalsk", "Wiśniewsk", "Dąbrowsk", "Kamińsk", "Lewandowsk", "Zielińsk", "Szymańsk", "Kozłowsk",
    "Jankowsk", "Kwiatkowsk", "Wojciechowsk", "Piotrowsk", "Grabowsk", "Pawłowsk", "Michalsk", "Majewsk",
    "Olszewsk", "Jaworsk", "Malinowsk", "Górsk", "Rutkowsk", "Sadowsk", "Zawadzk", "Borkowsk",
]  # fmt: skip
NOUN_SURNAMES = [
    "Nowak", "Mazur", "Wójcik", "Krawczyk", "Król", "Baran", "Pawlak", "Adamczyk", "Kubiak", "Szewczyk",
    "Wawrzyniak", "Woźniak", "Sikorski_", "Walczak", "Michalak", "Zalewski_",
]  # fmt: skip
NOUN_SURNAMES = [s for s in NOUN_SURNAMES if not s.endswith("_")]

CITIES = {  # nominative: locative
    "Warszawa": "Warszawie", "Kraków": "Krakowie", "Łódź": "Łodzi", "Wrocław": "Wrocławiu",
    "Poznań": "Poznaniu", "Gdańsk": "Gdańsku", "Szczecin": "Szczecinie", "Lublin": "Lublinie",
    "Białystok": "Białymstoku", "Katowice": "Katowicach", "Rzeszów": "Rzeszowie", "Kielce": "Kielcach",
    "Olsztyn": "Olsztynie", "Opole": "Opolu", "Toruń": "Toruniu", "Radom": "Radomiu",
    "Gliwice": "Gliwicach", "Płock": "Płocku", "Tarnów": "Tarnowie", "Elbląg": "Elblągu",
}  # fmt: skip
STREETS = [
    "Lipowa", "Kwiatowa", "Polna", "Szkolna", "Ogrodowa", "Słoneczna", "Leśna", "Długa", "Krótka",
    "Mickiewicza", "Sienkiewicza", "Kościuszki", "Piłsudskiego", "Wojska Polskiego", "Armii Krajowej",
    "Przemysłowa", "Dworcowa", "Mostowa", "Targowa", "Jagiellońska",
]  # fmt: skip
PREFIXES = [
    "Aquatek", "Terramax", "Poltech", "Ekoma", "Instalex", "Drogmost", "Medixa", "Informa", "Kolmar",
    "Zenitel", "Altera", "Virtum", "Prospero", "Nordis", "Orlen_", "Brukpol", "Dendron", "Sigmar",
    "Hydrotec", "Elektrim_", "Montaż-Bis", "Cerber", "Tartak", "Quadro", "Ligna", "Fortis", "Ambit",
]  # fmt: skip
PREFIXES = [p for p in PREFIXES if not p.endswith("_")]
SECTORS = [
    "Budownictwo", "Instalacje", "Systemy", "Serwis", "Logistyka", "Technologie", "Energetyka",
    "Transport", "Usługi", "Drogownictwo", "Informatyka", "Medyczne", "Konstrukcje", "Ochrona",
]  # fmt: skip
FORMS = ["sp. z o.o.", "S.A.", "sp. j.", "sp. k.", "sp. z o.o.", "S.A."]
ROLES = ["Prezes Zarządu", "Członek Zarządu", "Wiceprezes Zarządu", "Prokurent", "Dyrektor"]
AUTHORITY = [
    "Gmina {c}", "Miasto {c}", "Powiat {c}", "Miejski Zarząd Dróg w {l}", "Szpital Powiatowy w {l}",
    "Zespół Szkół nr {n} w {l}", "Zakład Gospodarki Komunalnej w {l}", "Urząd Miasta {c}",
    "Wodociągi {c} sp. z o.o.", "Miejskie Przedsiębiorstwo Energetyki Cieplnej S.A. w {l}",
    "Zarząd Dróg Wojewódzkich w {l}", "Komenda Miejska Policji w {l}", "Muzeum Regionalne w {l}",
    "Państwowa Uczelnia Zawodowa w {l}", "Spółdzielnia Mieszkaniowa „Zacisze” w {l}",
]  # fmt: skip
SUBJECTS = [
    "Dostawa sprzętu komputerowego wraz z oprogramowaniem", "Remont drogi powiatowej nr {n}",
    "Budowa kanalizacji sanitarnej w miejscowości {c}", "Termomodernizacja budynku szkoły podstawowej nr {n}",
    "Świadczenie usług sprzątania obiektów", "Zakup energii elektrycznej na potrzeby jednostek",
    "Dostawa wyposażenia pracowni dydaktycznych", "Przebudowa ulicy Kwiatowej wraz z infrastrukturą",
    "Wykonanie robót budowlanych w zakresie modernizacji oczyszczalni ścieków",
    "Zakup i dostawa aparatury medycznej", "Usługi ochrony fizycznej mienia", "Dostawa autobusów elektrycznych",
    "Rozbudowa systemu monitoringu wizyjnego", "Odbiór i zagospodarowanie odpadów komunalnych",
]  # fmt: skip
SIG_SYMBOLS = ["ZP", "DZP", "ZZP", "TP", "IZP", "ZP.271", "WZP", "PN"]


class Ctx:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.width = rng.choice([0, 0, 72, 80, 90, 100, 110])

    def para(self, text: str) -> str:
        """Wrap a paragraph the way a PDF text layer can do it."""
        if not self.width:
            return text
        return textwrap.fill(text, self.width, break_long_words=False, break_on_hyphens=False)


def digits(rng, n, first_nonzero=True):
    s = "".join(rng.choice("0123456789") for _ in range(n))
    return (str(rng.randint(1, 9)) + s[1:]) if first_nonzero else s


def pesel(rng) -> str:
    y, m, d = rng.randint(1955, 1999), rng.randint(1, 12), rng.randint(1, 28)
    base = f"{y % 100:02d}{m:02d}{d:02d}" + digits(rng, 4, False)
    w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    return base + str((10 - sum(int(a) * b for a, b in zip(base, w)) % 10) % 10)


def person(rng, sex=None):
    sex = sex or rng.choice("MF")
    if sex == "M":
        first = rng.choice(list(MALE))
        gen_f, dat_f = MALE[first]
        acc_f = gen_f
        if rng.random() < 0.6:
            stem = rng.choice(ADJ_STEMS)
            last, gen_l, dat_l, acc_l = stem + "i", stem + "iego", stem + "iemu", stem + "iego"
        else:
            last = rng.choice(NOUN_SURNAMES)
            gen_l, dat_l, acc_l = last + "a", last + "owi", last + "a"
            if last in ("Król",):
                gen_l, dat_l, acc_l = "Króla", "Królowi", "Króla"
    else:
        first = rng.choice(list(FEMALE))
        gen_f, dat_f, acc_f = FEMALE[first]
        if rng.random() < 0.6:
            stem = rng.choice(ADJ_STEMS)
            last, gen_l, dat_l, acc_l = stem + "a", stem + "iej", stem + "iej", stem + "ą"
        else:
            last = rng.choice(NOUN_SURNAMES)
            gen_l = dat_l = acc_l = last
    return {
        "sex": sex, "first": first, "last": last,
        "nom": f"{first} {last}", "gen": f"{gen_f} {gen_l}", "dat": f"{dat_f} {dat_l}", "acc": f"{acc_f} {acc_l}",
    }  # fmt: skip


def addr(rng):
    city = rng.choice(list(CITIES))
    return f"ul. {rng.choice(STREETS)} {rng.randint(1, 120)}", f"{digits(rng, 2)}-{digits(rng, 3, False)} {city}", city


def company(rng, form=None):
    form = form or rng.choice(FORMS)
    name = f"{rng.choice(PREFIXES)} {rng.choice(SECTORS)} {form}"
    street, town, city = addr(rng)
    return {
        "nazwa": name, "krs": "000" + digits(rng, 7, False), "nip": digits(rng, 10), "regon": digits(rng, 9),
        "street": street, "town": town, "city": city, "addr": f"{street}, {town}",
        "mail": f"biuro@{rng.choice(PREFIXES).lower()}.pl",
    }  # fmt: skip


def authority(rng):
    city = rng.choice(list(CITIES))
    name = rng.choice(AUTHORITY).format(c=city, l=CITIES[city], n=rng.randint(1, 15))
    street, town, _ = addr(rng)
    town = f"{digits(rng, 2)}-{digits(rng, 3, False)} {city}"
    return {
        "nazwa": name, "krs": "000" + digits(rng, 7, False), "nip": digits(rng, 10), "regon": digits(rng, 9),
        "street": street, "town": town, "city": city, "addr": f"{street}, {town}",
    }  # fmt: skip


def law_firm(rng, lawyer):
    last = lawyer["last"]
    forms = [
        f"Kancelaria Radców Prawnych {last} i Wspólnicy sp. k.",
        f"Kancelaria Adwokacka adw. {lawyer['nom']}",
        f"{last} {rng.choice(NOUN_SURNAMES)} Kancelaria Prawna sp.p.",
        f"Kancelaria Prawna {last} sp. z o.o.",
    ]
    return rng.choice(forms)


def proc_number(rng):
    style = rng.choice(range(5))
    y = 2026
    n = rng.randint(1, 250)
    if style == 0:
        return f"{rng.choice(SIG_SYMBOLS)}.{rng.randint(100, 900)}.{n}.{y}"
    if style == 1:
        return f"{rng.choice(['ZSCKR', 'DAZ', 'MZD', 'ZGK'])}/{n}/{y}"
    if style == 2:
        return f"{rng.choice(['ZP', 'PN', 'OI'])}/{n:02d}/{y}"
    if style == 3:
        return f"{rng.choice(['I', 'II', 'V'])}.ROZ.{rng.randint(2000, 2800)}.{n}.{y}"
    return f"{rng.randint(1, 99)}/{rng.choice(['ZP', 'PN', 'TP'])}/{y}"


def subject_title(rng, city=None):
    c = city or rng.choice(list(CITIES))
    return rng.choice(SUBJECTS).format(n=rng.randint(2, 99), c=c)


# --- dates and formats ----------------------------------------------------


def rdate(rng, lo=dt.date(2025, 9, 1), hi=dt.date(2026, 11, 15)):
    return lo + dt.timedelta(days=rng.randint(0, (hi - lo).days))


def fmt_date(d, style):
    if style == "iso":
        return d.isoformat()
    if style == "dot":
        return f"{d.day:02d}.{d.month:02d}.{d.year}"
    if style == "dash":
        return f"{d.day:02d}-{d.month:02d}-{d.year}"
    if style == "slash":
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    if style == "pl":
        return f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    if style == "pl_r":
        return f"{d.day} {MONTHS[d.month - 1]} {d.year} r."
    if style == "pl_roku":
        return f"{d.day} {MONTHS[d.month - 1]} {d.year} roku"
    if style == "dot_r":
        return f"{d.day:02d}.{d.month:02d}.{d.year} r."
    raise ValueError(style)


def group(s, sizes):
    out, i = [], 0
    for n in sizes:
        out.append(s[i : i + n])
        i += n
    return " ".join(out)


def fmt_acc(raw, style):
    if style == "plain":
        return raw
    if style == "pl":
        return "PL" + raw
    if style == "spaced":
        return group(raw, [2] + [4] * 6)
    if style == "pl_spaced":
        return "PL" + group(raw, [2] + [4] * 6)
    if style == "pl_space_spaced":
        return "PL " + group(raw, [2] + [4] * 6)
    if style == "pl_dash":
        return "PL" + raw[:2] + "-" + "-".join(raw[2:][i : i + 4] for i in range(0, 24, 4))
    raise ValueError(style)


def fmt_amount(a, style):
    whole, frac = f"{a:.2f}".split(".")
    thousands = f"{int(whole):,}".replace(",", " ")
    nb = thousands.replace(" ", " ")
    return {
        "space_pln": f"{thousands},{frac} PLN",
        "pln_first": f"PLN {thousands},{frac}",
        "bare": f"{thousands},{frac}",
        "neg_pln": f"-{thousands},{frac} PLN",
        "dot": f"{whole}.{frac} PLN",
        "nb_pln": f"{nb},{frac} PLN",
        "zl": f"{thousands},{frac} zł",
        "plain_comma": f"{whole},{frac}",
        "neg_spaced": f"- {thousands},{frac} PLN",
    }[style]


def gold_date(d):
    return d.isoformat()


# --- przelew --------------------------------------------------------------

BANKS = [
    "Bank Pocztowy Północ", "Nordbank Polska", "Bank Spółdzielczy w Zielonej Dolinie", "Millenia Bank",
    "Bank Północny", "Bank Handlowo-Kredytowy", "mBanco", "Alior Express", "Credit Zachodni",
]  # fmt: skip
KIO_ACCOUNT = "60101010100081362231000000"


def przelew_data(rng):
    payer_is_company = rng.random() < 0.8
    payer = company(rng) if payer_is_company else {**person(rng), "addr": ", ".join(addr(rng)[:2])}
    pn = payer["nazwa"] if payer_is_company else payer["nom"]
    wpis = rng.random() < 0.45
    d = rdate(rng)
    if wpis:
        zam = authority(rng)
        amount = float(rng.choice([7500, 10000, 15000, 20000]))
        proc = proc_number(rng)
        sep = rng.choice([", ", " - ", " / "])
        form = rng.choice(["upper", "lower", "full"])
        if form == "upper":
            title = f"WPIS OD ODW., ZAM: {zam['nazwa'].upper()}{sep}{proc}"
        elif form == "lower":
            title = f"Wpis od odwołania{sep}{proc}{sep}{zam['nazwa']}"
        else:
            title = f"Wpis od odwołania do KIO w postępowaniu {proc} prowadzonym przez {zam['nazwa']}"
        recipient = {"nazwa": "Urząd Zamówień Publicznych", "addr": "ul. Postępu 17A, 02-676 Warszawa"}
        racc = KIO_ACCOUNT
    else:
        zam = authority(rng)
        amount = float(rng.choice([17, 17, 50, 200]))
        proc = proc_number(rng)
        att = [person(rng) for _ in range(rng.choice([1, 1, 2]))]
        names = " i ".join(a["nom"] for a in att)
        ref = f"CEN{d:%y%m}{digits(rng, 9)}"
        title = rng.choice(
            [
                f"opłata skarbowa od pełnomocnictwa dla {names} w postępowaniu przed KIO w przetargu {proc}",
                f"Opłata skarbowa za pełnomocnictwo - {names} - sprawa {proc}",
                f"OPŁATA SKARBOWA OD PEŁNOMOCNICTWA {names.upper()} {proc}",
            ]
        )
        _ = ref
        recipient = {"nazwa": f"Urząd Miasta {zam['city']}", "addr": zam["addr"]}
        racc = digits(rng, 26)
    has_ref = rng.random() < 0.6
    ref = rng.choice([f"CEN{d:%y%m}{digits(rng, 9)}", f"TRX{digits(rng, 8)}", f"{d:%Y%m%d}/{digits(rng, 7)}"])
    return {
        "pn": pn, "pa": payer["addr"], "pacc": digits(rng, 26), "rn": recipient["nazwa"], "ra": recipient["addr"],
        "racc": racc, "amount": amount, "date": d, "title": title, "ref": ref if has_ref else None,
        "bank": rng.choice(BANKS), "balance": f"{rng.randint(1000, 900000) / 100:.2f}",
    }  # fmt: skip


def wrap_label(c, label, value, width=None):
    width = width or c.rng.choice([58, 66, 80])
    lines = textwrap.wrap(value, width - len(label), break_long_words=False) or [""]
    return "\n".join([label + lines[0]] + lines[1:])


def pz_1(c, d):
    r = c.rng
    a, am, ds = (
        r.choice(["plain", "pl", "spaced"]),
        r.choice(["space_pln", "neg_pln", "nb_pln"]),
        r.choice(["dot", "iso"]),
    )
    lines = [d["bank"], "Szczegóły operacji", "Rodzaj operacji: Przelew zewnętrzny",
             f"Data księgowania: {fmt_date(d['date'] + dt.timedelta(days=1), ds)}",
             f"Data operacji: {fmt_date(d['date'], ds)}", f"Kwota: {fmt_amount(d['amount'], am)}",
             f"Rachunek źródłowy: {fmt_acc(d['pacc'], a)}", f"Nadawca: {d['pn']}",
             f"Rachunek odbiorcy: {fmt_acc(d['racc'], a)}", f"Odbiorca: {d['rn']}",
             wrap_label(c, "Tytuł operacji: ", d['title'])]  # fmt: skip
    if d["ref"]:
        lines.append(f"Nr transakcji: {d['ref']}")
    lines.append(f"Saldo po operacji: {d['balance'].replace('.', ',')} PLN")
    return "\n".join(lines)


def pz_2(c, d):
    r = c.rng
    a, am = r.choice(["pl_spaced", "pl", "spaced"]), r.choice(["space_pln", "bare", "zl"])
    lines = ["POTWIERDZENIE PRZELEWU", d["bank"], "Nadawca:", d["pn"], d["pa"], f"Rachunek: {fmt_acc(d['pacc'], a)}",
             "Odbiorca:", d["rn"], d["ra"], f"Rachunek: {fmt_acc(d['racc'], a)}",
             f"Kwota: {fmt_amount(d['amount'], am)}", f"Data: {fmt_date(d['date'], r.choice(['dot', 'dash']))}",
             wrap_label(c, "Tytułem: ", d["title"])]  # fmt: skip
    if d["ref"]:
        lines.append(f"Numer referencyjny: {d['ref']}")
    return "\n".join(lines)


def pz_3(c, d):
    r = c.rng
    a, am = r.choice(["pl_spaced", "spaced"]), r.choice(["pln_first", "space_pln"])
    lines = ["Transfer confirmation / Potwierdzenie transakcji", d["bank"],
             f"Data / Date: {fmt_date(d['date'], 'dot')}",
             f"Kwota / Amount: {fmt_amount(d['amount'], am)}",
             f"Rachunek nadawcy / Sender account: {fmt_acc(d['pacc'], a)}",
             f"Nazwa nadawcy / Sender name: {d['pn']}",
             f"Rachunek odbiorcy / Beneficiary account: {fmt_acc(d['racc'], a)}",
             f"Nazwa odbiorcy / Beneficiary name: {d['rn']}",
             wrap_label(c, "Tytuł / Title: ", d["title"])]  # fmt: skip
    if d["ref"]:
        lines.append(f"Nr transakcji / Reference: {d['ref']}")
    lines.append("Status / Status: Zrealizowany / Executed")
    return "\n".join(lines)


def pz_4(c, d):
    r = c.rng
    a, am = r.choice(["pl", "pl_spaced", "plain"]), r.choice(["neg_pln", "dot", "space_pln"])
    lines = ["Przelew krajowy", f"Z rachunku: {fmt_acc(d['pacc'], a)}", f"Na rachunek: {fmt_acc(d['racc'], a)}",
             f"Kwota: {fmt_amount(d['amount'], am)}", f"Data operacji: {fmt_date(d['date'], 'iso')}",
             f"Odbiorca: {d['rn']}", wrap_label(c, "Tytułem: ", d["title"])]  # fmt: skip
    if d["ref"]:
        lines.append(f"Identyfikator operacji: {d['ref']}")
    lines.append(f"Wydrukowano: {fmt_date(d['date'] + dt.timedelta(days=2), 'dot')}")
    return "\n".join(lines)


def pz_5(c, d):
    r = c.rng
    a = r.choice(["pl_spaced", "spaced"])
    am = r.choice(["neg_spaced", "neg_pln"])
    lines = [d["bank"], am and fmt_amount(d["amount"], am), "Przelew wykonany", f"Dla: {d['rn']}",
             f"Z konta: {fmt_acc(d['pacc'], a)}", f"Na konto: {fmt_acc(d['racc'], a)}",
             wrap_label(c, "Opis: ", d["title"]), f"Data: {fmt_date(d['date'], 'pl')}"]  # fmt: skip
    if d["ref"]:
        lines.append(f"ID transakcji: {d['ref']}")
    return "\n".join(lines)


def pz_6(c, d):
    r = c.rng
    a, am = r.choice(["plain", "spaced", "pl_spaced"]), r.choice(["space_pln", "pln_first"])
    lines = ["Potwierdzenie wykonania przelewu", "Rachunek do obciążenia", fmt_acc(d["pacc"], a), "Rachunek beneficjenta",
             fmt_acc(d["racc"], a), "Nazwa beneficjenta", d["rn"], "Kwota przelewu", fmt_amount(d["amount"], am),
             "Data wykonania", fmt_date(d["date"], "dash"), "Tytuł przelewu"]  # fmt: skip
    lines += textwrap.wrap(d["title"], 70)
    if d["ref"]:
        lines += ["Numer transakcji", d["ref"]]
    return "\n".join(lines)


def pz_7(c, d):
    r = c.rng
    a, am = r.choice(["pl_spaced", "pl"]), r.choice(["space_pln", "bare"])
    lines = [f"{d['bank']} - Potwierdzenie przelewu", f"Wygenerowano: {fmt_date(d['date'] + dt.timedelta(days=1), 'dot')} 14:32:10",
             "Zleceniodawca", f"  Nazwa: {d['pn']}", f"  Adres: {d['pa']}", f"  Rachunek: {fmt_acc(d['pacc'], a)}",
             "Beneficjent", f"  Nazwa: {d['rn']}", f"  Adres: {d['ra']}", f"  Rachunek: {fmt_acc(d['racc'], a)}",
             "Szczegóły przelewu", f"  Kwota: {fmt_amount(d['amount'], am)}", "  Waluta: PLN",
             f"  Data operacji: {fmt_date(d['date'], 'dot')} 09:{r.randint(10, 59)}",
             wrap_label(c, "  Tytuł: ", d["title"])]  # fmt: skip
    if d["ref"]:
        lines.append(f"  Nr ref.: {d['ref']}")
    return "\n".join(lines)


def pz_8(c, d):
    r = c.rng
    a, am = r.choice(["spaced", "pl_spaced"]), r.choice(["space_pln", "zl"])
    lines = ["Zlecenie przelewu - potwierdzenie", "Z rachunku nadawcy", fmt_acc(d["pacc"], a), "Do rachunku odbiorcy",
             fmt_acc(d["racc"], a), f"Nadawca: {d['pn']}", f"Odbiorca: {d['rn']}", f"Kwota przelewu: {fmt_amount(d['amount'], am)}",
             "Opłata za przelew: 0,00 PLN", f"Data waluty: {fmt_date(d['date'] + dt.timedelta(days=1), 'dot')}",
             f"Data operacji: {fmt_date(d['date'], 'dot')}", wrap_label(c, "Tytuł: ", d["title"])]  # fmt: skip
    if d["ref"]:
        lines.append(f"Numer transakcji: {d['ref']}")
    return "\n".join(lines)


def pz_9(c, d):
    r = c.rng
    a = r.choice(["pl_space_spaced", "pl_dash", "pl_spaced"])
    am = r.choice(["space_pln", "plain_comma"])
    lines = ["Transfer details", f"Debit account (Rachunek obciążany): {fmt_acc(d['pacc'], a)}",
             f"Credit account (Rachunek uznawany): {fmt_acc(d['racc'], a)}", f"Beneficiary: {d['rn']}",
             f"Amount: {fmt_amount(d['amount'], am)}", "Currency: PLN",
             f"Execution date: {fmt_date(d['date'], 'slash')}", wrap_label(c, "Payment details: ", d["title"])]  # fmt: skip
    if d["ref"]:
        lines.append(f"Transaction ID: {d['ref']}")
    return "\n".join(lines)


def pz_10(c, d):
    r = c.rng
    a, am = r.choice(["plain", "pl"]), r.choice(["space_pln", "nb_pln"])
    lines = ["Dyspozycja przelewu - wydruk", f"{'Przelew do US' if d['amount'] < 300 else 'Przelew zewnętrzny'}",
             f"Podmiot zlecający: {d['pn']}", f"Rachunek zlecającego: {fmt_acc(d['pacc'], a)}",
             f"Podmiot odbierający: {d['rn']}", f"Rachunek odbierającego: {fmt_acc(d['racc'], a)}",
             f"Data realizacji: {fmt_date(d['date'], 'iso')}", f"Kwota: {fmt_amount(d['amount'], am)}",
             f"Saldo po operacji: {d['balance'].replace('.', ',')} PLN", wrap_label(c, "Tytuł: ", d["title"])]  # fmt: skip
    if d["ref"]:
        lines.append(f"Nr transakcji: {d['ref']}")
    return "\n".join(lines)


PZ_LAYOUTS = [pz_1, pz_2, pz_3, pz_4, pz_5, pz_6, pz_7, pz_8, pz_9, pz_10]


def gen_przelew(rng, i):
    c = Ctx(rng)
    d = przelew_data(rng)
    layout = PZ_LAYOUTS[i % len(PZ_LAYOUTS)]
    text = layout(c, d)
    if rng.random() < 0.4:
        text = text + "\nStrona 1 z 1"
    gold = {
        "przelew_bankowy": {
            "data_operacji": gold_date(d["date"]), "kwota": d["amount"], "na_rachunek": d["racc"],
            "numer_transakcji": d["ref"], "tytul": d["title"], "z_rachunku": d["pacc"],
        }
    }  # fmt: skip
    return layout.__name__, text, gold


# --- pelnomocnictwo -------------------------------------------------------


def mocodawca_data(rng, kind):
    """Give (display fields, gold entry, signers) for one principal."""
    if kind == "company":
        co = company(rng)
        signers = [person(rng) for _ in range(rng.choice([1, 1, 2]))]
        return co, {
            "data": {"imie_nazwisko": None, "krs": co["krs"], "nazwa": co["nazwa"], "nip": co["nip"], "typ": "osoba_prawna"},
            "podpisujacy": [{"imie_nazwisko": s["nom"]} for s in signers],
        }, signers  # fmt: skip
    p = person(rng)
    street, town, city = addr(rng)
    brand = rng.choice(PREFIXES).upper() + rng.choice(["-TECH", "-BUD", "-SERWIS", "-TRANS"])
    firm = f"{brand} {p['nom']}"
    co = {
        "nazwa": firm,
        "nip": digits(rng, 10),
        "regon": digits(rng, 9),
        "krs": None,
        "addr": f"{street}, {town}",
        "city": city,
        "person": p,
    }
    return co, {
        "data": {"imie_nazwisko": p["nom"], "krs": None, "nazwa": firm, "nip": co["nip"], "typ": "osoba_fizyczna"},
        "podpisujacy": [{"imie_nazwisko": p["nom"]}],
    }, [p]  # fmt: skip


def pel_data(rng, kind, n_moc=1):
    mocs = [mocodawca_data(rng, kind) for _ in range(n_moc)]
    n_att = rng.choice([1, 1, 2])
    atts = []
    for _ in range(n_att):
        p = person(rng)
        p["title"] = rng.choice(["adw.", "r. pr."])
        p["pesel"] = pesel(rng) if rng.random() < 0.4 else None
        p["reg"] = f"{rng.choice(['WA', 'KR', 'PO', 'GD'])}-{rng.randint(100, 9999)}"
        atts.append(p)
    zam = authority(rng)
    return {
        "mocs": mocs, "atts": atts, "zam": zam, "nr": proc_number(rng), "tytul": subject_title(rng, zam["city"]),
        "date": rdate(rng), "place": rng.choice(list(CITIES)),
    }  # fmt: skip


def pel_gold(d):
    return {
        "mocodawca": [m[1] for m in d["mocs"]],
        "pelnomocnicy": [{"imie_nazwisko": a["nom"], "pesel": a["pesel"]} for a in d["atts"]],
    }  # fmt: skip


def ids(co, krs=True):
    parts = []
    if co.get("krs") and krs:
        parts.append(f"KRS {co['krs']}")
    parts.append(f"NIP {co['nip']}")
    if co.get("regon"):
        parts.append(f"REGON {co['regon']}")
    return ", ".join(parts)


def att_acc(a):
    return f"{a['title']} {a['nom']}" + (f", PESEL {a['pesel']}" if a["pesel"] else "")


def att_dat(a):
    t = {"adw.": "adwokatowi", "r. pr.": "radcy prawnemu"}[a["title"]]
    pre = "Panu" if a["sex"] == "M" else "Pani"
    if a["sex"] == "F":
        t = {"adw.": "adwokat", "r. pr.": "radcy prawnej"}[a["title"]]
    s = f"{pre} {a['dat']}, {t}"
    return s + (f", legitymującemu się numerem PESEL {a['pesel']}" if a["pesel"] and a["sex"] == "M" else
                f", legitymującej się numerem PESEL {a['pesel']}" if a["pesel"] else "")  # fmt: skip


def sig_block(c, co, signers, style):
    r = c.rng
    out = []
    for s in signers:
        role = r.choice(ROLES)
        if style == "dash":
            out += ["............................", f"{s['nom']} – {role}", "(podpis)"]
        elif style == "lines":
            out += ["............................", s["nom"], role]
        elif style == "table":
            out += ["Imię i nazwisko: " + s["nom"], "Funkcja: " + role, "Podpis: ............................"]
        else:
            out += ["__________________________", f"{s['nom']}, {role}"]
    return out


def pl_1(c, d):
    """Prose with dative: Ja niżej podpisany ... udzielam pełnomocnictwa Panu ..."""
    m = d["mocs"][0][0]
    p = d["mocs"][0][2][0]
    head = f"{d['place']}, dnia {fmt_date(d['date'], 'pl_r')}"
    if "person" in m:
        f = p["sex"] == "F"
        who = f"Ja, niżej podpisan{'a' if f else 'y'} {p['nom']}, prowadząc{'a' if f else 'y'} działalność gospodarczą pod firmą {m['nazwa']}, {m['addr']}, NIP {m['nip']}, REGON {m['regon']}"
    else:
        f = p["sex"] == "F"
        who = f"Ja, niżej podpisan{'a' if f else 'y'} {p['nom']}, działając{'a' if f else 'y'} jako {c.rng.choice(ROLES)} spółki {m['nazwa']} z siedzibą w miejscowości {m['city']}, {ids(m)}"
    att = " oraz ".join(att_dat(a) for a in d["atts"])
    body = (f"{who}, udzielam pełnomocnictwa {att}, do reprezentowania mnie przed Krajową Izbą Odwoławczą w sprawie odwołania "
            f"w postępowaniu o udzielenie zamówienia pn. „{d['tytul']}”, numer postępowania {d['nr']}, prowadzonym przez {d['zam']['nazwa']}.")  # fmt: skip
    return "\n".join([head, "PEŁNOMOCNICTWO", c.para(body), "Pełnomocnictwo obejmuje prawo do składania i odbierania pism.",
                      *sig_block(c, m, d["mocs"][0][2], "dash")])  # fmt: skip


def pl_2(c, d):
    """Key-value layout with numbered attorneys."""
    m, _, signers = d["mocs"][0]
    lines = ["PEŁNOMOCNICTWO", f"Mocodawca: {m['nazwa']}", f"Adres: {m['addr']}", ids(m), "Pełnomocnik:"]
    lines += [f"{i}) {att_acc(a)}" for i, a in enumerate(d["atts"], 1)]
    lines += [c.para(f"Zakres: reprezentowanie Mocodawcy w postępowaniu odwoławczym przed KIO, {d['nr']}, „{d['tytul']}”."),
              f"Zamawiający: {d['zam']['nazwa']}", f"Data: {fmt_date(d['date'], 'dot')}", "Podpisy mocodawcy:"]  # fmt: skip
    if "person" in m:
        lines.insert(2, f"Imię i nazwisko: {signers[0]['nom']}")
    lines += sig_block(c, m, signers, "dash")
    return "\n".join(lines)


def pl_3(c, d):
    """Consortium of two companies. Each one has its own signers."""
    lines = [f"{d['place']}, {fmt_date(d['date'], 'dot')}", "PEŁNOMOCNICTWO"]
    firms = "; ".join(f"{i}) {m[0]['nazwa']}, {m[0]['addr']}, {ids(m[0])}" for i, m in enumerate(d["mocs"], 1))
    att = ", ".join(f"{a['title']} {a['nom']}" + (f" (PESEL {a['pesel']})" if a["pesel"] else "") for a in d["atts"])
    lines.append(c.para(f"My, niżej podpisani, jako Wykonawcy wspólnie ubiegający się o zamówienie: {firms}, ustanawiamy pełnomocnikiem: {att}, "
                        f"do reprezentowania nas w postępowaniu {d['nr']} „{d['tytul']}” prowadzonym przez {d['zam']['nazwa']}, w tym do wniesienia odwołania."))  # fmt: skip
    for m in d["mocs"]:
        lines.append(f"Za {m[0]['nazwa']}:")
        lines += sig_block(c, m[0], m[2], "dash")
    return "\n".join(lines)


def pl_4(c, d):
    m, _, signers = d["mocs"][0]
    lines = ["P E Ł N O M O C N I C T W O", f"{d['place']}, {fmt_date(d['date'], 'pl_roku')}", "Dane mocodawcy", f"Nazwa: {m['nazwa']}",
             f"Siedziba: {m['addr']}", f"NIP: {m['nip']}"]  # fmt: skip
    if m.get("krs"):
        lines.append(f"KRS: {m['krs']}")
    lines += ["Osoby upoważnione do reprezentacji:"]
    for s in signers:
        lines += [f"Imię i nazwisko: {s['nom']}", f"Funkcja: {c.rng.choice(ROLES)}"]
    lines.append("Dane pełnomocnika")
    for a in d["atts"]:
        lines.append(f"Imię i nazwisko: {a['nom']}")
        lines.append(f"Zawód: {'adwokat' if a['title'] == 'adw.' else 'radca prawny'}")
        if a["pesel"]:
            lines.append(f"PESEL: {a['pesel']}")
    lines.append(
        c.para(
            f"Mocodawca udziela pełnomocnictwa do działania w postępowaniu {d['nr']} ({d['tytul']}), Zamawiający: {d['zam']['nazwa']}."
        )
    )
    lines += ["Podpis mocodawcy: ............................", "(podpis)"]
    return "\n".join(lines)


def pl_5(c, d):
    """Civil partnership (spółka cywilna). The partners sign."""
    m, _, signers = d["mocs"][0]
    names = " i ".join(f"{p['first']} {p['last']}" for p in signers)
    return "\n".join([
        f"{d['place']}, {fmt_date(d['date'], 'dot')}", "PEŁNOMOCNICTWO",
        c.para(f"Wspólnicy spółki cywilnej {m['nazwa']}, {m['addr']}, NIP {m['nip']}, REGON {m['regon']}: {names}, udzielają pełnomocnictwa "
               f"{att_dat(d['atts'][0])} do wniesienia odwołania w postępowaniu {d['nr']}, zamawiający {d['zam']['nazwa']}."),
        *sig_block(c, m, signers, "lines")])  # fmt: skip


def pl_6(c, d):
    """Signature block first. The text uses 'ustanawiam moim pełnomocnikiem'."""
    m, _, signers = d["mocs"][0]
    lines = [f"{fmt_date(d['date'], 'dot')} {d['place']}", "PEŁNOMOCNICTWO", "(dla Wykonawcy)"]
    who = f"{m['nazwa']}, {m['addr']}, {ids(m)}"
    names = " i ".join(att_acc(a) for a in d["atts"])
    lines.append(c.para(f"Niniejszym ustanawiam moim pełnomocnikiem {names} do reprezentowania {who} w postępowaniu "
                        f"odwoławczym wszczętym w związku z postępowaniem „{d['tytul']}” ({d['nr']})."))  # fmt: skip
    lines.append("Mocodawca (pieczęć i podpis):")
    lines += sig_block(c, m, signers, "table")
    return "\n".join(lines)


def pl_7(c, d):
    """Signers named in the text (the signature has only dots)."""
    m, _, signers = d["mocs"][0]
    reps = " oraz ".join(f"{s['nom']} – {c.rng.choice(ROLES)}" for s in signers)
    att = ", ".join(att_acc(a) for a in d["atts"])
    lines = ["PEŁNOMOCNICTWO", f"{d['place']}, {fmt_date(d['date'], 'pl')} r.",
             c.para(f"{m['nazwa']}, {m['addr']}, {ids(m)}, reprezentowana przez: {reps}, udziela pełnomocnictwa: {att}, "
                    f"w postępowaniu {d['nr']} „{d['tytul']}”, prowadzonym przez {d['zam']['nazwa']}."),
             "............................", "(podpisy osób uprawnionych)"]  # fmt: skip
    return "\n".join(lines), [s["nom"] for s in signers]


def pl_8(c, d):
    """Two principals (consortium) in a numbered list, with signers under each one."""
    lines = ["PEŁNOMOCNICTWO", f"{d['place']}, {fmt_date(d['date'], 'dot_r')}", "Mocodawcy (konsorcjum):"]
    for i, m in enumerate(d["mocs"], 1):
        lines.append(f"{i}. {m[0]['nazwa']}, {m[0]['addr']}, {ids(m[0])}")
    lines.append("Pełnomocnicy:")
    for i, a in enumerate(d["atts"], 1):
        lines.append(f"{i}) {att_acc(a)}")
    lines.append(
        c.para(
            f"Mocodawcy udzielają pełnomocnictwa do reprezentowania w postępowaniu o udzielenie zamówienia: {d['tytul']} ({d['nr']})."
        )
    )
    for m in d["mocs"]:
        lines.append(f"{m[0]['nazwa']} reprezentowana przez:")
        for s in m[2]:
            lines += [f"{s['nom']} – {c.rng.choice(ROLES)}", "........................... (podpis)"]
    return "\n".join(lines)


def pl_9(c, d):
    """Short text. 'Pełnomocnictwo' then 'Mocodawca' and 'Pełnomocnik' in two blocks, dative-free."""
    m, _, signers = d["mocs"][0]
    lines = ["PEŁNOMOCNICTWO", f"Mocodawca: {m['nazwa']} z siedzibą w {m['city']}, {ids(m)}", "reprezentowany przez:"]
    lines += [f"{s['nom']} - {c.rng.choice(ROLES)}" for s in signers]
    lines.append("udziela pełnomocnictwa:")
    lines += [
        f"{i}) {a['title']} {a['dat']} (do reprezentowania w sprawie {d['nr']})" for i, a in enumerate(d["atts"], 1)
    ]
    return "\n".join(lines), None


PL_LAYOUTS = ["pl_1", "pl_2", "pl_3", "pl_4", "pl_5", "pl_6", "pl_7", "pl_8", "pl_9"]


def gen_pelnomocnictwo(rng, i):
    c = Ctx(rng)
    name = PL_LAYOUTS[i % len(PL_LAYOUTS)]
    if name in ("pl_3", "pl_8"):
        d = pel_data(rng, "company", 2)
    elif name == "pl_5":
        d = pel_data(rng, "person", 1)
        partners = [person(rng, "M"), person(rng, "F")]
        civil = f"{partners[0]['last']} i {partners[1]['last']} s.c."
        d["mocs"] = [({**d["mocs"][0][0], "nazwa": civil, "krs": None}, {"data": {}, "podpisujacy": []}, partners)]
        d["atts"] = d["atts"][:1]
    elif name == "pl_1":
        d = pel_data(rng, rng.choice(["company", "person"]), 1)
        d["mocs"][0][1]["podpisujacy"] = d["mocs"][0][1]["podpisujacy"][:1]
        d["mocs"] = [(d["mocs"][0][0], d["mocs"][0][1], d["mocs"][0][2][:1])]
    elif name == "pl_9":
        d = pel_data(rng, "company", 1)
        for a in d["atts"]:
            a["pesel"] = None  # this layout has no PESEL
    else:
        d = pel_data(rng, rng.choice(["company", "company", "person"]), 1)
    gold = pel_gold(d)
    if name == "pl_5":
        gold["mocodawca"][0]["data"] = {
            "imie_nazwisko": None,
            "krs": None,
            "nazwa": civil,
            "nip": d["mocs"][0][0]["nip"],
            "typ": "osoba_fizyczna",
        }
        gold["mocodawca"][0]["podpisujacy"] = [{"imie_nazwisko": p["nom"]} for p in partners]
    out = globals()[name](c, d)
    return name, out[0] if isinstance(out, tuple) else out, gold


# --- odwolanie ------------------------------------------------------------

# (code, canonical description, noun phrases in the locative, sentences)
CODES = {
    1: "Decyzja o odrzuceniu oferty",
    2: "Ogłoszenie wyboru oferty",
    3: "Decyzja o wykluczeniu wykonawcy",
    4: "Publikacja specyfikacji warunków zamówienia (SWZ)",
    5: "Modyfikacja treści SWZ",
    6: "Odpowiedzi/wyjaśnienia do SWZ",
    7: "Zaniechanie odrzucenia oferty",
    8: "Zaniechanie wykluczenia wykonawcy",
    9: "Decyzja o unieważnieniu postępowania",
    10: "Zaniechanie unieważnienia postępowania",
    11: "Opis przedmiotu zamówienia (OPZ)",
    12: "Projektowane postanowienia umowy",
}

ACTS = {
    1: [
        (
            "odrzuceniu oferty Odwołującego na podstawie art. 226 ust. 1 pkt 5 Pzp, o czym Zamawiający zawiadomił {d}",
            "Zamawiający {d} zawiadomił Odwołującego o odrzuceniu jego oferty.",
        ),
        (
            "czynności odrzucenia oferty Odwołującego jako niezgodnej z warunkami zamówienia, dokonanej {d}",
            "Zamawiający {d} odrzucił ofertę Odwołującego jako niezgodną z warunkami zamówienia.",
        ),
    ],
    2: [
        (
            "wyborze jako najkorzystniejszej oferty wykonawcy {o}, o czym zawiadomiono {d}",
            "Zamawiający {d} dokonał wyboru oferty wykonawcy {o} jako najkorzystniejszej.",
        ),
        (
            "ogłoszeniu wyniku postępowania i wyborze oferty złożonej przez {o} {d}",
            "Zamawiający {d} ogłosił wybór oferty złożonej przez {o}.",
        ),
    ],
    3: [
        (
            "wykluczeniu Odwołującego z postępowania na podstawie art. 109 ust. 1 pkt 4 Pzp, o czym Zamawiający poinformował {d}",
            "Zamawiający {d} wykluczył Odwołującego z postępowania.",
        ),
        (
            "decyzji o wykluczeniu wykonawcy ze względu na brak wykazania spełniania warunków, podjętej {d}",
            "Zamawiający {d} podjął decyzję o wykluczeniu Odwołującego z postępowania.",
        ),
    ],
    4: [
        (
            "ustaleniu treści Specyfikacji Warunków Zamówienia opublikowanej {d} wraz z ogłoszeniem o zamówieniu",
            "Zamawiający {d} opublikował Specyfikację Warunków Zamówienia.",
        ),
        ("treści SWZ udostępnionej wykonawcom {d}", "Zamawiający {d} udostępnił SWZ na stronie postępowania."),
    ],
    5: [
        (
            "modyfikacji treści SWZ dokonanej {d} w zakresie warunków udziału w postępowaniu",
            "Zamawiający {d} zmienił treść SWZ w zakresie warunków udziału w postępowaniu.",
        ),
        ("zmianie Specyfikacji Warunków Zamówienia ogłoszonej {d}", "Zamawiający {d} dokonał zmiany SWZ."),
    ],
    6: [
        (
            "udzieleniu {d} odpowiedzi na pytania wykonawców do SWZ w sposób niejednoznaczny",
            "Zamawiający {d} udzielił odpowiedzi na pytania do treści SWZ.",
        ),
        (
            "wyjaśnieniach treści SWZ przekazanych wykonawcom {d}",
            "Zamawiający {d} przekazał wykonawcom wyjaśnienia treści SWZ.",
        ),
    ],
    7: [
        (
            "zaniechaniu odrzucenia oferty wykonawcy {o}, o czym świadczy zawiadomienie z dnia {t}",
            "Zamawiający {d} nie odrzucił oferty wykonawcy {o}, mimo że podlegała odrzuceniu.",
        ),
        (
            "zaniechaniu odrzucenia oferty wykonawcy {o}, mimo że jest ona niezgodna z SWZ, co ujawniono {d}",
            "Zamawiający {d} zaniechał odrzucenia oferty wykonawcy {o}.",
        ),
    ],
    8: [
        (
            "zaniechaniu wykluczenia z postępowania wykonawcy {o}, o czym zawiadomiono {d}",
            "Zamawiający {d} nie wykluczył z postępowania wykonawcy {o}.",
        ),
        (
            "zaniechaniu wykluczenia wykonawcy {o} z postępowania (informacja z dnia {t})",
            "Zamawiający {d} zaniechał wykluczenia wykonawcy {o}.",
        ),
    ],
    9: [
        (
            "unieważnieniu postępowania o udzielenie zamówienia, o czym zawiadomiono wykonawców {d}",
            "Zamawiający {d} unieważnił postępowanie o udzielenie zamówienia.",
        ),
        (
            "decyzji o unieważnieniu postępowania na podstawie art. 255 pkt 3 Pzp podjętej {d}",
            "Zamawiający {d} podjął decyzję o unieważnieniu postępowania.",
        ),
    ],
    10: [
        (
            "zaniechaniu unieważnienia postępowania pomimo istnienia przesłanek z art. 255 Pzp, co potwierdza pismo z dnia {t}",
            "Zamawiający {d} zaniechał unieważnienia postępowania.",
        ),
        ("zaniechaniu unieważnienia postępowania {d}", "Zamawiający {d} nie unieważnił postępowania, choć powinien."),
    ],
    11: [
        (
            "opisaniu przedmiotu zamówienia (OPZ) w sposób naruszający uczciwą konkurencję, opublikowanym {d}",
            "Zamawiający {d} opublikował Opis Przedmiotu Zamówienia.",
        ),
        (
            "Opisie Przedmiotu Zamówienia udostępnionym wykonawcom {d}",
            "Zamawiający {d} udostępnił Opis Przedmiotu Zamówienia (załącznik nr 1 do SWZ).",
        ),
    ],
    12: [
        (
            "ukształtowaniu projektowanych postanowień umowy w sprawie zamówienia publicznego, opublikowanych {d}",
            "Zamawiający {d} opublikował projektowane postanowienia umowy.",
        ),
        (
            "treści projektowanych postanowień umowy (załącznik do SWZ) udostępnionych {d}",
            "Zamawiający {d} udostępnił projektowane postanowienia umowy jako załącznik do SWZ.",
        ),
    ],
}


def act_date_text(rng, date):
    style = rng.choice(["w dniu {} r.", "w dniu {} roku", "dnia {} r."])
    t = fmt_date(date, rng.choice(["pl", "dot"]))
    return style.format(t), t + " r."


def odw_data(rng, layout):
    odw = company(rng)
    consortium = layout in ("od_3", "od_9") and rng.random() < 0.7
    partner = company(rng) if consortium else None
    if layout == "od_10":
        p = person(rng, "M")
        brand = rng.choice(PREFIXES).upper() + "-TECH"
        street, town, city = addr(rng)
        odw = {"nazwa": f"{brand} {p['nom']}", "krs": None, "nip": digits(rng, 10), "regon": digits(rng, 9),
               "street": street, "town": town, "city": city, "addr": f"{street}, {town}"}  # fmt: skip
    # A missing identifier is not in the text. Thus gold has null.
    for co in (odw,):
        for k in ("krs", "nip", "regon"):
            if co.get(k) and rng.random() < 0.15:
                co[k] = None
    if not (odw.get("nip") or odw.get("krs")):
        odw["nip"] = digits(rng, 10)
    n_zam = 2 if layout in ("od_4",) or rng.random() < 0.12 else 1
    zams = [authority(rng) for _ in range(n_zam)]
    for z in zams:
        for k in ("krs", "nip", "regon"):
            if rng.random() < (0.55 if k == "krs" else 0.12):
                z[k] = None
        if not (z.get("nip") or z.get("regon")):
            z["nip"] = digits(rng, 10)
    lawyers = []
    if layout != "od_5":
        for _ in range(rng.choice([1, 1, 2])):
            p = person(rng)
            p["title"] = rng.choice(["adw.", "r. pr."])
            lawyers.append(p)
    firm = law_firm(rng, lawyers[0]) if lawyers else None
    if firm and rng.random() < 0.15:
        firm = None
    mail = None
    if lawyers and rng.random() < 0.85:
        mail = f"{lawyers[0]['last'].lower().replace('ł', 'l').replace('ń', 'n').replace('ś', 's').replace('ó', 'o').replace('ż', 'z').replace('ą', 'a').replace('ę', 'e').replace('ć', 'c').replace('ź', 'z')}@{rng.choice(['kancelaria', 'prawnik', 'adwokat', 'legalis'])}.pl"
    first_code = rng.randint(1, 12)
    base = rdate(rng, dt.date(2025, 9, 1), dt.date(2026, 10, 1))
    first_date = base
    n_other = rng.randint(1, 3)
    others = []
    for _ in range(n_other):
        code = rng.choice([x for x in CODES if x != first_code])
        others.append((code, base + dt.timedelta(days=rng.choice([-12, -9, -6, -4, -2, 1, 2]))))
    year = base.year
    bzp_n = digits(rng, 8, False)
    bzp_style = rng.choice(["plain", "space", "corr", "plain_corr"])
    bzp_suffix = f"/{rng.randint(1, 3):02d}" if "corr" in bzp_style else ""
    has_bzp = rng.random() < 0.85
    has_ted = rng.random() < 0.5
    ted_n = digits(rng, 6)
    ted_style = rng.choice(["slash", "dash"])
    return {
        "odw": odw, "partner": partner, "zams": zams, "lawyers": lawyers, "firm": firm, "mail": mail,
        "first_code": first_code, "first_date": first_date, "others": others, "year": year,
        "bzp": f"{year}/BZP{bzp_n}{bzp_suffix}" if has_bzp else None,
        "bzp_text": (f"{year}/BZP {bzp_n}{bzp_suffix}" if bzp_style in ("space", "corr") else f"{year}/BZP{bzp_n}{bzp_suffix}") if has_bzp else None,
        "ted": f"{ted_n}-{year}" if has_ted else None,
        "ted_text": (f"{year}/S {rng.randint(10, 250):03d}-{ted_n}" if ted_style == "slash" else f"{ted_n}-{year}") if has_ted else None,
        "nr": proc_number(rng) if rng.random() < 0.9 else None, "tytul": subject_title(rng, zams[0]["city"]),
        "competitor": f"{rng.choice(PREFIXES)} {rng.choice(SECTORS)} {rng.choice(FORMS)}",
        "n_zam": n_zam, "date": first_date + dt.timedelta(days=rng.randint(3, 10)), "place": rng.choice(list(CITIES)),
        "lider": rng.random() < 0.8,
    }  # fmt: skip


def odw_gold(d, header):
    odw = d["odw"]
    lawyer = d["lawyers"][0] if d["lawyers"] else None
    first_code = d["first_code"]
    gold = {
        "OdwolanieKIO": {
            "data": gold_date(d["date"]) if header else None, "czynnosc_dzien": gold_date(d["first_date"]),
            "czynnosc_powod_id": first_code, "czynnosc_opis": CODES[first_code],
            "miejscowosc": d["place"] if header else None,
        },
        "Odwolujacy": [{
            "krs": odw["krs"], "nazwa": odw["nazwa"], "nip": odw["nip"], "regon": odw["regon"],
            "przez-pelnomocnika": 1 if lawyer else 0,
            "pelnomocnik": ({"imie_nazwisko": lawyer["nom"], "nazwa": d["firm"], "mail": d["mail"]} if lawyer
                            else {"imie_nazwisko": None, "nazwa": None, "mail": None}),
        }],
        "Zamawiajacy": [
            {"krs": z["krs"], "nazwa": z["nazwa"], "nip": z["nip"], "regon": z["regon"],
             "prowadzacy_postepowanie": (None if d["n_zam"] == 1 else (1 if i == (0 if d["lider"] else 1) else 0))}
            for i, z in enumerate(d["zams"])
        ],
        "ZamowieniePubliczne": {"numer_bzp": d["bzp"], "numer_postepowania": d["nr"], "numer_ted": d["ted"], "tytul": d["tytul"]},
    }  # fmt: skip
    return gold


def co_ids(co):
    parts = []
    if co.get("krs"):
        parts.append(f"KRS: {co['krs']}")
    if co.get("nip"):
        parts.append(f"NIP: {co['nip']}")
    if co.get("regon"):
        parts.append(f"REGON: {co['regon']}")
    return ", ".join(parts)


def lawyer_line(d, mode):
    """Say 'represented by' in the accusative or the nominative."""
    names = []
    for a in d["lawyers"]:
        names.append(f"{a['title']} {a['acc'] if mode == 'acc' else a['nom']}")
    return ", ".join(names)


def act_lists(c, d):
    """Return the noun phrases and the sentences of the charges. The first one gives the code."""
    r = c.rng
    items = [(d["first_code"], d["first_date"])] + d["others"]
    nps, sents = [], []
    for code, date in items:
        np_t, s_t = r.choice(ACTS[code])
        dt_text, bare = act_date_text(r, date)
        nps.append(np_t.format(d=dt_text, t=bare, o=d["competitor"]))
        sents.append(s_t.format(d=dt_text, t=bare, o=d["competitor"]))
    return nps, sents


def charge_body(c, d, n):
    return [
        c.para(
            "Zamawiający naruszył art. 16 pkt 1 i 2 Pzp przez prowadzenie postępowania w sposób niezapewniający zachowania uczciwej konkurencji "
            "oraz równego traktowania wykonawców."
        ),
        c.para(
            "Naruszenie to ma istotny wpływ na wynik postępowania, ponieważ Odwołujący traci możliwość uzyskania zamówienia."
        ),
    ]


def zam_block(c, d, style):
    """Give (authority, tag) pairs. The tag tells the role when there are two."""
    out = []
    for i, z in enumerate(d["zams"]):
        tag = ""
        if d["n_zam"] > 1:
            lider = i == (0 if d["lider"] else 1)
            if style == "paren":
                tag = " (Zamawiający prowadzący postępowanie)" if lider else " (Zamawiający uczestniczący)"
            else:
                tag = " – lider, prowadzący postępowanie" if lider else " – partner"
        out.append((z, tag))
    return out


def od_1(c, d):
    r = c.rng
    nps, _sents = act_lists(c, d)
    lines = [f"{d['place']}, dnia {fmt_date(d['date'], r.choice(['pl_r', 'pl_roku']))}", "Krajowa Izba Odwoławcza", "ul. Postępu 17A", "02-676 Warszawa",
             "Odwołujący:", d["odw"]["nazwa"], d["odw"]["addr"], co_ids(d["odw"])]  # fmt: skip
    if d["lawyers"]:
        lines.append(f"reprezentowany przez: {lawyer_line(d, 'nom')}")
        lines.append(
            c.para(f"adres do korespondencji: {d['firm'] + ', ' if d['firm'] else ''}ul. Cicha 3, 00-001 Warszawa")
        )
        if d["mail"]:
            lines.append(f"e-mail: {d['mail']}")
    lines.append("Zamawiający:")
    for z, tag in zam_block(c, d, "paren"):
        lines += [z["nazwa"] + tag, z["addr"], co_ids(z)]
    lines.append("ODWOŁANIE")
    meta = f"dotyczy postępowania o udzielenie zamówienia publicznego pn. „{d['tytul']}”"
    if d["nr"]:
        meta += f", znak sprawy: {d['nr']}"
    if d["bzp_text"]:
        meta += f", ogłoszenie nr {d['bzp_text']}"
    if d["ted_text"]:
        meta += f", numer TED: {d['ted_text']}"
    lines.append(c.para(meta))
    lines.append(
        c.para("Na podstawie art. 513 Pzp wnoszę odwołanie wobec czynności i zaniechań Zamawiającego polegających na:")
    )
    for i, np_ in enumerate(nps, 1):
        lines.append(c.para(f"{i}) {np_};"))
    lines.append("ZARZUTY")
    for i in range(1, len(nps) + 1):
        lines.append(f"Zarzut {i}. Naruszenie przepisów ustawy Pzp.")
        lines += charge_body(c, d, i)
    lines.append("Wnoszę o uwzględnienie odwołania.")
    return "\n".join(lines), True


def od_2(c, d):
    _nps, sents = act_lists(c, d)
    lines = [
        f"{d['place']} {fmt_date(d['date'], 'dot')}",
        "ODWOŁANIE",
        "Wykonawca wnoszący odwołanie",
        f"Nazwa: {d['odw']['nazwa']}",
        f"Adres: {d['odw']['addr']}",
    ]
    for k, lab in (("nip", "NIP"), ("krs", "KRS"), ("regon", "REGON")):
        if d["odw"].get(k):
            lines.append(f"{lab}: {d['odw'][k]}")
    if d["lawyers"]:
        lines += ["Pełnomocnik wykonawcy", f"Imię i nazwisko: {d['lawyers'][0]['nom']}"]
        if d["firm"]:
            lines.append(f"Kancelaria: {d['firm']}")
        if d["mail"]:
            lines.append(f"E-mail: {d['mail']}")
    lines.append("Zamawiający")
    for z, tag in zam_block(c, d, "plain"):
        lines += [f"Nazwa: {z['nazwa']}", f"Adres: {z['addr']}"]
        if tag:
            lines.append(
                "Rola: "
                + tag.strip(" –").replace("lider, ", "Zamawiający ").replace("partner", "Zamawiający uczestniczący")
            )
        for k, lab in (("nip", "NIP"), ("krs", "KRS"), ("regon", "REGON")):
            if z.get(k):
                lines.append(f"{lab}: {z[k]}")
    lines.append("Dane postępowania")
    lines.append(c.para(f"Przedmiot zamówienia: {d['tytul']}"))
    if d["nr"]:
        lines.append(f"Numer referencyjny: {d['nr']}")
    if d["bzp_text"]:
        lines.append(f"Ogłoszenie w BZP: {d['bzp_text']}")
    if d["ted_text"]:
        lines.append(f"Ogłoszenie TED: {d['ted_text']}")
    lines.append("Zaskarżone czynności:")
    for i, s in enumerate(sents, 1):
        lines.append(c.para(f"{i}. {s}"))
    lines.append("Zarzuty:")
    for i in range(1, len(sents) + 1):
        lines.append(c.para(f"{i}. Naruszenie art. 16 Pzp."))
    return "\n".join(lines), True


def od_3(c, d):
    _nps, sents = act_lists(c, d)
    lines = [
        f"{d['place']}, {fmt_date(d['date'], 'dot')}",
        "Do: Prezes Krajowej Izby Odwoławczej, ul. Postępu 17A, 02-676 Warszawa",
        "ODWOŁANIE",
    ]
    if d["partner"]:
        lines += ["Odwołujący: Konsorcjum wykonawców w składzie:", "1) Lider Konsorcjum:", d["odw"]["nazwa"], d["odw"]["addr"], co_ids(d["odw"]),
                  "2) Partner Konsorcjum:", d["partner"]["nazwa"], d["partner"]["addr"], co_ids(d["partner"])]  # fmt: skip
    else:
        lines += ["Odwołujący:", d["odw"]["nazwa"], d["odw"]["addr"], co_ids(d["odw"])]
    if d["lawyers"]:
        lines.append(
            c.para(
                f"Odwołujący działa przez pełnomocnika – {lawyer_line(d, 'acc')}, ustanowionego pełnomocnictwem załączonym do odwołania."
            )
        )
        if d["firm"]:
            lines.append(f"Kancelaria: {d['firm']}")
        if d["mail"]:
            lines.append(f"Adres e-mail: {d['mail']}")
    lines.append("Zamawiający:")
    for z, tag in zam_block(c, d, "paren"):
        lines += [z["nazwa"] + tag, z["addr"], co_ids(z)]
    lines.append(c.para(f"Postępowanie: „{d['tytul']}”" + (f", nr {d['nr']}" if d["nr"] else "") + (f", BZP {d['bzp_text']}" if d["bzp_text"] else "")
                        + (f", TED {d['ted_text']}" if d["ted_text"] else "") + "."))  # fmt: skip
    lines.append(c.para("Odwołujący wnosi odwołanie od następujących czynności Zamawiającego:"))
    for i, s in enumerate(sents, 1):
        lines.append(c.para(f"{i}) {s}"))
    lines += charge_body(c, d, 1)
    return "\n".join(lines), True


def od_4(c, d):
    nps, _sents = act_lists(c, d)
    lines = [
        f"{d['place']}, dnia {fmt_date(d['date'], 'pl_r')}",
        "ODWOŁANIE",
        "Prezes Krajowej Izby Odwoławczej",
        "Odwołujący:",
        d["odw"]["nazwa"],
        d["odw"]["addr"],
        co_ids(d["odw"]),
    ]
    if d["lawyers"]:
        lines.append(
            c.para(
                f"reprezentowany przez {lawyer_line(d, 'acc')} – {d['firm'] + ', ' if d['firm'] else ''}e-mail: {d['mail'] or 'brak'}"
            )
        )
        if not d["mail"]:
            lines[-1] = lines[-1].replace(", e-mail: brak", "")
    lines.append("Zamawiający (zamawiający wspólnie przeprowadzający postępowanie):")
    for i, (z, tag) in enumerate(zam_block(c, d, "paren"), 1):
        lines += [f"{i}) {z['nazwa']}{tag}", z["addr"], co_ids(z)]
    lines.append(c.para(f"dotyczy: postępowania pn. „{d['tytul']}”" + (f", numer postępowania: {d['nr']}" if d["nr"] else "")
                        + (f", ogłoszenie o zamówieniu {d['bzp_text']}" if d["bzp_text"] else "")))  # fmt: skip
    lines.append(c.para("Wnoszę odwołanie wobec następujących czynności i zaniechań, polegających na:"))
    for i, np_ in enumerate(nps, 1):
        lines.append(c.para(f"{i}) {np_};"))
    lines.append(
        c.para("Zarzut 1 dotyczy pierwszej z wymienionych czynności. Pozostałe zarzuty są zarzutami uzupełniającymi.")
    )
    return "\n".join(lines), True


def od_5(c, d):
    """No attorney. No header."""
    nps, _sents = act_lists(c, d)
    lines = ["ODWOŁANIE", "Odwołujący (wykonawca działający samodzielnie, bez pełnomocnika):", d["odw"]["nazwa"], d["odw"]["addr"], co_ids(d["odw"]),
             "Zamawiający:"]  # fmt: skip
    for z, tag in zam_block(c, d, "paren"):
        lines += [z["nazwa"] + tag, z["addr"], co_ids(z)]
    if d["nr"]:
        lines.append(f"Znak sprawy: {d['nr']}")
    if d["bzp_text"]:
        lines.append(f"Numer ogłoszenia BZP: {d['bzp_text']}")
    if d["ted_text"]:
        lines.append(f"Numer TED: {d['ted_text']}")
    lines.append(c.para(f'Tytuł postępowania: "{d["tytul"]}"'))
    lines.append(c.para("Odwołujący wnosi odwołanie i zarzuca Zamawiającemu:"))
    for i, np_ in enumerate(nps, 1):
        lines.append(c.para(f"Zarzut {i} dotyczy czynności polegającej na {np_}."))
    return "\n".join(lines), False


def od_6(c, d):
    """No header. Metadata lines first."""
    nps, _sents = act_lists(c, d)
    lines = ["Krajowa Izba Odwoławcza", "ODWOŁANIE od czynności Zamawiającego", f"Znak sprawy: {d['nr']}" if d["nr"] else "Postępowanie prowadzone w trybie podstawowym",
             f'Tytuł: "{d["tytul"]}"']  # fmt: skip
    if d["bzp_text"]:
        lines.append(f"Ogłoszenie BZP: {d['bzp_text']}")
    if d["ted_text"]:
        lines.append(f"Ogłoszenie TED: {d['ted_text']}")
    lines += ["Wykonawca (Odwołujący): " + d["odw"]["nazwa"], f"Siedziba: {d['odw']['addr']}", co_ids(d["odw"])]
    if d["lawyers"]:
        lines.append(
            c.para(
                f"Pełnomocnik Odwołującego: {lawyer_line(d, 'nom')}"
                + (f", {d['firm']}" if d["firm"] else "")
                + (f", {d['mail']}" if d["mail"] else "")
            )
        )
    lines.append("Zamawiający:")
    for z, tag in zam_block(c, d, "plain"):
        lines += [z["nazwa"] + tag, z["addr"], co_ids(z)]
    lines.append("Zarzuty odwołania:")
    for i, np_ in enumerate(nps, 1):
        lines.append(c.para(f"{i}. Zarzut dotyczy czynności polegającej na {np_}."))
    return "\n".join(lines), False


def od_7(c, d):
    _nps, sents = act_lists(c, d)
    zam_names = " oraz ".join(z["nazwa"] for z in d["zams"])
    lines = [f"{d['place']} {fmt_date(d['date'], 'dot')}", "Prezes Krajowej Izby Odwoławczej", "ODWOŁANIE"]
    lines.append(c.para(f"W imieniu {d['odw']['nazwa']}, {d['odw']['addr']}, {co_ids(d['odw'])} (dalej: Odwołujący)"
                        + (f", działając jako pełnomocnik – {lawyer_line(d, 'nom')}" + (f" z {d['firm']}" if d["firm"] else "") + (f" ({d['mail']})" if d["mail"] else "")
                           if d["lawyers"] else "")
                        + f", wnoszę odwołanie od czynności Zamawiającego: {zam_names}."))  # fmt: skip
    for z, tag in zam_block(c, d, "paren"):
        lines.append(c.para(f"Zamawiający: {z['nazwa']}{tag}, {z['addr']}, {co_ids(z)}."))
    lines.append(c.para(f"Postępowanie „{d['tytul']}”" + (f" ({d['nr']})" if d["nr"] else "") + (f", ogłoszenie {d['bzp_text']}" if d["bzp_text"] else "")
                        + (f", {d['ted_text']} w TED" if d["ted_text"] else "") + "."))  # fmt: skip
    lines.append("I. Stan faktyczny")
    for s in sents:
        lines.append(c.para(s))
    lines.append("II. Zarzuty")
    lines.append(c.para("Zarzut 1: naruszenie art. 16 Pzp w związku z pierwszą ze wskazanych czynności."))
    return "\n".join(lines), True


def od_8(c, d):
    nps, _sents = act_lists(c, d)
    lines = [
        "Do: Krajowa Izba Odwoławcza",
        f"Od: {d['odw']['nazwa']} (odwołujący), {d['odw']['addr']}",
        co_ids(d["odw"]),
    ]
    if d["lawyers"]:
        lines.append(
            c.para(
                f"Pełnomocnik: {lawyer_line(d, 'nom')}"
                + (f", {d['firm']}" if d["firm"] else "")
                + (f", e-mail {d['mail']}" if d["mail"] else "")
            )
        )
    lines.append(
        "Przeciwko: "
        + "; ".join(
            f"{z['nazwa']}, {z['addr']}, {co_ids(z)}" + (tag if tag else "") for z, tag in zam_block(c, d, "paren")
        )
    )
    lines.append("Przedmiot odwołania: " + d["tytul"])
    if d["nr"]:
        lines.append(f"Numer postępowania: {d['nr']}")
    if d["bzp_text"]:
        lines.append(f"BZP: {d['bzp_text']}")
    if d["ted_text"]:
        lines.append(f"TED: {d['ted_text']}")
    lines.append("Zaskarżone czynności polegają na:")
    for i, np_ in enumerate(nps, 1):
        lines.append(c.para(f"{i}) {np_}"))
    return "\n".join(lines), False


def od_9(c, d):
    """Charges first as legal violations. Facts follow in the same order."""
    r = c.rng
    _nps, sents = act_lists(c, d)
    lines = [f"{d['place']}, dnia {fmt_date(d['date'], 'dot')}", "Krajowa Izba Odwoławcza", "ODWOŁANIE"]
    if d["partner"]:
        lines.append(
            c.para(
                f"Odwołujący: Konsorcjum – Lider: {d['odw']['nazwa']}, {d['odw']['addr']}, {co_ids(d['odw'])}; Partner: {d['partner']['nazwa']}, {d['partner']['addr']}, {co_ids(d['partner'])}."
            )
        )
    else:
        lines.append(c.para(f"Odwołujący: {d['odw']['nazwa']}, {d['odw']['addr']}, {co_ids(d['odw'])}."))
    if d["lawyers"]:
        lines.append(
            c.para(
                f"Odwołujący reprezentowany przez: {lawyer_line(d, 'nom')}"
                + (f", {d['firm']}" if d["firm"] else "")
                + (f", {d['mail']}" if d["mail"] else "")
                + "."
            )
        )
    for z, tag in zam_block(c, d, "plain"):
        lines.append(c.para(f"Zamawiający: {z['nazwa']}{tag}, {z['addr']}, {co_ids(z)}."))
    lines.append(c.para(f"Postępowanie: {d['tytul']}" + (f" ({d['nr']})" if d["nr"] else "") + (f". BZP {d['bzp_text']}" if d["bzp_text"] else "")
                        + (f". TED {d['ted_text']}" if d["ted_text"] else "") + "."))  # fmt: skip
    lines.append("Zarzuty:")
    for i in range(1, len(sents) + 1):
        lines.append(f"{i}. Naruszenie art. 16 pkt {r.choice([1, 2, 3])} Pzp (zarzut {i}).")
    lines.append("Uzasadnienie – stan faktyczny:")
    for s in sents:
        lines.append(c.para(s))
    return "\n".join(lines), True


def od_10(c, d):
    nps, _sents = act_lists(c, d)
    lines = [
        f"{d['place']}, {fmt_date(d['date'], 'pl_r')}",
        "ODWOŁANIE",
        "Odwołujący: " + d["odw"]["nazwa"],
        d["odw"]["addr"],
        co_ids(d["odw"]),
    ]
    if d["lawyers"]:
        lines.append(
            c.para(
                f"reprezentowany przez {lawyer_line(d, 'acc')}"
                + (f" ({d['firm']})" if d["firm"] else "")
                + (f", e-mail: {d['mail']}" if d["mail"] else "")
            )
        )
    for z, tag in zam_block(c, d, "paren"):
        lines += ["Zamawiający: " + z["nazwa"] + tag, z["addr"], co_ids(z)]
    lines.append(
        c.para(
            f"Postępowanie{' nr ' + d['nr'] if d['nr'] else ''}: „{d['tytul']}”"
            + (f", ogłoszenie {d['bzp_text']}" if d["bzp_text"] else "")
            + (f", {d['ted_text']}" if d["ted_text"] else "")
        )
    )
    lines.append("Wnoszę odwołanie. Zarzucam Zamawiającemu:")
    for i, np_ in enumerate(nps, 1):
        lines.append(c.para(f"{i}) {np_};"))
    return "\n".join(lines), True


OD_LAYOUTS = [od_1, od_2, od_3, od_4, od_5, od_6, od_7, od_8, od_9, od_10]


def gen_odwolanie(rng, i):
    c = Ctx(rng)
    layout = OD_LAYOUTS[i % len(OD_LAYOUTS)]
    d = odw_data(rng, layout.__name__)
    text, header = layout(c, d)
    gold = odw_gold(d, header)
    return layout.__name__, text, gold


# --- negatives ------------------------------------------------------------


def neg_wyrok(rng, c):
    o, z = company(rng), authority(rng)
    d = rdate(rng)
    return "\n".join([
        f"Sygn. akt KIO {rng.randint(100, 3999)}/{d.year % 100}", "WYROK", f"z dnia {fmt_date(d, 'pl_r')}", "Krajowa Izba Odwoławcza – w składzie:",
        f"Przewodniczący: {person(rng)['nom']}", f"po rozpoznaniu na rozprawie w dniu {fmt_date(d, 'pl')} r. w Warszawie odwołania wniesionego do Prezesa KIO przez wykonawcę {o['nazwa']}",
        f"w postępowaniu prowadzonym przez Zamawiającego {z['nazwa']}", "orzeka:",
        "1. Uwzględnia odwołanie i nakazuje Zamawiającemu powtórzenie czynności badania i oceny ofert.",
        "2. Kosztami postępowania obciąża Zamawiającego i zalicza w poczet kosztów postępowania odwoławczego kwotę 15 000 zł 00 gr uiszczoną przez Odwołującego tytułem wpisu od odwołania.",
        "Uzasadnienie", "Zamawiający – Odwołujący – Przystępujący", "Przewodniczący: ........................"])  # fmt: skip


def neg_wezwanie(rng, c):
    o, z = company(rng), authority(rng)
    d = rdate(rng)
    return "\n".join([
        f"{z['city']}, {fmt_date(d, 'dot')}", z["nazwa"], z["addr"], f"Znak: {proc_number(rng)}", f"{o['nazwa']}", o["addr"], "Wezwanie do uzupełnienia dokumentów",
        c.para("Na podstawie art. 128 ust. 1 ustawy Pzp wzywam do uzupełnienia w terminie 5 dni od otrzymania wezwania oświadczenia o niepodleganiu wykluczeniu oraz wykazu usług."),
        "Z poważaniem", f"{person(rng)['nom']}, Kierownik Zamawiającego"])  # fmt: skip


def neg_faktura(rng, c):
    o, z = company(rng), authority(rng)
    d = rdate(rng)
    net = rng.randint(1000, 90000)
    return "\n".join([
        f"Faktura VAT nr FV/{rng.randint(1, 900)}/{d.month:02d}/{d.year}", f"Data wystawienia: {fmt_date(d, 'dot')}", f"Sprzedawca: {o['nazwa']}", f"NIP: {o['nip']}", o["addr"],
        f"Nabywca: {z['nazwa']}", f"NIP: {z['nip']}", "Lp. Nazwa towaru lub usługi Ilość Cena netto Wartość netto VAT",
        f"1 Usługi serwisowe 1 {net},00 {net},00 23%", f"Razem do zapłaty: {net * 1.23:.2f} PLN".replace(".", ","),
        f"Numer rachunku: PL{digits(rng, 26)}", "Termin płatności: 14 dni"])  # fmt: skip


def neg_zawiadomienie(rng, c):
    z, o = authority(rng), company(rng)
    d = rdate(rng)
    return "\n".join([
        f"{z['city']}, {fmt_date(d, 'pl_r')}", z["nazwa"], z["addr"], f"Znak sprawy: {proc_number(rng)}", "ZAWIADOMIENIE O WYBORZE NAJKORZYSTNIEJSZEJ OFERTY",
        c.para(f"Zamawiający {z['nazwa']} zawiadamia, że w postępowaniu pn. „{subject_title(rng)}” jako najkorzystniejszą wybrano ofertę wykonawcy {o['nazwa']}, {o['addr']}."),
        c.para("Wykonawcom przysługuje odwołanie do Krajowej Izby Odwoławczej na podstawie art. 513 Pzp w terminie 10 dni od dnia przekazania zawiadomienia. Odwołanie wnosi się do Prezesa Izby."),
        "Zamawiający: " + z["nazwa"], f"Kierownik Zamawiającego: {person(rng)['nom']}"])  # fmt: skip


def neg_odpowiedz(rng, c):
    z, o = authority(rng), company(rng)
    d = rdate(rng)
    return "\n".join([
        f"{z['city']}, {fmt_date(d, 'pl_r')}", "Krajowa Izba Odwoławcza", "ODPOWIEDŹ NA ODWOŁANIE",
        c.para(f"Zamawiający {z['nazwa']} w sprawie odwołania wniesionego przez {o['nazwa']} wnosi o oddalenie odwołania w całości i zasądzenie kosztów postępowania."),
        c.para("Zarzuty Odwołującego są bezzasadne, a czynności Zamawiającego były zgodne z przepisami ustawy Pzp."), "Zamawiający"])  # fmt: skip


def neg_swz(rng, c):
    z = authority(rng)
    return "\n".join([
        "SPECYFIKACJA WARUNKÓW ZAMÓWIENIA (SWZ)", f"Zamawiający: {z['nazwa']}", f"Numer postępowania: {proc_number(rng)}", f"Przedmiot zamówienia: {subject_title(rng)}",
        c.para("Rozdział 1. Zamawiający. Rozdział 2. Tryb udzielenia zamówienia. Wykonawca może wnieść odwołanie na zasadach określonych w dziale IX ustawy Pzp. "
               "Środki ochrony prawnej przysługują wykonawcy, jeżeli ma lub miał interes w uzyskaniu zamówienia."),
        f"Termin składania ofert: {fmt_date(rdate(rng), 'dot')}"])  # fmt: skip


NEG_LAYOUTS = [neg_wyrok, neg_wezwanie, neg_faktura, neg_zawiadomienie, neg_odpowiedz, neg_swz]


def gen_negative(rng, i):
    fn = NEG_LAYOUTS[i % len(NEG_LAYOUTS)]
    return fn.__name__, fn(rng, Ctx(rng)), {}


# --- noise and API ----------------------------------------------------------


def add_noise(text, rng, kind):
    text = re.sub(r"(?<!\.)\.\.(?!\.)", ".", text)  # a name that ends with a dot, then the full stop
    lines = text.split("\n")
    if kind in ("odwolanie", "pelnomocnictwo", "negative") and len(lines) > 8 and rng.random() < 0.5:
        k = rng.randint(len(lines) * 2 // 3, len(lines) - 1)
        lines[k:k] = ["Strona 1 z 2"]
    if rng.random() < 0.25:
        lines.insert(0, rng.choice(["Wydruk z systemu", "Dokument elektroniczny", "KOPIA"]))
    if rng.random() < 0.3:
        lines.append(rng.choice(["Strona 2 z 2", "Dokument wygenerowany automatycznie", "- 1 -"]))
    return "\n".join(lines)


GENERATORS = {
    "przelew": gen_przelew,
    "pelnomocnictwo": gen_pelnomocnictwo,
    "odwolanie": gen_odwolanie,
    "negative": gen_negative,
}


def generate(n_per_type: int, seed: int, types=None) -> list[tuple[str, str, dict]]:
    """Give (name, text, gold) for each synthetic document."""
    out = []
    for t, fn in GENERATORS.items():
        if types and t not in types:
            continue
        rng = random.Random(f"{seed}-{t}")
        for i in range(n_per_type):
            layout, text, gold = fn(rng, i)
            out.append((f"{t}/{layout}/{i}", add_noise(text, rng, t), gold))
    return out


def main() -> None:
    from odw2json.evaluate import Score, compare, doc_type
    from odw2json.pipeline import process_text

    parser = argparse.ArgumentParser(description="Score the pipeline on synthetic documents.")
    parser.add_argument("--n", type=int, default=20, help="documents for each type")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--errors", action="store_true")
    parser.add_argument("--type", action="append", help="przelew, pelnomocnictwo, odwolanie or negative")
    parser.add_argument("--show", help="print the text and the gold of the documents with this name part")
    args = parser.parse_args()

    by_type, by_field, by_layout = defaultdict(Score), defaultdict(Score), defaultdict(Score)
    confusion = Counter()
    errors = []
    for name, text, gold in generate(args.n, args.seed, args.type):
        if args.show and args.show in name:
            print(f"##### {name}\n{text}\n{gold}\n")
        result = process_text(text)
        leaves = compare(gold, result.data)
        if "/pl_5/" in name:
            # The organizer does not define the type of a civil partnership.
            leaves = [x for x in leaves if x.path not in ("mocodawca[].data.typ", "mocodawca[].data.imie_nazwisko")]
        t = name.split("/")[0]
        by_type[t].add(leaves)
        by_layout["/".join(name.split("/")[:2])].add(leaves)
        confusion[(t, doc_type(result.data))] += 1
        for leaf in leaves:
            by_field[leaf.path].add([leaf])
        errors += [(name, text, leaf) for leaf in leaves if leaf.outcome in ("FP", "FN", "WRONG")]
    for t, s in by_type.items():
        print(f"type {t:15s} {s.line()}")
    print("Classification (gold -> predicted):")
    for (g, p), n in sorted(confusion.items()):
        print(f"  {g:15s} -> {p:15s} {n}")
    print("Layouts below F1 1.0:")
    for k, s in sorted(by_layout.items(), key=lambda kv: kv[1].f1):
        if s.f1 < 1:
            print(f"  {k:28s} {s.line()}")
    print("Worst fields:")
    for k, s in sorted(by_field.items(), key=lambda kv: kv[1].f1)[:15]:
        if s.f1 < 1:
            print(f"  {k:40s} {s.line()}")
    if args.errors:
        print("Errors:")
        for name, _, leaf in errors:
            print(f"  {leaf.outcome:5s} {name} {leaf.path}\n      gold={leaf.ref!r}\n      pred={leaf.pred!r}")


if __name__ == "__main__":
    main()
