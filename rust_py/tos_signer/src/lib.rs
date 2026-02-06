use lazy_static::lazy_static;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use sha3::{Digest, Sha3_512};
use tos_crypto::bulletproofs::PedersenGens;
use tos_crypto::curve25519_dalek::{RistrettoPoint, Scalar};

lazy_static! {
    static ref H: RistrettoPoint = PedersenGens::default().B_blinding;
}

fn keypair_from_byte(byte: u8) -> (Scalar, RistrettoPoint) {
    let mut bytes = [0u8; 32];
    bytes[0] = byte;
    let private = Scalar::from_bytes_mod_order(bytes);
    let public = private.invert() * (*H);
    (private, public)
}

fn hash_and_point_to_scalar(
    compressed_pub: &[u8; 32],
    message: &[u8],
    point: &RistrettoPoint,
) -> Scalar {
    let mut hasher = Sha3_512::new();
    hasher.update(compressed_pub);
    hasher.update(message);
    hasher.update(point.compress().as_bytes());
    let hash = hasher.finalize();
    Scalar::from_bytes_mod_order_wide(&hash.into())
}

fn sign(private_key: &Scalar, compressed_pub: &[u8; 32], message: &[u8]) -> [u8; 64] {
    let k = Scalar::random(&mut rand::rngs::OsRng);
    let r = k * (*H);
    let e = hash_and_point_to_scalar(compressed_pub, message, &r);
    let s = private_key.invert() * e + k;
    let mut sig = [0u8; 64];
    sig[..32].copy_from_slice(s.as_bytes());
    sig[32..].copy_from_slice(e.as_bytes());
    sig
}

#[pyfunction]
fn get_public_key(seed_byte: u8) -> PyResult<Vec<u8>> {
    let (_, public) = keypair_from_byte(seed_byte);
    Ok(public.compress().as_bytes().to_vec())
}

#[pyfunction]
fn sign_data(data: &[u8], seed_byte: u8) -> PyResult<Vec<u8>> {
    let (private, public) = keypair_from_byte(seed_byte);
    let compressed = public.compress();
    let sig = sign(&private, compressed.as_bytes(), data);
    Ok(sig.to_vec())
}

#[pymodule]
fn tos_signer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_public_key, m)?)?;
    m.add_function(wrap_pyfunction!(sign_data, m)?)?;
    Ok(())
}
