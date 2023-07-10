from __future__ import annotations

import shutil
from pathlib import Path

from aiaccel.common import (
    dict_error,
    dict_hp,
    dict_lock,
    dict_log,
    dict_output,
    dict_runner,
    dict_storage,
    dict_tensorboard,
)
from aiaccel.util import Suffix, make_directories

# from typing import Any



class Workspace:
    """Provides interface to workspace.

    Args:
        base_path (str): Path to the workspace.

    Attributes:
        path (Path): Path to the workspace.
        alive (Path): Path to "alive", i.e. `path`/alive.
        error (Path): Path to "error", i.e. 'path`/error.
        hp (Path): Path to "hp", i.e. `path`/hp.
        hp_ready (Path): Path to "ready", i.e. `path`/hp/ready.
        hp_running (Path): Path to "running", i.e. `path`/hp/running.
        hp_finished (Path): Path to "finished", i.e. `path`/hp/finished.
        jobstate (Path): Path to "jobstate", i.e. `path`/jobstate.
        lock (Path): Path to "lock", i.e. `path`/lock.
        log (Path): Path to "log", i.e. `path`/log.
        output (Path): Path to "abci_output", i.e. `path`/abci_output.
        pid (Path): Path to "pid", i.e. `path`/pid.
        runner (Path): Path to "runner", i.e. `path`/runner.
        storage (Path): Path to "storage", i.e. `path`/storage.
        timestamp (Path): Path to "timestamp", i.e. `path`/timestamp.
        consists (list[Path]): A list of pathes under the workspace.
        results (Path): Path to the results which is prepared in the execution
            directory, i.e. "./results".

    """

    def __init__(self, base_path: str):
        self.path = Path(base_path).resolve()

        self.error = self.path / dict_error
        self.hp = self.path / dict_hp
        self.lock = self.path / dict_lock
        self.log = self.path / dict_log
        self.output = self.path / dict_output
        self.runner = self.path / dict_runner
        self.storage = self.path / dict_storage
        self.tensorboard = self.path / dict_tensorboard

        self.consists = [
            self.error,
            self.hp,
            self.lock,
            self.log,
            self.output,
            self.runner,
            self.storage,
            self.tensorboard
        ]
        self.results = Path("./results")
        self.retults_csv_file = self.path / "results.csv"
        self.final_result_file = self.path / "final_result.result"
        self.storage_file_path = self.storage / "storage.db"

    def create(self) -> bool:
        """Create a work directory.

        Returns:
            None

        Raises:
            NotADirectoryError: It raises if a workspace argument (self.path)
                is not a directory.
        """
        if self.exists():
            return False

        make_directories(ds=self.consists, dict_lock=(self.lock))
        return True

    def exists(self) -> bool:
        """Returns whether workspace exists or not.

        Returns:
            bool: True if the workspace exists.
        """
        return self.path.exists()

    def clean(self) -> None:
        """Delete a workspace.

        It is assumed to be the first one to be executed.
        """
        if not self.path.exists():
            return
        shutil.rmtree(self.path)
        return

    def check_consists(self) -> bool:
        """Check required directories exist or not.

        Returns:
            bool: All required directories exist or not.
        """
        for d in self.consists:
            if d.is_dir():
                continue
            else:
                return False
        return True

    def move_completed_data(self) -> Path | None:
        """Move workspace to under of results directory when finished.

        Raises:
            FileExistsError: Occurs if destination directory already exists
                when the method is called.

        Returns:
            Path | None: Path of destination.
        """

        dst = self.results / Suffix.date()
        if not self.results.exists():
            self.results.mkdir()

        if dst.exists():
            print(f"Destination directory already exists: {dst}")
            return None

        ignptn = shutil.ignore_patterns("*-journal")

        shutil.copytree(self.path, dst, ignore=ignptn)
        return dst

    def get_runner_file(self, trial_id: int) -> Path:
        return self.runner / f"run_{trial_id}.sh"

    def get_error_output_file(self, trial_id: int) -> Path:
        return self.error / f"{trial_id}.txt"
