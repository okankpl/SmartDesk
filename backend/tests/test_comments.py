import pytest
from pydantic import ValidationError

from app.models.comment import Comment
from app.schemas.comment import CommentCreate


def test_comment_holds_ticket_and_author_reference():
    """Bei striktem TDD waere das der ERSTE Test gewesen, noch bevor
    models/comment.py existierte (Red: ImportError), dann das Model (Green)."""
    comment = Comment(ticket_id=1, author_id=2, body="Testkommentar")

    assert comment.ticket_id == 1
    assert comment.author_id == 2
    assert comment.body == "Testkommentar"


def test_comment_create_accepts_normal_text():
    payload = CommentCreate(body="Rueckfrage an IT gestellt")

    assert payload.body == "Rueckfrage an IT gestellt"


def test_comment_create_strips_surrounding_whitespace():
    payload = CommentCreate(body="  Danke, warte noch  ")

    assert payload.body == "Danke, warte noch"


@pytest.mark.parametrize("empty_body", ["", "   ", "\n\t "])
def test_comment_create_rejects_empty_or_whitespace_only_body(empty_body):
    """Ohne str_strip_whitespace im Schema wuerde "   " die min_length=1-
    Pruefung bestehen (Laenge 3), obwohl der Kommentar inhaltlich leer ist -
    genau dieser Fall wird hier abgesichert."""
    with pytest.raises(ValidationError):
        CommentCreate(body=empty_body)


def test_comment_create_has_no_author_or_ticket_field():
    """Mass-Assignment-Schutz: selbst wenn ein Client author_id/ticket_id
    mitschickt, landen sie NICHT im validierten Objekt - Pydantic ignoriert
    unbekannte Felder standardmaessig. author_id kommt ausschliesslich aus
    dem eingeloggten Nutzer, ticket_id aus der URL (siehe comments.py)."""
    payload = CommentCreate.model_validate({"body": "Text", "author_id": 999, "ticket_id": 999})

    assert not hasattr(payload, "author_id")
    assert not hasattr(payload, "ticket_id")
