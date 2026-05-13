# respaldos.py

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from databases.singleton import Database
from routers.authentication import User, current_user
from utilities.handleDocument.document import BusyPaths


router_respaldos = APIRouter(prefix="/respaldos")

ADMIN_USER_TYPES = {1, 2}
BUSY_CHUNK_SIZE = 1024 * 1024
AUTOMATIC_BACKUP_PREFIX = "Respaldo automático previo a actualización manual"
BUSY_MEDIA_TYPE = "application/octet-stream"


def _require_admin(user: User) -> None:
    if user.typeUser not in ADMIN_USER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage backups",
        )


def _close_database_instances() -> None:
    for instance in list(Database._instances.values()):
        instance.close_connection()


def _busy_download_filename(path: Path) -> str:
    if path.name == ".busy":
        return "busy.busy"
    return path.name if path.name.lower().endswith(".busy") else "busy.busy"


def _is_busy_upload_filename(filename: str) -> bool:
    normalized = filename.lower()
    return normalized == "busy" or normalized.endswith(".busy")


def _is_automatic_backup(path: Path) -> bool:
    return (
        path.is_file()
        and path.name.startswith(f"{AUTOMATIC_BACKUP_PREFIX} - ")
        and path.name.lower().endswith(".busy")
    )


def _automatic_backup_path(paths: BusyPaths) -> Path:
    date_label = datetime.now().strftime("%d-%m-%y")
    base_name = f"{AUTOMATIC_BACKUP_PREFIX} - {date_label}.busy"
    backup_path = paths.archive_path.with_name(base_name)
    counter = 1

    while backup_path.exists():
        backup_path = paths.archive_path.with_name(
            f"{AUTOMATIC_BACKUP_PREFIX} - {date_label} - {counter:02d}.busy"
        )
        counter += 1

    return backup_path


def _create_automatic_backup_locked(paths: BusyPaths) -> Path | None:
    if not paths.archive_path.exists():
        return None

    backup_path = _automatic_backup_path(paths)
    shutil.copy2(paths.archive_path, backup_path)
    return backup_path


def _automatic_backups(paths: BusyPaths) -> list[dict[str, object]]:
    backups: list[dict[str, object]] = []
    for path in paths.archive_path.parent.iterdir():
        if not _is_automatic_backup(path):
            continue
        stat = path.stat()
        backups.append(
            {
                "filename": path.name,
                "size": stat.st_size,
                "modifiedAt": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    return sorted(backups, key=lambda item: str(item["modifiedAt"]), reverse=True)


def _resolve_automatic_backup(paths: BusyPaths, filename: str) -> Path:
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=404, detail="Backup not found")

    backup_path = paths.archive_path.parent / safe_name
    if not _is_automatic_backup(backup_path):
        raise HTTPException(status_code=404, detail="Backup not found")

    return backup_path


def _validate_busy_archive(path: Path) -> None:
    try:
        with zipfile.ZipFile(path, mode="r") as archive:
            broken_file = archive.testzip()
            if broken_file is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid .busy archive: corrupted file '{broken_file}'",
                )

            names = set(archive.namelist())
            if "meta/manifest.json" not in names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid .busy archive: missing meta/manifest.json",
                )
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid .busy archive",
        ) from exc


async def _save_upload_to_temp(file: UploadFile, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=".busy-upload-",
        suffix=".tmp",
        dir=str(destination_dir),
        delete=False,
    )
    temp_path = Path(handle.name)

    try:
        with handle:
            while chunk := await file.read(BUSY_CHUNK_SIZE):
                handle.write(chunk)
        return temp_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


@router_respaldos.get("/ison")
async def ison():
    return {
        "message": "Yes, I'm on from '/respaldos'",
    }


@router_respaldos.get("/download")
async def download_busy_archive(user: User = Depends(current_user)):
    _require_admin(user)

    paths = BusyPaths()
    archive_path = paths.flush_archive()
    if not archive_path.exists():
        raise HTTPException(status_code=404, detail=".busy archive not found")

    return FileResponse(
        archive_path,
        media_type=BUSY_MEDIA_TYPE,
        filename=_busy_download_filename(archive_path),
    )


@router_respaldos.get("/automatic-backups")
async def list_automatic_backups(user: User = Depends(current_user)):
    _require_admin(user)
    paths = BusyPaths()
    return {
        "backups": _automatic_backups(paths),
    }


@router_respaldos.get("/automatic-backups/{filename}")
async def download_automatic_backup(
    filename: str,
    user: User = Depends(current_user),
):
    _require_admin(user)
    paths = BusyPaths()
    backup_path = _resolve_automatic_backup(paths, filename)
    return FileResponse(
        backup_path,
        media_type=BUSY_MEDIA_TYPE,
        filename=backup_path.name,
    )


@router_respaldos.post("/upload")
async def upload_busy_archive(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
):
    _require_admin(user)

    filename = Path(file.filename or "").name
    if not _is_busy_upload_filename(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .busy files are accepted",
        )

    paths = BusyPaths()
    temp_path = await _save_upload_to_temp(file, paths.archive_path.parent)

    backup_path: Path | None = None
    try:
        _validate_busy_archive(temp_path)
        _close_database_instances()
        with paths._archive_lock():
            backup_path = _create_automatic_backup_locked(paths)

            temp_path.replace(paths.archive_path)
            paths._bootstrapped = False
            paths._reset_runtime_locked()
            paths._extract_archive_locked()
            paths._upgrade_if_needed_locked()
            paths._write_runtime_state_locked(
                {
                    "runtime_root": str(paths._runtime_root),
                    "pids": [os.getpid()],
                }
            )
            paths._bootstrapped = True

        return {
            "message": ".busy archive uploaded successfully",
            "filename": _busy_download_filename(paths.archive_path),
            "backup": backup_path.name if backup_path is not None else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        if backup_path is not None:
            paths.restore_archive_backup(backup_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not replace .busy archive",
        ) from exc
    finally:
        temp_path.unlink(missing_ok=True)
        await file.close()
