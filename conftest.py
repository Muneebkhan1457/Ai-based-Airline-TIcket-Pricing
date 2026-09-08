"""Root conftest.py — ensures project root is on sys.path for all tests."""
import sys
import os

# Add project root to path so `from api.xxx import ...` works
sys.path.insert(0, os.path.dirname(__file__))
