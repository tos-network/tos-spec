use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyfunction]
fn dump_yaml(json_str: &str) -> PyResult<String> {
    let value: serde_json::Value = serde_json::from_str(json_str)
        .map_err(|err| pyo3::exceptions::PyValueError::new_err(err.to_string()))?;
    serde_yaml::to_string(&value)
        .map_err(|err| pyo3::exceptions::PyValueError::new_err(err.to_string()))
}

#[pymodule]
fn tos_yaml(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(dump_yaml, m)?)?;
    Ok(())
}
