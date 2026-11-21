"""Second generator of synthetic documents. It is a test of generalization.

It makes the text of Polish documents of KIO appeal cases, with the expected JSON.
The layouts imitate real documents: bank confirmations of many banks, appeals and
powers of attorney of law offices, and close negatives. The generator does not use
the rules of the extractors. Use it to measure the score on layouts that the rules
did not see.

Run: PYTHONPATH=src python -m odw2json.synth2 --n 20 --seed 1 [--type T] [--errors] [--show NAME]
"""

from __future__ import annotations

import argparse
import random
import textwrap
from collections import Counter, defaultdict
from datetime import date, timedelta

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
TYPES = ("odwolanie", "pelnomocnictwo", "przelew", "negatyw")
MONTHS = [
    "stycznia",
    "lutego",
    "marca",
    "kwietnia",
    "maja",
    "czerwca",
    "lipca",
    "sierpnia",
    "września",
    "października",
    "listopada",
    "grudnia",
]

# --- people ---------------------------------------------------------------

FIRST = {  # nominative: genitive, dative, accusative, instrumental, gender
    "Piotr": ("Piotra", "Piotrowi", "Piotra", "Piotrem", "m"),
    "Marek": ("Marka", "Markowi", "Marka", "Markiem", "m"),
    "Tomasz": ("Tomasza", "Tomaszowi", "Tomasza", "Tomaszem", "m"),
    "Paweł": ("Pawła", "Pawłowi", "Pawła", "Pawłem", "m"),
    "Andrzej": ("Andrzeja", "Andrzejowi", "Andrzeja", "Andrzejem", "m"),
    "Michał": ("Michała", "Michałowi", "Michała", "Michałem", "m"),
    "Jakub": ("Jakuba", "Jakubowi", "Jakuba", "Jakubem", "m"),
    "Krzysztof": ("Krzysztofa", "Krzysztofowi", "Krzysztofa", "Krzysztofem", "m"),
    "Anna": ("Anny", "Annie", "Annę", "Anną", "f"),
    "Katarzyna": ("Katarzyny", "Katarzynie", "Katarzynę", "Katarzyną", "f"),
    "Joanna": ("Joanny", "Joannie", "Joannę", "Joanną", "f"),
    "Ewa": ("Ewy", "Ewie", "Ewę", "Ewą", "f"),
    "Magdalena": ("Magdaleny", "Magdalenie", "Magdalenę", "Magdaleną", "f"),
    "Monika": ("Moniki", "Monice", "Monikę", "Moniką", "f"),
    "Agnieszka": ("Agnieszki", "Agnieszce", "Agnieszkę", "Agnieszką", "f"),
    "Barbara": ("Barbary", "Barbarze", "Barbarę", "Barbarą", "f"),
}
SURNAMES = [
    ("Kowalski", "adj"),
    ("Wiśniewski", "adj"),
    ("Zieliński", "adj"),
    ("Szymański", "adj"),
    ("Wojciechowski", "adj"),
    ("Kamiński", "adj"),
    ("Lewandowski", "adj"),
    ("Dąbrowski", "adj"),
    ("Jabłoński", "adj"),
    ("Sikorski", "adj"),
    ("Ostrowski", "adj"),
    ("Zawadzki", "adj"),
    ("Nowak", "c"),
    ("Kowalczyk", "c"),
    ("Wójcik", "c"),
    ("Michalak", "c"),
    ("Walczak", "c"),
    ("Lipowczyk", "c"),
    ("Mazur", "c"),
    ("Pawlak", "c"),
]
CASES = ("gen", "dat", "acc", "ins")
TITLES = {
    "rp": {
        "abbr": "r. pr.",
        "nom": "radca prawny",
        "gen": "radcy prawnego",
        "dat": "radcy prawnemu",
        "acc": "radcę prawnego",
        "ins": "radcą prawnym",
    },
    "adw": {
        "abbr": "adw.",
        "nom": "adwokat",
        "gen": "adwokata",
        "dat": "adwokatowi",
        "acc": "adwokata",
        "ins": "adwokatem",
    },
}
HONOR = {
    "m": {"nom": "Pan", "gen": "Pana", "dat": "Panu", "acc": "Pana", "ins": "Panem"},
    "f": {"nom": "Pani", "gen": "Pani", "dat": "Pani", "acc": "Panią", "ins": "Panią"},
}


def make_person(rng: random.Random, gender: str | None = None) -> dict:
    gender = gender or rng.choice("mf")
    first = rng.choice([f for f, v in FIRST.items() if v[4] == gender])
    masc, kind = rng.choice(SURNAMES)
    f = FIRST[first]
    stem = masc[:-1]
    forms = {"nom": f"{first} {masc if gender == 'm' else (stem + 'a' if kind == 'adj' else masc)}"}
    for i, case in enumerate(CASES):
        if kind == "adj":
            if gender == "m":
                last = stem + {"gen": "iego", "dat": "iemu", "acc": "iego", "ins": "im"}[case]
            else:
                last = stem + {"gen": "iej", "dat": "iej", "acc": "ą", "ins": "ą"}[case]
        else:
            last = masc
            if gender == "m":
                last = masc + {"gen": "a", "dat": "owi", "acc": "a", "ins": "iem"}[case]
        forms[case] = f"{f[i]} {last}"
    return {"first": first, "g": gender, "forms": forms, "nom": forms["nom"], "last": forms["nom"].split()[1]}


def luhn_free_digits(rng: random.Random, n: int) -> str:
    return str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(n - 1))


def make_pesel(rng: random.Random) -> str:
    base = [rng.randint(0, 9) for _ in range(2)] + [rng.choice([0, 1, 2, 3]), rng.randint(1, 9)]
    base += [rng.choice([0, 1, 2]), rng.randint(1, 8)] + [rng.randint(0, 9) for _ in range(4)]
    w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    return "".join(map(str, base)) + str((10 - sum(a * b for a, b in zip(base, w)) % 10) % 10)


# --- organizations --------------------------------------------------------

BRANDS = [
    "Vistula",
    "Karpaty",
    "Baltic",
    "Mazovia",
    "Silesia",
    "Podlasie",
    "Warta",
    "Tatra",
    "Odra",
    "Nadmorska",
    "Eko-Bud",
    "Elektro-Mont",
    "Pol-Tech",
    "Medi-Serwis",
    "Trans-Kom",
    "Inter-Bud",
    "Zielony Dom",
    "Alfa-Net",
    "Mostostal Północ",
    "Instal-Pro",
    "Brukpol",
    "Kolmex",
    "Dromet",
    "Hydro-Sys",
]
SECTORS = [
    "Inżynieria",
    "Budownictwo",
    "Systemy Informatyczne",
    "Transport",
    "Usługi Komunalne",
    "Energetyka",
    "Serwis",
    "Technologie",
    "Infrastruktura",
    "Logistyka",
    "Instalacje",
    "Dostawy Medyczne",
]
FORMS = ["S.A.", "sp. z o.o.", "Sp. z o.o.", "sp. j.", "sp. k.", "sp. z o.o. sp.k."]
CITIES = [
    "Warszawa",
    "Kraków",
    "Wrocław",
    "Poznań",
    "Gdańsk",
    "Szczecin",
    "Lublin",
    "Katowice",
    "Białystok",
    "Rzeszów",
    "Opole",
    "Kielce",
    "Olsztyn",
    "Toruń",
    "Radom",
    "Gliwice",
]
STREETS = [
    "Lipowa",
    "Kolejowa",
    "Szkolna",
    "Polna",
    "Ogrodowa",
    "Leśna",
    "Długa",
    "Krótka",
    "Słoneczna",
    "Mickiewicza",
    "Piłsudskiego",
    "Sienkiewicza",
    "Kościuszki",
    "Przemysłowa",
    "Fabryczna",
]
AUTHORITIES = [  # nominative, genitive
    ("Gmina Miejska Kalwaria", "Gminy Miejskiej Kalwaria"),
    ("Powiat Sztumski", "Powiatu Sztumskiego"),
    ("Zarząd Dróg Wojewódzkich", "Zarządu Dróg Wojewódzkich"),
    ("Szpital Powiatowy im. Jana Pawła II", "Szpitala Powiatowego im. Jana Pawła II"),
    ("Uniwersytet Medyczny", "Uniwersytetu Medycznego"),
    (
        "Miejskie Przedsiębiorstwo Wodociągów i Kanalizacji sp. z o.o.",
        "Miejskiego Przedsiębiorstwa Wodociągów i Kanalizacji sp. z o.o.",
    ),
    ("Politechnika Rzeszowska im. Ignacego Łukasiewicza", "Politechniki Rzeszowskiej im. Ignacego Łukasiewicza"),
    ("Regionalny Zarząd Gospodarki Wodnej", "Regionalnego Zarządu Gospodarki Wodnej"),
    ("Wojewódzki Szpital Zespolony", "Wojewódzkiego Szpitala Zespolonego"),
    ("Zespół Szkół Technicznych", "Zespołu Szkół Technicznych"),
    ("Miejski Zakład Komunikacji sp. z o.o.", "Miejskiego Zakładu Komunikacji sp. z o.o."),
    ("Śląski Park Technologii", "Śląskiego Parku Technologii"),
    ("Dom Pomocy Społecznej", "Domu Pomocy Społecznej"),
    ("Państwowa Straż Pożarna Komenda Wojewódzka", "Państwowej Straży Pożarnej Komendy Wojewódzkiej"),
]
TITLES_ZP = [
    "Budowa kanalizacji sanitarnej wraz z przyłączami w miejscowości {c}",
    "Dostawa sprzętu komputerowego wraz z oprogramowaniem i usługą wdrożenia",
    "Remont dachu i elewacji budynku administracyjnego przy ul. {s} w {c}",
    "Świadczenie usług sprzątania obiektów w latach 2026-2028",
    "Dostawa energii elektrycznej dla jednostek organizacyjnych na rok 2027",
    "Przebudowa drogi powiatowej nr 1234 na odcinku {c} - {c2}",
    "Zakup i dostawa aparatury medycznej do pracowni diagnostycznej",
    "Modernizacja systemu ogrzewania i wentylacji w budynku szkoły",
    "Wykonanie robót budowlanych oraz dostawa i montaż wyposażenia w ramach zadania, polegającego na przebudowie i rozbudowie budynku w {c}",
    "Usługa ochrony fizycznej mienia oraz monitoringu obiektów",
    "Dostawa pojazdów specjalistycznych dla jednostki ratowniczej",
    "Opracowanie dokumentacji projektowej i nadzór autorski dla inwestycji w {c}",
    "Zimowe utrzymanie dróg gminnych w sezonie 2026/2027",
    "Zakup licencji oraz wdrożenie systemu elektronicznego obiegu dokumentów",
]
NUMBER_PATTERNS = [
    "ZP.{n}.{y}",
    "DZP.260.{m}.{y}",
    "V.ROZ.2710.{n}.{y}",
    "ZSCKR/{n}/{y}",
    "WZP-271-{m}/{yy}",
    "OR-IV.272.{m}.{y}",
    "{m}/PN/{y}",
    "BZP/ZP/{m}/{y}",
    "TP/{n}/{yy}/ZO",
    "ZZP.271.{m}.{y}.{n}",
]


def make_company(rng: random.Random) -> str:
    return f"{rng.choice(BRANDS)} {rng.choice(SECTORS)} {rng.choice(FORMS)}"


def make_addr(rng: random.Random, city: str | None = None) -> str:
    city = city or rng.choice(CITIES)
    return f"ul. {rng.choice(STREETS)} {rng.randint(1, 120)}, {rng.randint(10, 99)}-{rng.randint(100, 999)} {city}"


def make_org(rng: random.Random, name: str, with_ids: tuple = (0.9, 0.95, 0.85)) -> dict:
    return {
        "name": name,
        "addr": make_addr(rng),
        "krs": "0000" + "".join(str(rng.randint(0, 9)) for _ in range(6)) if rng.random() < with_ids[0] else None,
        "nip": luhn_free_digits(rng, 10) if rng.random() < with_ids[1] else None,
        "regon": luhn_free_digits(rng, 9) if rng.random() < with_ids[2] else None,
    }


def nip_text(rng: random.Random, nip: str) -> str:
    return rng.choice([nip, f"{nip[:3]}-{nip[3:6]}-{nip[6:8]}-{nip[8:]}", f"{nip[:3]} {nip[3:6]} {nip[6:8]} {nip[8:]}"])


# --- dates, money, accounts -----------------------------------------------


def rand_date(rng: random.Random, lo: date = date(2025, 9, 1), days: int = 440) -> date:
    return lo + timedelta(days=rng.randrange(days))


def fmt_date(d: date, style: str) -> str:
    return {
        "dot": f"{d.day:02d}.{d.month:02d}.{d.year}",
        "dot_r": f"{d.day:02d}.{d.month:02d}.{d.year} r.",
        "dot1": f"{d.day}.{d.month}.{d.year} r.",
        "long": f"{d.day} {MONTHS[d.month - 1]} {d.year} r.",
        "roku": f"{d.day} {MONTHS[d.month - 1]} {d.year} roku",
        "iso": d.isoformat(),
        "dash": f"{d.day:02d}-{d.month:02d}-{d.year}",
        "slash": f"{d.day:02d}/{d.month:02d}/{d.year}",
    }[style]


def iban(rng: random.Random, bank: str) -> str:
    """Give 26 digits (without PL) with a correct check number."""
    bban = bank + "".join(str(rng.randint(0, 9)) for _ in range(16))
    check = 98 - int(bban + "252100") % 97
    return f"{check:02d}{bban}"


BANK_CODES = [
    "10201026",
    "11402004",
    "10501012",
    "10901014",
    "12401037",
    "11601202",
    "24901044",
    "16001462",
    "19401076",
    "81240001",
    "86190003",
]


def account_text(rng: random.Random, acc: str, style: str | None = None) -> str:
    style = style or rng.choice(["plain", "pl", "grouped", "plgrouped"])
    grouped = f"{acc[:2]} {acc[2:6]} {acc[6:10]} {acc[10:14]} {acc[14:18]} {acc[18:22]} {acc[22:]}"
    return {"plain": acc, "pl": "PL" + acc, "grouped": grouped, "plgrouped": "PL " + grouped}[style]


def money_text(rng: random.Random, v: float, style: str | None = None, cur: bool = True) -> str:
    whole, frac = f"{v:.2f}".split(".")
    sp = " " if rng.random() < 0.3 else " "
    grouped = f"{int(whole):,}".replace(",", sp)
    style = style or rng.choice(["pl", "plain", "dot", "cur_first"])
    body = {
        "pl": f"{grouped},{frac}",
        "plain": f"{whole},{frac}",
        "dot": f"{int(whole):,}.{frac}".replace(",", " "),
        "cur_first": f"{grouped},{frac}",
    }[style]
    if not cur:
        return body
    if style == "cur_first":
        return f"PLN {body}"
    return f"{body} {rng.choice(['PLN', 'zł', 'PLN'])}"


def words_pl(n: int) -> str:
    u = [
        "",
        "jeden",
        "dwa",
        "trzy",
        "cztery",
        "pięć",
        "sześć",
        "siedem",
        "osiem",
        "dziewięć",
        "dziesięć",
        "jedenaście",
        "dwanaście",
        "trzynaście",
        "czternaście",
        "piętnaście",
        "szesnaście",
        "siedemnaście",
        "osiemnaście",
        "dziewiętnaście",
    ]
    t = [
        "",
        "",
        "dwadzieścia",
        "trzydzieści",
        "czterdzieści",
        "pięćdziesiąt",
        "sześćdziesiąt",
        "siedemdziesiąt",
        "osiemdziesiąt",
        "dziewięćdziesiąt",
    ]
    h = ["", "sto", "dwieście", "trzysta", "czterysta", "pięćset", "sześćset", "siedemset", "osiemset", "dziewięćset"]

    def below_1000(k: int) -> str:
        parts = [h[k // 100]]
        r = k % 100
        parts.append(u[r] if r < 20 else f"{t[r // 10]} {u[r % 10]}")
        return " ".join(p for p in parts if p).strip()

    th, rest = divmod(n, 1000)
    out = []
    if th:
        form = (
            "tysiąc"
            if th == 1
            else ("tysiące" if th % 10 in (2, 3, 4) and th % 100 not in range(12, 15) else "tysięcy")
        )
        out.append(("" if th == 1 else below_1000(th) + " ") + form)
    if rest:
        out.append(below_1000(rest))
    return " ".join(out)


# --- the common case of an appeal -------------------------------------------

CH = {  # item of the list of charges, the fact sentence
    1: [
        (
            "odrzuceniu oferty Odwołującego na podstawie art. 226 ust. 1 pkt 5 Pzp, o czym Zamawiający zawiadomił w dniu {d}",
            "Zamawiający w dniu {d} zawiadomił Odwołującego o odrzuceniu jego oferty.",
        ),
        (
            "czynności odrzucenia oferty Odwołującego, wskazanej w zawiadomieniu z dnia {d}",
            "Pismem z dnia {d} Zamawiający poinformował o odrzuceniu oferty złożonej przez Odwołującego.",
        ),
        (
            "odrzuceniu oferty złożonej przez Odwołującego jako niezgodnej z warunkami zamówienia (informacja z {d})",
            "Informację o odrzuceniu oferty Odwołujący otrzymał {d}.",
        ),
    ],
    2: [
        (
            "wyborze jako najkorzystniejszej oferty wykonawcy {x}, o czym Zamawiający zawiadomił w dniu {d}",
            "W dniu {d} Zamawiający zawiadomił o wyborze oferty wykonawcy {x} jako najkorzystniejszej.",
        ),
        (
            "czynności wyboru najkorzystniejszej oferty złożonej przez {x}, dokonanej w dniu {d}",
            "Zamawiający dokonał wyboru oferty {x} w dniu {d}.",
        ),
        (
            "ogłoszeniu wyniku postępowania i wyborze oferty {x} (zawiadomienie z {d})",
            "Wynik postępowania ogłoszono {d}.",
        ),
    ],
    3: [
        (
            "wykluczeniu Odwołującego z postępowania na podstawie art. 108 ust. 1 pkt 5 Pzp (zawiadomienie z dnia {d})",
            "Zamawiający w dniu {d} wykluczył Odwołującego z postępowania.",
        ),
        (
            "czynności wykluczenia Odwołującego z postępowania, o której powiadomiono go w dniu {d}",
            "Decyzję o wykluczeniu Odwołujący otrzymał {d}.",
        ),
        (
            "podjęciu decyzji o wykluczeniu Odwołującego z udziału w postępowaniu w dniu {d}",
            "W dniu {d} Odwołujący został wykluczony.",
        ),
    ],
    4: [
        (
            "ustaleniu treści Specyfikacji Warunków Zamówienia, opublikowanej w dniu {d}",
            "Zamawiający w dniu {d} opublikował Specyfikację Warunków Zamówienia.",
        ),
        (
            "opublikowaniu w dniu {d} SWZ zawierającej wadliwe warunki udziału w postępowaniu",
            "SWZ udostępniono na stronie prowadzonego postępowania {d}.",
        ),
        (
            "sformułowaniu kryteriów oceny ofert w SWZ udostępnionej wykonawcom w dniu {d}",
            "Dokumenty zamówienia, w tym SWZ, zostały zamieszczone w dniu {d}.",
        ),
    ],
    5: [
        ("modyfikacji treści SWZ dokonanej w dniu {d}", "Zamawiający w dniu {d} dokonał zmiany treści SWZ."),
        (
            "zmianie SWZ ogłoszonej wykonawcom w dniu {d} bez przedłużenia terminu składania ofert",
            "Zmiana SWZ została opublikowana {d}.",
        ),
        (
            "wprowadzeniu w dniu {d} modyfikacji dokumentów zamówienia w zakresie warunków udziału",
            "Modyfikację SWZ przekazano wykonawcom {d}.",
        ),
    ],
    6: [
        (
            "udzieleniu w dniu {d} odpowiedzi na pytania wykonawców w sposób zmieniający treść SWZ",
            "Zamawiający w dniu {d} udzielił odpowiedzi na pytania do SWZ.",
        ),
        ("wyjaśnieniach treści SWZ opublikowanych w dniu {d}", "Wyjaśnienia treści SWZ zamieszczono {d}."),
        ("odpowiedziach na zapytania do SWZ udzielonych dnia {d}", "Odpowiedzi na pytania opublikowano w dniu {d}."),
    ],
    7: [
        (
            "zaniechaniu odrzucenia oferty wykonawcy {x}, mimo że oferta ta podlega odrzuceniu; Odwołujący dowiedział się o jej treści w dniu {d}",
            "W dniu {d} Odwołujący zapoznał się z ofertą wykonawcy {x}.",
        ),
        (
            "zaniechaniu odrzucenia oferty {x} pomimo jej niezgodności z SWZ (zawiadomienie o wyborze z dnia {d})",
            "Zawiadomienie o wyborze oferty {x} datowane jest na {d}.",
        ),
        (
            "niedokonaniu odrzucenia oferty złożonej przez {x}, o czym Odwołujący powziął wiedzę {d}",
            "Wiedzę o ofercie {x} Odwołujący powziął {d}.",
        ),
    ],
    8: [
        (
            "zaniechaniu wykluczenia wykonawcy {x} z postępowania, o czym Odwołujący dowiedział się w dniu {d}",
            "W dniu {d} Zamawiający poinformował o wyborze oferty wykonawcy {x}, którego nie wykluczono.",
        ),
        (
            "niewykluczeniu z postępowania {x} pomimo podstaw z art. 109 ust. 1 pkt 7 Pzp (informacja z dnia {d})",
            "Informacja o wyniku postępowania pochodzi z dnia {d}.",
        ),
        (
            "zaniechaniu wykluczenia {x} z udziału w postępowaniu, stwierdzonym dnia {d}",
            "Zaniechanie wykluczenia {x} ujawniło się w dniu {d}.",
        ),
    ],
    9: [
        ("unieważnieniu postępowania w dniu {d}", "Zamawiający w dniu {d} unieważnił postępowanie."),
        (
            "czynności unieważnienia postępowania na podstawie art. 255 pkt 3 Pzp, o której zawiadomiono wykonawców w dniu {d}",
            "Zawiadomienie o unieważnieniu postępowania wysłano {d}.",
        ),
        (
            "podjęciu decyzji o unieważnieniu postępowania o udzielenie zamówienia (zawiadomienie z {d})",
            "Decyzja o unieważnieniu postępowania zapadła {d}.",
        ),
    ],
    10: [
        (
            "zaniechaniu unieważnienia postępowania, mimo że jest ono obarczone wadą uniemożliwiającą zawarcie umowy; w dniu {d} Zamawiający zawiadomił o wyborze oferty",
            "W dniu {d} Zamawiający wybrał ofertę i nie unieważnił postępowania.",
        ),
        (
            "niedokonaniu unieważnienia postępowania na podstawie art. 255 pkt 6 Pzp (zawiadomienie z dnia {d})",
            "Zamawiający pismem z {d} podtrzymał postępowanie.",
        ),
        (
            "zaniechaniu unieważnienia postępowania pomimo istotnej zmiany okoliczności, o czym Odwołujący dowiedział się {d}",
            "Odwołujący dowiedział się o kontynuacji postępowania {d}.",
        ),
    ],
    11: [
        (
            "opisie przedmiotu zamówienia (OPZ) opublikowanym w dniu {d}, który ogranicza konkurencję",
            "Opis przedmiotu zamówienia został opublikowany w dniu {d}.",
        ),
        (
            "sformułowaniu Opisu Przedmiotu Zamówienia udostępnionego wykonawcom {d}",
            "OPZ zamieszczono wraz z ogłoszeniem {d}.",
        ),
        (
            "opisaniu przedmiotu zamówienia w sposób wskazujący na produkty jednego producenta (dokumentacja z dnia {d})",
            "Dokumentację z opisem przedmiotu zamówienia udostępniono {d}.",
        ),
    ],
    12: [
        (
            "ustaleniu projektowanych postanowień umowy opublikowanych w dniu {d}",
            "Projektowane postanowienia umowy opublikowano {d}.",
        ),
        (
            "wzorze umowy stanowiącym załącznik do SWZ, udostępnionym w dniu {d}, w zakresie kar umownych",
            "Wzór umowy udostępniono wykonawcom w dniu {d}.",
        ),
        (
            "kształcie projektowanych postanowień umowy w sprawie zamówienia publicznego (publikacja z {d})",
            "Projekt umowy zamieszczono w dniu {d}.",
        ),
    ],
}
SHORT = {
    1: "bezpodstawne odrzucenie oferty Odwołującego",
    2: "wadliwy wybór oferty jako najkorzystniejszej",
    3: "bezpodstawne wykluczenie Odwołującego",
    4: "wadliwe ukształtowanie warunków w SWZ",
    5: "wadliwą zmianę SWZ",
    6: "udzielenie wyjaśnień zmieniających treść SWZ",
    7: "zaniechanie odrzucenia oferty konkurenta",
    8: "zaniechanie wykluczenia konkurenta",
    9: "bezpodstawne unieważnienie postępowania",
    10: "zaniechanie unieważnienia postępowania",
    11: "nieprecyzyjny opis przedmiotu zamówienia",
    12: "niedozwolone postanowienia wzoru umowy",
}
FILLER = [
    "Odwołujący posiada interes we wniesieniu odwołania, ponieważ może ponieść szkodę w postaci utraty możliwości uzyskania zamówienia.",
    "Zaskarżona czynność narusza zasadę uczciwej konkurencji oraz równego traktowania wykonawców, o której mowa w art. 16 pkt 1 Pzp.",
    "Zamawiający nie wykazał, że przyjęte rozwiązanie jest uzasadnione przedmiotem zamówienia ani jego wartością.",
    "Zgodnie z utrwalonym orzecznictwem Krajowej Izby Odwoławczej ciężar wykazania okoliczności spoczywa na Zamawiającym.",
    "Wobec powyższego zarzuty odwołania są w pełni uzasadnione i zasługują na uwzględnienie.",
    "Zamawiający wyznaczył termin składania ofert na dzień {dd}, co oznacza, że czas na przygotowanie oferty jest ograniczony.",
    "Wpis od odwołania w kwocie {fee} został uiszczony przelewem w dniu {pd}.",
    "Odwołujący wykazał interes w uzyskaniu zamówienia, składając ofertę w terminie wyznaczonym przez Zamawiającego.",
    "Przepisy ustawy Prawo zamówień publicznych nie przewidują możliwości odmowy rozpatrzenia takiego zarzutu.",
]


def make_case(rng: random.Random) -> dict:
    """Make the data of one appeal. The gold JSON is built from it."""
    c: dict = {}
    c["town"] = rng.choice(CITIES) if rng.random() < 0.65 else None
    c["date"] = rand_date(rng)
    c["dstyle"] = rng.choice(["dot", "dot_r", "long", "dot1"])
    n_odw = 2 if rng.random() < 0.15 else 1
    person_mode = rng.random() < 0.12
    odw = []
    for i in range(n_odw):
        if person_mode and i == 0:
            p = make_person(rng)
            brand = rng.choice(BRANDS).upper()
            o = make_org(rng, f"{brand} {p['nom']}", (0.0, 1.0, 0.9))
            o["person"] = p
        else:
            o = make_org(rng, make_company(rng))
            o["person"] = None
        odw.append(o)
    c["odw"] = odw
    c["no_attorney"] = rng.random() < 0.12
    if not c["no_attorney"]:
        n_att = rng.choice([1, 1, 2, 3])
        atts = [make_person(rng) for _ in range(n_att)]
        for a in atts:
            a["title"] = rng.choice(["rp", "adw"])
        surname = atts[0]["last"]
        office = rng.choice(
            [
                f"Kancelaria Radców Prawnych {surname} i Wspólnicy sp.k.",
                f"Kancelaria Adwokacka {atts[0]['nom']}",
                f"{surname} & Partnerzy Kancelaria Prawna sp.p.",
                f"Kancelaria Prawna {surname} Sp. z o.o.",
                f"Kancelaria Radcy Prawnego {atts[0]['nom']}",
                "Kancelaria Prawa Zamówień Publicznych " + surname + " sp.k.",
            ]
        )
        slug = "".join(ch for ch in surname.lower() if ch.isascii() and ch.isalpha()) or "kancelaria"
        mail = rng.choice(
            [
                f"biuro@{slug}.pl",
                f"kancelaria@{slug}-legal.com.pl",
                f"sekretariat@{slug}.example",
                f"{slug}@adwokat.pl",
                f"zamowienia@{slug}.eu",
            ]
        )
        c["att"] = {
            "people": atts,
            "office": office if rng.random() < 0.88 else None,
            "mail": mail if rng.random() < 0.88 else None,
            "addr": make_addr(rng),
            "phone": f"{rng.randint(22, 91)} {rng.randint(100, 999)} {rng.randint(10, 99)} {rng.randint(10, 99)}",
        }
    else:
        c["att"] = None
    n_zam = 2 if rng.random() < 0.18 else 1
    zam = []
    for i in range(n_zam):
        nom, gen = rng.choice(AUTHORITIES)
        city = rng.choice(CITIES)
        nom_full = f"{nom} w {city}" if rng.random() < 0.4 else nom
        z = make_org(rng, nom_full, (0.35, 0.95, 0.8))
        z["gen"] = gen if nom_full == nom else f"{gen} w {city}"
        zam.append(z)
    names = {z["name"] for z in zam}
    if len(names) < len(zam):
        zam[1]["name"] += " - Oddział"
        zam[1]["gen"] += " - Oddziału"
    marked = rng.random() > 0.15
    lead_idx = rng.randrange(len(zam))
    for i, z in enumerate(zam):
        z["lead"] = None if len(zam) == 1 else ((1 if i == lead_idx else 0) if marked else 0)
    c["zam"] = zam
    d = rand_date(rng, date(2026, 1, 5), 330)
    year = d.year
    bzp_num = f"{rng.randint(0, 999999):08d}"
    bzp_suffix = f"/{rng.randint(1, 9):02d}" if rng.random() < 0.2 else ""
    has_bzp = rng.random() < 0.65
    c["bzp"] = f"{year}/BZP{bzp_num}{bzp_suffix}" if has_bzp else None
    c["bzp_text"] = rng.choice([f"{year}/BZP {bzp_num}{bzp_suffix}", f"{year}/BZP{bzp_num}{bzp_suffix}"])
    has_ted = rng.random() < 0.45
    ted_n = f"{rng.randint(100000, 899999)}"
    c["ted"] = f"{ted_n}-{year}" if has_ted else None
    c["ted_style"] = rng.choice(["plain", "s"])
    c["ted_text"] = f"{ted_n}-{year}" if c["ted_style"] == "plain" else f"{year}/S {rng.randint(60, 240)}-{ted_n}"
    pat = rng.choice(NUMBER_PATTERNS)
    c["nr"] = (
        pat.format(n=rng.randint(10, 999), m=rng.randint(1, 60), y=year, yy=year % 100) if rng.random() < 0.92 else None
    )
    c["title"] = rng.choice(TITLES_ZP).format(c=rng.choice(CITIES), c2=rng.choice(CITIES), s=rng.choice(STREETS))
    n_ch = rng.choice([1, 1, 2, 3])
    codes = rng.sample(range(1, 13), n_ch)
    base = rand_date(rng, date(2025, 9, 1), 400)
    c["charges"] = [(code, base - timedelta(days=rng.randrange(0, 12))) for code in codes]
    c["winner"] = make_company(rng)
    c["fee"] = rng.choice(["7 500,00 zł", "10 000,00 zł", "15 000,00 zł"])
    c["deadline"] = base + timedelta(days=rng.randint(10, 40))
    c["paid"] = base + timedelta(days=rng.randint(1, 5))
    c["dfmt"] = rng.choice(["long", "roku", "dot_r", "dot"])
    return c


def odw_gold(c: dict) -> dict:
    code, day = c["charges"][0]
    lead = c["odw"][0]
    att = c["att"]
    pel = {"imie_nazwisko": None, "nazwa": None, "mail": None}
    if att:
        pel = {"imie_nazwisko": att["people"][0]["nom"], "nazwa": att["office"], "mail": att["mail"]}
    return {
        "OdwolanieKIO": {
            "data": c["date"].isoformat() if c["town"] else None,
            "czynnosc_dzien": day.isoformat(),
            "czynnosc_powod_id": code,
            "czynnosc_opis": CODES[code],
            "miejscowosc": c["town"],
        },
        "Odwolujacy": [
            {
                "krs": lead["krs"],
                "nazwa": lead["name"],
                "nip": lead["nip"],
                "regon": lead["regon"],
                "przez-pelnomocnika": 1 if att else 0,
                "pelnomocnik": pel,
            }
        ],
        "Zamawiajacy": [
            {
                "krs": z["krs"],
                "nazwa": z["name"],
                "nip": z["nip"],
                "regon": z["regon"],
                "prowadzacy_postepowanie": z["lead"],
            }
            for z in c["zam"]
        ],
        "ZamowieniePubliczne": {
            "numer_bzp": c["bzp"],
            "numer_postepowania": c["nr"],
            "numer_ted": c["ted"],
            "tytul": c["title"],
        },
    }


# --- rendering of an appeal -------------------------------------------------


def ids_inline(rng: random.Random, o: dict, sep: str = ", ") -> str:
    parts = []
    if o["krs"]:
        parts.append(f"KRS: {o['krs']}")
    if o["nip"]:
        parts.append(f"NIP: {nip_text(rng, o['nip'])}")
    if o["regon"]:
        parts.append(f"REGON: {o['regon']}")
    return sep.join(parts)


def att_names(c: dict, rng: random.Random, case: str = "nom", style: str = "abbr") -> str:
    out = []
    for a in c["att"]["people"]:
        t = TITLES[a["title"]]
        title = t["abbr"] if style == "abbr" else t[case]
        out.append(f"{title} {a['forms'][case]}")
    return ", ".join(out)


def att_office_lines(c: dict, label: str = "adres do korespondencji: ") -> list[str]:
    a = c["att"]
    lines = []
    if a["office"]:
        lines.append(f"{label}{a['office']}, {a['addr']}")
    else:
        lines.append(f"{label}{a['addr']}")
    contact = [f"tel. {a['phone']}"]
    if a["mail"]:
        contact.append(f"e-mail: {a['mail']}")
    lines.append(", ".join(contact))
    return lines


def odw_party_lines(c: dict, rng: random.Random, style: str) -> list[str]:
    """The lines about the Odwolujacy. The lead is always the first one."""
    lines = []
    if len(c["odw"]) > 1:
        lines.append(
            "Konsorcjum wykonawców w składzie:" if style != "pl" else "Wykonawcy wspólnie ubiegający się o zamówienie:"
        )
    for i, o in enumerate(c["odw"]):
        role = ""
        if len(c["odw"]) > 1:
            role = "Lider konsorcjum: " if i == 0 else "Partner konsorcjum: "
            role = f"{i + 1}) {role}"
        lines.append(f"{role}{o['name']}")
        lines.append(o["addr"])
        ids = ids_inline(rng, o)
        if ids:
            lines.append(ids)
        if o["person"]:
            lines.append("przedsiębiorca wpisany do CEIDG, prowadzący działalność gospodarczą pod firmą " + o["name"])
    return lines


def zam_party_lines(c: dict, rng: random.Random) -> list[str]:
    zam = c["zam"]
    if len(zam) == 1:
        z = zam[0]
        return [z["name"], z["addr"]] + ([ids_inline(rng, z)] if ids_inline(rng, z) else [])
    lines = ["(zamawiający wspólnie przeprowadzający postępowanie na podstawie art. 38 ust. 1 Pzp):"]
    lead_words = rng.choice(
        [
            ("Lider, prowadzący postępowanie", "Partner"),
            ("zamawiający prowadzący postępowanie w imieniu pozostałych", "zamawiający uczestniczący"),
            ("Lider postępowania", "współzamawiający"),
        ]
    )
    for i, z in enumerate(zam):
        if z["lead"] == 1:
            role = lead_words[0]
        elif any(x["lead"] == 1 for x in zam):
            role = lead_words[1]
        else:
            role = "zamawiający"
        lines += [f"{i + 1}) Zamawiający – {role}:", z["name"], z["addr"]]
        ids = ids_inline(rng, z)
        if ids:
            lines.append(ids)
    return lines


def procurement_phrase(c: dict, rng: random.Random, style: int) -> str:
    bzp = f"ogłoszenie o zamówieniu w Biuletynie Zamówień Publicznych nr {c['bzp_text']}" if c["bzp"] else None
    if bzp and style % 2:
        bzp = f"numer ogłoszenia BZP: {c['bzp_text']}"
    ted = f"numer ogłoszenia TED: {c['ted_text']}" if c["ted"] else None
    nr = f"nr referencyjny: {c['nr']}" if c["nr"] else None
    if nr and style == 2:
        nr = f"numer postępowania: {c['nr']}"
    elif nr and style == 3:
        nr = f"znak sprawy: {c['nr']}"
    parts = [p for p in (f"„{c['title']}”", nr, bzp, ted) if p]
    return ", ".join(parts)


def charges_lines(c: dict, rng: random.Random, bullets: str) -> list[str]:
    lines = []
    for i, (code, day) in enumerate(c["charges"], 1):
        item = rng.choice(CH[code])[0] if i > 1 else c.setdefault("first_item", rng.choice(CH[code])[0])
        text = item.format(d=fmt_date(day, c["dfmt"]), x=c["winner"])
        mark = {"paren": f"{i})", "dot": f"{i}.", "alpha": f"{'abcdef'[i - 1]})", "dash": "–"}[bullets]
        lines.append(f"{mark} {text}{';' if i < len(c['charges']) else '.'}")
    return lines


def body_lines(c: dict, rng: random.Random, bullets: str, sections: bool) -> list[str]:
    """The part after the header: charges, facts, reasons and requests."""
    lines = []
    names = ", ".join(o["name"] for o in c["odw"][:1])
    who = "Konsorcjum" if len(c["odw"]) > 1 else names
    if c["att"]:
        lines.append(
            f"Działając w imieniu wykonawcy {who} (dalej: „Odwołujący”), na podstawie pełnomocnictwa załączonego do niniejszego pisma, na podstawie art. 505 ust. 1 i art. 513 ustawy z dnia 11 września 2019 r. – Prawo zamówień publicznych (dalej: „Pzp”), wnoszę odwołanie wobec czynności i zaniechań Zamawiającego, polegających na:"
        )
    else:
        lines.append(
            f"Działając jako wykonawca {who} (dalej: „Odwołujący”), na podstawie art. 505 ust. 1 i art. 513 ustawy Prawo zamówień publicznych (dalej: „Pzp”), wnoszę odwołanie wobec czynności i zaniechań Zamawiającego, polegających na:"
        )
    if sections:
        lines.insert(0, "II. CZYNNOŚCI ZASKARŻONE ODWOŁANIEM")
    lines += charges_lines(c, rng, bullets)
    lines.append("III. ZARZUTY" if sections else "Zaskarżonym czynnościom Zamawiającego zarzucam:")
    for i, (code, _) in enumerate(c["charges"], 1):
        art = rng.choice(["16 pkt 1", "99 ust. 4", "226 ust. 1 pkt 5", "112 ust. 1", "134 ust. 1 pkt 20", "255 pkt 3"])
        lines.append(f"Zarzut nr {i} – {SHORT[code]}, tj. naruszenie art. {art} Pzp.")
    lines.append("IV. UZASADNIENIE" if sections else "Uzasadnienie")
    for _ in range(rng.randint(3, 6)):
        lines.append(
            rng.choice(FILLER).format(
                dd=fmt_date(c["deadline"], c["dfmt"]), fee=c["fee"], pd=fmt_date(c["paid"], c["dfmt"])
            )
        )
    code, day = c["charges"][0]
    fact = rng.choice(CH[code])[1].format(d=fmt_date(day, c["dfmt"]), x=c["winner"])
    lines.insert(-2, "Stan faktyczny: " + fact)
    lines.append("V. WNIOSKI" if sections else "Wnoszę o:")
    lines += [
        "1) uwzględnienie odwołania i nakazanie Zamawiającemu unieważnienia zaskarżonej czynności;",
        "2) przeprowadzenie dowodów z dokumentów wskazanych w uzasadnieniu;",
        "3) zasądzenie od Zamawiającego kosztów postępowania odwoławczego, w tym kosztów zastępstwa.",
    ]
    lines += [
        "Załączniki:",
        "1. Dowód uiszczenia wpisu od odwołania.",
        "2. Pełnomocnictwo dla pełnomocnika Odwołującego." if c["att"] else "2. Odpis z rejestru.",
        "3. Dowód przekazania kopii odwołania Zamawiającemu.",
    ]
    lines.append("")
    if c["att"]:
        lines += ["Pełnomocnik Odwołującego", att_names(c, rng, "nom", rng.choice(["abbr", "nom"]))]
    else:
        lines += [
            "Odwołujący",
            c["odw"][0]["person"]["nom"] if c["odw"][0]["person"] else "(podpis osoby uprawnionej do reprezentacji)",
        ]
    return lines


def header_dateline(c: dict, rng: random.Random, kind: int) -> list[str]:
    if not c["town"]:
        return []
    d = fmt_date(c["date"], c["dstyle"])
    forms = [
        f"{c['town']}, {d}",
        f"{c['town']}, dnia {d}",
        f"{c['town']} {fmt_date(c['date'], 'dot')}",
        f"{c['town']}, {d}",
    ]
    line = forms[kind % 4]
    return [line.rjust(70) if kind % 2 else line]


def wrap(lines: list[str], width: int) -> list[str]:
    out = []
    for ln in lines:
        out += textwrap.wrap(ln, width) if len(ln) > width else [ln]
    return out


def paginate(lines: list[str], rng: random.Random, head: str, per_page: int = 46) -> str:
    pages = [lines[i : i + per_page] for i in range(0, len(lines), per_page)] or [[]]
    out = []
    for k, page in enumerate(pages, 1):
        if k > 1 and head:
            out.append(head)
        out += page
        out.append(f"Strona {k} z {len(pages)}" if head != "-" else f"- {k} -")
    return "\n".join(out)


KIO_ADDR = ["Prezes Krajowej Izby Odwoławczej", "ul. Postępu 17A", "02-676 Warszawa"]


def odw_A(c, rng):
    L = header_dateline(c, rng, 0) + KIO_ADDR
    L += ["Odwołujący:"] + odw_party_lines(c, rng, "k")
    if c["att"]:
        L.append("reprezentowany przez: " + att_names(c, rng))
        L += att_office_lines(c)
    L += ["Zamawiający:"] + zam_party_lines(c, rng)
    L += ["dotyczy: postępowania o udzielenie zamówienia publicznego pn. " + procurement_phrase(c, rng, 0), "ODWOŁANIE"]
    return L + body_lines(c, rng, "paren", False), "Odwołanie"


def odw_B(c, rng):
    L = header_dateline(c, rng, 1) + [
        "",
        "Krajowa Izba Odwoławcza",
        "ul. Postępu 17A, 02-676 Warszawa",
        "(za pośrednictwem Prezesa KIO)",
        "",
    ]
    L += ["ODWOŁANIE", "wobec czynności Zamawiającego w postępowaniu " + procurement_phrase(c, rng, 1), ""]
    L += ["Zamawiający"] + zam_party_lines(c, rng) + [""]
    first = odw_party_lines(c, rng, "k")
    L += ["Odwołujący"] + first
    if c["att"]:
        L += ["Pełnomocnik: " + att_names(c, rng, "nom", "abbr")] + att_office_lines(
            c, "Kancelaria: " if c["att"]["office"] else "adres: "
        )
    return L + body_lines(c, rng, "dot", False), "Odwołanie - Krajowa Izba Odwoławcza"


def odw_C(c, rng):
    """A table where the labels come first and the values come after them."""
    L = header_dateline(c, rng, 2) + KIO_ADDR + ["ODWOŁANIE", "Dane stron postępowania odwoławczego", "Odwołujący"]
    o = c["odw"][0]
    labels = ["Nazwa", "Adres", "KRS", "NIP", "REGON"]
    vals = [o["name"], o["addr"], o["krs"] or "-", nip_text(rng, o["nip"]) if o["nip"] else "-", o["regon"] or "-"]
    if c["att"]:
        labels += ["Pełnomocnik", "Kancelaria", "E-mail pełnomocnika"]
        vals += [att_names(c, rng), (c["att"]["office"] or "-"), c["att"]["mail"] or "-"]
    L += labels + vals
    if len(c["odw"]) > 1:
        p = c["odw"][1]
        L += ["Partner konsorcjum (Lider: " + o["name"] + ")", p["name"], p["addr"], ids_inline(rng, p)]
    for z in c["zam"]:
        lab = ["Zamawiający", "Nazwa", "Adres", "KRS", "NIP", "REGON"] + (
            ["Rola w postępowaniu"] if len(c["zam"]) > 1 else []
        )
        val = [z["name"], z["addr"], z["krs"] or "-", z["nip"] or "-", z["regon"] or "-"]
        if len(c["zam"]) > 1:
            val.append(
                "prowadzący postępowanie (lider)"
                if z["lead"] == 1
                else ("uczestnik" if any(x["lead"] == 1 for x in c["zam"]) else "zamawiający")
            )
        L += lab[:1] + lab[1:] + val
    L += ["Przedmiot postępowania", procurement_phrase(c, rng, 2)]
    return L + body_lines(c, rng, "paren", False), "Odwołanie do KIO"


def odw_D(c, rng):
    """The parties are in a paragraph, as in a letter of a law office."""
    L = []
    if c["att"] and c["att"]["office"]:
        L += [
            c["att"]["office"],
            c["att"]["addr"],
            f"tel. {c['att']['phone']}" + (f", {c['att']['mail']}" if c["att"]["mail"] else ""),
        ]
    L += header_dateline(c, rng, 3)
    L += KIO_ADDR + ["", "ODWOŁANIE", ""]
    o = c["odw"][0]
    z = c["zam"][0]
    txt = f"Odwołujący: {o['name']}, {o['addr']}" + (f" ({ids_inline(rng, o)})" if ids_inline(rng, o) else "")
    if len(c["odw"]) > 1:
        p = c["odw"][1]
        txt += f" – lider konsorcjum, wraz z {p['name']}, {p['addr']} – partnerem konsorcjum"
    if c["att"]:
        txt += ", reprezentowany przez " + att_names(c, rng, "acc", "full")
    txt += "."
    L.append(txt)
    if len(c["zam"]) == 1:
        L.append(
            f"Zamawiający: {z['name']}, {z['addr']}" + (f" ({ids_inline(rng, z)})" if ids_inline(rng, z) else "") + "."
        )
    else:
        L.append(
            "Zamawiający (wspólnie): "
            + "; ".join(
                f"{x['name']}, {x['addr']}"
                + (f" ({ids_inline(rng, x)})" if ids_inline(rng, x) else "")
                + (" – prowadzący postępowanie" if x["lead"] == 1 else "")
                for x in c["zam"]
            )
            + "."
        )
    L.append("Postępowanie: " + procurement_phrase(c, rng, 3) + ".")
    return L + body_lines(c, rng, "alpha", False), "Odwołanie " + (c["nr"] or "")


def odw_E(c, rng):
    """A formal appeal with numbered sections."""
    L = header_dateline(c, rng, 0) + ["Do:"] + KIO_ADDR
    L += ["ODWOŁANIE", "I. OZNACZENIE STRON I POSTĘPOWANIA", "1. Odwołujący (Wykonawca):"] + odw_party_lines(
        c, rng, "pl"
    )
    if c["att"]:
        L += ["Pełnomocnik Odwołującego: " + att_names(c, rng, "nom", "full")]
        L += att_office_lines(c, "Siedziba kancelarii: ")
    L += ["2. Zamawiający:"] + zam_party_lines(c, rng)
    L += ["3. Postępowanie: " + procurement_phrase(c, rng, 2)]
    return L + body_lines(c, rng, "dot", True), "Odwołanie (strona)"


def odw_F(c, rng):
    """The Zamawiajacy is first. The attorney is in an oblique case."""
    L = (
        header_dateline(c, rng, 1)
        + ["Krajowa Izba Odwoławcza", "ul. Postępu 17A", "02-676 Warszawa", "", "Zamawiający:"]
        + zam_party_lines(c, rng)
    )
    L += ["", "Odwołujący:"] + odw_party_lines(c, rng, "k")
    if c["att"]:
        L.append(
            "reprezentowany przez "
            + att_names(c, rng, "acc", "full")
            + (f" z {c['att']['office']}" if c["att"]["office"] else "")
        )
        L += att_office_lines(c, "adres: ")
    L += ["", "ODWOŁANIE", "od czynności Zamawiającego w postępowaniu " + procurement_phrase(c, rng, 0)]
    return L + body_lines(c, rng, "paren", False), "Odwołanie"


def odw_G(c, rng):
    """A short style with a dash list and the word Wykonawca."""
    L = ["Odwołanie", ""] + header_dateline(c, rng, 3)
    L += ["Wykonawca (Odwołujący): " + c["odw"][0]["name"], c["odw"][0]["addr"], ids_inline(rng, c["odw"][0], "; ")]
    if len(c["odw"]) > 1:
        L += [
            "wspólnie z: "
            + c["odw"][1]["name"]
            + ", "
            + c["odw"][1]["addr"]
            + " (konsorcjum, lider: "
            + c["odw"][0]["name"]
            + ")"
        ]
    if c["att"]:
        L += ["Pełnomocnik: " + att_names(c, rng, "nom", "full")] + att_office_lines(c, "Kontakt: ")
    L += ["Zamawiający:"] + zam_party_lines(c, rng)
    L += [
        "Organ odwoławczy: Krajowa Izba Odwoławcza, ul. Postępu 17A, 02-676 Warszawa",
        "Przedmiot: " + procurement_phrase(c, rng, 3),
    ]
    return L + body_lines(c, rng, "dash", False), "Odwołanie / " + c["odw"][0]["name"]


def odw_H(c, rng):
    """The label of each party is a bold word on its own line, then a block."""
    L = KIO_ADDR + header_dateline(c, rng, 0) + ["", "ODWOŁANIE", "(art. 505 Pzp)", "", "STRONY", "ODWOŁUJĄCY"]
    L += odw_party_lines(c, rng, "k")
    if c["att"]:
        L += ["PEŁNOMOCNIK", att_names(c, rng, "nom", "abbr")] + att_office_lines(c, "")
    L += ["ZAMAWIAJĄCY"] + zam_party_lines(c, rng)
    L += ["ZAMÓWIENIE", procurement_phrase(c, rng, 1), ""]
    return L + body_lines(c, rng, "paren", False), "-"


ODW_LAYOUTS = [odw_A, odw_B, odw_C, odw_D, odw_E, odw_F, odw_G, odw_H]


def gen_odwolanie(rng: random.Random, i: int) -> tuple[str, str, dict]:
    c = make_case(rng)
    k = i % len(ODW_LAYOUTS)
    lines, head = ODW_LAYOUTS[k](c, rng)
    text = paginate(wrap(lines, rng.choice([80, 90, 100])), rng, head if head != "-" else "-")
    return f"odwolanie/L{k}/{i:03d}", text, odw_gold(c)


# --- power of attorney ------------------------------------------------------

ROLES = ["Prezes Zarządu", "Członek Zarządu", "Prokurent", "Wiceprezes Zarządu", "Dyrektor"]


def make_pel_case(rng: random.Random, force_two: bool = False) -> dict:
    c = {"town": rng.choice(CITIES), "date": rand_date(rng), "dstyle": rng.choice(["dot", "long", "dot_r"])}
    person_mode = not force_two and rng.random() < 0.15
    mocs = []
    for i in range(2 if force_two else 1):
        if person_mode:
            p = make_person(rng)
            o = make_org(rng, f"{rng.choice(BRANDS).upper()} {p['nom']}", (0.0, 1.0, 0.9))
            o["person"], o["signers"] = p, [p]
        else:
            o = make_org(rng, make_company(rng), (0.9, 0.85, 0.85))
            o["person"] = None
            o["signers"] = []
            for _ in range(rng.choice([1, 1, 2])):
                s = make_person(rng)
                s["role"] = rng.choice(ROLES)
                o["signers"].append(s)
        mocs.append(o)
    c["mocs"] = mocs
    atts = [make_person(rng) for _ in range(rng.choice([1, 1, 2, 3]))]
    for a in atts:
        a["title"] = rng.choice(["rp", "adw"])
        a["pesel"] = make_pesel(rng) if rng.random() < 0.35 else None
        a["reg"] = f"{rng.choice(['WA', 'KR', 'LU', 'GD'])}-{rng.randint(1000, 99999)}"
    c["atts"] = atts
    c["title"] = rng.choice(TITLES_ZP).format(c=rng.choice(CITIES), c2=rng.choice(CITIES), s=rng.choice(STREETS))
    c["nr"] = rng.choice(NUMBER_PATTERNS).format(n=rng.randint(10, 999), m=rng.randint(1, 60), y=2026, yy=26)
    c["auth"] = rng.choice(AUTHORITIES)
    return c


def pel_gold(c: dict) -> dict:
    mocs = []
    for o in c["mocs"]:
        p = o["person"]
        mocs.append(
            {
                "data": {
                    "imie_nazwisko": p["nom"] if p else None,
                    "krs": o["krs"],
                    "nazwa": o["name"],
                    "nip": o["nip"],
                    "typ": "osoba_fizyczna" if p else "osoba_prawna",
                },
                "podpisujacy": [{"imie_nazwisko": s["nom"]} for s in o["signers"]],
            }
        )
    return {"mocodawca": mocs, "pelnomocnicy": [{"imie_nazwisko": a["nom"], "pesel": a["pesel"]} for a in c["atts"]]}


def pel_att(a: dict, rng: random.Random, case: str, style: str, pesel: bool = True) -> str:
    t = TITLES[a["title"]]
    s = f"{t['abbr'] if style == 'abbr' else t[case]} {a['forms'][case]}"
    extra = []
    if a["pesel"] and pesel:
        extra.append(f"PESEL {a['pesel']}")
    extra.append(f"nr wpisu na listę: {a['reg']}")
    return f"{s} ({', '.join(extra)})"


def pel_moc(o: dict, rng: random.Random, sep: str = ", ") -> str:
    parts = [o["name"], o["addr"]]
    ids = ids_inline(rng, o, sep)
    return sep.join(parts + ([ids] if ids else []))


def pel_signers(c: dict, label: str = "Mocodawca:") -> list[str]:
    L = []
    for o in c["mocs"]:
        L += [label if len(c["mocs"]) == 1 else f"{label} {o['name']}"]
        for s in o["signers"]:
            L += ["............................", s["nom"]] + ([s["role"]] if s.get("role") else [])
    return L


def pel_scope(rng: random.Random) -> list[str]:
    items = [
        "wniesienia odwołania do Prezesa Krajowej Izby Odwoławczej oraz jego cofnięcia",
        "zastępowania Mocodawcy na posiedzeniach i rozprawach przed Krajową Izbą Odwoławczą",
        "składania i odbierania pism procesowych, wniosków i oświadczeń",
        "wniesienia skargi na orzeczenie Krajowej Izby Odwoławczej",
        "udzielania dalszych pełnomocnictw",
    ]
    return rng.sample(items, 4)


def pel_A(c, rng):
    L = [f"{c['town']}, {fmt_date(c['date'], c['dstyle'])}", "PEŁNOMOCNICTWO", "§ 1. Mocodawca"]
    L += [f"Mocodawcą jest {pel_moc(o, rng)}." for o in c["mocs"]]
    L += [
        "§ 2. Pełnomocnik",
        "Mocodawca ustanawia pełnomocnikiem: " + "; ".join(pel_att(a, rng, "acc", "abbr") for a in c["atts"]) + ".",
    ]
    L += [
        "§ 3. Postępowanie",
        f"Pełnomocnictwo dotyczy postępowania „{c['title']}”, numer postępowania: {c['nr']}, prowadzonego przez {c['auth'][0]}.",
        "§ 4. Zakres umocowania",
        "Pełnomocnik jest umocowany do:",
    ] + [f"– {x}," for x in pel_scope(rng)]
    L += ["Pełnomocnictwo obowiązuje do zakończenia postępowania odwoławczego.", ""] + pel_signers(c)
    L += ["Pełnomocnictwo przyjmuję:"] + [f"{TITLES[a['title']]['abbr']} {a['nom']}" for a in c["atts"]]
    return L


def pel_B(c, rng):
    """The labels come first. The values come after them."""
    L = ["P E Ł N O M O C N I C T W O"]
    labels, vals = [], []
    for o in c["mocs"]:
        labels += ["Mocodawca", "Dane rejestrowe"]
        vals += [f"{o['name']}, {o['addr']}", ids_inline(rng, o) or "-"]
    labels += ["Pełnomocnicy", "Zamawiający", "Postępowanie", "Zakres", "Data"]
    vals += [
        "; ".join(pel_att(a, rng, "nom", "abbr") for a in c["atts"]),
        c["auth"][0],
        f"{c['title']}, nr {c['nr']}",
        "reprezentowanie w postępowaniu odwoławczym przed KIO, wniesienie odwołania",
        fmt_date(c["date"], "dot"),
    ]
    return L + labels + vals + pel_signers(c, "Podpisy:")


def pel_C(c, rng):
    """One paragraph. The attorney is in the dative case."""
    o = c["mocs"][0]
    who = "Ja, niżej podpisany" if o["person"] else f"{o['name']}"
    atts = " oraz ".join(f"{HONOR[a['g']]['dat']} {pel_att(a, rng, 'dat', 'full')}" for a in c["atts"])
    L = [
        "Pełnomocnictwo",
        f"{who}, {o['addr']}"
        + (f", {ids_inline(rng, o)}" if ids_inline(rng, o) else "")
        + f" udzielam pełnomocnictwa {atts} do reprezentowania w postępowaniu „{c['title']}”, nr {c['nr']}, "
        f"prowadzonym przez {c['auth'][1]}, w tym do wniesienia odwołania do Krajowej Izby Odwoławczej i udziału w rozprawie.",
        f"{c['town']}, {fmt_date(c['date'], 'long')}",
    ] + pel_signers(c, "")
    return L


def pel_D(c, rng):
    """A form with a label and a value on each line."""
    L = ["PEŁNOMOCNICTWO SZCZEGÓLNE", f"Data: {fmt_date(c['date'], 'dot')}  Miejsce: {c['town']}"]
    for i, o in enumerate(c["mocs"], 1):
        L += [f"Mocodawca {i}: {o['name']}", f"Adres: {o['addr']}"]
        if o["krs"]:
            L.append(f"KRS: {o['krs']}")
        if o["nip"]:
            L.append(f"NIP: {nip_text(rng, o['nip'])}")
    for i, a in enumerate(c["atts"], 1):
        L.append(f"Pełnomocnik {i}: {pel_att(a, rng, 'nom', 'full')}")
    L += [
        "Przedmiot: reprezentowanie przed Krajową Izbą Odwoławczą w sprawie wniesionego odwołania; postępowanie nr "
        + c["nr"],
        "Opłata skarbowa w wysokości 17 zł została uiszczona.",
    ]
    return L + pel_signers(c, "Osoby podpisujące w imieniu mocodawcy:")


def pel_E(c, rng):
    """The consortium form."""
    L = ["PEŁNOMOCNICTWO", "Wykonawcy wspólnie ubiegający się o udzielenie zamówienia:"]
    for i, o in enumerate(c["mocs"]):
        L.append(f"{i + 1}) {'Lider' if i == 0 else 'Partner'}: {pel_moc(o, rng)}")
    L += [
        "ustanawiają pełnomocnikiem " + ", ".join(pel_att(a, rng, "acc", "full") for a in c["atts"]),
        f"do reprezentowania w postępowaniu {c['nr']} „{c['title']}” przed Krajową Izbą Odwoławczą.",
        c["town"] + " " + fmt_date(c["date"], "dot"),
    ]
    return L + pel_signers(c)


def pel_F(c, rng):
    o = c["mocs"][0]
    L = [
        "Pełnomocnictwo",
        f"{o['name']} z siedzibą: {o['addr']}",
        ids_inline(rng, o, " ") if o["krs"] or o["nip"] else "",
        "niniejszym ustanawia: "
        + ", ".join(pel_att(a, rng, "acc", "abbr") for a in c["atts"])
        + " swoim pełnomocnikiem w postępowaniu odwoławczym.",
        f"Postępowanie: {c['title']}, {c['nr']}.",
    ]
    return [x for x in L if x] + [f"dnia {fmt_date(c['date'], 'long')}"] + pel_signers(c, "podpis:")


PEL_LAYOUTS = [(pel_A, False), (pel_B, False), (pel_C, False), (pel_D, False), (pel_E, True), (pel_F, False)]


def gen_pelnomocnictwo(rng: random.Random, i: int):
    k = i % len(PEL_LAYOUTS)
    fn, two = PEL_LAYOUTS[k]
    c = make_pel_case(rng, two or (k == 3 and rng.random() < 0.3))
    if fn is pel_F or fn is pel_C:
        c["mocs"] = c["mocs"][:1]
    text = paginate(wrap(fn(c, rng), 88), rng, "Pełnomocnictwo")
    return f"pelnomocnictwo/L{k}/{i:03d}", text, pel_gold(c)


# --- bank confirmations ---------------------------------------------------

BANKS = [  # name, mode, labels (key, text), footer
    (
        "PKO Bank Polski",
        "inline",
        [
            ("payer", "Nazwa nadawcy"),
            ("from", "Numer rachunku nadawcy"),
            ("recv", "Nazwa odbiorcy"),
            ("to", "Numer rachunku odbiorcy"),
            ("title", "Tytuł"),
            ("amount", "Kwota"),
            ("date", "Data operacji"),
            ("txid", "Numer referencyjny"),
        ],
        "Dokument wygenerowano elektronicznie {p}.",
    ),
    (
        "mBank",
        "inline",
        [
            ("date", "Data wykonania"),
            ("from", "Z rachunku"),
            ("to", "Na rachunek"),
            ("recv", "Odbiorca"),
            ("title", "Tytuł"),
            ("amount", "Kwota"),
            ("txid", "ID transakcji"),
        ],
        "mBank S.A. Potwierdzenie z dnia {p}",
    ),
    (
        "ING Bank Śląski",
        "labels_first",
        [
            ("date", "Data transakcji"),
            ("booking", "Data księgowania"),
            ("payer", "Dane zleceniodawcy"),
            ("from", "Rachunek zleceniodawcy"),
            ("recv", "Dane odbiorcy"),
            ("to", "Rachunek odbiorcy"),
            ("title", "Tytuł"),
            ("amount", "Kwota"),
            ("txid", "Nr transakcji"),
        ],
        "ING Bank Śląski S.A. {p}",
    ),
    (
        "Santander Bank Polska",
        "inline",
        [
            ("payer", "Nadawca"),
            ("from", "Rachunek nadawcy"),
            ("recv", "Odbiorca"),
            ("to", "Rachunek odbiorcy"),
            ("amount", "Kwota przelewu"),
            ("title", "Tytuł przelewu"),
            ("date", "Data realizacji"),
            ("txid", "Identyfikator"),
        ],
        "Wydruk z dnia {p}",
    ),
    (
        "Bank Pekao S.A.",
        "labels_first",
        [
            ("payer", "Zleceniodawca"),
            ("from", "Z rachunku"),
            ("recv", "Beneficjent"),
            ("to", "Na rachunek"),
            ("amount", "Kwota"),
            ("title", "Tytuł płatności"),
            ("date", "Data realizacji"),
            ("txid", "Numer transakcji"),
        ],
        "Pekao24 – data wydruku {p}",
    ),
    (
        "Bank Millennium",
        "inline",
        [
            ("date", "Data wykonania"),
            ("booking", "Data księgowania"),
            ("amount", "Kwota"),
            ("from", "Rachunek obciążany"),
            ("to", "Rachunek beneficjenta"),
            ("recv", "Beneficjent"),
            ("title", "Tytuł płatności"),
            ("txid", "Nr referencyjny"),
        ],
        "Wygenerowano: {p}",
    ),
    (
        "Alior Bank",
        "dotted",
        [
            ("amount", "KWOTA"),
            ("date", "DATA REALIZACJI"),
            ("from", "RACHUNEK NADAWCY"),
            ("to", "RACHUNEK ODBIORCY"),
            ("title", "TYTUŁ"),
            ("txid", "NR REFERENCYJNY"),
        ],
        "*** {p} ***",
    ),
    (
        "Bank Spółdzielczy w Kolbuszowej",
        "slip",
        [
            ("payer", "Wpłacający"),
            ("from", "Z rachunku"),
            ("recv", "Odbiorca"),
            ("to", "Na rachunek"),
            ("amount", "Kwota"),
            ("title", "Tytułem"),
            ("date", "Data operacji"),
        ],
        "Pieczęć banku, {p}",
    ),
]


def przelew_gold_and_text(rng: random.Random, i: int):
    k = i % len(BANKS)
    bank, mode, labels, foot = BANKS[k]
    d = rand_date(rng)
    wpis = rng.random() < 0.6
    amount = float(rng.choice([7500, 10000, 15000])) if wpis else float(rng.choice([17, 34, 51]))
    zam = rng.choice(AUTHORITIES)[0].upper()
    nr = rng.choice(NUMBER_PATTERNS).format(n=rng.randint(10, 999), m=rng.randint(1, 60), y=2026, yy=26)
    title = (
        f"WPIS OD ODWOŁANIA, ZAM: {zam}, {nr}, {rng.choice(TITLES_ZP).split(' w ')[0].upper()}"
        if wpis
        else f"opłata skarbowa od pełnomocnictwa - {make_company(rng)}, postępowanie {nr}"
    )
    title = title.replace("{C}", "X").replace("{c}", "X")
    txid = f"{rng.choice(['CEN', 'TR', 'ZL'])}{rng.randint(10**9, 10**11)}" if rng.random() < 0.6 else None
    if "txid" not in {key for key, _ in labels}:
        txid = None
    frm = iban(rng, rng.choice(BANK_CODES))
    to = "60101010100081362231000000" if wpis else iban(rng, rng.choice(BANK_CODES))
    ts = rng.choice([35, 60, 200])
    vals = {
        "payer": make_company(rng),
        "from": account_text(rng, frm),
        "recv": "Urząd Zamówień Publicznych" if wpis else "Urząd Miasta " + rng.choice(CITIES),
        "to": account_text(rng, to),
        "title": title,
        "amount": money_text(rng, amount),
        "date": fmt_date(d, rng.choice(["dot", "iso", "dash"])),
        "booking": fmt_date(d + timedelta(days=1), "dot"),
        "txid": txid,
    }
    print_d = fmt_date(d + timedelta(days=rng.randint(0, 9)), "dot")
    if bank == "mBank":
        vals["amount"] = "-" + vals["amount"]
    L = [
        bank.upper() if k % 2 else bank,
        "Potwierdzenie przelewu" if k % 3 else "POTWIERDZENIE REALIZACJI POLECENIA PRZELEWU",
    ]
    use = [(key, lab) for key, lab in labels if vals.get(key) is not None]
    if mode == "inline":
        for key, lab in use:
            if key == "title":
                L += [f"{lab}: " + textwrap.wrap(title, ts)[0]] + textwrap.wrap(title, ts)[1:]
            else:
                L.append(f"{lab}: {vals[key]}")
    elif mode == "labels_first":
        L += [lab for _, lab in use]
        for key, _ in use:
            L += textwrap.wrap(vals[key], ts) if key == "title" else [vals[key]]
    elif mode == "dotted":
        for key, lab in use:
            L += (
                [f"{lab} " + "." * max(3, 50 - len(lab) - len(vals[key])) + " " + vals[key]]
                if key != "title"
                else [lab + ":"] + textwrap.wrap(title, 60)
            )
    else:
        L += ["Dowód wpłaty/polecenie przelewu"]
        for key, lab in use:
            L += [lab] + (textwrap.wrap(title, ts) if key == "title" else [vals[key]])
        L.append("Słownie: " + words_pl(int(amount)) + " złotych 00/100")
    L.append(foot.format(p=print_d))
    gold = {
        "przelew_bankowy": {
            "data_operacji": d.isoformat(),
            "kwota": amount,
            "na_rachunek": to,
            "numer_transakcji": txid,
            "tytul": title,
            "z_rachunku": frm,
        }
    }
    return f"przelew/L{k}/{i:03d}", "\n".join(L), gold


# --- negatives --------------------------------------------------------------


def gen_negative(rng: random.Random, i: int):
    k = i % 8
    c = make_case(rng)
    z, o = c["zam"][0], c["odw"][0]
    acc = account_text(rng, iban(rng, rng.choice(BANK_CODES)))
    d = fmt_date(c["date"], "long")
    if k == 0:
        t = [
            f"Sygn. akt KIO {rng.randint(100, 3999)}/26",
            "WYROK",
            "z dnia " + d,
            "Krajowa Izba Odwoławcza w składzie:",
            f"Przewodniczący: {make_person(rng)['nom']}",
            f"po rozpoznaniu na rozprawie odwołania wniesionego przez {o['name']} w postępowaniu prowadzonym przez {z['name']}, nr {c['nr']},",
            "orzeka: 1. Oddala odwołanie. 2. Kosztami postępowania obciąża Odwołującego w kwocie " + c["fee"] + ".",
            "Przewodniczący: ...........",
        ]
    elif k == 1:
        t = [
            f"{c['town'] or 'Warszawa'}, dnia {d}",
            "Krajowa Izba Odwoławcza",
            "ODPOWIEDŹ NA ODWOŁANIE",
            f"Zamawiający: {z['name']}, {z['addr']}",
            f"Odwołujący: {o['name']}",
            f"w sprawie o sygn. akt KIO {rng.randint(100, 3999)}/26 dotyczącej postępowania {c['nr']}",
            "Zamawiający wnosi o oddalenie odwołania w całości oraz zasądzenie kosztów. W uzasadnieniu wskazuje, co następuje.",
            rng.choice(FILLER).format(dd=d, fee=c["fee"], pd=d),
        ]
    elif k == 2:
        t = [
            f"FAKTURA VAT nr FV/{rng.randint(1, 999)}/2026",
            f"Data wystawienia: {fmt_date(c['date'], 'dot')}",
            f"Sprzedawca: {o['name']}, NIP {o['nip'] or '5213456789'}",
            f"Nabywca: {z['name']}",
            "Lp. Nazwa towaru lub usługi  Ilość  Cena  Wartość",
            "1. Usługi serwisowe  1  8 000,00  8 000,00",
            "Razem do zapłaty: 9 840,00 PLN",
            f"Numer rachunku: {acc}",
            f"Termin płatności: {fmt_date(c['deadline'], 'dot')}",
            "Tytuł przelewu: FV/2026",
        ]
    elif k == 3:
        t = [
            f"WYCIĄG Z RACHUNKU {acc}",
            f"Okres: {fmt_date(c['date'], 'dot')} - {fmt_date(c['date'] + timedelta(days=30), 'dot')}",
            f"Właściciel: {o['name']}",
        ]
        for j in range(12):
            t.append(
                f"{fmt_date(c['date'] + timedelta(days=j), 'dot')}  {rng.choice(['Przelew przychodzący', 'Opłata', 'Przelew wychodzący', 'WPIS OD ODWOŁANIA KIO'])}  {money_text(rng, rng.randint(100, 20000) + 0.5)}  saldo {money_text(rng, rng.randint(5000, 90000))}"
            )
    elif k == 4:
        t = [
            f"{z['name']}",
            z["addr"],
            f"{c['town'] or 'Kraków'}, {d}",
            "ZAWIADOMIENIE O WYBORZE NAJKORZYSTNIEJSZEJ OFERTY",
            f"Postępowanie: {c['title']}, nr {c['nr']}",
            f"Zamawiający informuje, że wybrano ofertę wykonawcy {c['winner']}. Oferta {o['name']} otrzymała 82,5 pkt.",
            "Od czynności Zamawiającego przysługuje odwołanie do Krajowej Izby Odwoławczej w terminie 10 dni.",
        ]
    elif k == 5:
        p = make_person(rng)
        t = [
            "UPOWAŻNIENIE",
            f"{c['town'] or 'Opole'}, {d}",
            f"{o['name']}, {o['addr']}, NIP {o['nip'] or '7771234567'} upoważnia {HONOR[p['g']]['acc']} {p['forms']['acc']}",
            "do odbioru korespondencji i dokumentów w siedzibie urzędu skarbowego oraz do składania podpisu na potwierdzeniach odbioru.",
            "............................",
            "Prezes Zarządu",
        ]
    elif k == 6:
        t = [
            f"{c['town'] or 'Łódź'}, {d}",
            "Prezes Krajowej Izby Odwoławczej",
            "PRZYSTĄPIENIE DO POSTĘPOWANIA ODWOŁAWCZEGO",
            f"sygn. akt KIO {rng.randint(100, 3999)}/26",
            f"Wykonawca {c['winner']}, {make_addr(rng)}, zgłasza przystąpienie do postępowania odwoławczego po stronie Zamawiającego {z['name']} i wnosi o oddalenie odwołania wniesionego przez {o['name']}.",
            "Pełnomocnik Przystępującego: .........",
        ]
    else:
        t = [
            "INFORMACJA Z OTWARCIA OFERT",
            f"Zamawiający: {z['name']}",
            f"Postępowanie nr {c['nr']}",
            f"Kwota przeznaczona na sfinansowanie zamówienia: {money_text(rng, 1250000.0)}",
            f"1. {c['winner']} – cena {money_text(rng, 1180000.0)}",
            f"2. {o['name']} – cena {money_text(rng, 1210000.5)}",
            f"Rachunek bankowy Zamawiającego: {acc}",
        ]
    return f"negatyw/N{k}/{i:03d}", "\n".join(wrap(t, 90)), {}


GENERATORS = {
    "odwolanie": gen_odwolanie,
    "pelnomocnictwo": gen_pelnomocnictwo,
    "przelew": przelew_gold_and_text,
    "negatyw": gen_negative,
}


def generate(n_per_type: int, seed: int, types: tuple = TYPES) -> list[tuple[str, str, dict]]:
    out = []
    for t in types:
        for i in range(n_per_type):
            out.append(GENERATORS[t](random.Random(f"{seed}-{t}-{i}"), i))
    return out


def main() -> None:
    from odw2json.evaluate import Score, compare, doc_type
    from odw2json.pipeline import process_text

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--type", choices=TYPES)
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--show")
    a = ap.parse_args()
    items = generate(a.n, a.seed, (a.type,) if a.type else TYPES)
    by_type, by_field, conf, errs = defaultdict(Score), defaultdict(Score), Counter(), []
    for name, text, gold in items:
        if a.show and a.show == name:
            print(text, "\nGOLD", gold)
        try:
            pred = process_text(text).data
        except Exception as e:  # noqa: BLE001  a crash counts as an empty result
            pred = {}
            errs.append((name, "CRASH", repr(e), ""))
        leaves = compare(gold, pred)
        by_type[name.split("/")[0]].add(leaves)
        conf[(doc_type(gold), doc_type(pred))] += 1
        for lf in leaves:
            by_field[lf.path].add([lf])
            if lf.outcome in ("FP", "FN", "WRONG"):
                errs.append((name, lf.path, lf.ref, lf.pred))
        if a.show == name:
            print("PRED", pred)
    for t, s in by_type.items():
        print(f"{t:15s} {s.line()}")
    print("Confusion:", {f"{g}->{p}": n for (g, p), n in sorted(conf.items()) if g != p} or "none")
    print("Worst fields:")
    for f, s in sorted(by_field.items(), key=lambda kv: kv[1].f1)[:8]:
        print(f"  {f:40s} {s.line()}")
    if a.errors:
        for e in errs:
            print("  ", e)


if __name__ == "__main__":
    main()
