"""Generate shared crypto vectors via Rust generators (serde_yaml canonical output)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

TOS_CRYPTO_DIR = Path("/Users/tomisetsu/tos-spec/rust_generators/crypto")
TOS_UNO_DIR = Path("/Users/tomisetsu/tos/tck/uno")
OUT_DIR = Path("/Users/tomisetsu/tos-spec/fixtures/crypto")
MANIFEST_PATH = TOS_CRYPTO_DIR / "Cargo.toml"


@dataclass
class RustGen:
    name: str
    bin: str
    output: str
    mode: str = "file"  # file | stdout
    cwd: Path = OUT_DIR


def run_gen(gen: RustGen) -> None:
    cmd = [
        "cargo",
        "run",
        "--release",
        "--bin",
        gen.bin,
        "--manifest-path",
        str(MANIFEST_PATH),
    ]
    if gen.mode == "stdout":
        proc = subprocess.run(cmd, cwd=gen.cwd, check=True, capture_output=True, text=True)
        (OUT_DIR / gen.output).write_text(proc.stdout)
        return

    subprocess.run(cmd, cwd=gen.cwd, check=True)
    out = OUT_DIR / gen.output
    if not out.exists():
        raise FileNotFoundError(f"Expected output not found: {out}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    gens = [
        RustGen("sha256", "gen_sha256_vectors", "sha256.yaml"),
        RustGen("sha512", "gen_sha512_vectors", "sha512.yaml"),
        RustGen("sha3_512", "gen_sha3_vectors", "sha3_512.yaml"),
        RustGen("keccak256", "gen_keccak256_vectors", "keccak256.yaml"),
        RustGen("blake3", "gen_blake3_vectors", "blake3.yaml"),
        RustGen("hmac", "gen_hmac_vectors", "hmac_sha256.yaml"),
        RustGen("hmac", "gen_hmac_vectors", "hmac_sha512.yaml"),
        RustGen("base58", "gen_base58_vectors", "base58.yaml"),
        RustGen("bech32", "gen_bech32_vectors", "bech32.yaml"),
        RustGen("bigint", "gen_bigint_vectors", "bigint.yaml"),
        RustGen("ed25519", "gen_ed25519_vectors", "ed25519.yaml"),
        RustGen("curve25519", "gen_curve25519_vectors", "curve25519.yaml"),
        RustGen("x25519", "gen_x25519_vectors", "x25519.yaml"),
        RustGen("chacha20", "gen_chacha20_vectors", "chacha20.yaml"),
        RustGen("aes_gcm", "gen_aes_gcm_vectors", "aes_gcm.yaml"),
        RustGen("chacha20_poly1305", "gen_chacha20_poly1305_vectors", "chacha20_poly1305.yaml"),
        RustGen("poseidon", "gen_poseidon_vectors", "poseidon.yaml"),
        RustGen("bn254", "gen_bn254_vectors", "bn254.yaml"),
        RustGen("rangeproofs", "gen_rangeproofs_vectors", "rangeproofs.yaml"),
        RustGen("secp256k1", "gen_secp256k1_vectors", "secp256k1.yaml", mode="stdout"),
        RustGen("secp256r1", "gen_secp256r1_vectors", "secp256r1.yaml", mode="stdout"),
        RustGen("bls12_381", "gen_bls12_381_vectors", "bls12_381.yaml", mode="stdout"),
        RustGen("schnorr", "gen_schnorr_vectors", "schnorr.yaml"),
        RustGen("vrf", "gen_vrf_vectors", "vrf.yaml"),
        RustGen("multisig", "gen_multisig_vectors", "multisig.yaml"),
        RustGen("contract", "gen_contract_vectors", "contract.yaml"),
        RustGen("escrow", "gen_escrow_vectors", "escrow.yaml"),
        RustGen("arbitration", "gen_arbitration_vectors", "arbitration.yaml"),
        RustGen("kyc", "gen_kyc_vectors", "kyc.yaml"),
        RustGen("referral", "gen_referral_vectors", "referral.yaml"),
        RustGen("tns", "gen_tns_vectors", "tns.yaml"),
        RustGen("uno", "gen_uno_vectors", "uno.yaml"),
        RustGen("block_hash", "gen_block_hash_vectors", "block_hash.yaml"),
        RustGen("discv6", "gen_discv6_vectors", "discv6.yaml"),
        RustGen("basic", "gen_basic_vectors", "basic.yaml"),
    ]

    for gen in gens:
        run_gen(gen)

    # Copy UNO proofs (generated in TOS TCK)
    uno_proofs = TOS_UNO_DIR / "uno_proofs.yaml"
    if uno_proofs.exists():
        shutil.copy2(uno_proofs, OUT_DIR / "uno_proofs.yaml")


if __name__ == "__main__":
    main()
