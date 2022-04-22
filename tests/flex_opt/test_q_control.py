import numpy as np
import pandas as pd
import pytest

from edisgo.flex_opt import q_control
from edisgo.io import ding0_import
from edisgo.network import timeseries
from edisgo.network.topology import Topology
from edisgo.tools.config import Config


class TestTimeseriesReactive:
    @classmethod
    def setup_class(self):
        self.topology = Topology()
        self.timeseries = timeseries.TimeSeries()
        self.config = Config()
        ding0_import.import_ding0_grid(pytest.ding0_test_network_path, self)
        self.timeseries.timeindex = pd.date_range("1/1/1970", periods=4, freq="H")

    def test_get_q_sign_generator(self):
        # ToDo implement
        pass

    def test_get_q_sign_load(self):
        # ToDo implement
        pass

    def test_fixed_cosphi(self):
        # test for component_type="generators"
        comp_mv_1 = "Generator_1"
        comp_mv_2 = "GeneratorFluctuating_2"
        comp_lv_1 = "GeneratorFluctuating_25"
        comp_lv_2 = "GeneratorFluctuating_26"

        active_power_ts = pd.DataFrame(
            data={
                comp_mv_1: [0.5, 1.5],
                comp_mv_2: [2.5, 3.5],
                comp_lv_1: [0.1, 0.0],
                comp_lv_2: [0.15, 0.07],
            },
            index=self.timeseries.timeindex,
        )
        self.timeseries.generators_active_power = active_power_ts

        q_control.fixed_cosphi(
            self,
            self.topology.generators_df.loc[[comp_mv_1, comp_mv_2, comp_lv_1], :],
            "generators",
        )

        assert self.timeseries.generators_reactive_power.shape == (2, 3)
        assert np.isclose(
            self.timeseries.generators_reactive_power.loc[
                :, [comp_mv_1, comp_mv_2]
            ].values,
            active_power_ts.loc[:, [comp_mv_1, comp_mv_2]].values * -0.484322,
        ).all()
        assert np.isclose(
            self.timeseries.generators_reactive_power.loc[:, comp_lv_1].values,
            active_power_ts.loc[:, comp_lv_1] * -0.328684,
        ).all()

        q_control._set_reactive_power_time_series_for_fixed_cosphi_using_config(
            self, self.topology.generators_df.loc[[comp_lv_2], :], "generators"
        )

        # check new time series and that old reactive power time series
        # remained unchanged
        assert self.timeseries.generators_reactive_power.shape == (2, 4)
        assert np.isclose(
            self.timeseries.generators_reactive_power.loc[
                :, [comp_mv_1, comp_mv_2]
            ].values,
            active_power_ts.loc[:, [comp_mv_1, comp_mv_2]].values * -0.484322,
        ).all()
        assert np.isclose(
            self.timeseries.generators_reactive_power.loc[
                :, [comp_lv_1, comp_lv_2]
            ].values,
            active_power_ts.loc[:, [comp_lv_1, comp_lv_2]] * -0.328684,
        ).all()

        # test for component_type="loads"
        # change bus of load so that it becomes MV load
        comp_mv_1 = "Load_retail_MVGrid_1_Load_aggregated_retail_MVGrid_1_1"
        self.topology._loads_df.at[comp_mv_1, "bus"] = "Bus_BranchTee_MVGrid_1_1"
        comp_lv_1 = "Load_residential_LVGrid_7_2"
        comp_lv_2 = "Load_agricultural_LVGrid_8_1"

        active_power_ts = pd.DataFrame(
            data={
                comp_mv_1: [0.5, 1.5],
                comp_lv_1: [0.1, 0.0],
                comp_lv_2: [0.15, 0.07],
            },
            index=self.timeseries.timeindex,
        )
        self.timeseries.loads_active_power = active_power_ts

        q_control._set_reactive_power_time_series_for_fixed_cosphi_using_config(
            self,
            self.topology.loads_df.loc[[comp_mv_1, comp_lv_1], :],
            "loads",
        )

        assert self.timeseries.loads_reactive_power.shape == (2, 2)
        assert np.isclose(
            self.timeseries.loads_reactive_power.loc[:, [comp_mv_1]].values,
            active_power_ts.loc[:, [comp_mv_1]].values * 0.484322,
        ).all()
        assert np.isclose(
            self.timeseries.loads_reactive_power.loc[:, comp_lv_1].values,
            active_power_ts.loc[:, comp_lv_1] * 0.328684,
        ).all()

        q_control._set_reactive_power_time_series_for_fixed_cosphi_using_config(
            self, self.topology.loads_df.loc[[comp_lv_2], :], "loads"
        )

        assert self.timeseries.loads_reactive_power.shape == (2, 3)
        assert np.isclose(
            self.timeseries.loads_reactive_power.loc[:, comp_lv_2].values,
            active_power_ts.loc[:, comp_lv_2] * 0.328684,
        ).all()

        # test for component_type="storage_units"
        comp_mv_1 = "Storage_1"

        active_power_ts = pd.DataFrame(
            data={comp_mv_1: [0.5, 1.5]}, index=self.timeseries.timeindex
        )
        self.timeseries.storage_units_active_power = active_power_ts

        q_control._set_reactive_power_time_series_for_fixed_cosphi_using_config(
            self,
            self.topology.storage_units_df.loc[[comp_mv_1], :],
            "storage_units",
        )

        assert self.timeseries.storage_units_reactive_power.shape == (2, 1)
        assert np.isclose(
            self.timeseries.storage_units_reactive_power.loc[:, [comp_mv_1]].values,
            active_power_ts.loc[:, [comp_mv_1]].values * -0.484322,
        ).all()

    def test__fixed_cosphi_default_power_factor(
        self,
    ):

        # test for component_type="generators"
        df = pd.DataFrame(
            data={"voltage_level": ["mv", "lv", "lv"]},
            index=["comp_mv_1", "comp_lv_1", "comp_lv_2"],
        )
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="generators", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [0.9, 0.95, 0.95],
        ).all()

        # test for component_type="loads"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="loads", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [0.9, 0.95, 0.95],
        ).all()

        # test for component_type="charging_points"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="charging_points", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [1.0, 1.0, 1.0],
        ).all()

        # test for component_type="heat_pumps"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="heat_pumps", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [0.98, 0.98, 0.98],
        ).all()

        # test for component_type="storage_units"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="storage_units", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [0.9, 0.95, 0.95],
        ).all()

    def test__fixed_cosphi_default_reactive_power_sign(
        self,
    ):

        # test for component_type="generators"
        df = pd.DataFrame(
            data={"voltage_level": ["mv", "lv", "lv"]},
            index=["comp_mv_1", "comp_lv_1", "comp_lv_2"],
        )
        pf = q_control._fixed_cosphi_default_reactive_power_sign(
            comp_df=df, component_type="generators", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [-1.0, -1.0, -1.0],
        ).all()

        # test for component_type="loads"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="loads", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [0.9, 0.95, 0.95],
        ).all()

        # test for component_type="charging_points"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="charging_points", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [1.0, 1.0, 1.0],
        ).all()

        # test for component_type="heat_pumps"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="heat_pumps", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [0.98, 0.98, 0.98],
        ).all()

        # test for component_type="storage_units"
        pf = q_control._fixed_cosphi_default_power_factor(
            comp_df=df, component_type="storage_units", configs=self.config
        )

        assert pf.shape == (3,)
        assert np.isclose(
            pf.loc[["comp_mv_1", "comp_lv_1", "comp_lv_2"]].values,
            [0.9, 0.95, 0.95],
        ).all()
