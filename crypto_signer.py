"""
Cryptographic signing, key management, and tamper-evident verification engine.
Uses ECDSA (Curve SECP256R1 / P-256) with SHA-256 for compact, ultra-secure signatures.
Supports custom PEM private keys or automatically manages a secure default keypair.
"""

import base64
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature


DEFAULT_KEY_DIR = Path.home() / ".config" / "ev-battery-soh" / "keys"


def get_or_create_default_keypair(key_dir: Path = DEFAULT_KEY_DIR) -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """
    Retrieves or generates an ECDSA P-256 keypair stored locally.
    """
    key_dir.mkdir(parents=True, exist_ok=True)
    priv_path = key_dir / "soh_private_key.pem"
    pub_path = key_dir / "soh_public_key.pem"

    if priv_path.exists() and pub_path.exists():
        priv_bytes = priv_path.read_bytes()
        private_key = serialization.load_pem_private_key(priv_bytes, password=None)
        pub_bytes = pub_path.read_bytes()
        public_key = serialization.load_pem_public_key(pub_bytes)
        return private_key, public_key

    # Generate new ECDSA key
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    priv_path.write_bytes(priv_pem)
    priv_path.chmod(0o600)  # Restricted user-only read/write
    pub_path.write_bytes(pub_pem)

    return private_key, public_key


def load_private_key_from_path(key_path: Path, password: Optional[bytes] = None) -> ec.EllipticCurvePrivateKey:
    """
    Loads a custom private key PEM file specified by the user.
    """
    data = key_path.read_bytes()
    return serialization.load_pem_private_key(data, password=password)


def build_canonical_payload(
    cert_id: str,
    vin: Optional[str],
    current_soh: float,
    current_capacity: float,
    initial_capacity: float,
    odometer: float,
    dc_energy_pct: float,
    dataset_hash: str,
    issue_date: str
) -> bytes:
    """
    Constructs a deterministic canonical JSON payload for cryptographic signing.
    """
    data = {
        "cert_id": cert_id,
        "vin": vin or "N/A",
        "soh": round(current_soh, 2),
        "capacity_usable_kwh": round(current_capacity, 2),
        "capacity_baseline_kwh": round(initial_capacity, 2),
        "odometer_km": round(odometer, 0),
        "dc_fast_charge_pct": round(dc_energy_pct, 1),
        "dataset_sha256": dataset_hash,
        "issued_at": issue_date
    }
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode("utf-8")


def sign_payload(payload: bytes, private_key: ec.EllipticCurvePrivateKey) -> str:
    """
    Signs canonical payload using ECDSA with SHA-256 and returns a URL-safe Base64 string.
    """
    signature = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))
    return base64.urlsafe_b64encode(signature).decode("ascii")


def export_public_key_pem(public_key: ec.EllipticCurvePublicKey) -> str:
    """
    Exports public key in standard PEM format string.
    """
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")


def verify_signature(payload: bytes, signature_b64: str, public_key: ec.EllipticCurvePublicKey) -> bool:
    """
    Verifies the signature against the canonical payload.
    """
    try:
        sig_bytes = base64.urlsafe_b64decode(signature_b64.encode("ascii"))
        public_key.verify(sig_bytes, payload, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, Exception):
        return False
