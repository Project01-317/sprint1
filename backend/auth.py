"""
auth.py
-------
Password security for ACC-01.

The previous-term example compared passwords in plaintext
(user.Password == password) and stored them unhashed. We do not do that.

We hash with Argon2id, the winner of the 2015 Password Hashing Competition
and OWASP's current first-choice password hashing algorithm. Argon2id is
*memory-hard*: each hash is tuned to consume a fixed amount of RAM, which is
what defeats GPU/ASIC cracking rigs — they can run thousands of cores in
parallel, but they cannot cheaply give every core its own block of fast
memory. A unique random salt is generated and embedded in each hash, so two
identical passwords never produce the same stored value (defeating rainbow
tables).

Parameters below follow the OWASP baseline (19 MiB memory, 2 iterations,
1 lane). Argon2id is the hybrid variant, resistant to both GPU attacks and
side-channel attacks.

  * On sign up, the password is hashed and only the ~$argon2id$... string is
    stored. The plaintext is never persisted or logged.
  * On login, the entered password is verified against the stored hash in
    constant time, so no timing information leaks.
  * Unlike bcrypt, Argon2 has no 72-byte password length limit.
"""

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
