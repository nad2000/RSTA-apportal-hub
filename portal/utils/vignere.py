import base64

from django.conf import settings


def encode(clear, key=settings.SECRET_KEY):
    key_len = len(key)
    return base64.urlsafe_b64encode(
        "".join(chr((ord(v) + ord(key[i % key_len])) % 256) for i, v in enumerate(clear)).encode()
    ).decode()


def decode(enc, key=settings.SECRET_KEY):
    enc = base64.urlsafe_b64decode(enc).decode()
    key_len = len(key)
    return "".join(chr((256 + ord(v) - ord(key[i % key_len])) % 256) for i, v in enumerate(enc))
