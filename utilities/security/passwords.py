from __future__ import annotations

import bcrypt


class PasswordManager:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


crypt = PasswordManager()


def hash_password(password: str) -> str:
    return crypt.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return crypt.verify(plain_password, hashed_password)
