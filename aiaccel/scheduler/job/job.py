from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from omegaconf.dictconfig import DictConfig
from transitions import Machine
from transitions.extensions.states import Tags, add_state_features

from aiaccel.common import datetime_format
from aiaccel.storage import Storage
from aiaccel.util import Buffer
from aiaccel.workspace import Workspace

if TYPE_CHECKING:  # pragma: no cover
    from aiaccel.scheduler import AbstractModel, AbstractScheduler


JOB_STATES = [
    {"name": "init"},
    {"name": "ready"},
    {"name": "running"},
    {"name": "finished"},
    {"name": "success"},
    {"name": "failure"},
    {"name": "timeout"},
]


JOB_TRANSITIONS: list[dict[str, str | list[str]]] = [
    {
        "trigger": "next_state",
        "source": "init",
        "dest": "ready",
        "before": "before_ready",
        "after": "after_ready",
    },
    {
        "trigger": "next_state",
        "source": "ready",
        "dest": "running",
        "before": "before_running",
        "after": "after_running",
    },
    {
        "trigger": "next_state",
        "source": "running",
        "dest": "finished",
        "conditions": "conditions_job_finished",
        "before": "before_finished",
        "after": "after_finished",
    },
    {
        "trigger": "next_state",
        "source": "finished",
        "dest": "success",
    },
    {
        "trigger": "expire",
        "source": ["init", "ready", "running", "finished"],
        "dest": "failure",
    },
    {
        "trigger": "timeout",
        "source": ["init", "ready", "running", "finished"],
        "dest": "timeout",
        "before": "before_timeout",
        "after": "after_timeout",
    },
]


@add_state_features(Tags)
class CustomMachine(Machine):
    pass


class Job:
    """A job thread to manage running jobs on local computer or ABCI."""

    def __init__(self, config: DictConfig, scheduler: AbstractScheduler, model: AbstractModel, trial_id: int) -> None:
        super(Job, self).__init__()
        # === Load config file===
        self.config = config
        # === Get config parameter values ===
        self.count_retry = 0
        self.logger = logging.getLogger("root.scheduler.job")
        self.workspace = Workspace(self.config.generic.workspace)
        self.storage = Storage(self.workspace.storage_file_path)
        self.trial_id = trial_id
        self.content = self.storage.get_hp_dict(self.trial_id)
        self.scheduler = scheduler
        self.model = model
        if self.model is None:
            raise ValueError(
                "model is None. "
                "Be sure to specify the model to use in the Job class. "
                "For example, PylocalScheduler doesn't use model. "
                "Therefore, Job class cannot be used."
            )
        self.machine = CustomMachine(
            model=self.model,
            states=JOB_STATES,
            transitions=JOB_TRANSITIONS,
            initial=JOB_STATES[0]["name"],
            auto_transitions=False,
            ordered_transitions=False,
        )
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.trial_id = trial_id
        self.proc: Any = None
        self.th_oh: Any = None
        self.buff = Buffer(["state.name"])
        self.buff.d["state.name"].set_max_len(2)

    def get_state_name(self) -> str | Enum:
        """Get a current state name.

        Returns:
            str | Enum: A current state name.
        """
        state = self.machine.get_state(self.model.state)
        return state.name

    def write_start_time_to_storage(self) -> None:
        """Set a start time."""
        self.start_time = datetime.now()
        _start_time = self.start_time.strftime(datetime_format)
        self.storage.timestamp.set_any_trial_start_time(trial_id=self.trial_id, start_time=_start_time)

    def write_end_time_to_storage(self) -> None:
        """Set an end time."""
        self.end_time = datetime.now()
        _end_time = self.end_time.strftime(datetime_format)
        self.storage.timestamp.set_any_trial_end_time(trial_id=self.trial_id, end_time=_end_time)

    def write_state_to_storage(self, state: str) -> None:
        """Write a current state to the database."""
        self.storage.state.set_any_trial_state(trial_id=self.trial_id, state=state)

    def write_job_success_or_failed_to_storage(self) -> None:
        """Write a job success or failed to the database."""
        returncode = self.storage.returncode.get_any_trial_returncode(trial_id=self.trial_id)
        end_state = "success"
        if returncode != 0:
            end_state = "failure"
        self.storage.jobstate.set_any_trial_jobstate(trial_id=self.trial_id, state=end_state)

    def get_job_elapsed_time_in_seconds(self) -> float:
        """Get a job elapsed time in seconds.

        Returns:
            float: A job elapsed time in seconds.
        """
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def is_timeout(self) -> bool:
        """Check if a job is timeout.

        Returns:
            bool: True if a job is timeout.
        """
        if self.start_time is None:
            return False
        if self.end_time is None:
            return False
        elapsed_time = self.get_job_elapsed_time_in_seconds()
        if elapsed_time > self.config.job_setting.job_timeout_seconds:
            return True
        return False

    def main(self) -> None:
        """Thread.run method.

        Returns:
            None
        """

        state = self.machine.get_state(self.model.state)
        try:
            if state.name.lower() == "init":
                self.model.next_state(self)
            elif state.name.lower() == "ready":
                self.model.next_state(self)
            elif state.name.lower() == "running":
                self.model.next_state(self)
            elif state.name.lower() == "finished":
                self.model.next_state(self)
        except BaseException as e:
            self.logger.error(f"An error occurred in the job thread. {e}")
            self.model.expire(self)
            return
        if self.is_timeout():
            self.model.timeout(self)
        return
