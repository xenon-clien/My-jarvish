"""JARVIS 3.0 - Comprehensive Test Suite Runner."""
import sys
import pytest


def main():
    print("=" * 60)
    print("🧪 Running JARVIS 3.0 Comprehensive Regression Test Suite...")
    print("=" * 60)
    ret_code = pytest.main(["-v", "tests/"])
    if ret_code == 0:
        print("\n🎉 ALL TESTS PASSED! JARVIS 3.0 Architecture is 100% verified.")
    else:
        print(f"\n❌ Test run finished with exit code {ret_code}.")
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
