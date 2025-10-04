# Quickstart

```python
from aws_nitro_enclaves.nsm import NsmClient

with NsmClient() as client:
    random_bytes = client.get_random(32)
    print(random_bytes.hex())

    pcr_value = client.describe_pcr(0)
    print("PCR[0]", pcr_value.digest.hex(), "locked?", pcr_value.locked)

    client.lock_pcr(0)
    print("PCR[0] after lock", client.describe_pcr(0).locked)

    info = client.describe_nsm()
    print("Locked PCRs", info["locked_pcrs"])

    raw_doc = client.get_attestation_raw(user_data=b"example")
    print("Raw attestation", raw_doc.keys())

    doc = client.get_attestation(user_data=b"example")
    print("Module ID", doc.module_id)
```

For development environments without an NSM device present, point the client at a
stub socket file:

```python
from pathlib import Path
from aws_nitro_enclaves.nsm import NsmClient

fake_socket = Path("/tmp/nsm.sock")
fake_socket.touch(exist_ok=True)

with NsmClient(device_path=str(fake_socket)) as client:
    try:
        client.get_random(16)
    except Exception as exc:
        print(f"NSM not available: {exc}")
```
