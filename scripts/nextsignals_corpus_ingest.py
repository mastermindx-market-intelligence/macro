#!/usr/bin/env python3
"""Resumable public-X corpus ingest for nextSignals research.

Raw third-party content belongs on the private vendor-source volume, never in Git.
The API key is loaded from TWITTERAPI_IO_KEY or a private key file supplied on-host.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import mimetypes
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://api.twitterapi.io"
DEFAULT_ROOT = Path("/Volumes/Mastermind/vendor-sources/nextsignals")
DEFAULT_KEY_FILE = Path.home() / ".config" / "mastermind" / "twitterapi_io.key"
HTTP_UA = "MMX-nextsignals-research/1.0"
MEDIA_RE = re.compile(r"^https?://(?:pbs\.twimg\.com|video\.twimg\.com)/", re.I)
