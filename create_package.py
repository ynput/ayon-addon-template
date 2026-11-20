#!/usr/bin/env python

"""Prepares server package from addon repo to upload to server.

Requires Python 3.9. (Or at least 3.8+).

This script should be called from cloned addon repo.

It will produce 'package' subdirectory which could be pasted into server
addon directory directly (eg. into `ayon-backend/addons`).

Format of package folder:
ADDON_REPO/package/{addon name}/{addon version}

You can specify `--output_dir` in arguments to change output directory where
package will be created. Existing package directory will always be purged if
already present! This could be used to create package directly in server folder
if available.

Package contains server side files directly,
client side code zipped in `private` subfolder.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterable, Optional, Pattern, Tuple, Union

import package

FileMapping = Tuple[Union[str, io.BytesIO], str]
ADDON_NAME: str = package.name
ADDON_VERSION: str = package.version
ADDON_CLIENT_DIR: Union[str, None] = getattr(package, "client_dir", None)

CURRENT_ROOT: str = os.path.dirname(os.path.abspath(__file__))
SERVER_ROOT: str = os.path.join(CURRENT_ROOT, "server")
FRONTEND_ROOT: str = os.path.join(CURRENT_ROOT, "frontend")
FRONTEND_DIST_ROOT: str = os.path.join(FRONTEND_ROOT, "dist")
DST_DIST_DIR: str = os.path.join("frontend", "dist")
PRIVATE_ROOT: str = os.path.join(CURRENT_ROOT, "private")
PUBLIC_ROOT: str = os.path.join(CURRENT_ROOT, "public")
CLIENT_ROOT: str = os.path.join(CURRENT_ROOT, "client")

VERSION_PY_CONTENT = (
    f'''"""Package declaring AYON addon '{ADDON_NAME}' version."""
__version__ = "{ADDON_VERSION}"
''')

# Patterns of directories to be skipped for server part of addon
IGNORE_DIR_PATTERNS: list[Pattern] = [
    re.compile(pattern)
    for pattern in (
        # Skip directories starting with '.'
        r"^\.",
        # Skip any pycache folders
        "^__pycache__$"
    )
]

# Patterns of files to be skipped for server part of addon
IGNORE_FILE_PATTERNS: list[Pattern] = [
    re.compile(pattern)
    for pattern in (
        # Skip files starting with '.'
        # NOTE this could be an issue in some cases
        r"^\.",
        # Skip '.pyc' files
        r"\.pyc$"
    )
]


class ZipFileLongPaths(zipfile.ZipFile):
    r"""Allows longer paths in zip files.

    Regular DOS paths are limited to MAX_PATH (260) characters, including
    the string's terminating NUL character.
    That limit can be exceeded by using an extended-length path that
    starts with the '\\?\' prefix.
    """
    _is_windows = platform.system().lower() == "windows"

    def _extract_member(
            self, member: zipfile.ZipInfo,
            tpath: str, pwd: bytes) -> str:
        if self._is_windows:
            tpath = os.path.abspath(tpath)
            if tpath.startswith("\\\\"):
                tpath = "\\\\?\\UNC\\" + tpath[2:]
            else:
                tpath = "\\\\?\\" + tpath

        # mypy cannot find _extract_members in super class for some reason
        return super()._extract_member(member, tpath, pwd)  # type: ignore[misc]


def _get_yarn_executable() -> Union[str, None]:
    cmd = "which"
    if platform.system().lower() == "windows":
        cmd = "where"

    for line in subprocess.check_output(
        [cmd, "yarn"], encoding="utf-8"
    ).splitlines():
        if not line or not os.path.exists(line):
            continue
        try:
            subprocess.call([line, "--version"])
        except OSError:
            continue
        else:
            return line
    return None


def safe_copy_file(src_path: str, dst_path: str) -> None:
    """Copy file and make sure destination directory exists.

    Ignore if destination already contains directories from source.

    Args:
        src_path (str): File path that will be copied.
        dst_path (str): Path to destination file.
    """
    if src_path == dst_path:
        return

    dst_dir: str = os.path.dirname(dst_path)
    os.makedirs(dst_dir, exist_ok=True)

    shutil.copy2(src_path, dst_path)


def _value_match_regexes(value: str, regexes: Iterable[Pattern]) -> bool:
    return any(
        regex.search(value)
        for regex in regexes
    )


def find_files_in_subdir(
    src_path: str,
    ignore_file_patterns: Optional[list[Pattern]] = None,
    ignore_dir_patterns: Optional[list[Pattern]] = None
) -> list[FileMapping]:
    """Find all files to copy in subdirectories of the given path.

    All files that match any of the patterns in 'ignore_file_patterns' will
        be skipped, and any directories that match any of the patterns in
        'ignore_dir_patterns' will be skipped with all subfiles.

    Args:
        src_path (str): Path to directory to search in.
        ignore_file_patterns (Optional[list[Pattern]]): List of regexes
            to match files to ignore.
        ignore_dir_patterns (Optional[list[Pattern]]): List of regexes
            to match directories to ignore.

    Returns:
        list[FileMapping]: List of tuples with path to file and parent
            directories relative to 'src_path'.
    """
    if ignore_file_patterns is None:
        ignore_file_patterns = IGNORE_FILE_PATTERNS

    if ignore_dir_patterns is None:
        ignore_dir_patterns = IGNORE_DIR_PATTERNS
    output: list[FileMapping] = []
    if not os.path.exists(src_path):
        return output

    hierarchy_queue: collections.deque = collections.deque()
    hierarchy_queue.append((src_path, []))
    while hierarchy_queue:
        item: FileMapping = hierarchy_queue.popleft()
        dirpath, parents = item
        for name in os.listdir(dirpath):
            path: str = os.path.join(dirpath, name)
            if os.path.isfile(path):
                if not _value_match_regexes(name, ignore_file_patterns):
                    items: list[str] = list(parents)
                    items.append(name)
                    output.append((path, os.path.sep.join(items)))
                continue

            if not _value_match_regexes(name, ignore_dir_patterns):
                items = list(parents)
                items.append(name)
                hierarchy_queue.append((path, items))

    return output


def update_client_version(addon_client_dir: str, log: logging.Logger) -> None:
    """Update version in client code if version.py is present."""
    if not addon_client_dir:
        return

    version_path: str = os.path.join(
        CLIENT_ROOT, addon_client_dir, "version.py"
    )
    if not os.path.exists(version_path):
        log.debug("Creating version.py in client directory")

    log.info("Updating client version")
    Path(version_path).write_text(VERSION_PY_CONTENT, encoding="utf-8")


def update_frontend_version(log: logging.Logger) -> None:
    """Write the package version into the frontend.

    Its endpoints call /api/addons/{name}/{version}/... with the version
    in frontend/src/addonVersion.ts.
    """
    log.info("Updating frontend version")
    Path(FRONTEND_ROOT, "src", "addonVersion.ts").write_text(
        f'export default "{ADDON_VERSION}";\n', encoding="utf-8"
    )

    package_json = Path(FRONTEND_ROOT, "package.json")
    data = json.loads(package_json.read_text(encoding="utf-8"))
    data["version"] = ADDON_VERSION
    package_json.write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )


def build_frontend() -> None:
    """Build frontend code using yarn.

    Raises:
        RuntimeError: If yarn executable was not found or frontend
            build failed.

    """
    yarn_executable = _get_yarn_executable()
    if yarn_executable is None:
        msg = "Yarn executable was not found."
        raise RuntimeError(msg)

    subprocess.run([yarn_executable, "install"], cwd=FRONTEND_ROOT, check=True)
    subprocess.run([yarn_executable, "build"], cwd=FRONTEND_ROOT, check=True)
    if not os.path.exists(FRONTEND_DIST_ROOT):
        msg = "Frontend build failed. Did not find 'dist' folder."
        raise RuntimeError(msg)


def get_client_files_mapping(addon_client_dir: str) -> set[FileMapping]:
    """Mapping of source client code files to destination paths.

    Example output:
        [
            (
                "C:/addons/MyAddon/version.py",
                "my_addon/version.py"
            ),
            (
                "C:/addons/MyAddon/client/my_addon/__init__.py",
                "my_addon/__init__.py"
            )
        ]

    Returns:
        list[FileMapping]: List of path mappings to copy. The destination
            path is relative to expected output directory.

    """
    # Add client code content to zip
    if addon_client_dir:
        client_code_dir: str = os.path.join(CLIENT_ROOT, addon_client_dir)
    else:
        client_code_dir = CLIENT_ROOT
    mapping = []
    for path, sub_path in find_files_in_subdir(client_code_dir):
        if addon_client_dir:
            client_dir = os.path.join(addon_client_dir, sub_path)
        else:
            client_dir = sub_path
        mapping.append((path, client_dir))

    license_path = os.path.join(CURRENT_ROOT, "LICENSE")
    if os.path.exists(license_path):
        mapping.append((license_path, f"{addon_client_dir}/LICENSE"))
    return set(mapping)


def get_client_zip_content(
        addon_client_dir: str, log: logging.Logger) -> io.BytesIO:
    """Prepare client code zip.

    Args:
        addon_client_dir (str): Client directory path.
        log (logging.Logger): Logger object.

    Returns:
        io.BytesIO: BytesIO object with zipped client code.

    """
    log.info("Preparing client code zip")
    files_mapping: set[FileMapping] = get_client_files_mapping(
        addon_client_dir)
    stream = io.BytesIO()
    with ZipFileLongPaths(stream, "w", zipfile.ZIP_DEFLATED) as zipf:
        for src_path, subpath in files_mapping:
            if isinstance(src_path, io.BytesIO):
                zipf.writestr(subpath, src_path.getvalue())
            else:
                zipf.write(src_path, subpath)
    stream.seek(0)
    return stream


def get_base_files_mapping() -> list[FileMapping]:
    """Get mapping of server side files to copy.

    Returns:
        list: FileMapping with source file and destination
            subpath.

    """
    filepaths_to_copy: list[FileMapping] = [
        (
            os.path.join(CURRENT_ROOT, "package.py"),
            "package.py"
        )
    ]
    # Add license file to package if exists
    license_path = os.path.join(CURRENT_ROOT, "LICENSE")
    if os.path.exists(license_path):
        filepaths_to_copy.append((license_path, "LICENSE"))

    # Go through server, private and public directories and find all files
    for dirpath in (SERVER_ROOT, PRIVATE_ROOT, PUBLIC_ROOT):
        if not os.path.exists(dirpath):
            continue

        dirname = os.path.basename(dirpath)
        for src_file, subpath in find_files_in_subdir(dirpath):
            dst_subpath = os.path.join(dirname, subpath)
            filepaths_to_copy.append((src_file, dst_subpath))

    if os.path.exists(FRONTEND_DIST_ROOT):
        for src_file, subpath in find_files_in_subdir(FRONTEND_DIST_ROOT):
            dst_subpath = os.path.join(DST_DIST_DIR, subpath)
            filepaths_to_copy.append((src_file, dst_subpath))

    pyproject_toml = os.path.join(CLIENT_ROOT, "pyproject.toml")
    if os.path.exists(pyproject_toml):
        filepaths_to_copy.append(
            (pyproject_toml, "private/pyproject.toml")
        )

    return filepaths_to_copy


def copy_client_code(
        output_dir: str, addon_client_dir: str, log: logging.Logger) -> None:
    """Copies server side folders to 'addon_package_dir'.

    Args:
        output_dir (str): Output directory path.
        addon_client_dir (str): Client directory path.
        log (logging.Logger): Logger object.

    """
    log.info(
        "Copying client for %s-%s", ADDON_NAME, ADDON_VERSION)

    full_output_path = os.path.join(
        output_dir, f"{ADDON_NAME}_{ADDON_VERSION}"
    )
    if os.path.exists(full_output_path):
        shutil.rmtree(full_output_path)
    os.makedirs(full_output_path, exist_ok=True)

    for src_path, dst_subpath in get_client_files_mapping(addon_client_dir):
        dst_path = os.path.join(full_output_path, dst_subpath)
        if isinstance(src_path, io.BytesIO):
            Path(dst_path).write_bytes(src_path.getvalue())
        else:
            safe_copy_file(src_path, dst_path)

    log.info("Client copy finished")


def copy_addon_package(
    output_dir: str,
    files_mapping: list[FileMapping],
    log: logging.Logger
) -> None:
    """Copy client code to output directory.

    Args:
        output_dir (str): Directory path to output client code.
        files_mapping (List[FileMapping]): List of tuples with source file
            and destination subpath.
        log (logging.Logger): Logger object.

    """
    log.info("Copying package for %s-%s", ADDON_NAME, ADDON_VERSION)

    # Add addon name and version to output directory
    addon_output_dir: str = os.path.join(
        output_dir, ADDON_NAME, ADDON_VERSION
    )
    if os.path.isdir(addon_output_dir):
        log.info("Purging %s", addon_output_dir)
        shutil.rmtree(addon_output_dir)

    os.makedirs(addon_output_dir, exist_ok=True)

    # Copy server content
    for src_file, dst_subpath in files_mapping:
        dst_path: str = os.path.join(addon_output_dir, dst_subpath)
        dst_dir: str = os.path.dirname(dst_path)
        os.makedirs(dst_dir, exist_ok=True)
        if isinstance(src_file, io.BytesIO):
            Path(dst_path).write_bytes(src_file.getvalue())
        else:
            safe_copy_file(src_file, dst_path)

    log.info("Package copy finished")


def create_addon_package(
    output_dir: str,
    files_mapping: list[FileMapping],
    log: logging.Logger
) -> None:
    """Create zip package for addon.

    Args:
        output_dir (str): Directory path to output package.
        files_mapping (list[FileMapping]): List of tuples with source file
            and destination subpath.
        log (logging.Logger): Logger object

    """
    log.info("Creating package for %s-%s", ADDON_NAME, ADDON_VERSION)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(
        output_dir, f"{ADDON_NAME}-{ADDON_VERSION}.zip"
    )

    with ZipFileLongPaths(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Copy server content
        for src_file, dst_subpath in files_mapping:
            if isinstance(src_file, io.BytesIO):
                zipf.writestr(dst_subpath, src_file.getvalue())
            else:
                zipf.write(src_file, dst_subpath)

    log.info("Package created")


def main(
    output_dir: Optional[str] = None,
    addon_client_dir: Optional[str] = None,
    *,
    skip_zip: Optional[bool] = False,
    only_client: Optional[bool] = False
) -> None:
    """Main function to create package.

    Raises:
        RuntimeError: If client code is not found.

    """
    log: logging.Logger = logging.getLogger("create_package")
    log.info("Package creation started")

    if not output_dir:
        output_dir = os.path.join(CURRENT_ROOT, "package")

    # has_client_code = bool(addon_client_dir)
    if addon_client_dir:
        client_dir: str = os.path.join(CLIENT_ROOT, addon_client_dir)

        if not os.path.exists(client_dir):
            msg = (
                f"Client directory was not found '{client_dir}'."
                " Please check 'client_dir' in 'package.py'."
            )
            raise RuntimeError(msg)
        update_client_version(addon_client_dir, log)

    if only_client:
        if not addon_client_dir:
            msg = "Client code is not available. Skipping"
            raise RuntimeError(msg)

        copy_client_code(output_dir, addon_client_dir, log)
        return

    log.info("Preparing package for %s, %s", ADDON_NAME, ADDON_VERSION)

    if os.path.exists(FRONTEND_ROOT):
        update_frontend_version(log)
        build_frontend()

    files_mapping: list[FileMapping] = []
    files_mapping.extend(get_base_files_mapping())

    if addon_client_dir:
        files_mapping.append(
            (get_client_zip_content(
                addon_client_dir, log), "private/client.zip")
        )

    # Skip server zipping
    if skip_zip:
        copy_addon_package(output_dir, files_mapping, log)
    else:
        create_addon_package(output_dir, files_mapping, log)

    log.info("Package creation finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-zip",
        dest="skip_zip",
        action="store_true",
        help=(
            "Skip zipping server package and create only"
            " server folder structure."
        )
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_dir",
        default=None,
        help=(
            "Directory path where package will be created"
            " (Will be purged if already exists!)"
        )
    )
    parser.add_argument(
        "--only-client",
        dest="only_client",
        action="store_true",
        help=(
            "Extract only client code. This is useful for development."
            " Requires '-o', '--output' argument to be filled."
        )
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Debug log messages."
    )

    args = parser.parse_args(sys.argv[1:])
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(level=level)
    main(
        args.output_dir,
        ADDON_CLIENT_DIR,
        skip_zip=args.skip_zip,
        only_client=args.only_client
    )
