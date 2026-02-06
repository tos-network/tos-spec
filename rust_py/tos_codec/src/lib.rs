use pyo3::prelude::*;
use pyo3::types::PyModule;
use tos_common::serializer::Serializer;
use tos_common::transaction::Transaction;

#[pyfunction]
fn encode_tx(json_str: &str) -> PyResult<String> {
    let tx: Transaction = serde_json::from_str(json_str)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("JSON parse error: {e}")))?;
    Ok(tx.to_hex())
}

#[pyfunction]
fn decode_tx(hex_str: &str) -> PyResult<String> {
    let tx = Transaction::from_hex(hex_str)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Decode error: {e:?}")))?;
    serde_json::to_string(&tx)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Serialize error: {e}")))
}

#[pyfunction]
fn tx_hash(hex_str: &str) -> PyResult<String> {
    use tos_common::crypto::Hashable;
    let tx = Transaction::from_hex(hex_str)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Decode error: {e:?}")))?;
    Ok(tx.hash().to_hex())
}

#[pymodule]
fn tos_codec(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encode_tx, m)?)?;
    m.add_function(wrap_pyfunction!(decode_tx, m)?)?;
    m.add_function(wrap_pyfunction!(tx_hash, m)?)?;
    Ok(())
}
