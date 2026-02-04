// Generate discv6 peer discovery test vectors for Avatar C cross-validation
// Run: cd ~/tos-spec/rust_generators/crypto && cargo run --release --bin gen_discv6_vectors
//
// Test vectors cover:
// - Node ID computation (SHA3-256 of compressed public key)
// - XOR distance calculation
// - Bucket index (log2_distance) calculation
// - tosnode:// URL parsing

use bulletproofs::PedersenGens;
use curve25519_dalek_ng::scalar::Scalar;
use hex;
use serde::Serialize;
use sha3::{Digest, Sha3_256};
use std::fs::File;
use std::io::Write;

// ============================================================================
// Test Vector Structures
// ============================================================================

#[derive(Serialize)]
struct IdentityVector {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    description: Option<String>,
    secret_key_hex: String,
    public_key_hex: String,
    node_id_hex: String,
}

#[derive(Serialize)]
struct XorDistanceVector {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    description: Option<String>,
    node_id_a_hex: String,
    node_id_b_hex: String,
    xor_distance_hex: String,
}

#[derive(Serialize)]
struct Log2DistanceVector {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    description: Option<String>,
    node_id_a_hex: String,
    node_id_b_hex: String,
    bucket_index: Option<u8>,
}

#[derive(Serialize)]
struct UrlVector {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    description: Option<String>,
    url: String,
    valid: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    node_id_hex: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    ip: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    port: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    is_ipv6: Option<bool>,
}

#[derive(Serialize)]
struct Discv6TestFile {
    protocol: String,
    version: u8,
    node_id_algorithm: String,
    signature_algorithm: String,
    kademlia_k: u8,
    kademlia_alpha: u8,
    num_buckets: u16,
    identity_vectors: Vec<IdentityVector>,
    xor_distance_vectors: Vec<XorDistanceVector>,
    log2_distance_vectors: Vec<Log2DistanceVector>,
    url_vectors: Vec<UrlVector>,
}

// ============================================================================
// Identity Generation (matching TOS Rust discovery/identity.rs)
// Uses the same approach as TOS: public_key = scalar^-1 * H (Pedersen H generator)
// ============================================================================

/// Create a keypair from 32-byte secret using from_bytes_mod_order
/// Returns (private_key_scalar, public_key_compressed_bytes) or None if invalid
fn keypair_from_secret_bytes(bytes: &[u8; 32]) -> Option<(Scalar, [u8; 32])> {
    let scalar = Scalar::from_bytes_mod_order(*bytes);
    if scalar == Scalar::zero() {
        return None;
    }

    // Use Pedersen H generator (same as TOS Schnorr signatures)
    let pc_gens = PedersenGens::default();
    let h = pc_gens.B_blinding;

    // Public key = private_key^-1 * H (TOS convention)
    let public_key = scalar.invert() * h;
    let compressed = public_key.compress().to_bytes();

    Some((scalar, compressed))
}

/// Compute node ID from compressed public key (SHA3-256)
fn compute_node_id(compressed_pubkey: &[u8; 32]) -> [u8; 32] {
    let mut hasher = Sha3_256::new();
    hasher.update(compressed_pubkey);
    let result = hasher.finalize();
    let mut node_id = [0u8; 32];
    node_id.copy_from_slice(&result);
    node_id
}

// ============================================================================
// Distance Functions (matching TOS Rust discovery/identity.rs)
// ============================================================================

/// Calculate XOR distance between two node IDs
fn xor_distance(a: &[u8; 32], b: &[u8; 32]) -> [u8; 32] {
    let mut result = [0u8; 32];
    for i in 0..32 {
        result[i] = a[i] ^ b[i];
    }
    result
}

/// Calculate log2 distance (bucket index)
/// Returns None if IDs are identical, Some(0..255) otherwise
fn log2_distance(a: &[u8; 32], b: &[u8; 32]) -> Option<u8> {
    let distance = xor_distance(a, b);

    for (i, byte) in distance.iter().enumerate() {
        if *byte != 0 {
            let leading_zeros = byte.leading_zeros() as usize;
            let bit_position = i.saturating_mul(8).saturating_add(leading_zeros);
            return Some(255u8.saturating_sub(bit_position as u8));
        }
    }

    None
}

// ============================================================================
// Vector Generation
// ============================================================================

fn generate_identity_vectors() -> Vec<IdentityVector> {
    let mut vectors = Vec::new();

    // Test 1: All zeros secret (should produce deterministic result)
    let secret1 = [0u8; 32];
    if let Some((scalar, pubkey)) = keypair_from_secret_bytes(&secret1) {
        let node_id = compute_node_id(&pubkey);
        vectors.push(IdentityVector {
            name: "zero_secret".to_string(),
            description: Some("Secret key of all zeros".to_string()),
            secret_key_hex: hex::encode(scalar.as_bytes()),
            public_key_hex: hex::encode(pubkey),
            node_id_hex: hex::encode(node_id),
        });
    }

    // Test 2: All ones secret
    let secret2 = [0xffu8; 32];
    if let Some((scalar, pubkey)) = keypair_from_secret_bytes(&secret2) {
        let node_id = compute_node_id(&pubkey);
        vectors.push(IdentityVector {
            name: "ones_secret".to_string(),
            description: Some("Secret key of all 0xff bytes".to_string()),
            secret_key_hex: hex::encode(scalar.as_bytes()),
            public_key_hex: hex::encode(pubkey),
            node_id_hex: hex::encode(node_id),
        });
    }

    // Test 3: Sequential bytes
    let mut secret3 = [0u8; 32];
    for i in 0..32 {
        secret3[i] = i as u8;
    }
    if let Some((scalar, pubkey)) = keypair_from_secret_bytes(&secret3) {
        let node_id = compute_node_id(&pubkey);
        vectors.push(IdentityVector {
            name: "sequential_secret".to_string(),
            description: Some("Secret key of sequential bytes 0x00..0x1f".to_string()),
            secret_key_hex: hex::encode(scalar.as_bytes()),
            public_key_hex: hex::encode(pubkey),
            node_id_hex: hex::encode(node_id),
        });
    }

    // Test 4: TOS-style hash input (like a mnemonic-derived key)
    let seed = b"tos discovery test seed 12345678";
    let mut secret4 = [0u8; 32];
    secret4.copy_from_slice(seed);
    if let Some((scalar, pubkey)) = keypair_from_secret_bytes(&secret4) {
        let node_id = compute_node_id(&pubkey);
        vectors.push(IdentityVector {
            name: "seed_based_secret".to_string(),
            description: Some("Secret key from ASCII seed".to_string()),
            secret_key_hex: hex::encode(scalar.as_bytes()),
            public_key_hex: hex::encode(pubkey),
            node_id_hex: hex::encode(node_id),
        });
    }

    // Test 5: Random-looking but deterministic
    let secret5: [u8; 32] = [
        0x1a, 0x2b, 0x3c, 0x4d, 0x5e, 0x6f, 0x70, 0x81, 0x92, 0xa3, 0xb4, 0xc5, 0xd6, 0xe7, 0xf8,
        0x09, 0x10, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x87, 0x98, 0xa9, 0xba, 0xcb, 0xdc, 0xed,
        0xfe, 0x0f,
    ];
    if let Some((scalar, pubkey)) = keypair_from_secret_bytes(&secret5) {
        let node_id = compute_node_id(&pubkey);
        vectors.push(IdentityVector {
            name: "random_pattern_secret".to_string(),
            description: Some("Deterministic random-looking pattern".to_string()),
            secret_key_hex: hex::encode(scalar.as_bytes()),
            public_key_hex: hex::encode(pubkey),
            node_id_hex: hex::encode(node_id),
        });
    }

    vectors
}

fn generate_xor_distance_vectors() -> Vec<XorDistanceVector> {
    let mut vectors = Vec::new();

    // Test 1: Same IDs (distance = 0)
    let id1 = [0x12u8; 32];
    vectors.push(XorDistanceVector {
        name: "same_ids".to_string(),
        description: Some("XOR distance between identical IDs is zero".to_string()),
        node_id_a_hex: hex::encode(id1),
        node_id_b_hex: hex::encode(id1),
        xor_distance_hex: hex::encode([0u8; 32]),
    });

    // Test 2: All zeros vs all ones
    let id_zeros = [0u8; 32];
    let id_ones = [0xffu8; 32];
    vectors.push(XorDistanceVector {
        name: "zeros_vs_ones".to_string(),
        description: Some("Maximum XOR distance".to_string()),
        node_id_a_hex: hex::encode(id_zeros),
        node_id_b_hex: hex::encode(id_ones),
        xor_distance_hex: hex::encode(xor_distance(&id_zeros, &id_ones)),
    });

    // Test 3: Differ in only first byte
    let mut id_a = [0u8; 32];
    let mut id_b = [0u8; 32];
    id_a[0] = 0x80;
    id_b[0] = 0x00;
    vectors.push(XorDistanceVector {
        name: "differ_first_byte_msb".to_string(),
        description: Some("Differ in MSB of first byte (bucket 255)".to_string()),
        node_id_a_hex: hex::encode(id_a),
        node_id_b_hex: hex::encode(id_b),
        xor_distance_hex: hex::encode(xor_distance(&id_a, &id_b)),
    });

    // Test 4: Differ in only last bit
    let mut id_c = [0u8; 32];
    let mut id_d = [0u8; 32];
    id_c[31] = 0x00;
    id_d[31] = 0x01;
    vectors.push(XorDistanceVector {
        name: "differ_last_bit".to_string(),
        description: Some("Differ in LSB of last byte (bucket 0)".to_string()),
        node_id_a_hex: hex::encode(id_c),
        node_id_b_hex: hex::encode(id_d),
        xor_distance_hex: hex::encode(xor_distance(&id_c, &id_d)),
    });

    // Test 5: Arbitrary pattern
    let id_e: [u8; 32] = [
        0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
        0x07, 0x08,
    ];
    let id_f: [u8; 32] = [
        0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10, 0xee, 0xdd, 0xcc, 0xbb, 0xaa, 0x99, 0x88,
        0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11, 0x00, 0xff, 0xfe, 0xfd, 0xfc, 0xfb, 0xfa, 0xf9,
        0xf8, 0xf7,
    ];
    vectors.push(XorDistanceVector {
        name: "arbitrary_pattern".to_string(),
        description: Some("XOR of two arbitrary patterns".to_string()),
        node_id_a_hex: hex::encode(id_e),
        node_id_b_hex: hex::encode(id_f),
        xor_distance_hex: hex::encode(xor_distance(&id_e, &id_f)),
    });

    vectors
}

fn generate_log2_distance_vectors() -> Vec<Log2DistanceVector> {
    let mut vectors = Vec::new();

    // Test 1: Same IDs (bucket = None)
    let id1 = [0x12u8; 32];
    vectors.push(Log2DistanceVector {
        name: "same_ids".to_string(),
        description: Some("Identical IDs have no bucket index".to_string()),
        node_id_a_hex: hex::encode(id1),
        node_id_b_hex: hex::encode(id1),
        bucket_index: None,
    });

    // Test 2: Differ in MSB of first byte -> bucket 255
    let mut id_a = [0u8; 32];
    let mut id_b = [0u8; 32];
    id_a[0] = 0x80;
    id_b[0] = 0x00;
    vectors.push(Log2DistanceVector {
        name: "bucket_255".to_string(),
        description: Some("Differ in MSB of first byte".to_string()),
        node_id_a_hex: hex::encode(id_a),
        node_id_b_hex: hex::encode(id_b),
        bucket_index: log2_distance(&id_a, &id_b),
    });

    // Test 3: Differ in LSB of last byte -> bucket 0
    let mut id_c = [0u8; 32];
    let mut id_d = [0u8; 32];
    id_c[31] = 0x00;
    id_d[31] = 0x01;
    vectors.push(Log2DistanceVector {
        name: "bucket_0".to_string(),
        description: Some("Differ in LSB of last byte".to_string()),
        node_id_a_hex: hex::encode(id_c),
        node_id_b_hex: hex::encode(id_d),
        bucket_index: log2_distance(&id_c, &id_d),
    });

    // Test 4: Differ in second bit of first byte -> bucket 254
    let mut id_e = [0u8; 32];
    let mut id_f = [0u8; 32];
    id_e[0] = 0x40;
    id_f[0] = 0x00;
    vectors.push(Log2DistanceVector {
        name: "bucket_254".to_string(),
        description: Some("Differ in second bit of first byte".to_string()),
        node_id_a_hex: hex::encode(id_e),
        node_id_b_hex: hex::encode(id_f),
        bucket_index: log2_distance(&id_e, &id_f),
    });

    // Test 5: Differ in MSB of second byte -> bucket 247 (255 - 8)
    let mut id_g = [0u8; 32];
    let mut id_h = [0u8; 32];
    id_g[1] = 0x80;
    id_h[1] = 0x00;
    vectors.push(Log2DistanceVector {
        name: "bucket_247".to_string(),
        description: Some("Differ in MSB of second byte".to_string()),
        node_id_a_hex: hex::encode(id_g),
        node_id_b_hex: hex::encode(id_h),
        bucket_index: log2_distance(&id_g, &id_h),
    });

    // Test 6: Differ in bit 4 of last byte -> bucket 3
    let mut id_i = [0u8; 32];
    let mut id_j = [0u8; 32];
    id_i[31] = 0x08;
    id_j[31] = 0x00;
    vectors.push(Log2DistanceVector {
        name: "bucket_3".to_string(),
        description: Some("Differ in bit 4 of last byte (0x08)".to_string()),
        node_id_a_hex: hex::encode(id_i),
        node_id_b_hex: hex::encode(id_j),
        bucket_index: log2_distance(&id_i, &id_j),
    });

    // Test 7: Middle byte difference -> bucket 127 (255 - 128 = byte 16, MSB)
    let mut id_k = [0u8; 32];
    let mut id_l = [0u8; 32];
    id_k[16] = 0x80;
    id_l[16] = 0x00;
    vectors.push(Log2DistanceVector {
        name: "bucket_127".to_string(),
        description: Some("Differ in MSB of middle byte (index 16)".to_string()),
        node_id_a_hex: hex::encode(id_k),
        node_id_b_hex: hex::encode(id_l),
        bucket_index: log2_distance(&id_k, &id_l),
    });

    vectors
}

fn generate_url_vectors() -> Vec<UrlVector> {
    let mut vectors = Vec::new();

    // Sample node ID (32 bytes = 64 hex chars)
    let sample_node_id = "1a2b3c4d5e6f708192a3b4c5d6e7f80910213243546576879899aabbccddeeff";

    // Test 1: Valid IPv4 URL
    vectors.push(UrlVector {
        name: "valid_ipv4".to_string(),
        description: Some("Standard IPv4 tosnode URL".to_string()),
        url: format!("tosnode://{}@192.168.1.1:2126", sample_node_id),
        valid: true,
        node_id_hex: Some(sample_node_id.to_string()),
        ip: Some("192.168.1.1".to_string()),
        port: Some(2126),
        is_ipv6: Some(false),
    });

    // Test 2: Valid IPv6 URL
    vectors.push(UrlVector {
        name: "valid_ipv6".to_string(),
        description: Some("IPv6 tosnode URL with brackets".to_string()),
        url: format!("tosnode://{}@[::1]:2126", sample_node_id),
        valid: true,
        node_id_hex: Some(sample_node_id.to_string()),
        ip: Some("::1".to_string()),
        port: Some(2126),
        is_ipv6: Some(true),
    });

    // Test 3: Valid IPv6 full address
    vectors.push(UrlVector {
        name: "valid_ipv6_full".to_string(),
        description: Some("Full IPv6 address".to_string()),
        url: format!("tosnode://{}@[2001:db8::1]:2126", sample_node_id),
        valid: true,
        node_id_hex: Some(sample_node_id.to_string()),
        ip: Some("2001:db8::1".to_string()),
        port: Some(2126),
        is_ipv6: Some(true),
    });

    // Test 4: Missing scheme
    vectors.push(UrlVector {
        name: "missing_scheme".to_string(),
        description: Some("URL without tosnode:// prefix".to_string()),
        url: format!("{}@192.168.1.1:2126", sample_node_id),
        valid: false,
        node_id_hex: None,
        ip: None,
        port: None,
        is_ipv6: None,
    });

    // Test 5: Missing @ separator
    vectors.push(UrlVector {
        name: "missing_separator".to_string(),
        description: Some("URL without @ separator".to_string()),
        url: format!("tosnode://{}192.168.1.1:2126", sample_node_id),
        valid: false,
        node_id_hex: None,
        ip: None,
        port: None,
        is_ipv6: None,
    });

    // Test 6: Short node ID
    vectors.push(UrlVector {
        name: "short_node_id".to_string(),
        description: Some("Node ID too short (not 64 hex chars)".to_string()),
        url: "tosnode://1a2b3c@192.168.1.1:2126".to_string(),
        valid: false,
        node_id_hex: None,
        ip: None,
        port: None,
        is_ipv6: None,
    });

    // Test 7: Invalid hex in node ID
    vectors.push(UrlVector {
        name: "invalid_hex".to_string(),
        description: Some("Node ID contains non-hex characters".to_string()),
        url: "tosnode://gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg@192.168.1.1:2126".to_string(),
        valid: false,
        node_id_hex: None,
        ip: None,
        port: None,
        is_ipv6: None,
    });

    // Test 8: Invalid address
    vectors.push(UrlVector {
        name: "invalid_address".to_string(),
        description: Some("Invalid IP address format".to_string()),
        url: format!("tosnode://{}@not-an-address:2126", sample_node_id),
        valid: false,
        node_id_hex: None,
        ip: None,
        port: None,
        is_ipv6: None,
    });

    // Test 9: Missing port
    vectors.push(UrlVector {
        name: "missing_port".to_string(),
        description: Some("URL without port number".to_string()),
        url: format!("tosnode://{}@192.168.1.1", sample_node_id),
        valid: false,
        node_id_hex: None,
        ip: None,
        port: None,
        is_ipv6: None,
    });

    // Test 10: Localhost
    vectors.push(UrlVector {
        name: "localhost".to_string(),
        description: Some("Localhost address".to_string()),
        url: format!("tosnode://{}@127.0.0.1:2126", sample_node_id),
        valid: true,
        node_id_hex: Some(sample_node_id.to_string()),
        ip: Some("127.0.0.1".to_string()),
        port: Some(2126),
        is_ipv6: Some(false),
    });

    // Test 11: High port number
    vectors.push(UrlVector {
        name: "high_port".to_string(),
        description: Some("Maximum valid port number".to_string()),
        url: format!("tosnode://{}@192.168.1.1:65535", sample_node_id),
        valid: true,
        node_id_hex: Some(sample_node_id.to_string()),
        ip: Some("192.168.1.1".to_string()),
        port: Some(65535),
        is_ipv6: Some(false),
    });

    // Test 12: All zeros node ID
    let zeros_node_id = "0000000000000000000000000000000000000000000000000000000000000000";
    vectors.push(UrlVector {
        name: "zeros_node_id".to_string(),
        description: Some("Node ID of all zeros".to_string()),
        url: format!("tosnode://{}@10.0.0.1:2126", zeros_node_id),
        valid: true,
        node_id_hex: Some(zeros_node_id.to_string()),
        ip: Some("10.0.0.1".to_string()),
        port: Some(2126),
        is_ipv6: Some(false),
    });

    vectors
}

fn main() {
    let test_file = Discv6TestFile {
        protocol: "discv6".to_string(),
        version: 6,
        node_id_algorithm: "SHA3-256".to_string(),
        signature_algorithm: "TOS Schnorr (Ristretto255 + SHA3-512)".to_string(),
        kademlia_k: 16,
        kademlia_alpha: 3,
        num_buckets: 256,
        identity_vectors: generate_identity_vectors(),
        xor_distance_vectors: generate_xor_distance_vectors(),
        log2_distance_vectors: generate_log2_distance_vectors(),
        url_vectors: generate_url_vectors(),
    };

    // Output YAML
    let yaml = serde_yaml::to_string(&test_file).unwrap();
    println!("{}", yaml);

    // Also write to file
    let mut file = File::create("discv6.yaml").unwrap();
    file.write_all(yaml.as_bytes()).unwrap();
    eprintln!("Written to discv6.yaml");
}
