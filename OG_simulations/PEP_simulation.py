"""
This script simulates the 2023 Philippine Energy Plan (PEP).  Key features
of the plan include:

"""
import multiprocessing
from distributed import Client
import os
import json
import time
import copy
import numpy as np
import importlib.resources
import matplotlib.pyplot as plt
from ogcore.parameters import Specifications
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle
from ogphl import input_output as io

# import some constants from calibration_values.py
from calibration_values import PROD_DICT

# Use a custom matplotlib style file for plots
plt.style.use("ogcore.OGcorePlots")


def main():
    # Define parameters to use for multiprocessing
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    print("Number of workers = ", num_workers)

    # Directories to save data
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(CUR_DIR, "PEP23_simulation_results")
    base_dir = os.path.join(save_dir, "OUTPUT_BASELINE")
    reform_dir = os.path.join(save_dir, "OUTPUT_PEP2023")

    """
    ---------------------------------------------------------------------------
    Run baseline policy
    ---------------------------------------------------------------------------
    """
    # Set up baseline parameterization
    p = Specifications(
        baseline=True,
        num_workers=num_workers,
        baseline_dir=base_dir,
        output_base=base_dir,
    )
    # Update parameters for baseline from default json file
    with importlib.resources.open_text(
        "ogphl", "ogphl_default_parameters.json"
    ) as file:
        defaults = json.load(file)
    p.update_specifications(defaults)

    # Now make the model multisector with 4 industries
    p.M = 4
    p.I = 5
    alpha_c_dict = io.get_alpha_c()
    io_df = io.get_io_matrix(prod_dict=PROD_DICT)
    updated_params = {
        "gamma_g": [p.gamma_g] * p.M,
        "epsilon": [p.epsilon] * p.M,
        "gamma": [p.gamma] * p.M,
         "cit_rate": [[p.cit_rate[0][0]]],
        "tau_c": [[p.tau_c[0][0]]],
        "alpha_c": np.array(list(alpha_c_dict.values())),
        "io_matrix": io_df.values,
        "initial_guess_r_SS": 0.044,
        "initial_guess_TR_SS": 0.123 * 0.2,
        "initial_guess_factor_SS": 337283.0,
    }
    p.update_specifications(updated_params)

    # Run model
    start_time = time.time()
    runner(p, time_path=True, client=client)
    print("run time = ", time.time() - start_time)
    client.close()

    """
    ---------------------------------------------------------------------------
    Run reform policy
    ---------------------------------------------------------------------------
    """
    client = Client(n_workers=num_workers, threads_per_worker=1)

    # create new Specifications object for reform simulation
    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir

    #TODO:
    # * Make TFP shock for electricity sector (2nd of 4 sectors) -- align with PEP targets/CLEW output
    # * Change alpha_G to approximate government investment plan in PEP (300-550B USD over 10 years)
    # * Change mortality and productivity/labor supply to align with impact of PEP on health outcomes

    # Parameter change for the reform run: shock TFP for manufacturing
    updated_params_ref = {
        "Z": [
            [1.0, 1.0],
            [1.0, 1.01],
            [1.0, 1.02],
            [1.0, 1.03],
            [1.0, 1.04],
            [1.0, 1.05],
            [1.0, 1.06],
            [1.0, 1.07],
            [1.0, 1.08],
            [1.0, 1.09],
        ],
    }
    p2.update_specifications(updated_params_ref)

    # Run model
    start_time = time.time()
    runner(p2, time_path=True, client=client)
    print("run time = ", time.time() - start_time)
    client.close()

    """
    ---------------------------------------------------------------------------
    Save some results of simulations
    ---------------------------------------------------------------------------
    """
    base_tpi = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
    base_params = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
    reform_tpi = safe_read_pickle(
        os.path.join(reform_dir, "TPI", "TPI_vars.pkl")
    )
    reform_params = safe_read_pickle(
        os.path.join(reform_dir, "model_params.pkl")
    )
    ans = ot.macro_table(
        base_tpi,
        base_params,
        reform_tpi=reform_tpi,
        reform_params=reform_params,
        var_list=["Y", "C", "K", "L", "r", "w"],
        output_type="pct_diff",
        num_years=10,
        start_year=base_params.start_year,
    )

    # create plots of output
    op.plot_all(
        base_dir,
        reform_dir,
        os.path.join(save_dir, "OG-PHL_MultiExample_plots"),
    )

    print("Percentage changes in aggregates:", ans)
    # save percentage change output to csv file
    ans.to_csv(os.path.join(save_dir, "OG-PHL_MultiExample_output.csv"))


if __name__ == "__main__":
    # execute only if run as a script
    main()