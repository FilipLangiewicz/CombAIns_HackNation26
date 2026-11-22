import pytest

from odw2json.classify import load_types
from odw2json.extractors import odwolanie
from odw2json.pipeline import process_text

HEADER = """Gdańsk, dnia 3 września 2026 roku
Prezes Krajowej Izby Odwoławczej
Zamawiający (zamawiający wspólnie przeprowadzający postępowanie):
1) Zamawiający – Lider, prowadzący postępowanie:
Gmina Alfa
ul. Długa 1, 80-001 Gdańsk
KRS: 9990000001, NIP: 9990000002, REGON: 999000003
2) Zamawiający – Partner:
Gmina Beta
ul. Krótka 2, 80-002 Gdańsk
NIP: 9990000004
Odwołujący: Konsorcjum wykonawców w składzie:
1) Lider Konsorcjum:
Firma Gamma sp. z o.o.
ul. Polna 3, 80-003 Gdańsk
KRS: 9990000005, NIP: 9990000006, REGON: 999000007
2) Partner Konsorcjum:
Firma Delta S.A.
ul. Leśna 4, 80-004 Gdańsk
NIP: 9990000008
reprezentowany przez: adw. Jan Kowalski, r. pr. Anna Nowak
adres do korespondencji: Kancelaria Adwokacka Kowalski,
ul. Cicha 5, 80-005 Gdańsk
tel. 000 000 000, e-mail: jan@kancelaria.example
dotyczy: postępowania pn. „Budowa drogi
wraz z chodnikiem”, nr referencyjny: ZP.1.2026, ogłoszenie nr 2026/BZP
00999778, ogłoszenie w Dzienniku nr 2026/S 142-999327
Strona 1 z 2
O D W O Ł A N I E
Działając w imieniu Konsorcjum, wnoszę odwołanie wobec czynności Zamawiającego, polegających na:
1) zaniechaniu odrzucenia oferty wykonawcy X z dnia 2 czerwca 2026 r.;
2) wyborze oferty.
Zarzut nr 1 – zaniechania odrzucenia oferty
"""


@pytest.fixture(scope="module")
def result():
    doc_type = next(t for t in load_types() if t.name == "odwolanie")
    evidence: dict[str, str] = {}
    return odwolanie.extract(HEADER, doc_type, evidence), evidence


def test_header_line(result):
    kio = result[0]["OdwolanieKIO"]
    assert (kio["data"], kio["miejscowosc"]) == ("2026-09-03", "Gdańsk")


def test_action(result):
    kio = result[0]["OdwolanieKIO"]
    assert kio["czynnosc_powod_id"] == 7
    assert kio["czynnosc_opis"] == "Zaniechanie odrzucenia oferty"
    assert kio["czynnosc_dzien"] == "2026-06-02"


def test_consortium_leader_and_attorney(result):
    row = result[0]["Odwolujacy"][0]
    assert row["nazwa"] == "Firma Gamma sp. z o.o."
    assert (row["krs"], row["nip"], row["regon"]) == ("9990000005", "9990000006", "999000007")
    assert row["przez-pelnomocnika"] == 1
    assert row["pelnomocnik"] == {
        "imie_nazwisko": "Jan Kowalski",
        "nazwa": "Kancelaria Adwokacka Kowalski",
        "mail": "jan@kancelaria.example",
    }


def test_several_contracting_authorities(result):
    rows = result[0]["Zamawiajacy"]
    assert [r["nazwa"] for r in rows] == ["Gmina Alfa", "Gmina Beta"]
    assert [r["prowadzacy_postepowanie"] for r in rows] == [1, 0]
    assert rows[1]["krs"] is None


def test_procurement(result):
    p = result[0]["ZamowieniePubliczne"]
    assert p == {
        "numer_bzp": "2026/BZP00999778",
        "numer_postepowania": "ZP.1.2026",
        "numer_ted": "999327-2026",
        "tytul": "Budowa drogi wraz z chodnikiem",
    }


@pytest.mark.parametrize(
    "sentence, code",
    [
        ("Zamawiający w dniu 1 marca 2026 roku unieważniił postępowanie.", 9),
        ("Zamawiający w dniu 1 marca 2026 roku zaniechał unieważnienia postępowania.", 10),
        ("Zamawiający w dniu 1 marca 2026 roku nie wykluczył wykonawcy.", 8),
        ("Zamawiający w dniu 1 marca 2026 roku udostępnił Opis Przedmiotu Zamówienia.", 11),
        ("Zamawiający w dniu 1 marca 2026 roku przekazał odpowiedzi i wyjaśnienia do treści SWZ.", 6),
    ],
)
def test_action_codes(sentence, code):
    doc_type = next(t for t in load_types() if t.name == "odwolanie")
    found, _ = odwolanie.classify_action([sentence], doc_type.raw["action_rules"])
    assert found == code


def _extract(text):
    doc_type = next(t for t in load_types() if t.name == "odwolanie")
    return odwolanie.extract(text, doc_type, {})


INLINE = (
    "Warszawa, 12.03.2026 r.\nODWOŁUJĄCY: Firma Zeta S.A., ul. Polna 3, 00-001 Warszawa, "
    "KRS: 9990000005, NIP: 9990000006\nreprezentowanego przez r. pr. Jana Kowalskiego\n"
    "adres do korespondencji: Kancelaria Prawna Kowalski, ul. Cicha 5, 00-002 Warszawa\n"
    "ZAMAWIAJĄCY: Gmina Eta ul. Długa 1, 00-003 Warszawa NIP: 9990000002\n"
    'dotyczy: postępowania pn. "Budowa drogi", nr referencyjny: ZP.1.2026\n'
    "Działając w imieniu Odwołującego wnoszę o:\n"
)


def test_inline_labels_and_genitive_name():
    data = _extract(INLINE)
    row = data["Odwolujacy"][0]
    assert row["nazwa"] == "Firma Zeta S.A."
    assert row["pelnomocnik"]["imie_nazwisko"] == "Jan Kowalski"
    assert data["Zamawiajacy"][0]["nazwa"] == "Gmina Eta"
    assert data["ZamowieniePubliczne"]["tytul"] == "Budowa drogi"
    assert data["OdwolanieKIO"]["miejscowosc"] == "Warszawa"


def test_appellant_without_attorney():
    text = INLINE.replace("reprezentowanego przez r. pr. Jana Kowalskiego\n", "").replace(
        "adres do korespondencji: Kancelaria Prawna Kowalski, ul. Cicha 5, 00-002 Warszawa\n", ""
    )
    row = _extract(text)["Odwolujacy"][0]
    assert row["przez-pelnomocnika"] == 0
    assert row["pelnomocnik"] is None


GENERAL = """Od: Firma Zeta S.A. (odwołujący), ul. Polna 3, 00-001 Warszawa
KRS: 9990000005, NIP: 9990000006
Pełnomocnik: adw. Anna Nowak, Kancelaria Prawna Nowak sp. z o.o., e-mail anna@kancelaria.example
Przeciwko: Gmina Eta, ul. Długa 1, 00-003 Warszawa, NIP: 9990000002 (Zamawiający prowadzący postępowanie); Gmina Theta, ul. Krótka 2, 00-004 Warszawa, NIP: 9990000003 (Zamawiający uczestniczący)
Przedmiot odwołania: Budowa drogi Numer postępowania: ZP.1.2026
Zaskarżone czynności polegają na:
1) wyborze oferty w dniu 4 marca 2026 roku
2) odrzuceniu oferty w dniu 1 marca 2026 roku
"""


def test_labels_od_przeciwko_and_roles_in_parentheses():
    data = _extract(GENERAL)
    assert data["Odwolujacy"][0]["nazwa"] == "Firma Zeta S.A."
    assert [(r["nazwa"], r["prowadzacy_postepowanie"]) for r in data["Zamawiajacy"]] == [
        ("Gmina Eta", 1),
        ("Gmina Theta", 0),
    ]
    assert data["Odwolujacy"][0]["pelnomocnik"]["imie_nazwisko"] == "Anna Nowak"
    assert data["Odwolujacy"][0]["pelnomocnik"]["nazwa"] == "Kancelaria Prawna Nowak sp. z o.o."
    assert data["OdwolanieKIO"]["czynnosc_powod_id"] == 2
    assert data["OdwolanieKIO"]["czynnosc_dzien"] == "2026-03-04"
    assert data["ZamowieniePubliczne"]["tytul"] == "Budowa drogi"


def test_attorney_in_accusative_with_firm_suffix():
    text = INLINE.replace(
        "reprezentowanego przez r. pr. Jana Kowalskiego",
        "działa przez pełnomocnika – adw. Annę Piotrowską – Kancelaria Adwokacka, e-mail: a@b.example",
    )
    assert _extract(text)["Odwolujacy"][0]["pelnomocnik"]["imie_nazwisko"] == "Anna Piotrowska"


def test_answer_to_appeal_is_not_an_appeal():
    from odw2json.classify import classify

    text = "ODPOWIEDŹ NA ODWOŁANIE\nZamawiający Gmina Eta wnosi o oddalenie odwołania. Zarzuty Odwołującego są bezzasadne.\nKrajowa Izba Odwoławcza"
    assert classify(text).doc_type is None


ROLE_HEAD = "Warszawa, dnia 12.10.2026 r.\nKrajowa Izba Odwoławcza\nul. Postępu 17a, 02-676 Warszawa\n"
ROLE_TAIL = (
    "Zamawiający: Gmina Miasto Płock, ul. Stary Rynek 1, 09-400 Płock, NIP 7740001454\nODWOŁANIE\n"
    "od czynności Zamawiającego polegającej na odrzuceniu oferty Odwołującego, o czym Zamawiający zawiadomił "
    "w dniu 2.10.2026 r.\n"
)
APPELLANT = "Odwołujący: Budimex Serwis sp. z o.o., ul. Długa 5, 00-950 Warszawa, KRS 0000123456\n"


def appellant(block: str) -> dict:
    doc_type = next(t for t in load_types() if t.name == "odwolanie")
    return odwolanie.extract(ROLE_HEAD + block + ROLE_TAIL, doc_type, {})["Odwolujacy"][0]


@pytest.mark.parametrize(
    "rep",
    [
        "reprezentowana przez Prezesa Zarządu Jana Kowalskiego",
        "reprezentowany przez: Jan Kowalski – Prezes Zarządu",
        "reprezentowany przez prokurenta Adama Nowaka",
    ],
)
def test_member_of_the_board_is_not_an_attorney(rep):
    row = appellant(APPELLANT + rep + "\n")
    assert row["przez-pelnomocnika"] == 0
    assert row["pelnomocnik"] is None


def test_board_and_attorney_together():
    row = appellant(
        APPELLANT + "reprezentowana przez Prezesa Zarządu Jana Kowalskiego, działająca przez pełnomocnika "
        "adw. Piotra Zielińskiego\n"
    )
    assert row["przez-pelnomocnika"] == 1
    assert row["pelnomocnik"]["imie_nazwisko"] == "Piotr Zieliński"


def test_attorney_after_the_word_pelnomocnik():
    row = appellant(APPELLANT + "reprezentowana przez pełnomocnika: r. pr. Anna Nowak, e-mail: a.nowak@kancelaria.pl\n")
    assert row["pelnomocnik"] == {"imie_nazwisko": "Anna Nowak", "nazwa": None, "mail": "a.nowak@kancelaria.pl"}


def test_attorney_before_the_appellant():
    row = appellant(
        "Pełnomocnik Odwołującego: adw. Piotr Zieliński, Kancelaria Adwokacka Zieliński, ul. Prosta 2, 00-001 Warszawa\n"
        + APPELLANT
    )
    assert row["nazwa"] == "Budimex Serwis sp. z o.o."
    assert row["pelnomocnik"]["imie_nazwisko"] == "Piotr Zieliński"
    assert row["pelnomocnik"]["nazwa"] == "Kancelaria Adwokacka Zieliński"


def test_sole_trader_gives_the_name_of_the_firm():
    row = appellant(
        "Odwołujący: Jan Kowalski prowadzący działalność gospodarczą pod firmą KOWALSKI-BUD Jan Kowalski, "
        "ul. Długa 5, 00-950 Warszawa, NIP 5250001090\n"
    )
    assert row["nazwa"] == "KOWALSKI-BUD Jan Kowalski"


def test_surnames_before_the_law_firm():
    row = appellant(
        APPELLANT + "Pełnomocnik: adw. Łukasz Wiśniewski, Wiśniewski Adamczyk Kancelaria Prawna sp.p., "
        "wisniewski@adwokat.pl\n"
    )
    assert row["pelnomocnik"]["nazwa"] == "Wiśniewski Adamczyk Kancelaria Prawna sp.p."


def parties(text: str) -> dict:
    doc_type = next(t for t in load_types() if t.name == "odwolanie")
    return odwolanie.extract(ROLE_HEAD + text + ROLE_TAIL.split("\n", 1)[1], doc_type, {})


FIRM = "Budimex Serwis sp. z o.o.\nul. Długa 5, 00-950 Warszawa\nNIP: 5250001090\n"
AUTHORITY = "Gmina Miasto Płock\nul. Stary Rynek 1, 09-400 Płock\nNIP: 7740001454\n"


@pytest.mark.parametrize(
    ("odw", "zam"),
    [
        ("ODWOŁUJĄCY", "ZAMAWIAJĄCY"),
        ("I. Odwołujący", "II. Zamawiający"),
        ("Odwołujący –", "Zamawiający –"),
        ("Wykonawca:", "Zamawiający:"),
    ],
)
def test_headings_without_a_colon(odw, zam):
    data = parties(f"{odw}\n{FIRM}{zam}\n{AUTHORITY}")
    assert data["Odwolujacy"][0]["nazwa"] == "Budimex Serwis sp. z o.o."
    assert data["Zamawiajacy"][0]["nazwa"] == "Gmina Miasto Płock"


@pytest.mark.parametrize(
    "ids",
    [
        "NIP 525 000 10 90; REGON 012345678",
        "nr NIP: 5250001090 nr REGON: 012345678",
        "NIP: PL5250001090, REGON: 012345678",
    ],
)
def test_forms_of_the_identifiers(ids):
    row = parties(
        f"Odwołujący:\nBudimex Serwis sp. z o.o.\nul. Długa 5, 00-950 Warszawa\n{ids}\nZamawiający:\n{AUTHORITY}"
    )["Odwolujacy"][0]
    assert (row["nip"], row["regon"]) == ("5250001090", "012345678")


@pytest.mark.parametrize(
    "lead",
    [
        "1) Gmina Alfa (pełnomocnik Zamawiających), ul. Długa 1, 80-001 Gdańsk, NIP 9990000002\n2) Gmina Beta, ul. Krótka 2, 80-002 Gdańsk, NIP 9990000004",
        "1) Gmina Alfa (Zamawiający wiodący), ul. Długa 1, 80-001 Gdańsk, NIP 9990000002\n2) Gmina Beta, ul. Krótka 2, 80-002 Gdańsk, NIP 9990000004",
        "1 (prowadzący postępowanie):\nGmina Alfa, ul. Długa 1, 80-001 Gdańsk, NIP 9990000002\nZamawiający 2:\nGmina Beta, ul. Krótka 2, 80-002 Gdańsk, NIP 9990000004",
    ],
)
def test_lead_contracting_authority(lead):
    sep = " " if lead.startswith("1 (") else ":\n"
    rows = parties(f"Odwołujący:\n{FIRM}Zamawiający{sep}{lead}\n")["Zamawiajacy"]
    assert [(r["nazwa"], r["prowadzacy_postepowanie"]) for r in rows] == [("Gmina Alfa", 1), ("Gmina Beta", 0)]


def test_name_of_the_attorney_on_its_own_line():
    row = parties(
        "Odwołujący:\n"
        + FIRM
        + "Pełnomocnik Odwołującego:\nr. pr. Anna Nowak\nNowak i Partnerzy Kancelaria Prawna sp. p.\n"
        "ul. Prosta 2, 00-001 Warszawa\nemail: a.nowak@kancelaria.pl\nZamawiający:\n" + AUTHORITY
    )["Odwolujacy"][0]
    assert row["pelnomocnik"] == {
        "imie_nazwisko": "Anna Nowak", "nazwa": "Nowak i Partnerzy Kancelaria Prawna sp. p.", "mail": "a.nowak@kancelaria.pl",
    }  # fmt: skip


def test_attorney_only_in_the_signature():
    doc_type = next(t for t in load_types() if t.name == "odwolanie")
    text = ROLE_HEAD + APPELLANT + ROLE_TAIL + "W imieniu Odwołującego:\nadw. Piotr Zieliński\n(pełnomocnik)\n"
    row = odwolanie.extract(text, doc_type, {})["Odwolujacy"][0]
    assert row["przez-pelnomocnika"] == 1
    assert row["pelnomocnik"]["imie_nazwisko"] == "Piotr Zieliński"


def test_board_member_in_the_signature_is_not_an_attorney():
    doc_type = next(t for t in load_types() if t.name == "odwolanie")
    text = ROLE_HEAD + APPELLANT + ROLE_TAIL + "............\nJan Kowalski\nPrezes Zarządu\n"
    row = odwolanie.extract(text, doc_type, {})["Odwolujacy"][0]
    assert row["przez-pelnomocnika"] == 0


APPEAL_HEAD = "Warszawa, dnia 14.04.2026 r.\nDo: Prezes Krajowej Izby Odwoławczej\n"
PROBE_APPELLANT = "Odwołujący:\nAlfa Budowa sp. z o.o.\nul. Leśna 3, 00-950 Warszawa\nNIP: 5250001234\n"
APPEAL_BODY = (
    "\nODWOŁANIE\nNa podstawie art. 513 Pzp wnoszę odwołanie i zarzucam Zamawiającemu naruszenie art. 226 Pzp.\n"
)
ONE_AUTHORITY = "Zamawiający:\nGmina Miasto Kielce\nul. Rynek 1, 25-303 Kielce\nNIP: 6570000001\n"


@pytest.mark.parametrize(
    "block",
    [
        "Zamawiający:\n1. Gmina Alfa (Lider), ul. Długa 1, 80-001 Gdańsk, NIP: 9990000002\n"
        "2. Gmina Beta, ul. Krótka 2, 80-002 Gdańsk, NIP: 9990000004\n",
        "Zamawiający wspólnie udzielający zamówienia:\nGmina Alfa – Zamawiający prowadzący postępowanie\n"
        "ul. Długa 1, 80-001 Gdańsk\nNIP: 9990000002\noraz\nGmina Beta\nul. Krótka 2, 80-002 Gdańsk\nNIP: 9990000004\n",
        "Zamawiający 1: Gmina Alfa, ul. Długa 1, 80-001 Gdańsk, NIP 9990000002 – pełnomocnik Zamawiających"
        " prowadzący postępowanie\nZamawiający 2: Gmina Beta, ul. Krótka 2, 80-002 Gdańsk, NIP 9990000004\n",
        "Zamawiający:\na) Gmina Alfa – Lider Zamawiających\nul. Długa 1, 80-001 Gdańsk, NIP: 9990000002\n"
        "b) Gmina Beta – Partner\nul. Krótka 2, 80-002 Gdańsk, NIP: 9990000004\n",
        "Zamawiający:\n- Gmina Alfa, ul. Długa 1, 80-001 Gdańsk, NIP: 9990000002\n"
        "- Gmina Beta, ul. Krótka 2, 80-002 Gdańsk, NIP: 9990000004\nPostępowanie prowadzi Gmina Alfa.\n",
    ],
)
def test_lead_authority_forms(block):
    data = process_text(APPEAL_HEAD + block + PROBE_APPELLANT + APPEAL_BODY).data
    assert [(z["nazwa"], z["prowadzacy_postepowanie"]) for z in data["Zamawiajacy"]] == [
        ("Gmina Alfa", 1),
        ("Gmina Beta", 0),
    ]


@pytest.mark.parametrize(
    "block, person, firm",
    [
        (
            "reprezentowany przez:\nadw. Ewa Wójcik – Kancelaria Adwokacka Ewa Wójcik\nul. Mostowa 3, 61-001 Poznań\n",
            "Ewa Wójcik",
            "Kancelaria Adwokacka Ewa Wójcik",
        ),
        (
            "Pełnomocnik:\nr.pr. Michał Szymański\nSzymański Dąbrowski Kancelaria Prawna sp.p.\nul. Ogrodowa 8, 90-001 Łódź\n",
            "Michał Szymański",
            "Szymański Dąbrowski Kancelaria Prawna sp.p.",
        ),
        (
            "reprezentowany przez pełnomocnika radcę prawnego Krzysztofa Kozłowskiego z Kancelarii Radcy Prawnego"
            " Krzysztof Kozłowski, ul. Lipowa 6, 20-001 Lublin\n",
            "Krzysztof Kozłowski",
            "Kancelaria Radcy Prawnego Krzysztof Kozłowski",
        ),
    ],
)
def test_attorney_firm_forms(block, person, firm):
    data = process_text(APPEAL_HEAD + ONE_AUTHORITY + PROBE_APPELLANT + block + APPEAL_BODY).data
    attorney = data["Odwolujacy"][0]["pelnomocnik"]
    assert (attorney["imie_nazwisko"], attorney["nazwa"]) == (person, firm)


@pytest.mark.parametrize(
    "block, title",
    [
        (
            'Postępowanie Odbiór i zagospodarowanie odpadów komunalnych" (ZP/101/2026).',
            "Odbiór i zagospodarowanie odpadów komunalnych",
        ),
        ("Przedmiot Odwołanie: Usługi ochrony fizycznej mienia", "Usługi ochrony fizycznej mienia"),
        ("pn. „Dostawa materiałów biurowych\"'nr referencyjny sprawy: DI.228.2026", "Dostawa materiałów biurowych"),
        ('pn. „Świadczenie usług pocztowych"nr referencyjny sprawy: DI.579.2026', "Świadczenie usług pocztowych"),
        (
            'Postępowanie nr PN/244/2026: Termomodernizacja szkoły nr 56", ogłoszenie 2025/BZP 51132740',
            "Termomodernizacja szkoły nr 56",
        ),
    ],
)
def test_title_after_ocr_errors(block, title):
    # The OCR loses quote marks and spaces, and can change the label.
    assert odwolanie.parse_procurement(block, {})["tytul"] == title


TABLE_HEAD = """Kielce 26.02.2026
Prezes Krajowej Izby Odwoławczej
ODWOŁANIE
Dane stron postępowania odwoławczego
Odwołujący
Nazwa
Adres
KRS
NIP
REGON
Pełnomocnik
Kancelaria
E-mail pełnomocnika
Pol-Tech Energetyka sp. z o.o.
ul. Polna 106, 70-786 Kraków
-
8131368471
318996932
adw. Ewa Michalak
Kancelaria Prawa Zamówień Publicznych Michalak sp.k.
zamowienia@michalak.eu
Zamawiający
Nazwa
Adres
KRS
NIP
REGON
Rola w postępowaniu
Gmina Alfa
ul. Polna 119, 30-979 Lublin
-
3794510839
149845728
uczestnik
Zamawiający
Nazwa
Adres
KRS
NIP
REGON
Rola w postępowaniu
Wojewódzki Szpital Zespolony w Szczecin
ul. Lipowa 91, 10-824 Warszawa
0000554179
6632377006
908164548
prowadzący postępowanie (lider)
"""


def test_party_tables():
    # A table gives the labels in lines and then the values in the same order.
    data = process_text(TABLE_HEAD + APPEAL_BODY).data
    appellant = data["Odwolujacy"][0]
    assert (appellant["nazwa"], appellant["krs"], appellant["nip"], appellant["regon"]) == (
        "Pol-Tech Energetyka sp. z o.o.",
        None,
        "8131368471",
        "318996932",
    )
    assert appellant["pelnomocnik"] == {
        "imie_nazwisko": "Ewa Michalak",
        "nazwa": "Kancelaria Prawa Zamówień Publicznych Michalak sp.k.",
        "mail": "zamowienia@michalak.eu",
    }
    rows = [(z["nazwa"], z["krs"], z["nip"], z["prowadzacy_postepowanie"]) for z in data["Zamawiajacy"]]
    assert rows == [
        ("Gmina Alfa", None, "3794510839", 0),
        ("Wojewódzki Szpital Zespolony w Szczecin", "0000554179", "6632377006", 1),
    ]


def test_attorney_before_label_line():
    block = "Pełnomocnik: adwokat Katarzyna Michalak\nKontakt: Kancelaria Radcy Prawnego Katarzyna Michalak, ul. Kościuszki 34, 82-572 Kraków\n"
    data = process_text(APPEAL_HEAD + ONE_AUTHORITY + PROBE_APPELLANT + block + APPEAL_BODY).data
    assert data["Odwolujacy"][0]["pelnomocnik"]["imie_nazwisko"] == "Katarzyna Michalak"


@pytest.mark.parametrize(
    "item, code",
    [
        ("niewykluczeniu z postępowania Odra Budownictwo S.A. pomimo podstaw z art. 109 Pzp", 8),
        ("niedokonaniu odrzucenia oferty złożonej przez Hydro-Sys Sp. z o.o.", 7),
        ("zmianie SWZ ogłoszonej wykonawcom w dniu 17 listopada 2025 r.", 5),
        ("wzorze umowy stanowiącym załącznik do SWZ, udostępnionym w dniu 22 września 2026 r.", 12),
        ("publikacji SWZ w zakresie kryteriów oceny ofert i wzoru umowy z dnia 6 maja 2026 r.", 4),
    ],
)
def test_action_forms(item, code):
    text = APPEAL_HEAD + ONE_AUTHORITY + PROBE_APPELLANT + (
        "\nODWOŁANIE\nwnoszę odwołanie wobec czynności Zamawiającego, polegających na:\n1) " + item + ";\n"
    )
    assert process_text(text).data["OdwolanieKIO"]["czynnosc_powod_id"] == code
