"""Safely scan public GitHub repositories from a hosted deployment."""
from __future__ import annotations

import io
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from analyzer import analyze
from scanner import EXCLUDED_DIRS, MAX_FILE_BYTES, scan_repository

MAX_ARCHIVE_BYTES = 30 * 1024 * 1024
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 5000
REPO_RE = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?$", re.IGNORECASE)


def scan_public_github(url: str):
    """Download and inspect a public GitHub repository without running its code."""
    match = REPO_RE.fullmatch(url.strip())
    if not match:
        raise ValueError("Enter a public GitHub repository URL such as https://github.com/owner/repository.")
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    if not owner or not repo:
        raise ValueError("The GitHub URL must include an owner and repository name.")
    download_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    request = urllib.request.Request(download_url, headers={"User-Agent": "Codebase-XRay/1.0", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            host = urllib.parse.urlparse(response.geturl()).hostname
            if host not in {"api.github.com", "github.com", "codeload.github.com"}:
                raise ValueError("GitHub redirected the download to an unexpected host.")
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_ARCHIVE_BYTES:
                raise ValueError("This repository archive is larger than the 30 MB download limit.")
            archive_bytes = response.read(MAX_ARCHIVE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError("Repository not found. Check the URL and make sure the repository is public.") from exc
        if exc.code == 403 or exc.code == 429:
            raise ValueError("GitHub temporarily rate-limited the request. Please try again later.") from exc
        raise ValueError(f"GitHub returned HTTP {exc.code} while downloading the repository.") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError(f"Could not reach GitHub: {exc}") from exc
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("This repository archive is larger than the 30 MB download limit.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("GitHub returned an invalid repository archive.") from exc
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        raise ValueError(f"This repository has more than {MAX_ARCHIVE_ENTRIES:,} archive entries.")
    base_total = sum(info.file_size for info in infos if not info.is_dir())
    if base_total > MAX_SOURCE_BYTES:
        raise ValueError("This repository expands beyond the 100 MB source limit.")

    with tempfile.TemporaryDirectory(prefix="codebase-xray-") as temp:
        root = Path(temp).resolve()
        with archive:
            for info in infos:
                if info.is_dir() or info.file_size > MAX_FILE_BYTES:
                    continue
                if info.flag_bits & 0x1:  # encrypted zip member
                    continue
                # Zip Unix mode indicates symlinks in the high 16 bits.
                if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                    continue
                member = PurePosixPath(info.filename)
                if member.is_absolute() or ".." in member.parts:
                    continue
                parts = member.parts[1:]  # Drop GitHub's single top-level archive directory.
                if not parts or parts[0] == ".env" or parts[0].startswith(".env."):
                    continue
                if any(part in EXCLUDED_DIRS or part.startswith(".env") for part in parts[:-1]):
                    continue
                if parts[-1] == ".env" or parts[-1].startswith(".env."):
                    continue
                target = root.joinpath(*parts)
                resolved = target.resolve()
                if root not in resolved.parents:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as dst:
                    dst.write(src.read(MAX_FILE_BYTES + 1))

        scan = scan_repository(root)
        analysis = analyze(scan)
        scan["name"] = repo
        scan["root"] = f"https://github.com/{owner}/{repo}"
    return scan, analysis
