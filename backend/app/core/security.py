import bcrypt

# bcrypt erwartet bytes statt str (die zugrundeliegende C-Bibliothek kennt kein
# Python-/Unicode-str). encode()/decode() übersetzen zwischen beiden Welten;
# gespeichert wird der Hash am Ende wieder als str (User.hashed_password: Mapped[str]).


def hash_password(plain_password: str) -> str:
    """Wandelt ein Klartext-Passwort in einen speicherbaren Hash um.

    Wird bei der Registrierung aufgerufen, BEVOR das Passwort in die
    Datenbank geschrieben wird - das Original wird nie gespeichert.
    """
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Prüft, ob ein eingegebenes Passwort zum gespeicherten Hash passt.

    checkpw liest den Salt aus hashed_password heraus, hasht plain_password
    damit erneut und vergleicht die beiden Hashes - kein eigener Salt nötig.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
