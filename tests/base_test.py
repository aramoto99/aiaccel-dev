import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from aiaccel.config import load_config
from aiaccel.util import create_yaml
from aiaccel.workspace import Workspace

d0 = {
    "end_time": "11/03/2020 16:07:45",
    "trial_id": "0",
    "parameters": [
        {"name": "x1", "type": "FLOAT", "value": 0.9932890709584586},
        {"name": "x10", "type": "FLOAT", "value": 3.599465287952899},
        {"name": "x2", "type": "FLOAT", "value": -3.791100401941936},
        {"name": "x3", "type": "FLOAT", "value": -1.6730481463987088},
        {"name": "x4", "type": "FLOAT", "value": 2.2148440758326835},
        {"name": "x5", "type": "FLOAT", "value": 2.111917696952796},
        {"name": "x6", "type": "FLOAT", "value": 4.364405867994597},
        {"name": "x7", "type": "FLOAT", "value": -0.7789300003858477},
        {"name": "x8", "type": "FLOAT", "value": 3.30035693274327},
        {"name": "x9", "type": "FLOAT", "value": 1.7030556641407104},
    ],
    "result": 73.92756153914445,
    "start_time": "11/03/2020 16:07:38",
}


d1 = {
    "end_time": "11/03/2020 16:07:45",
    "trial_id": "1",
    "parameters": [
        {"name": "x1", "type": "FLOAT", "value": 0.8521885935278827},
        {"name": "x10", "type": "FLOAT", "value": -0.6723293209494665},
        {"name": "x2", "type": "FLOAT", "value": 2.6228008245794197},
        {"name": "x3", "type": "FLOAT", "value": -4.978939466488893},
        {"name": "x4", "type": "FLOAT", "value": -0.546128059451986},
        {"name": "x5", "type": "FLOAT", "value": 2.2154003234078257},
        {"name": "x6", "type": "FLOAT", "value": -2.7123777872954733},
        {"name": "x7", "type": "FLOAT", "value": 4.452706955539224},
        {"name": "x8", "type": "FLOAT", "value": 4.014274576114836},
        {"name": "x9", "type": "FLOAT", "value": -4.694100169664464},
    ],
    "result": 103.38599820960606,
    "start_time": "11/03/2020 16:07:38",
}


d2 = {
    "end_time": "11/03/2020 16:07:46",
    "trial_id": 2,
    "parameters": [
        {"name": "x1", "type": "FLOAT", "value": 0.2209278197011611},
        {"name": "x10", "type": "FLOAT", "value": 3.4743373693723267},
        {"name": "x2", "type": "FLOAT", "value": 2.6377461897661405},
        {"name": "x3", "type": "FLOAT", "value": -2.449309742605783},
        {"name": "x4", "type": "FLOAT", "value": -0.04564912908059071},
        {"name": "x5", "type": "FLOAT", "value": -0.505089352112619},
        {"name": "x6", "type": "FLOAT", "value": 1.515929727227629},
        {"name": "x7", "type": "FLOAT", "value": 2.8872335113551317},
        {"name": "x8", "type": "FLOAT", "value": -4.0614041322576515},
        {"name": "x9", "type": "FLOAT", "value": -4.716525234779937},
    ],
    "result": 74.70862563400767,
    "start_time": "11/03/2020 16:07:40",
}


class BaseTest(object):
    @pytest.fixture(autouse=True)
    def _setup(self, tmpdir, work_dir, create_tmp_config, cd_work):
        self.test_data_dir = Path(__file__).resolve().parent.joinpath("test_data")
        self.config_json_path = create_tmp_config(self.test_data_dir.joinpath("config.yaml"))

        self.configs = {
            "config.yaml": create_tmp_config(self.test_data_dir.joinpath("config.yaml")),
            "config_random.yaml": create_tmp_config(self.test_data_dir.joinpath("config_random.yaml")),
            "config_grid.yaml": create_tmp_config(self.test_data_dir.joinpath("config_grid.yaml")),
            "config_budget-specified-grid.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_budget-specified-grid.yaml")
            ),
            "config_sobol.yaml": create_tmp_config(self.test_data_dir.joinpath("config_sobol.yaml")),
            "config_sobol_int.yaml": create_tmp_config(self.test_data_dir.joinpath("config_sobol_int.yaml")),
            "config_sobol_no_initial.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_sobol_no_initial.yaml")
            ),
            "config_tpe.yaml": create_tmp_config(self.test_data_dir.joinpath("config_tpe.yaml")),
            "config_tpe_2.yaml": create_tmp_config(self.test_data_dir.joinpath("config_tpe_2.yaml")),
            "config_motpe.yaml": create_tmp_config(self.test_data_dir.joinpath("config_motpe.yaml")),
            "config_nelder_mead.yaml": create_tmp_config(self.test_data_dir.joinpath("config_nelder_mead.yaml")),
            "config_nelder_mead_resumption.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_nelder_mead_resumption.yaml")
            ),
            "config_random_resumption.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_random_resumption.yaml")
            ),
            "config_sobol_resumption.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_sobol_resumption.yaml")
            ),
            "config_tpe_resumption.yaml": create_tmp_config(self.test_data_dir.joinpath("config_tpe_resumption.yaml")),
            "config_grid_resumption.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_grid_resumption.yaml")
            ),
            "config_budget-specified-grid_resumption.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_budget-specified-grid_resumption.yaml")
            ),
            "config_motpe_resumption.yaml": create_tmp_config(
                self.test_data_dir.joinpath("config_motpe_resumption.yaml")
            ),
        }

        self.tmpdir_path = tmpdir

        # for label in self.configs.keys():
        #     self.configs[label].resume = None
        #     self.configs[label].clean = None
        #     self.configs[label].generic.workspace = self.tmpdir_path / 'work'

        self.workspace = Workspace(str(self.tmpdir_path / "work"))
        if self.workspace.path.exists():
            self.workspace.clean()
        self.workspace.create()

        self.test_result_data = []
        self.test_result_data.append(d0)
        self.test_result_data.append(d1)
        self.test_result_data.append(d2)

        # for d in self.test_result_data:
        #     name = f"{d['trial_id']}.yml"
        #     path = work_dir / 'result' / name
        #     create_yaml(path, d)

        self.result_comparison = []

    def load_config_for_test(self, path):
        config = load_config(path)
        config.resume = None
        config.clean = None
        config.generic.workspace = self.tmpdir_path / "work"

        return config

    @contextmanager
    def create_main(self, from_file_path=None):
        if from_file_path is None:
            from_file_path = self.test_data_dir.joinpath("original_main.py")
        to_file_path = self.tmpdir_path.joinpath("original_main.py")
        shutil.copy(from_file_path, to_file_path)
        yield
