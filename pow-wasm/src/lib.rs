//! AegisLocal Proof-of-Work — SHA-256 leading zero-bit challenge.
//!
//! Payload format (must match backend `app.services.pow`):
//!   `{nonce_prefix}:{challenge_id}:{counter}`
//!
//! Build (optional toolchain):
//!   wasm-pack build --target web

use sha2::{Digest, Sha256};
use wasm_bindgen::prelude::*;

/// Return true if `digest` has at least `difficulty_bits` leading zero bits.
pub fn meets_difficulty(digest: &[u8; 32], difficulty_bits: u32) -> bool {
    let full_bytes = (difficulty_bits / 8) as usize;
    let rem = difficulty_bits % 8;

    if digest[..full_bytes].iter().any(|&b| b != 0) {
        return false;
    }
    if rem == 0 {
        return true;
    }
    let mask: u8 = 0xFFu8 << (8 - rem);
    (digest[full_bytes] & mask) == 0
}

/// Native / testable solver used by WASM export and unit tests.
pub fn solve_pow(nonce_prefix: &str, challenge_id: &str, difficulty: u32) -> (u64, String) {
    let mut counter: u64 = 0;
    loop {
        let payload = format!("{nonce_prefix}:{challenge_id}:{counter}");
        let digest = Sha256::digest(payload.as_bytes());
        let mut arr = [0u8; 32];
        arr.copy_from_slice(&digest);
        if meets_difficulty(&arr, difficulty) {
            return (counter, hex::encode(arr));
        }
        counter = counter.wrapping_add(1);
        // Safety valve for pathological difficulty in demos
        if counter > 50_000_000 {
            panic!("PoW exceeded iteration budget");
        }
    }
}

#[wasm_bindgen]
pub struct PowResult {
    pub counter: u64,
    digest: String,
}

#[wasm_bindgen]
impl PowResult {
    #[wasm_bindgen(getter)]
    pub fn digest(&self) -> String {
        self.digest.clone()
    }
}

/// Browser entrypoint — keep difficulty modest (≤18) for <50ms on mid hardware.
#[wasm_bindgen]
pub fn solve(nonce_prefix: &str, challenge_id: &str, difficulty: u32) -> PowResult {
    let (counter, digest) = solve_pow(nonce_prefix, challenge_id, difficulty);
    PowResult { counter, digest }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn easy_pow_solves() {
        let (counter, digest) = solve_pow("abc", "chal", 8);
        let bytes = hex::decode(&digest).unwrap();
        let mut arr = [0u8; 32];
        arr.copy_from_slice(&bytes);
        assert!(meets_difficulty(&arr, 8));
        assert!(counter < 10_000);
    }
}
