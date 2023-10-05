from __future__ import annotations

from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from multiprocessing.pool import Pool, ThreadPool
from pathlib import Path
from typing import Any

from omegaconf.dictconfig import DictConfig

from aiaccel.cli.set_result import write_results_to_database
from aiaccel.common import datetime_format
from aiaccel.config import load_config
from aiaccel.optimizer import AbstractOptimizer
from aiaccel.run import set_logging_file_for_trial_id
from aiaccel.scheduler.abstract_scheduler import AbstractScheduler

# These are for avoiding mypy-errors from initializer().
# `global` does not work well.
# https://github.com/python/mypy/issues/5732
user_func: Any
workspace: Path


class PylocalScheduler(AbstractScheduler):
    """A scheduler class running on a local computer."""

    def __init__(self, config: DictConfig, optimizer: AbstractOptimizer) -> None:
        super().__init__(config, optimizer)
        self.processes: list[Any] = []

        Pool_ = Pool if self.num_workers > 1 else ThreadPool  # noqa: N806
        self.pool = Pool_(self.num_workers, initializer=initializer, initargs=(self.config.config_path,))

    def run_in_main_loop(self) -> bool:
        """A main loop process. This process is repeated every main loop.

        Returns:
            bool: The process succeeds or not. The main loop exits if failed.
        """

        num_ready, num_running, num_finished = self.storage.get_num_running_ready_finished()
        self.search_hyperparameters(num_ready, num_running, num_finished)

        if num_finished >= self.config.optimize.trial_number:
            return False

        trial_ids = self.storage.state.get_ready()
        if trial_ids is None or len(trial_ids) == 0:
            return True

        args = []
        for trial_id in trial_ids:
            self.storage.state.set_any_trial_state(trial_id=trial_id, state="running")
            args.append([trial_id, self.get_any_trial_xs(trial_id)])
            self.serialize(trial_id)

        for trial_id, _, ys, err, start_time, end_time in self.pool.imap_unordered(execute, args):
            write_results_to_database(
                storage_file_path=self.workspace.storage_file_path,
                trial_id=trial_id,
                objective=ys,
                start_time=start_time,
                end_time=end_time,
                error=err,
                returncode=None,
            )
            self.storage.state.set_any_trial_state(trial_id=trial_id, state="finished")
        return True

    def post_process(self) -> None:
        for process in self.processes:
            process.wait()

        super().post_process()

    def get_any_trial_xs(self, trial_id: int) -> dict[str, Any] | None:
        """Gets a parameter list of specific trial ID from Storage object.

        Args:
            trial_id (int): Trial ID.

        Returns:
            dict | None: A dictionary of parameters. None if the parameter
                specified by the given trial ID is not registered.
        """
        params = self.storage.hp.get_any_trial_params(trial_id=trial_id)
        if params is None:
            return {}

        xs = {}
        for param in params:
            xs[param.param_name] = param.param_value

        return xs

    def report(self, trial_id: int, ys: list[Any], err: str, start_time: str, end_time: str) -> None:
        """Saves results in the Storage object.

        Args:
            trial_id (int): Trial ID.
            xs (dict): A dictionary of parameters.
            y (Any): Objective value.
            err (str): Error string.
            start_time (str): Execution start time.
            end_time (str): Execution end time.
        """

        self.storage.result.set_any_trial_objective(trial_id, ys)
        self.storage.timestamp.set_any_trial_start_time(trial_id, start_time)
        self.storage.timestamp.set_any_trial_end_time(trial_id, end_time)
        if err != "":
            self.storage.error.set_any_trial_error(trial_id, err)

    def create_model(self) -> None:
        """Creates model object of state machine.
        Returns:
            None: Because it does not use the state transition model.
        """
        return None

    def __getstate__(self) -> dict[str, Any]:
        obj = super().__getstate__()
        del obj["pool"]
        del obj["processes"]
        return obj


def initializer(config_path: str | Path) -> None:
    """Initializer for multiprocessing.Pool.

    Args:
        config_path (str | Path): Path to the configuration file.
    Returns:
        None
    """
    global user_func, workspace

    config = load_config(config_path)

    # Load the specified module from the specified python program.
    spec = spec_from_file_location("user_module", config.generic.python_file)
    if spec is None:
        raise ValueError("Invalid python_path.")
    module = module_from_spec(spec)
    if spec.loader is None:
        raise ValueError("spec.loader not defined.")
    spec.loader.exec_module(module)

    user_func = getattr(module, config.generic.function)

    workspace = Path(config.generic.workspace).resolve()


def execute(args: Any) -> tuple[int, dict[str, Any], list[Any], str, str, str]:
    """Executes the specified function with the specified arguments.

    Args:
        args (list): Arguments.
    Returns:
        tuple: Trial ID, arguments, objective value, error string, start time, end time.
    """
    trial_id, xs = args

    start_time = datetime.now().strftime(datetime_format)
    set_logging_file_for_trial_id(workspace, trial_id)

    try:
        y = user_func(xs)
        if isinstance(y, list):
            ys = [yi for yi in y]
        else:
            ys = [y]
    except BaseException as e:
        err = str(e)
        ys = [None]
    else:
        err = ""

    end_time = datetime.now().strftime(datetime_format)

    return trial_id, xs, ys, err, start_time, end_time
