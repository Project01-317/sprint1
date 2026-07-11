from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError

# OWASP baseline: 19 MiB (19456 KiB) memory, 2 iterations, 1 degree of
# parallelism. These can be raised on stronger hardware to increase cost.
_ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def hash_password(plaintext: str) -> str:
    """Return an Argon2id hash (salt + parameters embedded) for the password."""
    return _ph.hash(plaintext)


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """Check a password against a stored Argon2id hash."""
    try:
        return _ph.verify(stored_hash, plaintext)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # Wrong password, or a malformed hash in the DB: a failed login,
        # not a crash.
        return False
