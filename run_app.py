# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

from app import main
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main.run_app()
