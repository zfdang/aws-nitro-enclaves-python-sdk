use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::fs::OpenOptions;
use std::io::Result as IoResult;
use std::os::unix::fs::OpenOptionsExt;
use std::os::unix::io::{AsRawFd, RawFd};
use std::path::PathBuf;

// ---------------------------------------------------------------------------
// IMPORTANT
// Replace these placeholder IOCTL request codes with the real values from
// your NSM device header. The values below are examples only and WILL NOT
// match real kernel/ioctl numbers.
// ---------------------------------------------------------------------------

// Example placeholder ioctl numbers (u64 -> passed as libc::c_ulong)
const IOCTL_GET_RANDOM: libc::c_ulong = 0xC004_0001;
const IOCTL_DESCRIBE_PCR: libc::c_ulong = 0xC004_0002;
const IOCTL_EXTEND_PCR: libc::c_ulong = 0xC004_0003;
const IOCTL_DESCRIBE_NSM: libc::c_ulong = 0xC004_0004;

fn open_device_inner(path: &str) -> IoResult<std::fs::File> {
    // Open with read/write. Use 0 for custom flags (or add libc::O_NONBLOCK etc).
    OpenOptions::new()
        .read(true)
        .write(true)
        .custom_flags(0)
        .open(path)
}

#[pyclass]
pub struct NsmDevice {
    path: PathBuf,
    fd: Option<std::fs::File>,
}

#[pymethods]
impl NsmDevice {
    /// Construct a new NsmDevice for a device path (e.g. /dev/nsm)
    #[new]
    #[pyo3(signature = (device_path = "/dev/nsm"))]
    fn new(device_path: &str) -> PyResult<Self> {
        let path = PathBuf::from(device_path);
        // Try to open but don't fail hard here - match behaviour in other session
        match open_device_inner(device_path) {
            Ok(f) => Ok(Self {
                path,
                fd: Some(f),
            }),
            Err(err) => Err(PyRuntimeError::new_err(format!(
                "failed to open device '{}': {}",
                device_path, err
            ))),
        }
    }

    fn device_path(&self) -> PyResult<String> {
        Ok(self.path.to_string_lossy().to_string())
    }

    fn is_open(&self) -> PyResult<bool> {
        Ok(self.fd.is_some())
    }

    fn close(&mut self) -> PyResult<()> {
        self.fd = None;
        Ok(())
    }

    /// Generic ioctl-style helper that performs an ioctl with an input buffer
    /// and returns an output buffer of the requested size. This is a low-level
    /// primitive you can use while wiring real ioctl numbers and C structs.
    fn ioctl_request<'py>(
        &self,
        py: Python<'py>,
        request: usize,
        in_buf: Option<&[u8]>,
        out_size: usize,
    ) -> PyResult<&'py PyBytes> {
        let fd = self
            .fd
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("device not open"))?
            .as_raw_fd();

        // allocate output buffer
        let mut out = vec![0u8; out_size];

        // If there's input data, we copy it into a temporary buffer pointer
        // and pass that pointer to ioctl. Many ioctl APIs use structs so you'll
        // typically need to assemble a proper struct here.
        let in_ptr = match in_buf {
            Some(b) if !b.is_empty() => b.as_ptr() as *mut libc::c_void,
            _ => out.as_mut_ptr() as *mut libc::c_void,
        };

        let res = unsafe { libc::ioctl(fd, request as libc::c_ulong, in_ptr) };
        if res < 0 {
            let e = std::io::Error::last_os_error();
            return Err(PyRuntimeError::new_err(format!(
                "ioctl request 0x{:x} failed: {}",
                request, e
            )));
        }

        // For many devices the ioctl writes into the provided buffer; if the
        // device returns data via a separate read, you would instead call read().
        Ok(PyBytes::new(py, &out))
    }

    /// Example: high-level wrapper that requests random bytes from the device.
    /// Replace IOCTL_GET_RANDOM with the real request and adapt the call
    /// according to the kernel API (structs/args).
    fn get_random<'py>(&self, py: Python<'py>, length: usize) -> PyResult<&'py PyBytes> {
        // Basic guard
        if length == 0 {
            return Err(PyRuntimeError::new_err("length must be > 0"));
        }
        // This example assumes the kernel ioctl will fill a buffer you pass in.
        self.ioctl_request(py, IOCTL_GET_RANDOM as usize, None, length)
    }

    /// Example: describe PCR - this will be heavily dependent on the kernel API.
    fn describe_pcr<'py>(&self, py: Python<'py>, slot: u32) -> PyResult<&'py PyBytes> {
        // Pack slot into a 32-bit little-endian buffer - adjust per your C struct
        let slot_buf = slot.to_ne_bytes();
        self.ioctl_request(py, IOCTL_DESCRIBE_PCR as usize, Some(&slot_buf), 32)
    }

    /// Example: extend PCR - kernel may expect a struct with slot/len/data.
    fn extend_pcr<'py>(&self, py: Python<'py>, slot: u32, data: &[u8]) -> PyResult<&'py PyBytes> {
        // Build a small flat buffer: slot (u32) + data. Real C API is likely different.
        let mut buf = Vec::with_capacity(4 + data.len());
        buf.extend_from_slice(&slot.to_ne_bytes());
        buf.extend_from_slice(data);
        self.ioctl_request(py, IOCTL_EXTEND_PCR as usize, Some(&buf), 32)
    }

    /// Describe NSM metadata via ioctl
    fn describe_nsm<'py>(&self, py: Python<'py>) -> PyResult<&'py PyBytes> {
        // Ask the device for a small JSON or struct blob - here we request 256 bytes
        self.ioctl_request(py, IOCTL_DESCRIBE_NSM as usize, None, 256)
    }
}

// Expose module-level helper to check device existence without opening
#[pyfunction]
fn device_exists(path: &str) -> PyResult<bool> {
    Ok(std::path::Path::new(path).exists())
}

#[pymodule]
fn device(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<NsmDevice>()?;
    m.add_function(wrap_pyfunction!(device_exists, m)?)?;
    // Also re-export into package namespace if helpful
    py.import("sys")?.getattr("modules")?.set_item("aws_nitro_enclaves.nsm.device", m)?;
    Ok(())
}
