import asyncio
import logging
import os
import shutil
import time
from pathlib import Path

import utils
import database


logger = logging.getLogger(__name__)


class FolderIngestService:
    """
    Polls a configured inbound folder and, when files are stable, performs an action:
    - "pdf_professor": move PDFs to utils.PDF_DIRECTORY and schedule background processing
    - "local_storage": copy files to backend/local_storage for UI-driven selection

    Config (backend/config.json -> inbound):
      enabled (bool), folder (str), poll_seconds (int), stable_seconds (int),
      action (str: pdf_professor|local_storage),
      server_type (str), server_name (str|None), model_name (str|None), prompt (str)
    """

    def __init__(self):
        self.is_running = False
        self._size_seen: dict[str, tuple[int, float]] = {}

    async def run(self, process_func):
        cfg = utils.config.get("inbound", {}) or {}
        if not cfg.get("enabled"):
            logger.info("Inbound folder ingest disabled.")
            return

        folder = cfg.get("folder") or "backend/inbox"
        poll_s = int(cfg.get("poll_seconds", 5))
        stable_s = int(cfg.get("stable_seconds", 2))
        action = (cfg.get("action") or "pdf_professor").strip().lower()

        server_type = cfg.get("server_type") or "ollama"
        model_name = cfg.get("model_name")
        server_name = cfg.get("server_name")  # may be None -> auto-pick
        prompt = cfg.get("prompt") or "Summarize key points."

        os.makedirs(folder, exist_ok=True)
        # Ensure destinations exist
        os.makedirs(utils.PDF_DIRECTORY, exist_ok=True)
        local_storage_dir = "backend/local_storage"
        os.makedirs(local_storage_dir, exist_ok=True)

        self.is_running = True
        logger.info(f"Inbound ingest watching: {os.path.abspath(folder)} (action={action})")

        while self.is_running:
            try:
                for p in Path(folder).iterdir():
                    if not p.is_file() or p.name.startswith("."):
                        continue
                    # Only auto-process PDFs for pdf_professor mode
                    if action == "pdf_professor" and p.suffix.lower() != ".pdf":
                        continue

                    size = p.stat().st_size
                    now = time.time()
                    key = str(p)
                    prev = self._size_seen.get(key)
                    if prev and prev[0] == size and (now - prev[1]) >= stable_s:
                        try:
                            if action == "pdf_professor":
                                await self._pickup_pdf_professor(
                                    p, process_func, prompt, model_name, server_name, server_type
                                )
                            elif action == "local_storage":
                                self._pickup_local_storage(p, local_storage_dir)
                            else:
                                logger.warning(f"Unknown inbound.action '{action}', skipping {p.name}")
                        finally:
                            # clear seen state regardless of outcome
                            self._size_seen.pop(key, None)
                    else:
                        self._size_seen[key] = (size, now)
            except Exception:
                logger.exception("Error in folder ingest loop")

            await asyncio.sleep(poll_s)

    async def _pickup_pdf_professor(self, path: Path, process_func, prompt, model_name, server_name, server_type):
        # Resolve defaults when not configured
        if not server_name:
            if server_type == "ollama":
                servers = await database.get_ollama_servers()
            else:
                servers = await database.get_external_ai_servers()
            if servers:
                server_name = servers[0]["name"]

        if not model_name and server_type == "ollama":
            model_name = utils.config.get("ollama_model")

        # Validate minimal config
        if not (prompt and model_name and server_name and server_type):
            logger.warning(f"Skipping {path.name}: missing prompt/model/server config")
            return

        # Ensure unique destination filename in pdf directory
        dest_dir = utils.PDF_DIRECTORY
        base, ext = os.path.splitext(path.name)
        dest_name = path.name
        i = 0
        while os.path.exists(os.path.join(dest_dir, dest_name)):
            i += 1
            dest_name = f"{base}-{int(time.time())}-{i}{ext}"
        dest_path = os.path.join(dest_dir, dest_name)

        # Move (supports cross-device via shutil.move)
        shutil.move(str(path), dest_path)
        logger.info(f"Picked up {path.name} -> {dest_path}; scheduling processing")

        # Create task and schedule processing
        await database.add_or_update_task(dest_name, prompt, model_name, server_name)
        asyncio.create_task(process_func(dest_name, prompt, model_name, server_name, server_type))

    def _pickup_local_storage(self, path: Path, local_storage_dir: str):
        base, ext = os.path.splitext(path.name)
        dest_name = path.name
        i = 0
        while os.path.exists(os.path.join(local_storage_dir, dest_name)):
            i += 1
            dest_name = f"{base}-{int(time.time())}-{i}{ext}"
        dest_path = os.path.join(local_storage_dir, dest_name)
        shutil.move(str(path), dest_path)
        logger.info(f"Moved {path.name} -> {dest_path} for Local Storage UI")


ingest_service = FolderIngestService()


async def run_ingest_loop(process_func):
    await ingest_service.run(process_func)


def stop():
    ingest_service.stop()

