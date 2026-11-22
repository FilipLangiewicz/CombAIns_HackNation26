import numpy as np

from odw2json.ocr import boxes_to_lines, fold, repair, repair_emails, split_points


def test_fold():
    assert fold("Odwołujący Łódź") == "Odwolujacy Lodz"


def test_repair_diacritics_only_for_unique_words():
    text = repair("ODWOLANIE\nOdwolujacy: Firma\nDostawa sprzetu")
    assert text.startswith("ODWOŁANIE\nOdwołujący:")
    assert "Dostawa" in text  # "dostawa" is a word without diacritics, so it does not change


def test_repair_letters_and_joined_words():
    assert repair("Firma sp. Z 0.0.") == "Firma sp. z o.o."
    assert repair("YIdenia Sieci") == "Yldenia Sieci"
    assert repair("Serwisspółka akcyjna zsiedzibą wBiałystok") == "Serwis spółka akcyjna z siedzibą w Białystok"


def test_repair_label_only_before_a_colon():
    assert repair("Tytut: opłata").startswith("Tytuł:")
    assert repair("wniesienia odwołania") == "wniesienia odwołania"  # an inflected word does not change


def test_repair_emails():
    assert repair_emails("tel. 0, bi uro@biuro.exam ple") == "tel. 0, biuro@biuro.example"
    assert repair_emails("biuro @ kontakt.pl") == "biuro@kontakt.pl"
    assert repair_emails("Jan ma kota @ dom") == "Jan ma kota@dom"


def test_lines_and_two_columns():
    boxes = [
        [100, 100, 400, 130, "Jan Nowak"],
        [900, 102, 1200, 132, "Anna Kowalska"],
        [100, 140, 400, 170, "Prezes Zarządu"],
        [900, 142, 1200, 172, "Prokurent"],
        [100, 300, 300, 330, "Kwota:"],
        [320, 300, 500, 330, "17,00 PLN"],
    ]
    assert boxes_to_lines(boxes).split("\n") == [
        "Jan Nowak",
        "Prezes Zarządu",
        "Anna Kowalska",
        "Prokurent",
        "Kwota:  17,00 PLN",
    ]


def test_label_value_table_keeps_rows():
    boxes = [
        [100, 100, 400, 130, "Data operacji"],
        [900, 102, 1200, 132, "2026-04-20"],
        [100, 140, 400, 170, "Kwota"],
        [900, 142, 1200, 172, "17,00 PLN"],
    ]
    assert boxes_to_lines(boxes).split("\n") == ["Data operacji  2026-04-20", "Kwota  17,00 PLN"]


def test_split_points_only_in_gaps():
    gray = np.full((10, 1200), 255, dtype=np.uint8)
    gray[:, :1200] = 0  # one long word without a gap
    assert split_points(gray) == [0, 1200]
    gray[:, 400:420] = 255  # a gap between two words
    cuts = split_points(gray)
    assert len(cuts) == 3 and 400 <= cuts[1] <= 420


def test_repair_emails_after_ocr():
    from odw2json.ocr import repair_emails

    assert (
        repair_emails("e-mail: sekretariat@zawadzkakancelaria .example")
        == "e-mail: sekretariat@zawadzkakancelaria.example"
    )
    assert repair_emails("wiśniewska@prawnik.pl") == "wisniewska@prawnik.pl"


def test_repair_legal_form_keeps_the_case():
    assert repair("Nordenix Automatyka Sp. z 0.0.") == "Nordenix Automatyka Sp. z o.o."
    assert repair("ALFA SP. Z 0.0.") == "ALFA SP. Z O.O."
    assert repair("Beta sp.z o.0.") == "Beta sp. z o.o."


def test_repair_comma_in_email():
    assert repair_emails("e-mail: a,wrobel@wrobel-kancelaria.example") == "e-mail: a.wrobel@wrobel-kancelaria.example"


def test_repair_t_for_l_with_stroke():
    assert repair("wnoszę odwotanie wobec Odwotującego") == "wnoszę odwołanie wobec Odwołującego"
