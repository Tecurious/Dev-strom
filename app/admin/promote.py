"""Break-glass CLI: promote an existing user to admin by email.

Usage (from the API repo root, with DATABASE_URL set):

    python -m app.admin.promote you@example.com

Does not create users — they must have signed in with Google/GitHub first.
Prefer ADMIN_EMAILS for routine bootstrap; this is for one-off recovery.
"""

from __future__ import annotations

import sys

from app.auth import service


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or not args[0].strip():
        print("Usage: python -m app.admin.promote <email>", file=sys.stderr)
        return 2
    email = args[0].strip()
    try:
        user = service.promote_email(email)
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"promoted {user['email']} -> role={user['role']} id={user['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
