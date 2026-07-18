# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import logging

from app import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main.run_app()
