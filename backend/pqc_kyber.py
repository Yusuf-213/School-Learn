"""
Post-quantum crypto (Kyber / ML-KEM-1024) helpers.

Uses `kyber-py` — pure-Python NIST FIPS 203 ML-KEM implementation, so there are
no C-extension issues on Render/Railway. Ships alongside `_compat.py` in the
backend package so both packages live in-repo.
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_ALGO = "ML-KEM-1024"

try:
    from kyber_py.ml_kem import ML_KEM_1024 as _KEM   # type: ignore
    _KYBER_AVAILABLE = True
except Exception as e:                                 # pragma: no cover
    logger.warning(f"kyber-py not available: {e}")
    _KEM = None
    _KYBER_AVAILABLE = False


def is_available() -> bool:
    return _KYBER_AVAILABLE


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def selftest() -> dict:
    """Prove the KEM roundtrips on this pod. Returns a status dict."""
    if not _KYBER_AVAILABLE:
        return {"algorithm": _ALGO, "available": False, "roundtrip_ok": False}
    try:
        ek, dk = _KEM.keygen()
        k1, ct = _KEM.encaps(ek)
        k2 = _KEM.decaps(dk, ct)
        ok = k1 == k2 and len(k1) == 32
        return {
            "algorithm": _ALGO,
            "standard": "NIST FIPS 203",
            "available": True,
            "roundtrip_ok": bool(ok),
            "public_key_bytes": len(ek),
            "ciphertext_bytes": len(ct),
            "shared_secret_bytes": len(k1),
        }
    except Exception as e:
        logger.error(f"Kyber selftest failed: {e}")
        return {"algorithm": _ALGO, "available": True, "roundtrip_ok": False, "error": str(e)}


def encapsulate(pk_b64: str) -> dict:
    """Encapsulate a shared secret against a caller-supplied public key.

    Returns {ciphertext_b64, shared_secret_b64} — the caller can use the shared
    secret as an AEAD key (Fernet, AES-256-GCM…) for envelope encryption.
    """
    if not _KYBER_AVAILABLE:
        raise RuntimeError("Kyber unavailable on this pod")
    ek = base64.b64decode(pk_b64)
    k, ct = _KEM.encaps(ek)
    return {"ciphertext_b64": _b64(ct), "shared_secret_b64": _b64(k)}


def generate_keypair() -> dict:
    if not _KYBER_AVAILABLE:
        raise RuntimeError("Kyber unavailable on this pod")
    ek, dk = _KEM.keygen()
    return {"public_key_b64": _b64(ek), "secret_key_b64": _b64(dk)}
