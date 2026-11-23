#!/usr/bin/env python3
"""Controlled domain-availability checker (business-naming research).

Checks whether domains are delegated in their TLD zone via NS lookups
(dnspython). This is the method behind files 06 and 08-12 of the naming
research. It is a *screening* tool:

  REGISTERED  = NS delegation exists           -> definitive
  AVAILABLE   = NXDOMAIN (no delegation)       -> near-certain for .com/.ai,
                effectively certain for .de (DENIC requires working NS)

ALWAYS re-verify at a registrar before purchase or any public mention.

SAFETY: every run first executes control queries. If the positive control
(google.com must be REGISTERED) or the negative control (random gibberish
must be AVAILABLE) fails, the environment cannot do valid DNS lookups and
the run ABORTS instead of printing false results. This caught a real
failure on 2026-11-23 where a sandbox returned "available" for everything.

Usage:
    python3 check_domains.py NAME [NAME ...] [--tlds com,ai,de]

Example:
    python3 check_domains.py tivran tivrin sumarga --tlds com,ai,de

Requires: pip install dnspython
"""

import argparse
import random
import string
import sys

try:
    import dns.exception
    import dns.resolver
except ImportError:
    sys.exit("dnspython missing: run `python3 -m pip install dnspython` first")

resolver = dns.resolver.Resolver()
resolver.timeout = 5
resolver.lifetime = 12


def check(domain: str) -> str:
    try:
        resolver.resolve(domain, "NS")
        return "REGISTERED"
    except dns.resolver.NXDOMAIN:
        return "AVAILABLE"
    except dns.resolver.NoAnswer:
        # Delegated node without NS answer at the recursive: fall back to SOA,
        # then A (a bare A record still means someone holds the name).
        for rtype in ("SOA", "A"):
            try:
                resolver.resolve(domain, rtype)
                return f"REGISTERED ({rtype} only)"
            except dns.resolver.NXDOMAIN:
                return "AVAILABLE"
            except Exception:
                continue
        return "UNCLEAR (NoAnswer)"
    except dns.resolver.NoNameservers:
        return "REGISTERED (broken delegation)"
    except dns.exception.Timeout:
        return "TIMEOUT"
    except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
        return f"ERROR {type(exc).__name__}"


def run_controls() -> None:
    gibberish = (
        "".join(random.choices(string.ascii_lowercase, k=6))
        + "-controltest-"
        + "".join(random.choices(string.digits, k=5))
        + ".com"
    )
    pos = check("google.com")
    neg = check(gibberish)
    print(f"controls: google.com={pos}  {gibberish}={neg}")
    if not pos.startswith("REGISTERED"):
        sys.exit(
            "ABORT: positive control failed (google.com did not resolve as "
            "REGISTERED). This environment cannot perform valid DNS lookups "
            "(port 53 blocked or filtered). Every result would be false. "
            "Use a registrar search or RDAP from an unrestricted network."
        )
    if neg != "AVAILABLE":
        sys.exit(
            "ABORT: negative control failed (gibberish domain did not come "
            "back AVAILABLE). Resolver may be hijacking NXDOMAIN. Results "
            "would be unreliable."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", help="bare names, without TLD")
    parser.add_argument(
        "--tlds", default="com,ai,de", help="comma-separated TLDs (default com,ai,de)"
    )
    args = parser.parse_args()
    tlds = [t.strip().lstrip(".") for t in args.tlds.split(",") if t.strip()]

    run_controls()
    print()
    width = max(len(n) for n in args.names) + 1
    for name in args.names:
        cells = [f".{t}: {check(f'{name}.{t}'):<24}" for t in tlds]
        print(f"{name:<{width}} " + " | ".join(cells))
    print(
        "\nReminder: AVAILABLE = not delegated in the TLD zone at this moment."
        "\nRe-verify at a registrar before purchase; register before going public."
    )


if __name__ == "__main__":
    main()
