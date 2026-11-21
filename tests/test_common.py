import pytest

from odw2json.common import to_nominative


@pytest.mark.parametrize(
    "name, expected",
    [
        # male: genitive, dative, accusative, instrumental
        ("Jana Kowalskiego", "Jan Kowalski"),
        ("Janowi Kowalskiemu", "Jan Kowalski"),
        ("Jana Nowaka", "Jan Nowak"),
        ("Janem Kowalskim", "Jan Kowalski"),
        ("Marka Wiśniewskiego", "Marek Wiśniewski"),
        ("Pawła Zielińskiego", "Paweł Zieliński"),
        ("Jerzego Wysockiego", "Jerzy Wysocki"),
        # female: genitive, dative, accusative, instrumental
        ("Anny Nowickiej", "Anna Nowicka"),
        ("Annie Nowickiej", "Anna Nowicka"),
        ("Annę Nowicką", "Anna Nowicka"),
        ("Anną Nowicką", "Anna Nowicka"),
        ("Katarzyny Kowalskiej", "Katarzyna Kowalska"),
        ("Małgorzacie Dąbrowskiej", "Małgorzata Dąbrowska"),
        ("Marii Lewandowskiej", "Maria Lewandowska"),
        # a first name that is not in the list: only the surname changes
        ("Xyzon Kowalskiego", "Xyzon Kowalski"),
    ],
)
def test_oblique_case_to_nominative(name, expected):
    assert to_nominative(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "Jolanta Zajkowski",
        "Bartosz Szymanski",
        "Jan Kowalski",
        "Anna Nowicka",
        "Marek Nowak",
        "Xyzon Nowak",
        "Kowalski",
    ],
)
def test_nominative_does_not_change(name):
    assert to_nominative(name) == name


def test_own_name_lists():
    assert to_nominative("Xyzona Nowaka", frozenset({"Xyzon"}), frozenset()) == "Xyzon Nowak"
