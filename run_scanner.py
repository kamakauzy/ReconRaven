import sys
import traceback

try:
    import reconraven
    sys.exit(reconraven.main())
except Exception as e:
    print(f"\nERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

