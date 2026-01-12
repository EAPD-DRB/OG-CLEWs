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
# import get_pop_data module
import get_pop_data


UN_COUNTRY_CODE = "608"  # Philippines

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
        "tG1": 50,
        "start_year": 2026,
        "etr_params": [[[0.18]]],
        "tau_bq": [0.0],
        "debt_ratio_ss": 1.2,
        "gamma_g": [p.gamma_g] * p.M,
        "epsilon": [p.epsilon] * p.M,
        "gamma": [p.gamma] * p.M,
        "cit_rate": [[p.cit_rate[0][0]]],
        "tau_c": [[p.tau_c[0][0]]],
        "alpha_c": np.array(list(alpha_c_dict.values())),
        "c_min": np.array([0.05, 0.004, 0.007, 0.03, 0.08]),
        "io_matrix": io_df.values,
        # The values below are the steady-state values, multiplied by factors
        # that work on the first try for reason's we do not understand.
        "initial_guess_r_SS": 0.050 * 1.2,
        "initial_guess_TR_SS": 0.2,  # 0.423 * 0.6,
        "initial_guess_factor_SS": 144617.0,
    }
    p.update_specifications(updated_params)

    # get baseline population data (rather than use what is in JSON)
    (
        pop_dict,
        pop_dist,
        pre_pop_dist,
        fert_rates,
        mort_rates,
        infmort_rates,
        imm_rates,
        baseline_deaths,
    ) = get_pop_data.baseline_pop(p, un_country_code=UN_COUNTRY_CODE, download=True)
    p.update_specifications(pop_dict)

    print(f"Baseline dealths = {baseline_deaths[10:15, :].sum()}")
    # save baseline_deaths array to csv file
    np.savetxt(
        os.path.join(base_dir, "baseline_deaths.csv"),
        baseline_deaths,
        delimiter=",",
    )

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

    #################
    # Fiscal costs of energy transition
    #################
    transition_investment_USD = 300 * 0.1  # in billions, assumed gov't cost about 10% of all investment (see PEP docs)
    investment_horizon = (
        20  # years over which investment spread (assume linear), PEP plan suggests this may be longer
    )
    PHL_GDP = 461.6  # in billions USD, 2024 value (https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=PH)
    # spread out investment over time with it front loaded and smoothly declining
    investment_profile = np.array([
        71.47383123,
        82.13856462,
        31.91362223,
        28.13425372,
        21.95610587,
        18.06133707,
        19.16543852,
        21.03081355,
        17.22572634,
        12.70885258,
        10.44593532,
        9.573177303,
        8.891963878,
        8.323563844,
        7.471094661,
        6.764190725,
        6.242713866,
        5.882017178,
        4.923950646,
        4.923950646,
        4.923950646,
        4.923950646,
        4.923950646,
        0
    ])
    # put in percent of total investment over the period
    investment_profile = investment_profile / investment_profile.sum()
    # scale to total investment amount
    pct_gdp_investment = (transition_investment_USD * investment_profile) / PHL_GDP
    print(
        "Pct of GDP for government investment increase: ", pct_gdp_investment
    )
    new_alpha_G = p.alpha_G[:investment_horizon + 1]
    for y in range(investment_horizon):
        new_alpha_G[y] += pct_gdp_investment[y]
    # Apply new alpha_G for first T years, then go back to baseline

    #################
    # Health benefits affecting productivity and labor supply
    #################
    pct_change_productivity = (
        0.15/0.5 * 0.03  # increase in labor productivity due to better health, 15% decline in PM2.5
    )
    # roughly based on https://docs.iza.org/dp8916.pdf who find about 50% change in PM2.5 leads to 3% decline in productivity
    num_years_prod = 15  # years to phase in
    prod_J = 7  # max lifetime income group affected by productivity changes
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

    #################
    # Health benefits affecting mortality
    #################
    # Find new population with excess deaths
    num_years_mort = 15  # years to phase in
    pct_change_mortality = (
        -0.06
    )  # reduction in mortality rates due to improved air quality, PM2.5 down about 15% or about 10 ug/m3
    # Roughly based on https://pmc.ncbi.nlm.nih.gov/articles/PMC2801178/
    # find that 26% increase in mort rates for 10-μg/m3 increase in PM2.5
    new_pop_dict, PEP_deaths = get_pop_data.health_pop(
        p2,
        pop_dist,
        pre_pop_dist,
        fert_rates,
        mort_rates,
        infmort_rates,
        imm_rates,
        UN_COUNTRY_CODE,
        mort_effect=pct_change_mortality,
        time_horizon=num_years_mort,
    )
    p2.update_specifications(new_pop_dict)

    print(f"PEP dealths = {PEP_deaths[10:15, :].sum()}")
    # save PEP_deaths array to csv file
    np.savetxt(
        os.path.join(base_dir, "PEP_deaths.csv"),
        PEP_deaths,
        delimiter=",",
    )

    #################
    # Parameter changes for TFP and government spending
    #################
    updated_params_ref = {
        "Z": [  # energy sector TFP decline as per CLEWS (higher input cost per KwH) -> but maybe it comes back up over time since large fixed costs of investment?
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
            [1.0, 0.97, 1.0, 1.0],
            [1.0, 0.99, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 1.01, 1.0, 1.0],
            [1.0, 1.02, 1.0, 1.0],
        ],
        "alpha_G": new_alpha_G,
        "RC_SS": 3e-4,   # temporary increase in error tolerance -- some issue with demographics when change mortality
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
