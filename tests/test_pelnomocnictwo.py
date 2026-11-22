import pytest

from odw2json.classify import load_types
from odw2json.extractors.pelnomocnictwo import extract
from odw2json.pipeline import process_text

DOC_TYPE = next(t for t in load_types() if t.name == "pelnomocnictwo")


def run(text: str) -> dict:
    return extract(text, DOC_TYPE, {})


COMPANY = """P E Ł N O M O C N I C T W O
Mocodawca Hartica Serwis S.A.
ul. Akacjowa 54, 80-122 Gdańsk
Dane rejestrowe KRS 9999669444, NIP 9990678035, REGON 999114017
Pełnomocnicy adw. Bartosz Szymanski, nr wpisu WA 33513
r. pr. Katarzyna Michalak, PESEL 85071204278
Zakres: udzielania dalszych pełnomocnictw radcom prawnym i adwokatom.
............
Aleksandra Nowakowicz
Prokurent
"""


def test_company_with_two_attorneys():
    data = run(COMPANY)
    principal = data["mocodawca"][0]
    assert principal["data"] == {
        "imie_nazwisko": None, "krs": "9999669444", "nazwa": "Hartica Serwis S.A.", "nip": "9990678035", "typ": "osoba_prawna",
    }  # fmt: skip
    assert principal["podpisujacy"] == [{"imie_nazwisko": "Aleksandra Nowakowicz"}]
    assert data["pelnomocnicy"] == [
        {"imie_nazwisko": "Bartosz Szymanski", "pesel": None},
        {"imie_nazwisko": "Katarzyna Michalak", "pesel": "85071204278"},
    ]


def test_natural_person():
    text = (
        "PEŁNOMOCNICTWO\nJa, niżej podpisany Jarosław Dudek, prowadzący działalność gospodarczą pod firmą DUDEK-TECH\n"
        "Jarosław Dudek, ul. Nadbystrzycka 40, 20-618 Lublin, NIP 9994150873, REGON 999603218, niniejszym udzielam\n"
        "pełnomocnictwa: adw. Natalia Górecka (nr wpisu na listę: LU/Adw/733).\n"
    )
    data = run(text)["mocodawca"][0]
    assert data["data"]["typ"] == "osoba_fizyczna"
    assert data["data"]["imie_nazwisko"] == "Jarosław Dudek"
    assert data["data"]["nazwa"] == "DUDEK-TECH Jarosław Dudek"
    assert data["data"]["krs"] is None
    assert data["podpisujacy"] == [{"imie_nazwisko": "Jarosław Dudek"}]


def test_consortium_signers_follow_the_company():
    text = (
        "PEŁNOMOCNICTWO\nKonsorcjum: 1) Torvex Budownictwo sp. z o.o., ul. Przemysłowa 8, 87-100 Toruń, KRS 9995540127, "
        "NIP 9992284611, REGON 999473016; 2) Hydromel Instalacje sp.j., ul. Lipowa 15, 85-016 Bydgoszcz, KRS "
        "9997108834, NIP 9994417025, REGON 999650438 udzielają pełnomocnictwa: adw. Piotr Zalewski.\n"
        "W imieniu Torvex Budownictwo sp. z o.o.:\n....\nMarek Domański\nPrezes Zarządu\n"
        "W imieniu Hydromel Instalacje sp.j.:\n....\nAgnieszka Kurek\nWspólnik\n....\nRobert Kurek\nWspólnik\n"
    )
    principals = run(text)["mocodawca"]
    assert [p["data"]["nazwa"] for p in principals] == ["Torvex Budownictwo sp. z o.o.", "Hydromel Instalacje sp.j."]
    assert [len(p["podpisujacy"]) for p in principals] == [1, 2]


def test_attorney_in_another_case():
    text = "PEŁNOMOCNICTWO\nFirma Alfa S.A., KRS 9999669444, NIP 9990678035 udzielam pełnomocnictwa Panu Piotrowi Nowakowi."
    assert run(text)["pelnomocnicy"] == [{"imie_nazwisko": "Piotr Nowak", "pesel": None}]
    text = "PEŁNOMOCNICTWO\nFirma Alfa S.A., KRS 9999669444, NIP 9990678035 udzielam pełnomocnictwa adw. Katarzynie Kowalskiej."
    assert run(text)["pelnomocnicy"] == [{"imie_nazwisko": "Katarzyna Kowalska", "pesel": None}]
    text = "PEŁNOMOCNICTWO\nFirma Alfa S.A., KRS 9999669444, NIP 9990678035 ustanawiam r. pr. Marka Kowalskiego."
    assert run(text)["pelnomocnicy"] == [{"imie_nazwisko": "Marek Kowalski", "pesel": None}]


def test_signer_on_one_line_and_without_role():
    text = (
        "Pełnomocnictwo\nMocodawca Beta Usługi sp. z o.o. (KRS 9999669444, NIP 9990678035) upoważnia adw. Jan Nowak.\n"
        "............\nAnna Kowalska – Prezes Zarządu\n............\nPiotr Wiśniewski\n"
    )
    signers = run(text)["mocodawca"][0]["podpisujacy"]
    assert signers == [{"imie_nazwisko": "Anna Kowalska"}, {"imie_nazwisko": "Piotr Wiśniewski"}]


def test_company_without_known_legal_form():
    text = "PEŁNOMOCNICTWO\nMocodawca: Przedsiębiorstwo Handlowe Gamma, ul. Długa 1, 00-001 Łódź, KRS 9999669444, NIP 9990678035\nudziela adw. Jan Nowak."
    assert run(text)["mocodawca"][0]["data"]["nazwa"] == "Przedsiębiorstwo Handlowe Gamma"


DECLARANT = """PEŁNOMOCNICTWO
Ja, niżej podpisana Justyna Walczak, działająca jako Dyrektor spółki Zenitel
Medyczne sp. j. z siedzibą w Gliwicach, KRS 0009991806, NIP 8321217280,
udzielam pełnomocnictwa Panu Grzegorzowi Jaworskiemu, adwokatowi, legitymującemu się numerem PESEL
80021565391, do reprezentowania mnie przed KIO.
............
Justyna Walczak – Dyrektor
"""


def test_declarant_acting_for_a_company():
    principal = run(DECLARANT)["mocodawca"][0]
    assert principal["data"]["typ"] == "osoba_prawna"
    assert principal["data"]["nazwa"] == "Zenitel Medyczne sp. j."
    assert principal["podpisujacy"] == [{"imie_nazwisko": "Justyna Walczak"}]
    assert run(DECLARANT)["pelnomocnicy"] == [{"imie_nazwisko": "Grzegorz Jaworski", "pesel": "80021565391"}]


def test_sole_proprietor_without_krs():
    text = (
        "PEŁNOMOCNICTWO\nMocodawca: NORDIS-TRANS Grzegorz Kozłowski\nImię i nazwisko: Grzegorz Kozłowski\n"
        "NIP 4039453214, REGON 422468394\nPełnomocnik: adw. Aleksandra Krawczyk\n"
    )
    data = run(text)["mocodawca"][0]["data"]
    assert data["typ"] == "osoba_fizyczna"
    assert data["imie_nazwisko"] == "Grzegorz Kozłowski"


def names(items: list[dict]) -> list[str]:
    return [i["imie_nazwisko"] for i in items]


def test_signer_with_pan_is_not_an_attorney():
    data = run(
        "PEŁNOMOCNICTWO\nPani Maria Jankowska, działająca jako Dyrektor spółki Poltech Serwis sp. z o.o., KRS 0003884146, "
        "NIP 1553848431, niniejszym udziela Panu Adamowi Baranowi (PESEL 68042407885) pełnomocnictwa.\n"
        "............................\nMaria Jankowska\nDyrektor\n"
    )
    assert names(data["mocodawca"][0]["podpisujacy"]) == ["Maria Jankowska"]
    assert data["pelnomocnicy"] == [{"imie_nazwisko": "Adam Baran", "pesel": "68042407885"}]


def test_attorney_who_accepts_is_not_a_signer():
    data = run(
        "PEŁNOMOCNICTWO\nEkoma Ochrona sp. z o.o., KRS 0007275192, NIP 7317663813, udziela pełnomocnictwa Pani Aleksandrze "
        "Woźniak, adwokat, legitymującej się numerem PESEL 83060299696.\nW imieniu Mocodawcy:\n"
        "............................\nKarolina Szymańska\n(Członek Zarządu)\nPrzyjmuję pełnomocnictwo:\n"
        "............................\nadw. Aleksandra Woźniak\n"
    )
    assert names(data["mocodawca"][0]["podpisujacy"]) == ["Karolina Szymańska"]
    assert data["pelnomocnicy"] == [{"imie_nazwisko": "Aleksandra Woźniak", "pesel": "83060299696"}]


def test_roles_before_the_names_in_the_accusative():
    data = run(
        "PEŁNOMOCNICTWO\nMedixa Technologie S.A. (KRS 0001250745, NIP 9454494443), reprezentowana przez Prokurenta "
        "Katarzynę Nowak, ustanawia swoim pełnomocnikiem radcę prawną Marię Kubiak w sprawie odwołania.\n"
        "............................\n(podpis i pieczęć)\n"
    )
    assert names(data["mocodawca"][0]["podpisujacy"]) == ["Katarzyna Nowak"]
    assert names(data["pelnomocnicy"]) == ["Maria Kubiak"]


def test_letterhead_of_the_law_firm_is_not_a_principal():
    data = run(
        "Kancelaria Prawna Majewska sp. z o.o.\nul. Mokotowska 45, NIP 3376507103\nPEŁNOMOCNICTWO\n"
        "Działając w imieniu Nordis Konstrukcje sp. j., ul. Piłsudskiego 42, 30-799 Warszawa, KRS 0002947999, NIP "
        "8913991871, my, Magdalena Szewczyk (Prokurent), upoważniamy adw. Natalia Majewska z kancelarii Kancelaria "
        "Prawna Majewska sp. z o.o.\nZa zgodność z oryginałem:\nadw. Natalia Majewska\n"
    )
    assert len(data["mocodawca"]) == 1
    principal = data["mocodawca"][0]
    assert principal["data"]["nazwa"] == "Nordis Konstrukcje sp. j."
    assert principal["data"]["krs"] == "0002947999"
    assert names(principal["podpisujacy"]) == ["Magdalena Szewczyk"]
    assert names(data["pelnomocnicy"]) == ["Natalia Majewska"]


def test_list_of_attorneys_without_titles():
    data = run(
        "PEŁNOMOCNICTWO\nKalinex Logistyka Spółka z ograniczoną odpowiedzialnością z siedzibą w Wrocław, ul.\n"
        "Leśna 58, KRS: 9998927009, NIP: 9990864252, reprezentowana przez: Szymon Jabłoń -\n"
        "Wiceprezes Zarządu, niniejszym udziela Pełnomocnictwo:\nAleksandra Rybak\n"
        "Krzysztof Jodłowski (radca prawny, nr wpisu PO-4973, PESEL: 69102340858)\ndo reprezentowania Mocodawcy.\n"
    )
    principal = data["mocodawca"][0]
    assert principal["data"]["nazwa"] == "Kalinex Logistyka Spółka z ograniczoną odpowiedzialnością"
    assert names(principal["podpisujacy"]) == ["Szymon Jabłoń"]
    assert data["pelnomocnicy"] == [
        {"imie_nazwisko": "Aleksandra Rybak", "pesel": None},
        {"imie_nazwisko": "Krzysztof Jodłowski", "pesel": "69102340858"},
    ]


def test_role_under_the_attorney_in_two_ocr_columns():
    # The OCR mixes the rows of two signature columns: the role of the signer stands under the attorney.
    text = """PEŁNOMOCNICTWO
Mocodawcą jest Belmoria Rozwiązania S.A., ul. Zaczarowana 78, 90-803 Łódź, KRS 9999405188, NIP 9999284065.
Mocodawca ustanawia pełnomocnikiem r. pr. Aleksandra Marciniak (nr wpisu na listę: WA 93198).
Mocodawcy:
Oliwia Kaczmarek
Pełnomocnictwo przyjmuję:
r. pr. Aleksandra Marciniak
Prezes Zarządu
"""
    data = run(text)
    assert data["mocodawca"][0]["podpisujacy"] == [{"imie_nazwisko": "Oliwia Kaczmarek"}]
    assert [p["imie_nazwisko"] for p in data["pelnomocnicy"]] == ["Aleksandra Marciniak"]


@pytest.mark.parametrize(
    "head, name",
    [
        (
            "§ 1. Mocodawca\nMocodawcą jest Karpaty Transport Sp. z o.o., ul. Długa 54, 48-579 Wrocław, KRS:\n"
            "0000861670, NIP: 390 469 94 36, REGON: 678296758.\n",
            "Karpaty Transport Sp. z o.o.",
        ),
        (
            "Mocodawca 1: ALFA-NET Andrzej Wójcik\nAdres: ul. Lipowa 75, 54-851 Warszawa\nNIP: 982-385-54-38\n",
            "ALFA-NET Andrzej Wójcik",
        ),
    ],
)
def test_principal_heading_forms(head, name):
    text = (
        "PEŁNOMOCNICTWO\n" + head + "Pełnomocnik 1: radca prawny Andrzej Nowak (PESEL 56262305539)\n"
        "Osoby podpisujące w imieniu mocodawcy:\n............................\nAndrzej Wójcik\n"
    )
    data = process_text(text).data
    assert data["mocodawca"][0]["data"]["nazwa"] == name
