#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

import sys
from pathlib import Path

try:
	from torii_ila.cli import main
except ImportError:
	torii_ila_path = Path(sys.argv[0]).resolve()

	if (torii_ila_path.parent / 'torii_ila').is_dir():
		sys.path.insert(0, str(torii_ila_path.parent))

	from torii_ila.cli import main

raise SystemExit(main())
