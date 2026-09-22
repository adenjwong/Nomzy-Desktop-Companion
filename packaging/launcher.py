import sys

from nomzy.main import main

if len(sys.argv) == 3 and sys.argv[1] == "--verify-bundle":
    from check_bundle import verify

    raise SystemExit(verify(sys.argv[2]))

raise SystemExit(main())
