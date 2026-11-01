"""The path parser: shapes of steps, and rejection of anything outside the schema's grammar."""

import pytest

from codemeta_drift.paths import Step, parse


def test_parse_gives_steps_per_alternative() -> None:
    assert parse("a.b[] | ids[type=cff-1.2].value | @x") == [
        [
            Step("a", is_list=False, filter_key=None, filter_value=None),
            Step("b", is_list=True, filter_key=None, filter_value=None),
        ],
        [
            Step("ids", is_list=True, filter_key="type", filter_value="cff-1.2"),
            Step("value", is_list=False, filter_key=None, filter_value=None),
        ],
        [Step("@x", is_list=False, filter_key=None, filter_value=None)],
    ]


@pytest.mark.parametrize("path", ["", "a.", "a[0]", "a[k=]", "a[k=v w]", "a|b", "a  | b", "1a", "a..b", "a[k=v][]"])
def test_parse_rejects_what_the_grammar_rejects(path: str) -> None:
    with pytest.raises(ValueError, match="not a mapping path"):
        parse(path)
