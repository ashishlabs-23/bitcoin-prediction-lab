#!/usr/bin/env python3
"""Check whether optional ONNX conversion and runtime packages are installed.

This utility only checks toolchain readiness; it does not export a model.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def check_onnx_readiness():
    print("Checking ONNX runtime toolchain readiness...")
    try:
        import skl2onnx
        import onnxruntime
        print("  -> ONNX toolchain is available.")
    except ImportError:
        print("  -> Notice: 'skl2onnx' or 'onnxruntime' not installed in lightweight mode.")
        print("     To enable C++ inference: pip install onnx skl2onnx onnxruntime")


if __name__ == "__main__":
    check_onnx_readiness()
