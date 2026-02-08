use lazy_static::lazy_static;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyModule, PyTuple};
use rand::SeedableRng;
use rand_chacha::ChaCha20Rng;
use sha3::{Digest, Sha3_512};
use tos_crypto::bulletproofs::PedersenGens;
use tos_crypto::curve25519_dalek::{RistrettoPoint, Scalar};
use tos_crypto::merlin::Transcript;

lazy_static! {
    static ref PC_GENS: PedersenGens = PedersenGens::default();
    static ref G: RistrettoPoint = PC_GENS.B;
    static ref H: RistrettoPoint = PC_GENS.B_blinding;
}

// ---------------------------------------------------------------------------
// Writer – minimal big-endian binary writer matching Python's Writer class
// ---------------------------------------------------------------------------

struct Writer {
    buf: Vec<u8>,
}

impl Writer {
    fn with_capacity(cap: usize) -> Self {
        Self {
            buf: Vec::with_capacity(cap),
        }
    }

    fn write_u8(&mut self, v: u8) {
        self.buf.push(v);
    }

    fn write_u16(&mut self, v: u16) {
        self.buf.extend_from_slice(&v.to_be_bytes());
    }

    fn write_u64(&mut self, v: u64) {
        self.buf.extend_from_slice(&v.to_be_bytes());
    }

    fn write_bytes(&mut self, b: &[u8]) {
        self.buf.extend_from_slice(b);
    }

    fn write_bool(&mut self, v: bool) {
        self.buf.push(u8::from(v));
    }

    /// Encode Option<&[u8]>: bool flag, then if present u16 length + bytes.
    fn write_optional_vec_u8(&mut self, value: Option<&[u8]>) {
        match value {
            None => self.write_bool(false),
            Some(data) => {
                self.write_bool(true);
                self.write_u16(data.len() as u16);
                self.write_bytes(data);
            }
        }
    }

    fn into_vec(self) -> Vec<u8> {
        self.buf
    }
}

// ---------------------------------------------------------------------------
// Key derivation helpers
// ---------------------------------------------------------------------------

fn keypair_from_byte(byte: u8) -> (Scalar, RistrettoPoint) {
    let mut bytes = [0u8; 32];
    bytes[0] = byte;
    let private = Scalar::from_bytes_mod_order(bytes);
    let public = private.invert() * (*H);
    (private, public)
}

fn keypair_from_private_key_bytes(key: &[u8; 32]) -> (Scalar, RistrettoPoint) {
    let private = Scalar::from_bytes_mod_order(*key);
    let public = private.invert() * (*H);
    (private, public)
}

// ---------------------------------------------------------------------------
// Signing helpers
// ---------------------------------------------------------------------------

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
    // Deterministic nonce for stable test vectors. This is NOT intended as a
    // production signing implementation.
    let mut hasher = Sha3_512::new();
    hasher.update(b"tos-signer/deterministic-nonce/v1");
    hasher.update(private_key.as_bytes());
    hasher.update(compressed_pub);
    hasher.update(message);
    let hash = hasher.finalize();
    let mut k = Scalar::from_bytes_mod_order_wide(&hash.into());
    if k == Scalar::from(0u64) {
        k = Scalar::from(1u64);
    }
    let r = k * (*H);
    let e = hash_and_point_to_scalar(compressed_pub, message, &r);
    let s = private_key.invert() * e + k;
    let mut sig = [0u8; 64];
    sig[..32].copy_from_slice(s.as_bytes());
    sig[32..].copy_from_slice(e.as_bytes());
    sig
}

fn chacha_seed(label: &[u8], a: u8, b: u64) -> [u8; 32] {
    let mut hasher = Sha3_512::new();
    hasher.update(b"tos-signer/chacha-seed/v1");
    hasher.update(label);
    hasher.update([a]);
    hasher.update(b.to_be_bytes());
    let hash = hasher.finalize();
    let mut seed = [0u8; 32];
    seed.copy_from_slice(&hash[..32]);
    seed
}

// ---------------------------------------------------------------------------
// Transfer payload encoding (shared inner logic)
// ---------------------------------------------------------------------------

fn encode_transfer_payload_inner(transfers: &Bound<'_, PyList>) -> PyResult<Vec<u8>> {
    let count = transfers.len();
    if count == 0 {
        return Err(PyValueError::new_err("transfers list must not be empty"));
    }
    // Estimate capacity: 2 (count) + count * (32 + 32 + 8 + 1) = 2 + count * 73
    let mut w = Writer::with_capacity(2 + count * 73);
    w.write_u16(count as u16);

    for i in 0..count {
        let item = transfers.get_item(i)?;
        let tuple = item
            .downcast::<PyTuple>()
            .map_err(|_| PyValueError::new_err(format!("transfers[{i}]: expected a tuple")))?;

        let tuple_len = tuple.len();
        if tuple_len < 3 || tuple_len > 4 {
            return Err(PyValueError::new_err(format!(
                "transfers[{i}]: expected 3 or 4 elements, got {tuple_len}"
            )));
        }

        // asset: bytes (32)
        let asset: Vec<u8> = tuple.get_item(0)?.extract()?;
        if asset.len() != 32 {
            return Err(PyValueError::new_err(format!(
                "transfers[{i}].asset: expected 32 bytes, got {}",
                asset.len()
            )));
        }

        // destination: bytes (32)
        let dest: Vec<u8> = tuple.get_item(1)?.extract()?;
        if dest.len() != 32 {
            return Err(PyValueError::new_err(format!(
                "transfers[{i}].destination: expected 32 bytes, got {}",
                dest.len()
            )));
        }

        // amount: u64
        let amount: u64 = tuple.get_item(2)?.extract()?;

        // extra_data: Optional[bytes]
        let extra_data: Option<Vec<u8>> = if tuple_len == 4 {
            let item = tuple.get_item(3)?;
            if item.is_none() {
                None
            } else {
                Some(item.extract()?)
            }
        } else {
            None
        };

        w.write_bytes(&asset);
        w.write_bytes(&dest);
        w.write_u64(amount);
        w.write_optional_vec_u8(extra_data.as_deref());
    }

    Ok(w.into_vec())
}

// ---------------------------------------------------------------------------
// PyO3-exposed functions
// ---------------------------------------------------------------------------

// -- Existing Level 0 (seed-byte based) ------------------------------------

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

// -- Level 1: Raw private key support --------------------------------------

#[pyfunction]
fn get_public_key_from_private(private_key: &[u8]) -> PyResult<Vec<u8>> {
    if private_key.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "private_key must be 32 bytes, got {}",
            private_key.len()
        )));
    }
    let key: &[u8; 32] = private_key
        .try_into()
        .map_err(|_| PyValueError::new_err("private_key must be 32 bytes"))?;
    let (_, public) = keypair_from_private_key_bytes(key);
    Ok(public.compress().as_bytes().to_vec())
}

#[pyfunction]
fn sign_with_key(data: &[u8], private_key: &[u8]) -> PyResult<Vec<u8>> {
    if private_key.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "private_key must be 32 bytes, got {}",
            private_key.len()
        )));
    }
    let key: &[u8; 32] = private_key
        .try_into()
        .map_err(|_| PyValueError::new_err("private_key must be 32 bytes"))?;
    let (private, public) = keypair_from_private_key_bytes(key);
    let compressed = public.compress();
    let sig = sign(&private, compressed.as_bytes(), data);
    Ok(sig.to_vec())
}

// -- Level 2: Transaction frame assembly -----------------------------------

/// Assemble the signing-bytes frame for any transaction type.
///
/// Layout: [version:u8][chain_id:u8][source:32][tx_type_id:u8][encoded_payload:var]
///         [fee:u64][fee_type:u8][nonce:u64][ref_hash:32][ref_topo:u64]
#[pyfunction]
fn build_signing_bytes(
    version: u8,
    chain_id: u8,
    source: &[u8],
    tx_type_id: u8,
    encoded_payload: &[u8],
    fee: u64,
    fee_type: u8,
    nonce: u64,
    ref_hash: &[u8],
    ref_topo: u64,
) -> PyResult<Vec<u8>> {
    if source.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "source must be 32 bytes, got {}",
            source.len()
        )));
    }
    if ref_hash.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "ref_hash must be 32 bytes, got {}",
            ref_hash.len()
        )));
    }

    // 1 + 1 + 32 + 1 + payload + 8 + 1 + 8 + 32 + 8 = 92 + payload
    let mut w = Writer::with_capacity(92 + encoded_payload.len());
    w.write_u8(version);
    w.write_u8(chain_id);
    w.write_bytes(source);
    w.write_u8(tx_type_id);
    w.write_bytes(encoded_payload);
    w.write_u64(fee);
    w.write_u8(fee_type);
    w.write_u64(nonce);
    w.write_bytes(ref_hash);
    w.write_u64(ref_topo);

    Ok(w.into_vec())
}

// -- Level 3: Payload encoding ---------------------------------------------

/// Encode a list of transfers into payload bytes.
///
/// Each transfer is a tuple: (asset: bytes, destination: bytes, amount: int,
///                             extra_data: Optional[bytes])
/// 3-element tuples are accepted (extra_data defaults to None).
///
/// Format: [count:u16] + for each: [asset:32][dest:32][amount:u64][optional_extra_data]
#[pyfunction]
fn encode_transfer_payload(transfers: &Bound<'_, PyList>) -> PyResult<Vec<u8>> {
    encode_transfer_payload_inner(transfers)
}

/// Encode a burn payload.
///
/// Format: [asset:32][amount:u64]
#[pyfunction]
fn encode_burn_payload(asset: &[u8], amount: u64) -> PyResult<Vec<u8>> {
    if asset.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "asset must be 32 bytes, got {}",
            asset.len()
        )));
    }
    let mut w = Writer::with_capacity(40);
    w.write_bytes(asset);
    w.write_u64(amount);
    Ok(w.into_vec())
}

// -- Level 4: All-in-one convenience ---------------------------------------

/// Build and sign a transfer transaction in one call.
///
/// Returns the 64-byte signature.
#[pyfunction]
fn sign_transfer(
    seed_byte: u8,
    chain_id: u8,
    nonce: u64,
    fee: u64,
    fee_type: u8,
    ref_hash: &[u8],
    ref_topo: u64,
    transfers: &Bound<'_, PyList>,
) -> PyResult<Vec<u8>> {
    if ref_hash.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "ref_hash must be 32 bytes, got {}",
            ref_hash.len()
        )));
    }

    let (private, public) = keypair_from_byte(seed_byte);
    let compressed = public.compress();
    let source = compressed.as_bytes();

    // Encode the transfer payload
    let payload = encode_transfer_payload_inner(transfers)?;

    // Build the signing-bytes frame
    // version = 1 (TxVersion::T1), tx_type_id = 1 (Transfers)
    let mut w = Writer::with_capacity(92 + payload.len());
    w.write_u8(1); // version T1
    w.write_u8(chain_id);
    w.write_bytes(source);
    w.write_u8(1); // tx_type_id for Transfers
    w.write_bytes(&payload);
    w.write_u64(fee);
    w.write_u8(fee_type);
    w.write_u64(nonce);
    w.write_bytes(ref_hash);
    w.write_u64(ref_topo);

    let signing_bytes = w.into_vec();
    let sig = sign(&private, source, &signing_bytes);
    Ok(sig.to_vec())
}

// ---------------------------------------------------------------------------
// Level 5: Privacy crypto helpers
// ---------------------------------------------------------------------------

/// Generate valid shield transfer crypto (commitment, receiver_handle, proof).
///
/// Returns (commitment: 32 bytes, receiver_handle: 32 bytes, proof: 96 bytes).
/// The proof is a valid ShieldCommitmentProof that passes daemon verification.
#[pyfunction]
fn make_shield_crypto(dest_seed: u8, amount: u64) -> PyResult<(Vec<u8>, Vec<u8>, Vec<u8>)> {
    let (_, dest_pub) = keypair_from_byte(dest_seed);

    let seed = chacha_seed(b"shield-crypto", dest_seed, amount);
    let mut rng = ChaCha20Rng::from_seed(seed);

    // Pedersen opening (deterministic scalar r)
    let r = Scalar::random(&mut rng);

    // Commitment C = amount*G + r*H
    let x = Scalar::from(amount);
    let commitment = &x * &*G + &r * &*H;

    // Receiver handle D = r * P_dest
    let receiver_handle = &r * &dest_pub;

    // Shield commitment proof using fresh transcript (matches daemon verifier)
    let mut transcript = Transcript::new(b"shield_commitment_proof");
    // Domain separator (matches ProtocolTranscript::shield_commitment_proof_domain_separator)
    transcript.append_message(b"dom-sep", b"shield-commitment-proof");

    // Deterministic nonce k
    let k = Scalar::random(&mut rng);
    let y_h = (&k * &*H).compress();
    let y_p = (&k * &dest_pub).compress();

    // Append proof commitments to transcript
    transcript.append_message(b"Y_H", y_h.as_bytes());
    transcript.append_message(b"Y_P", y_p.as_bytes());

    // Challenge c
    let c = {
        let mut bytes = [0u8; 64];
        transcript.challenge_bytes(b"c", &mut bytes);
        Scalar::from_bytes_mod_order_wide(&bytes)
    };

    // Response z = c*r + k
    let z = &c * &r + &k;

    // Consume w challenge (matches proof protocol)
    {
        let mut bytes = [0u8; 64];
        transcript.challenge_bytes(b"w", &mut bytes);
    }

    // Serialize commitment (32 bytes)
    let commitment_bytes = commitment.compress().as_bytes().to_vec();

    // Serialize receiver handle (32 bytes)
    let handle_bytes = receiver_handle.compress().as_bytes().to_vec();

    // Serialize proof: Y_H (32) + Y_P (32) + z (32) = 96 bytes
    let mut proof = Vec::with_capacity(96);
    proof.extend_from_slice(y_h.as_bytes());
    proof.extend_from_slice(y_p.as_bytes());
    proof.extend_from_slice(z.as_bytes());

    Ok((commitment_bytes, handle_bytes, proof))
}

/// Generate a random valid compressed Ristretto point (32 bytes).
///
/// Useful for filling fields that need valid curve points for deserialization
/// but don't need to pass proof verification.
#[pyfunction]
fn random_valid_point() -> PyResult<Vec<u8>> {
    // Fixed deterministic point to keep fixtures stable across regenerations.
    let seed = chacha_seed(b"random-valid-point", 0, 0);
    let mut rng = ChaCha20Rng::from_seed(seed);
    let point = RistrettoPoint::random(&mut rng);
    Ok(point.compress().as_bytes().to_vec())
}

/// Generate a valid CiphertextValidityProof byte sequence (160 bytes for T1+).
///
/// Contains valid compressed Ristretto points and canonical scalars that
/// pass wire deserialization. Does NOT pass proof verification.
#[pyfunction]
fn make_dummy_ct_validity_proof() -> PyResult<Vec<u8>> {
    // Deterministic, valid-looking values for wire deserialization stability.
    let seed = chacha_seed(b"dummy-ct-validity-proof", 0, 0);
    let mut rng = ChaCha20Rng::from_seed(seed);

    // Y_0, Y_1, Y_2 (for T1), z_r, z_x
    let y0 = RistrettoPoint::random(&mut rng).compress();
    let y1 = RistrettoPoint::random(&mut rng).compress();
    let y2 = RistrettoPoint::random(&mut rng).compress();
    let z_r = Scalar::random(&mut rng);
    let z_x = Scalar::random(&mut rng);

    let mut out = Vec::with_capacity(160);
    out.extend_from_slice(y0.as_bytes());
    out.extend_from_slice(y1.as_bytes());
    out.extend_from_slice(y2.as_bytes());
    out.extend_from_slice(z_r.as_bytes());
    out.extend_from_slice(z_x.as_bytes());

    Ok(out)
}

// ---------------------------------------------------------------------------
// Module registration
// ---------------------------------------------------------------------------

#[pymodule]
fn tos_signer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Level 0: seed-byte based (existing)
    m.add_function(wrap_pyfunction!(get_public_key, m)?)?;
    m.add_function(wrap_pyfunction!(sign_data, m)?)?;
    // Level 1: raw private key
    m.add_function(wrap_pyfunction!(get_public_key_from_private, m)?)?;
    m.add_function(wrap_pyfunction!(sign_with_key, m)?)?;
    // Level 2: transaction frame
    m.add_function(wrap_pyfunction!(build_signing_bytes, m)?)?;
    // Level 3: payload encoding
    m.add_function(wrap_pyfunction!(encode_transfer_payload, m)?)?;
    m.add_function(wrap_pyfunction!(encode_burn_payload, m)?)?;
    // Level 4: convenience
    m.add_function(wrap_pyfunction!(sign_transfer, m)?)?;
    // Level 5: privacy crypto
    m.add_function(wrap_pyfunction!(make_shield_crypto, m)?)?;
    m.add_function(wrap_pyfunction!(random_valid_point, m)?)?;
    m.add_function(wrap_pyfunction!(make_dummy_ct_validity_proof, m)?)?;
    Ok(())
}
