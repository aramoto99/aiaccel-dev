from __future__ import annotations

import copy
from typing import Any

from numpy import str_
from omegaconf.dictconfig import DictConfig

from aiaccel.config import is_multi_objective
from aiaccel.module import AiaccelCore
from aiaccel.parameter import HyperParameterConfiguration
from aiaccel.util import str_to_logging_level


class AbstractOptimizer(AiaccelCore):
    """An abstract class for Optimizer classes.

    Args:
        options (dict[str, str | int | bool]): A dictionary containing
            command line options.

    Attributes:
        options (dict[str, str | int | bool]): A dictionary containing
            command line options.
        num_ready (int): A ready number of hyperparameters.
        num_running (int): A running number of hyperprameters.
        num_finished (int): A finished number of hyperparameters.
        num_of_generated_parameter (int): A number of generated hyperparamters.
        all_parameters_generated (bool): Whether all parameters are generated.
            True if all parameters are generated.
        params (HyperParameterConfiguration): Loaded hyper parameter
            configuration object.
        trial_id (TrialId): TrialId object.
    """

    def __init__(self, config: DictConfig) -> None:
        super().__init__(config, "optimizer")
        self.set_logger(
            "root.optimizer",
            self.workspace.log / self.config.logger.file.optimizer,
            str_to_logging_level(self.config.logger.log_level.optimizer),
            str_to_logging_level(self.config.logger.stream_level.optimizer),
            "Optimizer",
        )

        self.trial_number = self.config.optimize.trial_number
        self.num_of_generated_parameter = 0
        self.params = HyperParameterConfiguration(self.config.optimize.parameters)
        self.write_random_seed_to_debug_log()

    def register_new_parameters(self, params: list[dict[str, float | int | str]]) -> None:
        """Create hyper parameter files.

        Args:
            params (list[dict[str, float | int | str]]): A list of hyper
                parameter dictionaries.

        Returns:
            None

        Note:
            ::

                param = {
                    'parameter_name': ...,
                    'type': ...,
                    'value': ...
                }

        """
        self.storage.hp.set_any_trial_params(trial_id=self.trial_id.get(), params=params)
        self.storage.trial.set_any_trial_state(trial_id=self.trial_id.get(), state="ready")
        self.num_of_generated_parameter += 1
        self.logger.debug(f"Generated parameters: {params}")
        self.logger.debug(f"Num Of Generated parameters: {self.num_of_generated_parameter}")

    def generate_initial_parameter(self) -> Any:
        """Generate a list of initial parameters.

        Returns:
            list[dict[str, float | int | str]]: A created list of initial
            parameters.
        """
        sample = self.params.sample(self._rng, initial=True)
        new_params = []

        for s in sample:
            new_param = {"parameter_name": s["name"], "type": s["type"], "value": s["value"]}
            new_params.append(new_param)

        return new_params

    def generate_parameter(self) -> Any:
        """Generate a list of parameters.

        Raises:
            NotImplementedError: Causes when the inherited class does not
                implement.

        Returns:
            list[dict[str, float | int | str]] | None: A created list of
            parameters.
        """
        raise NotImplementedError

    def generate_new_parameter(self) -> list[dict[str, float | int | str]] | None:
        """Generate a list of parameters.

        Returns:
            list[dict[str, float | int | str]] | None: A created list of
            parameters.
        """
        if self.num_of_generated_parameter == 0:
            new_params = self.generate_initial_parameter()
        else:
            new_params = self.generate_parameter()

        return new_params

    def run_optimizer_multiple_times(self, available_pool_size) -> None:
        if available_pool_size <= 0:
            return
        for _ in range(available_pool_size):
            if new_params := self.generate_new_parameter():
                self.register_new_parameters(new_params)
                self.trial_id.increment()
                self._serialize(self.trial_id.integer)

    def resume(self) -> None:
        """When in resume mode, load the previous optimization data in advance.

        Args:
            None

        Returns:
            None
        """
        self.logger.info(f"Resume mode: {self.config.resume}")
        self.trial_id.initial(num=self.config.resume)
        super()._deserialize(self.config.resume)
        self.trial_number = self.config.optimize.trial_number

    def get_any_trial_objective(self, trial_id: int) -> Any:
        """Get any trial result.

            if the objective is multi-objective, return the list of objective.

        Args:
            trial_id (int): Trial ID.

        Returns:
            Any: Any trial result.
        """

        objective = self.storage.result.get_any_trial_objective(trial_id)
        if objective is None:
            return None

        if is_multi_objective(self.config):
            return objective
        else:
            return objective[0]
