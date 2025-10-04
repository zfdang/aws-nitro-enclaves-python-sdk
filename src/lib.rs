use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyBytes, PyDict, PyList};
use rand::rngs::OsRng;
use rand::RngCore;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;

const DEFAULT_DEVICE_PATH: &str = "/var/run/nsm";
const PCR_SLOTS: usize = 32;
const PCR_DIGEST_LEN: usize = 32;
const CERTIFICATE_SLOTS: usize = 4;

#[derive(Debug, Error)]
pub enum NsmError {
    #[error("the NSM device path '{0}' does not exist")]
    DeviceMissing(String),
    #[error("session is closed")]
    SessionClosed,
    #[error("requested random byte length {0} is zero")]
    InvalidRandomLength(usize),
    #[error("PCR slot {0} out of range (0..{1})")]
    InvalidPcrSlot(u32, usize),
    #[error("PCR slot {0} is locked")]
    PcrLocked(u32),
    #[error("certificate slot {0} out of range (0..{1})")]
    InvalidCertificateSlot(u32, usize),
    #[error("certificate slot {0} is empty")]
    CertificateNotFound(u32),
    #[error("attestation generation failed: {0}")]
    AttestationFailure(String),
    #[error("OS random generator failure: {0}")]
    RandomFailure(String),
}

impl NsmError {
    fn into_py_err(self) -> PyErr {
        PyRuntimeError::new_err(self.to_string())
    }
}

fn ensure_device_exists(path: &Path) -> Result<(), NsmError> {
    if Path::new(path).exists() {
        Ok(())
    } else {
        Err(NsmError::DeviceMissing(
            path.to_string_lossy().to_string(),
        ))
    }
}

fn generate_module_id() -> Result<String, NsmError> {
    let mut bytes = vec![0u8; 16];
    OsRng
        .try_fill_bytes(&mut bytes)
        .map_err(|err| NsmError::RandomFailure(err.to_string()))?;
    Ok(bytes.iter().map(|byte| format!("{:02x}", byte)).collect())
}

fn optional_bytes(obj: Option<&PyAny>) -> PyResult<Option<Vec<u8>>> {
    match obj {
        Some(value) => {
            if value.is_none() {
                Ok(None)
            } else {
                value.extract::<Vec<u8>>().map(Some)
            }
        }
        None => Ok(None),
    }
}

fn current_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or_default()
}

#[pyclass]
pub struct NsmSession {
    device_path: PathBuf,
    closed: bool,
    pcrs: Vec<Vec<u8>>,
    pcr_locks: Vec<bool>,
    certificates: HashMap<u32, Vec<u8>>,
    module_id: String,
}

impl NsmSession {
    fn ensure_open(&self) -> Result<(), NsmError> {
        if self.closed {
            Err(NsmError::SessionClosed)
        } else {
            Ok(())
        }
    }

    fn validate_pcr_slot(slot: u32) -> Result<usize, NsmError> {
        let index = slot as usize;
        if index < PCR_SLOTS {
            Ok(index)
        } else {
            Err(NsmError::InvalidPcrSlot(slot, PCR_SLOTS))
        }
    }

    fn validate_certificate_slot(slot: u32) -> Result<u32, NsmError> {
        if (slot as usize) < CERTIFICATE_SLOTS {
            Ok(slot)
        } else {
            Err(NsmError::InvalidCertificateSlot(slot, CERTIFICATE_SLOTS))
        }
    }

    fn pcr_locked(&self, index: usize) -> bool {
        *self.pcr_locks.get(index).unwrap_or(&false)
    }
}

#[pymethods]
impl NsmSession {
    #[new]
    #[pyo3(signature = (device_path = None))]
    fn new(device_path: Option<String>) -> PyResult<Self> {
        let path = device_path.unwrap_or_else(|| DEFAULT_DEVICE_PATH.to_string());
        let pathbuf = PathBuf::from(&path);
        ensure_device_exists(&pathbuf).map_err(NsmError::into_py_err)?;
        let module_id = generate_module_id().map_err(NsmError::into_py_err)?;
        let mut pcrs = Vec::with_capacity(PCR_SLOTS);
        for _ in 0..PCR_SLOTS {
            pcrs.push(vec![0u8; PCR_DIGEST_LEN]);
        }
        Ok(Self {
            device_path: pathbuf,
            closed: false,
            pcrs,
            pcr_locks: vec![false; PCR_SLOTS],
            certificates: HashMap::new(),
            module_id,
        })
    }

    #[getter]
    fn device_path(&self) -> PyResult<String> {
        Ok(self
            .device_path
            .to_str()
            .unwrap_or(DEFAULT_DEVICE_PATH)
            .to_string())
    }

    fn is_closed(&self) -> PyResult<bool> {
        Ok(self.closed)
    }

    fn close(&mut self) -> PyResult<()> {
        self.closed = true;
        Ok(())
    }

    fn get_random<'py>(&self, py: Python<'py>, length: usize) -> PyResult<&'py PyBytes> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        if length == 0 {
            return Err(NsmError::InvalidRandomLength(length).into_py_err());
        }
        let mut buffer = vec![0u8; length];
        OsRng
            .try_fill_bytes(&mut buffer)
            .map_err(|err| NsmError::RandomFailure(err.to_string()).into_py_err())?;
        Ok(PyBytes::new(py, &buffer))
    }

    fn describe_pcr<'py>(&self, py: Python<'py>, slot: u32) -> PyResult<&'py PyBytes> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let index = Self::validate_pcr_slot(slot).map_err(NsmError::into_py_err)?;
        Ok(PyBytes::new(py, &self.pcrs[index]))
    }

    fn describe_pcr_raw<'py>(&self, py: Python<'py>, slot: u32) -> PyResult<&'py PyDict> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let index = Self::validate_pcr_slot(slot).map_err(NsmError::into_py_err)?;
        let dict = PyDict::new(py);
        dict.set_item("index", slot)?;
        dict.set_item("digest", PyBytes::new(py, &self.pcrs[index]))?;
        dict.set_item("locked", self.pcr_locked(index))?;
        Ok(dict)
    }

    fn extend_pcr<'py>(&mut self, py: Python<'py>, slot: u32, data: &[u8]) -> PyResult<&'py PyBytes> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let index = Self::validate_pcr_slot(slot).map_err(NsmError::into_py_err)?;
        if self.pcr_locked(index) {
            return Err(NsmError::PcrLocked(slot).into_py_err());
        }
        let mut hasher = Sha256::new();
        hasher.update(&self.pcrs[index]);
        hasher.update(data);
        let digest = hasher.finalize();
        let mut new_value = vec![0u8; PCR_DIGEST_LEN];
        new_value.copy_from_slice(&digest[..PCR_DIGEST_LEN]);
        self.pcrs[index] = new_value;
        Ok(PyBytes::new(py, &self.pcrs[index]))
    }

    fn lock_pcr(&mut self, slot: u32) -> PyResult<bool> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let index = Self::validate_pcr_slot(slot).map_err(NsmError::into_py_err)?;
        self.pcr_locks[index] = true;
        Ok(true)
    }

    fn lock_pcrs(&mut self, lock_range: u32) -> PyResult<bool> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let max_index = lock_range.min(PCR_SLOTS as u32) as usize;
        for slot in 0..max_index {
            self.pcr_locks[slot] = true;
        }
        Ok(true)
    }

    fn set_certificate(&mut self, slot: u32, certificate: &[u8]) -> PyResult<()> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let slot = Self::validate_certificate_slot(slot).map_err(NsmError::into_py_err)?;
        self.certificates.insert(slot, certificate.to_vec());
        Ok(())
    }

    fn describe_certificate<'py>(&self, py: Python<'py>, slot: u32) -> PyResult<&'py PyBytes> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let slot = Self::validate_certificate_slot(slot).map_err(NsmError::into_py_err)?;
        match self.certificates.get(&slot) {
            Some(value) => Ok(PyBytes::new(py, value)),
            None => Err(NsmError::CertificateNotFound(slot).into_py_err()),
        }
    }

    fn remove_certificate(&mut self, slot: u32) -> PyResult<()> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let slot = Self::validate_certificate_slot(slot).map_err(NsmError::into_py_err)?;
        if self.certificates.remove(&slot).is_some() {
            Ok(())
        } else {
            Err(NsmError::CertificateNotFound(slot).into_py_err())
        }
    }

    fn describe_nsm<'py>(&self, py: Python<'py>) -> PyResult<&'py PyDict> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let dict = PyDict::new(py);
        dict.set_item("module_id", self.module_id.clone())?;
        dict.set_item("pcr_slots", PCR_SLOTS as u32)?;
        dict.set_item("certificate_slots", CERTIFICATE_SLOTS as u32)?;
        let locked = PyList::empty(py);
        for (index, locked_flag) in self.pcr_locks.iter().enumerate() {
            if *locked_flag {
                locked.append(index as u32)?;
            }
        }
        dict.set_item("locked_pcrs", locked)?;
        dict.set_item("certificates", self.certificates.len() as u32)?;
        Ok(dict)
    }

    fn get_attestation<'py>(
        &self,
        py: Python<'py>,
        user_data: Option<&PyAny>,
        public_key: Option<&PyAny>,
        nonce: Option<&PyAny>,
    ) -> PyResult<&'py PyDict> {
        self.ensure_open().map_err(NsmError::into_py_err)?;
        let user_data = optional_bytes(user_data)?;
        let public_key = optional_bytes(public_key)?;
        let nonce = optional_bytes(nonce)?;

        let mut digest_hasher = Sha256::new();
        for value in &self.pcrs {
            digest_hasher.update(value);
        }
        if let Some(ref data) = user_data {
            digest_hasher.update(data);
        }
        let attestation_digest = digest_hasher.finalize();

        let dict = PyDict::new(py);
        dict.set_item("module_id", self.module_id.clone())?;
        dict.set_item("timestamp", current_timestamp())?;
        dict.set_item("digest", PyBytes::new(py, &attestation_digest[..PCR_DIGEST_LEN]))?;

        let pcr_dict = PyDict::new(py);
        for (index, value) in self.pcrs.iter().enumerate() {
            pcr_dict.set_item(index, PyBytes::new(py, value))?;
        }
        dict.set_item("pcrs", pcr_dict)?;

        let locked = PyList::empty(py);
        for (index, locked_flag) in self.pcr_locks.iter().enumerate() {
            if *locked_flag {
                locked.append(index as u32)?;
            }
        }
        dict.set_item("locked_pcrs", locked)?;

        match self.certificates.get(&0) {
            Some(cert) => dict.set_item("certificate", PyBytes::new(py, cert))?,
            None => dict.set_item("certificate", py.None())?,
        }
        dict.set_item("cabundle", py.None())?;

        match user_data {
            Some(ref data) => dict.set_item("user_data", PyBytes::new(py, data))?,
            None => dict.set_item("user_data", py.None())?,
        }
        match public_key {
            Some(ref data) => dict.set_item("public_key", PyBytes::new(py, data))?,
            None => dict.set_item("public_key", py.None())?,
        }
        match nonce {
            Some(ref data) => dict.set_item("nonce", PyBytes::new(py, data))?,
            None => dict.set_item("nonce", py.None())?,
        }

        Ok(dict)
    }
}

#[pyfunction]
fn sdk_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pyfunction]
fn default_device_path() -> &'static str {
    DEFAULT_DEVICE_PATH
}

#[pymodule]
fn _rust(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<NsmSession>()?;
    m.add_function(wrap_pyfunction!(sdk_version, m)?)?;
    m.add_function(wrap_pyfunction!(default_device_path, m)?)?;
    py.import("sys")?.getattr("modules")?.set_item(
        "aws_nitro_enclaves.nsm._rust",
        m,
    )?;
    Ok(())
}
