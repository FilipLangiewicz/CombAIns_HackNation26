import re

from odw2json import common
from odw2json.evaluate import dataset
from odw2json.pipeline import process_pdf

LEADER = re.compile(r"\s*\.{3,}\s*")


def leaves(node, path=""):
    """Give (path, value) for each scalar in the JSON. A list index is in brackets."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from leaves(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from leaves(value, f"{path}[{i}]")
    elif node is not None:
        yield path, node


def normal(text: str) -> str:
    # The przelew extractor turns a row of dots into a colon.
    return common.normalize_spaces(LEADER.sub(": ", common.despace_caps(text)))


def test_each_value_has_evidence_from_the_text():
    problems = []
    for _, pdf in dataset("dev"):
        result = process_pdf(pdf)
        text = normal(result.text)
        for path, value in leaves(result.data):
            snippet = result.evidence.get(path)
            if snippet is None:
                problems.append(f"{pdf.parent.name}/{pdf.name}: no evidence for {path} = {value!r}")
            elif normal(snippet).strip(" :") not in text:
                problems.append(f"{pdf.parent.name}/{pdf.name}: {path}: snippet not in text: {snippet!r}")
    assert not problems, "\n".join(problems[:30])
