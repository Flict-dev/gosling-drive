from app.infrastructure.security.passwords import hash_password, verify_password


def test_hash_and_verify_long_password() -> None:
    password = "p" * 128
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password)
    assert not verify_password("wrong-password", hashed_password)
