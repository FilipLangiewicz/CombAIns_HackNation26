import json
from collections import Counter

import pytest

from odw2json.evaluate import DATA, Score, compare, dataset, gold_for, levenshtein, similarity


def outcomes(ref, pred):
    return Counter(leaf.outcome for leaf in compare(ref, pred))


def test_levenshtein():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "abc") == 0
    assert similarity("abcde", "abcdx") == pytest.approx(0.8)


def test_the_four_outcomes():
    ref = {"a": "1", "b": None, "c": "3", "d": None}
    pred = {"a": "1", "b": None, "c": None, "d": "4"}
    assert outcomes(ref, pred) == Counter(TP=1, TN=1, FN=1, FP=1)


def test_wrong_value_is_fp_for_organizer_and_fp_fn_for_strict():
    score = Score()
    score.add(compare({"a": "1", "b": "2"}, {"a": "1", "b": "x"}))
    assert score.counts == Counter(TP=1, WRONG=1)
    assert score.f1 == pytest.approx(2 / 3)  # 2*1 / (2*1 + 1)
    assert score.f1_strict == pytest.approx(0.5)  # 2*1 / (2*1 + 1 + 1)


def test_missing_key_is_null_and_extra_key_is_fp():
    assert outcomes({"a": "1", "b": None}, {"a": "1"}) == Counter(TP=1, TN=1)
    assert outcomes({"a": "1"}, {"a": "1", "x": "added"}) == Counter(TP=1, FP=1)


def test_types_must_agree_but_int_and_float_agree():
    assert outcomes({"k": 200.0}, {"k": 200}) == Counter(TP=1)
    assert outcomes({"k": 200.0}, {"k": "200.00"}) == Counter(WRONG=1)
    assert outcomes({"k": 1}, {"k": True}) == Counter(WRONG=1)


def test_long_fields_need_80_percent():
    ref = {"przelew_bankowy": {"tytul": "abcdefghij"}}
    assert outcomes(ref, {"przelew_bankowy": {"tytul": "abcdefghXY"}}) == Counter(TP=1)
    assert outcomes(ref, {"przelew_bankowy": {"tytul": "abcdefgXYZ"}}) == Counter(WRONG=1)
    # A short field must agree exactly.
    assert outcomes(
        {"przelew_bankowy": {"kwota_x": "abcdefghij"}}, {"przelew_bankowy": {"kwota_x": "abcdefghiX"}}
    ) == Counter(WRONG=1)


def test_list_items_match_by_content_not_by_order():
    ref = {"p": [{"n": "Anna", "pesel": None}, {"n": "Jan", "pesel": "1"}]}
    pred = {"p": [{"n": "Jan", "pesel": "1"}, {"n": "Anna", "pesel": None}]}
    assert outcomes(ref, pred) == Counter(TP=3, TN=1)


def test_list_with_missing_and_extra_items():
    ref = {"p": [{"n": "Anna"}, {"n": "Jan"}]}
    assert outcomes(ref, {"p": [{"n": "Jan"}]}) == Counter(TP=1, FN=1)
    assert outcomes(ref, {"p": [{"n": "Jan"}, {"n": "Anna"}, {"n": "Ola"}]}) == Counter(TP=2, FP=1)
    assert outcomes(ref, {}) == Counter(FN=2)


def test_list_paths_use_brackets():
    paths = {leaf.path for leaf in compare({"Odwolujacy": [{"nazwa": "X", "pelnomocnik": {"nazwa": "Y"}}]}, {})}
    assert paths == {"Odwolujacy[].nazwa", "Odwolujacy[].pelnomocnik.nazwa"}


def test_negative_document():
    assert outcomes({}, {}) == Counter()
    assert outcomes({}, {"przelew_bankowy": {"kwota": 1.0, "tytul": None}}) == Counter(FP=1, TN=1)


def test_identical_gold_gives_f1_one():
    score = Score()
    for _, pdf in dataset("all"):
        gold = gold_for(pdf)
        score.add(compare(gold, json.loads(json.dumps(gold))))
    assert score.counts["TP"] > 0
    assert score.f1 == 1.0 and score.f1_strict == 1.0


def test_empty_prediction_gives_f1_zero():
    score = Score()
    for _, pdf in dataset("dev"):
        score.add(compare(gold_for(pdf), {}))
    assert score.f1 == 0.0


def test_gold_pairs():
    assert gold_for(DATA / "przyklad_01" / "przelew.pdf")["przelew_bankowy"]
    assert gold_for(DATA / "przyklad_03" / "potwierdzenie_przelewu.pdf")["przelew_bankowy"]
    negatives = [p for _, p in dataset("negatywne")]
    assert negatives and all(gold_for(p) == {} for p in negatives)
    pdfs = [p for _, p in dataset("dev,holdout")]
    assert sum(gold_for(p) == {} for p in pdfs) == 4  # four cases have one extra negative document


def test_split_is_disjoint_and_complete():
    dev = {p.parent.name for _, p in dataset("dev")}
    holdout = {p.parent.name for _, p in dataset("holdout")}
    assert not dev & holdout
    assert len(dev | holdout) == 60
