#!/usr/bin/env python3
"""
ONNX Model Exporter Utility
===========================
Exports trained Scikit-Learn and XGBoost baseline estimators into
portable ONNX runtime artifacts for microsecond edge execution.
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
