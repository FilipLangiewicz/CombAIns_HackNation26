# Classification of documents

This file tells how the application finds the type of a document: `odwolanie`, `pelnomocnictwo`, `przelew`, or an unknown type. A document of an unknown type gives `{}`.

The application does not use the file name. The challenge forbids it.

## The rule

The code is in `src/odw2json/classify.py`. The rules are in the key `classify` of each file in `config/types/`.

1. The application joins titles with spaces between the letters, for example "P E Ł N O M O C N I C T W O" becomes "PEŁNOMOCNICTWO".
2. Each type has a list of rules. Each rule is a regular expression with a weight.
3. A rule applies to one of these parts of the text (`where`):
   - `start`: the first 300 characters,
   - `head`: the first `head_chars` characters of the type,
   - `all`: the full text.
4. A rule also matches the text without Polish diacritics, because the OCR can lose them. For example, the rule `ODWOŁANIE` also finds "ODWOLANIE".
5. The key `titles` gives the titles of the type. A line in the head that is 80% or more similar to a title adds `title_weight` (4). Thus "Pehnomocnictwo" from the OCR counts as the title "PEŁNOMOCNICTWO".
6. The score of a type is the sum of the weights of the rules that match.
7. The type with the highest score wins, if its score is equal to or more than its `min_score`.
8. If no type has its `min_score`, the document is of an unknown type.

## The kinds of rules

| Kind | Weight | Example |
|---|---|---|
| Title of the document | +3 or +4 | `ODWOŁANIE`, `PEŁNOMOCNICTWO`, "Potwierdzenie wykonania przelewu" |
| Words for the type | +1 | "Zamawiający", "mocodawca", "rachunek", "PLN" |
| Signs of another kind of document | -10 | "Sygn. akt", "WYROK", "Ogłoszenie o zamówieniu", "See the notice on TED" |

The minimum score is 5. Words alone are not sufficient: each type has 4 or fewer rules of +1. Thus a document needs a title.

A title can match two title rules, for example `^\s*PEŁNOMOCNICTWO` and the same word in capitals. Then the title alone gives the minimum score. The second rule finds a title that a PDF reader joined to another line.

A payment confirmation (`przelew`) has no single required title. A title gives +4. Without a title, these signs together pass the minimum score: two account numbers (+2), a sender and a recipient (+1.5), words for the operation, an account, an amount and "PLN" (+1 each). An invoice has one account and gets fewer points. Titles of an appeal, a power of attorney or an invoice at the start give -10.

The negative rules are necessary. A decision of the KIO or a procurement notice contains many words of an appeal ("odwołanie", "Zamawiający", "Odwołujący").

An appeal without a title in capitals (the header "Do: KIO", "Od:", "Przeciwko:") gets points from these labels and from "Zaskarżone czynności". The answer of the contracting authority ("Odpowiedź na odwołanie") and letters that start with "ODPOWIEDŹ", "ZAWIADOMIENIE" or "WEZWANIE" get -10. The title rule for `odwolanie` is case sensitive and needs a whole line, because a wrapped line that starts with "odwołanie" is not a title.

## Results

On the 196 example documents with a text layer, the classification is correct for all documents:

- 60 appeals, 60 powers of attorney, 60 payment confirmations,
- 16 negative documents (decisions of the KIO, notices from BZP and TED, other letters).

## Limits and what we do about them

| Limit | What we do |
|---|---|
| A new kind of title, for example "Wniosek" or "Skarga" | A document without a known title gets a low score and gives `{}`. This is the safe result: an empty JSON loses fewer points than a wrong type. |
| A negative document that looks like an appeal | The negative rules cover the kinds in `dane/negatywne/`. A new kind needs a new rule in the YAML file. |
| A scan without OCR | The text is empty, so the result is `{}`. |

## Add a new type

To add a new type, do these steps:

1. Copy a file in `config/types/` to a new file.
2. Change `name`, `label` and `template`.
3. Write the `classify` rules for the title and for the other words of the type.
4. Write field rules in the key `fields`. Set `extractor: generic` (see `docs/extraction-rules.md`).

No change of the code is necessary.
