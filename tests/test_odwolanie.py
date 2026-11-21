import pytest

from odw2json.classify import load_types
from odw2json.extractors import odwolanie

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
