"""
This script provides and integration prototype that simulates the
2023 Philippine Energy Plan (PEP) in both the CLEWs model and OG-PHL.

To run this script:
* Ensure you have Python from Anaconda installed.
* Clone the OG-CLEWS repo: https://github.com/EAPD-DRB/OG-CLEWS
* Build the ogphl-dev environment by running the following command from the
  OG-CLEWs repo root directory:
    `conda env create`
* Activate the ogphl-dev environment:
    `conda activate ogphl-dev`
* Run this script:
    `python OG_simulations/OG-CLEWs-example.py`
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

# import functions to read CLEWs data
from CLEWS_data import (
    read_cost_data,
    read_emissions_data,
)


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

    # Directories for CLEWs data
    clews_base_dir = os.path.join(
        CUR_DIR, "..", "CLEWS_simulations", "v8-Base"
    )
    clews_pep_dir = os.path.join(CUR_DIR, "..", "CLEWS_simulations", "v8-PEP")

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
        "etr_params": [[[0.25]]],
        "tau_bq": [0.0],
        "debt_ratio_ss": 1.5,
        "gamma_g": [p.gamma_g] * p.M,
        "epsilon": [p.epsilon] * p.M,
        "gamma": [p.gamma] * p.M,
        "cit_rate": [[p.cit_rate[0][0]]],
        "tau_c": [[p.tau_c[0][0]]],
        "alpha_c": np.array(list(alpha_c_dict.values())),
        "c_min": np.zeros(p.I),
        "io_matrix": io_df.values,
        "initial_guess_r_SS": 0.050 * 1.2,
        "initial_guess_TR_SS": 0.2,  # 0.423 * 0.6,
        "initial_guess_factor_SS": 144617.0,
    }
    p.update_specifications(updated_params)

    # get baseline population data
    (
        pop_dict,
        pop_dist,
        pre_pop_dist,
        fert_rates,
        mort_rates,
        infmort_rates,
        imm_rates,
        baseline_deaths,
    ) = get_pop_data.baseline_pop(
        p, un_country_code=UN_COUNTRY_CODE, download=False
    )
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
    Run counterfactual policy (PEP23)
    ---------------------------------------------------------------------------
    """
    client = Client(n_workers=num_workers, threads_per_worker=1)

    # create new Specifications object for reform simulation
    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir

    #################
    # Fiscal costs of energy transition -- not modeled in CLEWs but important for OG-PHL
    #################
    transition_investment_USD = (
        300 * 0.1
    )  # in billions, assumed gov't cost about 10% of all investment (see PEP docs)
    investment_horizon = 20  # years over which investment spread (assume linear), PEP plan suggests this may be longer
    PHL_GDP = 461.6  # in billions USD, 2024 value (https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=PH)
    # spread out investment over time with it front loaded and smoothly declining
    investment_profile = np.array(
        [
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
            0,
        ]
    )
    # put in percent of total investment over the period
    investment_profile = investment_profile / investment_profile.sum()
    # scale to total investment amount
    pct_gdp_investment = (
        transition_investment_USD * investment_profile
    ) / PHL_GDP
    print(
        "Pct of GDP for government investment increase: ", pct_gdp_investment
    )
    new_alpha_G = p.alpha_G[: investment_horizon + 1]
    for y in range(investment_horizon):
        new_alpha_G[y] += pct_gdp_investment[y]
    # Apply new alpha_G for first T years, then go back to baseline

    #################
    # Health benefits affecting productivity and labor supply: use emissions from CLEWS
    #################
    # Read in in CLEWS emissions data
    base_emissions_file = os.path.join(
        clews_base_dir, "Base-v8-Emissions.xlsx"
    )
    pep_emissions_file = os.path.join(clews_pep_dir, "PEP-v8-Emissions.xlsx")
    base_pm25 = read_emissions_data(base_emissions_file, "PM2_5")
    pep_pm25 = read_emissions_data(pep_emissions_file, "PM2_5")
    pct_change_pm25 = ((base_pm25[6:] - pep_pm25[6:]) / base_pm25[6:]).mean()

    pct_change_productivity = (
        pct_change_pm25
        / 0.5
        * 0.03  # increase in labor productivity due to better health, 15% decline in PM2.5
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
        pct_change_pm25 / 0.15
    ) * -0.06  # reduction in mortality rates due to improved air quality
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

    print(f"PEP deaths = {PEP_deaths[10:15, :].sum()}")
    # save PEP_deaths array to csv file
    np.savetxt(
        os.path.join(base_dir, "PEP_deaths.csv"),
        PEP_deaths,
        delimiter=",",
    )

    TFP = np.ones((p2.T, p2.M))
    # Read in price per kWh data from CLEWs
    base_cost_file = os.path.join(
        clews_base_dir,
        "260110_Cost of electricity generation_PHL_Base_v8_updated.xlsx",
    )
    pep_cost_file = os.path.join(
        clews_pep_dir, "260111_Cost of electricity generation_PHL_PEP_v8.xlsx"
    )
    base_cost = read_cost_data(
        base_cost_file, "Grid_cost_Base_v8", row_index=5
    )
    pep_cost = read_cost_data(pep_cost_file, "Grid_cost_PEP", row_index=5)
    pct_change_cost = (pep_cost - base_cost) / base_cost
    length_cost = len(pct_change_cost)
    # Assume TFP changes inversely with cost changes
    TFP[:length_cost, 1] = 1 / (1 + pct_change_cost)
    TFP[length_cost:, 1] = TFP[length_cost - 1, 1]  # hold last value constant
    #################
    # Parameter changes for TFP and government spending
    #################
    updated_params_ref = {
        "Z": TFP,
        "alpha_G": new_alpha_G,
        "RC_SS": 3e-4,  # temporary increase in error tolerance -- some issue with demographics when change mortality
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

    """
    ---------------------------------------------------------------------------
    Outputs to go back to CLEWs model
    ---------------------------------------------------------------------------
    """
    CLEWs_path = os.path.join(save_dir, "OG_to_CLEWs_outputs")
    os.makedirs(CLEWs_path, exist_ok=True)
    # Percentage change in energy demand
    energy_demand = (reform_tpi["Y_m"][1] - base_tpi["Y_m"][1]) / base_tpi[
        "Y_m"
    ][1]
    np.savetxt(
        os.path.join(CLEWs_path, "pct_change_energy_demand.csv"),
        energy_demand,
        delimiter=",",
    )
    # Real interest rate (for discounting in CLEWs)
    real_interest_rate = reform_tpi["r"]
    np.savetxt(
        os.path.join(CLEWs_path, "real_interest_rate.csv"),
        real_interest_rate,
        delimiter=",",
    )


if __name__ == "__main__":
    # execute only if run as a script
    main()
