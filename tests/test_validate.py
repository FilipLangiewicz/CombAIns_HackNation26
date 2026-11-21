from odw2json.validate import apply, checksum_ok


def test_digits_are_repaired_and_checked():
    data = {"A": [{"nip": "999-928-4O65"}, {"nip": "12345"}], "B": {"d": "2026-02-30", "m": "a@b.pl"}}
    rules = [
        {"path": "A[].nip", "kind": "digits", "lengths": [10]},
        {"path": "B.d", "kind": "date"},
        {"path": "B.m", "kind": "email"},
    ]
    warnings = apply(data, rules)
    assert data["A"][0]["nip"] == "9999284065"
    assert data["A"][1]["nip"] is None
    assert data["B"] == {"d": None, "m": "a@b.pl"}
    assert len(warnings) == 2


def test_checksums():
    assert checksum_ok("1234563218", "nip")
    assert not checksum_ok("1234563219", "nip")
    assert checksum_ok("44051401359", "pesel")
