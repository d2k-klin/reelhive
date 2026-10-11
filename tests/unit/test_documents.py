import pytest
from conftest import pdf
from pydantic import ValidationError

from reelhive.config import Config
from reelhive.core.context import RunContext
from reelhive.core.events import EventBus
from reelhive.core.workspace import Workspace
from reelhive.schemas.brief import Brief
from reelhive.visuals import documents, provided
from reelhive.visuals.resolver import MINIMUM_SIZE, catalog, image_ok


def brief(**extra) -> Brief:
    return Brief(audience="Ops teams", storyline="Show the savings", features=["Savings"], closing="Try it", **extra)


def test_pdf_pages_feed_the_catalog_but_match_only_by_name(tmp_path):
    deck = tmp_path / "Pitch Deck.pdf"
    deck.write_bytes(pdf("Savings dashboard cuts cloud bills"))
    ctx = RunContext(tmp_path / "run", brief(documents=[str(deck)]), EventBus(), {}, None, None)

    [page] = documents.pages(ctx.brief.documents, tmp_path / "run" / "documents")
    assert page["image"] == "doc1-pitch-deck-p01.png" and "Savings dashboard" in page["text"]
    assert all(image_ok(tmp_path / "run" / "documents" / page["image"], f) for f in MINIMUM_SIZE)

    entries = catalog(ctx)
    assert [e["image"] for e in entries] == [page["image"]] and "text" not in entries[0]
    # Keyword overlap is strong, but page text never wins a match on its own; the exact filename does.
    assert provided.match(entries, None, "savings dashboard cloud bills") is None
    assert provided.match(entries, page["image"], "") == entries[0]


def test_documents_must_be_pdf_or_decks():
    with pytest.raises(ValidationError):
        brief(documents=["notes.docx"])


def test_document_upload_checks_type_and_joins_the_brief(tmp_path):
    workspace = Workspace(Config(runs_dir=tmp_path / "runs"))
    run = workspace.create(brief(visuals={"source": "none"}), start=False)
    with pytest.raises(ValueError, match="not a valid"):
        workspace.upload(run.id, b"<html>", "fake.pdf")
    result = workspace.upload(run.id, pdf("Hello"), "Q3 deck.pdf")
    assert result["brief"]["documents"] == [result["file"]] and result["name"].startswith("Q3-deck-")
