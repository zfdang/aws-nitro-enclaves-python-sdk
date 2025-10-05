#!/usr/bin/env python3
"""Simple demo app that calls the NSM SDK to get randomness and an attestation.

This script is intended to run inside an enclave (or in a debug environment).
It will log the random bytes and a serialized attestation payload to stdout.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from aws_nitro_enclaves.nsm.client import NsmClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("demo_app")


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo NSM app")
    parser.add_argument("--keep-alive", "-k", action="store_true", help="Keep the process alive after demo run (useful for console attach)")
    parser.add_argument("--keep-seconds", "-s", type=int, default=300, help="Number of seconds to keep the demo running when --keep-alive is used")
    args = parser.parse_args()

    try:
        def do_one_iteration(client_instance):
            random_bytes = client_instance.get_random(32)
            logger.info("Random (hex): %s", random_bytes.hex())

            att = client_instance.get_attestation()
            # Ensure attestation is JSON-serializable
            try:
                att_json = json.dumps(att, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
            except Exception:
                att_json = str(att)
            logger.info("Attestation payload: %s", att_json)

        if args.keep_alive:
            logger.info("Keep-alive requested: will retry opening NSM and emit random+attestation every 5s for up to %d seconds (Ctrl-C to exit)", args.keep_seconds)
            end_ts = time.time() + args.keep_seconds
            # Try to open NsmClient until success or timeout
            while time.time() < end_ts:
                try:
                    with NsmClient() as client:
                        logger.info("NSM device path: %s", client.device_path)
                        # Run iterations until timeout
                        while time.time() < end_ts:
                            try:
                                do_one_iteration(client)
                            except Exception:
                                logger.exception("Iteration failed; will retry after 5s")
                            # Sleep up to 5s but don't oversleep past end_ts
                            remaining = end_ts - time.time()
                            if remaining <= 0:
                                break
                            time.sleep(min(5, remaining))
                        # If we exit inner loop (timeout reached), break outer retry loop
                        break
                except Exception:
                    logger.exception("Failed to open NsmClient; will retry in 5s until timeout")
                    # If timeout is reached, exit with error
                    if time.time() + 5 >= end_ts:
                        logger.error("Timeout reached while attempting to open NsmClient")
                        return 2
                    time.sleep(5)
        else:
            # One-shot mode: attempt once and exit on failure
            with NsmClient() as client:
                logger.info("NSM device path: %s", client.device_path)
                do_one_iteration(client)

    except Exception as exc:  # pragma: no cover - demo error handling
        logger.exception("Demo failed: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
