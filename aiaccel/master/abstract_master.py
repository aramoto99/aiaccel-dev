from aiaccel.module import AbstractModule
from aiaccel.master.evaluator.maximize_evaluator import MaximizeEvaluator
from aiaccel.master.evaluator.minimize_evaluator import MinimizeEvaluator
from aiaccel.master.verification.abstract_verification import AbstractVerification
from aiaccel.util.logger import str_to_logging_level
from aiaccel.util.time_tools import get_time_now_object
from aiaccel.util.time_tools import get_time_string_from_object
import aiaccel
import logging
from aiaccel.util.serialize import Serializer


class AbstractMaster(AbstractModule):
    """An abstract class for AbciMaster and LocalMaster.

    Attributes:
        loop_start_time (datetime.datetime): A stored loop starting time.
        optimizer_proc (subprocess.Popen): A reference for a subprocess of
            Optimizer.
        start_time (datetime.datetime): A stored starting time.
        verification (AbstractVerification): A verification object.
    """

    def __init__(self, options: dict) -> None:
        """Initial method of AbstractMaster.

        Args:
            config (str): A file name of a configuration.
        """
        self.start_time = get_time_now_object()
        self.loop_start_time = None
        self.options = options
        self.options['process_name'] = 'master'

        super().__init__(self.options)
        self.logger = logging.getLogger('root.master')
        self.logger.setLevel(logging.DEBUG)

        self.set_logger(
            'root.master',
            self.dict_log / self.config.master_logfile.get(),
            str_to_logging_level(self.config.master_file_log_level.get()),
            str_to_logging_level(self.config.master_stream_log_level.get()),
            'Master   '
        )

        self.verification = AbstractVerification(self.options)
        self.goal = self.config.goal.get()
        self.trial_number = self.config.trial_number.get()
        self.serialize = Serializer(self.config, 'master', self.options)

    def pre_process(self) -> None:
        """Pre-procedure before executing processes.

        Returns:
            None

        Raises:
            IndexError: Causes when expire the count which cannot confirm to
                run Optimizer and Scheduler.
        """
        return

    def post_process(self) -> None:
        """Pre-procedure before executing processes.

        Returns:
            None

        Raises:
            ValueError: Causes when an invalid goal is set.
        """
        if not self.check_finished():
            return

        if self.goal.lower() == aiaccel.goal_maximize:
            evaluator = MaximizeEvaluator(self.options)
        elif self.goal.lower() == aiaccel.goal_minimize:
            evaluator = MinimizeEvaluator(self.options)
        else:
            self.logger.error(f'Invalid goal: {self.goal}.')
            raise ValueError(f'Invalid goal: {self.goal}.')

        evaluator.evaluate()
        evaluator.print()
        evaluator.save()

        # verification
        self.verification.verify()
        self.verification.save('final')
        self.logger.info('Master finished.')

    def print_dict_state(self):
        """ Display the number of yaml files in 'ready' 'running'
            and 'finished' directries in hp directory.

        Returns:
            None
        """
        now = get_time_now_object()

        if self.loop_start_time is None:
            end_estimated_time = 'Unknown'
        else:
            looping_time = now - self.loop_start_time

            if self.hp_finished != 0:
                one_loop_time = (looping_time / self.hp_finished)
                hp_finished = self.hp_finished
                finishing_time = (now + (self.trial_number - hp_finished) * one_loop_time)
                end_estimated_time = get_time_string_from_object(finishing_time)
            else:
                end_estimated_time = 'Unknown'

        self.logger.info(
            f'{self.hp_finished}/{self.trial_number} finished, '
            f'ready: {self.hp_ready} ,'
            f'running: {self.hp_running}, '
            f'end estimated time: {end_estimated_time}'
        )

    def loop_pre_process(self) -> None:
        """Called before entering a main loop process.

        Returns:
            None
        """
        self.loop_start_time = get_time_now_object()

    def loop_post_process(self) -> None:
        """Called after exiting a main loop process.

        Returns:
            None
        """
        return

    def inner_loop_pre_process(self) -> bool:
        """Called before executing a main loop process. This process is
            repeated every main loop.

        Returns:
            bool: The process succeeds or not. The main loop exits if failed.
        """
        self.get_each_state_count()

        return True

    def inner_loop_main_process(self) -> bool:
        """A main loop process. This process is repeated every main loop.

        Returns:
            bool: The process succeeds or not. The main loop exits if failed.
        """
        if self.hp_finished >= self.trial_number:
            return False

        return True

    def inner_loop_post_process(self) -> bool:
        """Called after exiting a main loop process. This process is repeated
            every main loop.

        Returns:
            bool: The process succeeds or not. The main loop exits if failed.
        """
        self.print_dict_state()
        # verification
        self.verification.verify()

        return True