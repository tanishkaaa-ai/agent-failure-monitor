#!/usr/bin/env python3
"""
Environment Verification Script
Tests Python version, virtual environment status, and core library imports.
"""

import sys

REQUIRED_PACKAGES = [
    ("numpy", "NumPy"),
    ("pandas", "Pandas"),
    ("sklearn", "scikit-learn"),
    ("matplotlib", "Matplotlib"),
    ("seaborn", "Seaborn"),
    ("IPython", "IPython / Jupyter Kernel"),
]


def check_python_version():
    major, minor = sys.version_info[:2]
    status = "PASS" if (major, minor) >= (3, 10) else "WARN"
    print(f"[{status}] Python Version: {sys.version.split()[0]} (Recommended: 3.10+)")
    return status == "PASS"


def check_virtual_env():
    # In a virtualenv, sys.prefix != sys.base_prefix
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    status = "PASS" if in_venv else "WARN"
    print(
        f"[{status}] Virtual Environment: {'Active (' + sys.prefix + ')' if in_venv else 'Not active (Using global interpreter)'}"
    )
    return in_venv


def check_libraries():
    print("\nChecking required libraries:")
    all_ok = True
    for module_name, display_name in REQUIRED_PACKAGES:
        try:
            mod = __import__(module_name)
            ver = getattr(mod, "__version__", "installed")
            print(f"  [PASS] {display_name:<25} version: {ver}")
        except ImportError:
            print(f"  [FAIL] {display_name:<25} NOT INSTALLED")
            all_ok = False
    return all_ok


def main():
    print("=" * 60)
    print("  Agent Failure Prediction System - Environment Verification")
    print("=" * 60)

    py_ok = check_python_version()
    venv_ok = check_virtual_env()
    libs_ok = check_libraries()

    print("\n" + "=" * 60)
    if py_ok and venv_ok and libs_ok:
        print("  ALL CHECKS PASSED! Your environment is ready.")
    else:
        print("  SOME CHECKS NEED ATTENTION:")
        if not venv_ok:
            print("  - Activate your virtual environment: source venv/bin/activate")
        if not libs_ok:
            print("  - Install packages: pip install -r requirements.txt")
    print("=" * 60)


if __name__ == "__main__":
    main()

