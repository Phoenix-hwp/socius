"""Hook launcher for task error logging.

Tries Python logger first; Node fallback is handled by hooks.json command chain.
This file exists for naming consistency with other launchers.
"""

from error_log_record import main


if __name__ == "__main__":
    main()
