#!/usr/bin/env python3
"""Check a Kortix deployment's identity layer before you turn SSO enforcement on.

    python3 verify-identity.py --base https://kortix.example.com --scim-token $SCIM_TOKEN

Exit code is the number of failed checks, so it can gate a change request.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "kortix-identity-check/1.0", "Accept": "application/json, application/xml"}


def get(url: str, token: str | None = None, timeout: float = 20.0):
    req = urllib.request.Request(url, headers=dict(UA))
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400_000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read(4_000).decode("utf-8", "ignore")
    except Exception as e:  # connection refused, DNS, TLS
        return 0, f"{type(e).__name__}: {e}"


def check_saml(base: str) -> bool:
    status, body = get(f"{base}/api/auth/saml/metadata")
    if status != 200:
        print(f"FAIL saml: {base}/api/auth/saml/metadata answered {status}")
        return False
    has_entity = "entityID" in body or "entity_id" in body
    has_binding = "HTTP-POST" in body or "HTTP-Redirect" in body
    ok = has_entity and has_binding
    print(f"{'PASS' if ok else 'FAIL'} saml: entityID={has_entity} binding={has_binding}")
    return ok


def check_scim(base: str, token: str) -> bool:
    status, body = get(f"{base}/scim/v2/ServiceProviderConfig", token)
    if status != 200:
        print(f"FAIL scim: ServiceProviderConfig answered {status}: {body[:160]}")
        return False
    try:
        cfg = json.loads(body)
    except json.JSONDecodeError:
        print("FAIL scim: ServiceProviderConfig is not JSON")
        return False
    print(f"PASS scim: ServiceProviderConfig read, {len(cfg)} keys")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, help="instance base URL, e.g. https://kortix.example.com")
    p.add_argument("--scim-token", help="SCIM bearer token from the identity settings")
    p.add_argument("--skip-saml", action="store_true")
    a = p.parse_args()
    base = a.base.rstrip("/")
    failed = 0
    if not a.skip_saml and not check_saml(base):
        failed += 1
    if a.scim_token and not check_scim(base, a.scim_token):
        failed += 1
    elif not a.scim_token:
        print("SKIP scim: no --scim-token given; group sync is untested")
    if failed:
        print(f"\n{failed} check(s) failed. Do not enforce SSO yet: a person locked out of "
              "the only admin account needs the instance operator to fix it.")
    else:
        print("\nidentity layer answers. Enforce SSO only after the first admin has signed "
              "in through the identity provider at least once.")
    return failed


if __name__ == "__main__":
    sys.exit(main())
