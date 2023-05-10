from __future__ import annotations

import re
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Any

from aiaccel.scheduler.job.model.abstract_model import AbstractModel
from aiaccel.util import OutputHandler

if TYPE_CHECKING:
    from aiaccel.scheduler import Job


class LocalModel(AbstractModel):

    def before_runner_create(self, obj: Job) -> None:
        return None

    def conditions_runner_confirmed(self, obj: Job) -> bool:
        return True

    def before_job_submitted(self, obj: Job) -> None:
        runner_command = self.create_runner_command(
            obj.config.generic.job_command,
            obj.content,
            obj.trial_id,
            str(obj.config.config_path),
            str(obj.command_error_output),
        )
        obj.logger.info(f'runner command: {" ".join(runner_command)}')
        obj.proc = Popen(runner_command, stdout=PIPE, stderr=PIPE)

        obj.th_oh = OutputHandler(obj.proc)
        obj.th_oh.start()
        self.is_firsttime_called: bool = False

    def conditions_result(self, obj: "Job") -> bool:
        if super().conditions_result(obj):
            return True

        if obj.th_oh.get_returncode() is None or self.is_firsttime_called:
            return False
        else:
            self.create_result_file(obj)
            self.is_firsttime_called = True
            return False

    def create_runner_command(
        self,
        command: str,
        param_content: dict[str, Any],
        trial_id: int,
        config_path: str,
        command_error_output: str
    ) -> list[str]:
        """Create a list of command strings to run a hyper parameter.

        Args:
            command (str): A string command.
            param_content (dict): A hyper parameter content.
            trial_id (str): A unique name of a hyper parameter.

        Returns:
            list[str]: A list of command strings.
        """
        commands = re.split(" +", command)
        params = param_content["parameters"]
        for param in params:
            # Fix a bug related a negative exponential parameters
            # Need to modify wrapper.py as follows:
            if "parameter_name" in param.keys() and "value" in param.keys():
                commands.append(f'--{param["parameter_name"]}')
                commands.append(f'{param["value"]}')
        commands.append("--trial_id")
        commands.append(str(trial_id))
        commands.append("--config")
        commands.append(config_path)
        commands.append("2>")
        commands.append(command_error_output)
        return commands

    def create_result_file(self, obj: "Job") -> None:
        """Create result file.

        Args:
            obj (Job): Job object.

        Returns:
            None
        """
        trial_id: str = str(obj.trial_id)
        stdouts: list[str] = obj.th_oh.get_stdouts()
        stderrs: list[str] = obj.th_oh.get_stderrs()
        start_time: str = str(obj.th_oh.get_start_time())
        end_time: str = str(obj.th_oh.get_end_time())
        exitcode: str = str(obj.th_oh.get_returncode())
        params: list[dict[str, Any]] = obj.content["parameters"]
        objective: str = "nan"
        objectives: list[str] = []

        if len(stdouts) > 0:
            objective = stdouts[-1]  # TODO: fix
            objective = objective.strip("[]")
            objective = objective.replace(" ", "")
            objectives = objective.split(",")

        error = "\n".join(stderrs)
        output_file_path = str(obj.get_result_file_path())
        config_file_path = str(obj.config.config_path)

        args = {
            "file": output_file_path,
            "trial_id": trial_id,
            "config": config_file_path,
            "start_time": start_time,
            "end_time": end_time,
            "error": error,
            "exitcode": exitcode,
        }

        if len(error) == 0:
            del args["error"]

        commands = ["aiaccel-set-result"]
        for key in args.keys():
            commands.append("--" + key)
            commands.append(str(args[key]))

        commands.append("--objective")
        for objective in objectives:
            commands.append(str(objective))

        for param in params:
            if "parameter_name" in param.keys() and "value" in param.keys():
                commands.append("--" + param["parameter_name"])
                commands.append(str(param["value"]))

        obj.logger.info(" ".join(commands))
        Popen(commands)

        return None
