from tags import ProposedTag, append_candidate_tags, known_tags

TAGGING = """# Tagging System

## Initial canonical tags

| Tag | When to use |
|-----|-------------|
| `work` | Consulting |

## Candidate tags (promote when recurring)

Introduce only when at least two entries need the tag:

- `work/shipt` — Shipt client work
"""


def test_known_tags_extracts_backtick_tags():
    tags = known_tags(TAGGING)
    assert "work" in tags
    assert "work/shipt" in tags


def test_append_candidate_tags_adds_new_only():
    updated, added = append_candidate_tags(
        TAGGING,
        [ProposedTag(tag="work/beauty", definition="Beauty client QA")],
    )
    assert len(added) == 1
    assert "`work/beauty`" in updated
    assert updated.count("`work/shipt`") == 1


def test_append_candidate_tags_skips_duplicates():
    updated, added = append_candidate_tags(
        TAGGING,
        [ProposedTag(tag="work/shipt", definition="Duplicate")],
    )
    assert added == []
    assert updated == TAGGING
