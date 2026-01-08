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
        # The values below are the steady-state values, multiplied by factors
        # that work on the first try for reason's we do not understand.
        "initial_guess_r_SS": 0.050 * 1.2,
        "initial_guess_TR_SS": 0.423 * 0.6,
        "initial_guess_factor_SS": 144617.0,
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

    # TODO:
    # * Make TFP shock for electricity sector (2nd of 4 sectors) -- align with PEP targets/CLEW output
    # * Change alpha_G to approximate government investment plan in PEP (300-550B USD over 10 years)
    # * Change mortality and productivity/labor supply to align with impact of PEP on health outcomes

    # Fiscal costs of energy transition
    transition_investment_USD = 300  #  in billions
    investment_horizon = (
        10  # years over which investment spread (assume linear)
    )
    PHL_GDP = 461.6  # in billions USD, 2024 value (https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=PH)
    pct_gdp_investment = transition_investment_USD / (
        PHL_GDP * investment_horizon
    )
    print(
        "Pct of GDP for government investment increase: ", pct_gdp_investment
    )
    new_alpha_G = p.alpha_G[:investment_horizon]
    for y in range(investment_horizon):
        new_alpha_G[y] += pct_gdp_investment

    # Health beenfits
    pct_change_mortality = (
        -0.01
    )  # 1% reduction in mortality rates due to improved air quality
    pct_change_productivity = (
        0.005  # 0.5% increase in labor productivity due to better health
    )
    num_years_mort = 15  # years to phase in
    num_years_prod = 15  # years to phase in
    mort_J = 7  # max lifetime income group affected by mortality changes
    prod_J = 7  # max lifetime income group affected by productivity changes
    mort_benefits = np.linspace(0, pct_change_mortality, num_years_mort)
    prod_benefits = np.linspace(0, pct_change_productivity, num_years_prod)
    # productivity adjustments
    for t, benefit in enumerate(prod_benefits):
        p2.e[t, :, :prod_J] = p.e[t, :, :prod_J] * (1 + benefit)
        p2.chi_n[t, :] = p.chi_n[t, :] * (1 - benefit)
    p2.e[num_years_prod:, :, :prod_J] = p.e[num_years_prod:, :, :prod_J] * (
        1 + pct_change_productivity
    )
    p2.chi_n[num_years_prod:, :] = p.chi_n[num_years_prod:, :] * (
        1 - pct_change_productivity
    )
    # mortality adjustments
    for t, benefit in enumerate(mort_benefits):
        p2.rho[t, :-1, :mort_J] = p.rho[t, :-1, :mort_J] * (1 - benefit)
    p2.rho[num_years_mort:, :-1, :mort_J] = p.rho[
        num_years_mort:, :-1, :mort_J
    ] * (1 - pct_change_mortality)

    # Parameter changes for TFP and government spending
    updated_params_ref = {
        "Z": [  # enery sector TFP decline as per CLEWS (higher input cost per KwH) -> but maybe it comes back up over time since large fixed costs of investment?
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 0.99, 1.0, 1.0],
            [1.0, 0.98, 1.0, 1.0],
            [1.0, 0.97, 1.0, 1.0],
            [1.0, 0.96, 1.0, 1.0],
            [1.0, 0.95, 1.0, 1.0],
            [1.0, 0.95, 1.0, 1.0],
            [1.0, 0.95, 1.0, 1.0],
            [1.0, 0.95, 1.0, 1.0],
            [1.0, 0.95, 1.0, 1.0],
        ],
        "alpha_G": new_alpha_G,
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
        os.path.join(save_dir, "plots"),
    )

    print("Percentage changes in aggregates:", ans)
    # save percentage change output to csv file
    ans.to_csv(os.path.join(save_dir, "output.csv"))


if __name__ == "__main__":
    # execute only if run as a script
    main()
