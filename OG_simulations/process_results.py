"""
This script processes the results of the PEP simulation.

Key things we want to present:

* Table: I/O table with use with multi industry calibration for PEP sims
* Table: alpha_c used for PEP sims

Parametrization of PEP:
* Plot TFP of the energy sector over time (50 years)
* Plot kWh cost from CLEWS over time(baseline and PEP)
* Plot government spending over time
* Plot investment from CLEWS over time (baseline and PEP)

* Plot C02 emissions over time (50 years) baseline and PEP
* Plot PM2.5 concentrations over time (50 years) baseline and PEP
* Plot ability profiles in baseline and PEP (full phase in)
* Plot chi_in profiles in baseline and PEP (full phase in)
* Plot mortality rates in baseline and PEP (full phase in)

OG Model outcomes:
Health:
* Plot deaths over time in baseline and PEP by year (50 years)
* Plot delta in deaths over time in PEP vs baseline by year (50 years)
* Plot pct change in L over time
Macro:
* Plots of pct change K, Y, C, L over time
* Table with NPV of GDP effects (100 years, under different discount rates -- compare with NPV of assumed investment)
Fiscal:
* Plot G/Y in baseline and PEP
* Could we look at tax/Y then convert to levels (using Y forcast above) and get NPV of revenue -- this would give the marginal value of public funds for energy investment
MVPF can be done in 2 ways:
1) NPV(GDP) / NPV(Govt spending on energy investment)
2) NPV(GDP) / (NPV(Govt spending on energy investment) - NPV(increased tax revenue from higher GDP))
* Plot D/Y in baseline and PEP
Distributional:
* Plot pct change in p_i over time
* Plot pct change in p_m over time
* Plot pct change in n by ability group (10-20 years out)
* Plot pct change in y by ability group (10-20 years out)
* Plot pct change in c by ability group (10-20 years out)


"""

# imports
import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import ogcore.output_plots as op
import ogcore.output_tables as ot
import ogcore.parameter_plots as pp
from ogcore.utils import safe_read_pickle
from ogphl import input_output as io
from calibration_values import PROD_DICT
from ogphl.input_output import CONS_DICT
from CLEWS_data import (
    read_cost_data,
    read_investments_data,
    read_emissions_data,
    calculate_percentage_change,
)


# set plot style
plt.style.use("ogcore.OGcorePlots")
# set current directory
CUR_DIR = os.path.dirname(os.path.realpath(__file__))
plot_dir = os.path.join(CUR_DIR, "PEP_simulation_plots")
if not os.path.exists(plot_dir):
    os.makedirs(plot_dir)
table_dir = os.path.join(CUR_DIR, "PEP_simulation_tables")
if not os.path.exists(table_dir):
    os.makedirs(table_dir)
# set base and reform directories
base_dir = os.path.join(CUR_DIR, "PEP23_simulation_results", "OUTPUT_BASELINE")
reform_dir = os.path.join(
    CUR_DIR, "PEP23_simulation_results", "OUTPUT_PEP2023"
)


# CLEWS output paths
# Define file paths
clews_base_dir = os.path.join(CUR_DIR, "..", "CLEWS_simulations", "v8-Base")
clews_pep_dir = os.path.join(CUR_DIR, "..", "CLEWS_simulations", "v8-PEP")

# Cost of electricity generation files
base_cost_file = os.path.join(
    clews_base_dir,
    "260110_Cost of electricity generation_PHL_Base_v8_updated.xlsx",
)
pep_cost_file = os.path.join(
    clews_pep_dir, "260111_Cost of electricity generation_PHL_PEP_v8.xlsx"
)

# Emissions files
base_emissions_file = os.path.join(clews_base_dir, "Base-v8-Emissions.xlsx")
pep_emissions_file = os.path.join(clews_pep_dir, "PEP-v8-Emissions.xlsx")

# set constants
TIME_HORIZON = 50  # years to plot
NUM_YEARS_NPV = 100
# To get GDP in levels, can use # Source: https://governance.neda.gov.ph/govt-cuts-growth-target-to-6-7-neda/
NEDA_Forecast = np.array(
    [
        26.55,
        28.27575,
        30.2550525,
        32.44854381,
        34.80106323,
        37.32414032,
        40.03014049,
        42.93232567,
        46.04491929,
        49.38317593,
        52.96345619,
        56.80330676,
        60.9215465,
        65.33835863,
        70.07538963,
        75.15585537,
        80.60465489,
        86.44849237,
        92.71600806,
        99.43791865,
        106.6471678,
    ]
)  # Units are Trillions of PHP
# use last period's growth rate to extend to NUM_YEARS_NPV
last_growth_rate = NEDA_Forecast[-1] / NEDA_Forecast[-2]
for i in range(NUM_YEARS_NPV - len(NEDA_Forecast)):
    NEDA_Forecast = np.append(
        NEDA_Forecast, NEDA_Forecast[-1] * last_growth_rate
    )

# read in parameters and output
base_params = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
reform_params = safe_read_pickle(os.path.join(reform_dir, "model_params.pkl"))
base_tpi = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
reform_tpi = safe_read_pickle(os.path.join(reform_dir, "TPI", "TPI_vars.pkl"))


print(
    "DY ratio = ",
    reform_tpi["D"][:TIME_HORIZON] / reform_tpi["Y"][:TIME_HORIZON],
)


################
# Calibration Tables and Figures
################
# Multisector I/O table
alpha_c_dict = io.get_alpha_c()
io_df = io.get_io_matrix(prod_dict=PROD_DICT)
io_df.to_latex(
    os.path.join(table_dir, "PEP_IO_Table.tex"),
    caption="Input-Output Table used for Multi-Industry Calibration in PEP Simulation",
    label="tab:PEP_IO_Table",
    float_format="%.3f",
)
pd.DataFrame.from_dict(
    {
        "Cons. Category": list(alpha_c_dict.keys()),
        "Exp. Share": list(alpha_c_dict.values()),
    }
).to_latex(
    os.path.join(table_dir, "PEP_alpha_c_Table.tex"),
    caption="$\\alpha_c$ values used for Multi-Industry Calibration in PEP Simulation",
    label="tab:PEP_alpha_c_Table",
    float_format="%.3f",
)

# Plot TFP of the energy sector over time (50 years)
years = np.arange(
    base_params.start_year, base_params.start_year + TIME_HORIZON
)
tfp = base_params.Z[:TIME_HORIZON, 1]  # energy sector is index 1
plt.figure()
plt.plot(years, tfp, label="Baseline TFP")
plt.plot(years, reform_params.Z[:TIME_HORIZON, 1], label="PEP TFP")
plt.xlabel("Year")
plt.ylabel("Energy Sector TFP")
plt.title("Energy Sector TFP over Time")
plt.legend()
plt.grid()
plt.savefig(os.path.join(plot_dir, "PEP_Energy_Sector_TFP.png"), dpi=300)
plt.close()

# * Plot kWh cost from CLEWS over time (baseline and PEP)
base_cost = read_cost_data(base_cost_file, "Grid_cost_Base_v8", row_index=5)
pep_cost = read_cost_data(pep_cost_file, "Grid_cost_PEP", row_index=5)
plt.figure()
plt.plot(base_cost.index, base_cost.values, label="Baseline Cost")
plt.plot(pep_cost.index, pep_cost.values, label="PEP Cost")
plt.xlabel("Year")
plt.ylabel("Cost (USD/kWh)")
plt.title("Cost of Electricity Generation over Time")
plt.legend()
plt.grid()
plt.savefig(
    os.path.join(plot_dir, "PEP_Cost_of_Electricity_Generation.png"), dpi=300
)
plt.close()

# Plot government spending over time
op.plot_gdp_ratio(
    base_tpi,
    base_params,
    reform_tpi,
    reform_params,
    var_list=["G"],
    start_year=base_params.start_year,
    num_years_to_plot=TIME_HORIZON,
    path=os.path.join(plot_dir, "PEP_G_over_Y.png"),
)

# * Plot investment from CLEWS over time (baseline and PEP)
base_investments = read_investments_data(base_cost_file, "Investments_Base_v8")
pep_investments = read_investments_data(pep_cost_file, "Investments_PEP")
plt.figure()
plt.plot(
    base_investments.index,
    base_investments.values,
    label="Baseline Investments",
)
plt.plot(
    pep_investments.index, pep_investments.values, label="PEP Investments"
)
plt.xlabel("Year")
plt.ylabel("Investments (Million USD)")
plt.title("Annualized Investments over Time")
plt.legend()
plt.grid()
plt.savefig(os.path.join(plot_dir, "PEP_Annualized_Investments.png"), dpi=300)
plt.close()

# * Plot C02 emissions over time (50 years) baseline and PEP
base_co2e = read_emissions_data(base_emissions_file, "CO2e")
pep_co2e = read_emissions_data(pep_emissions_file, "CO2e")
plt.figure()
plt.plot(base_co2e.index, base_co2e.values, label="Baseline CO2e Emissions")
plt.plot(pep_co2e.index, pep_co2e.values, label="PEP CO2e Emissions")
plt.xlabel("Year")
plt.ylabel("CO2e Emissions (tons)")
plt.title("CO2e Emissions over Time")
plt.legend()
plt.grid()
plt.savefig(os.path.join(plot_dir, "PEP_CO2e_Emissions.png"), dpi=300)
plt.close()


# * Plot PM2.5 concentrations over time (50 years) baseline and PEP
base_pm25 = read_emissions_data(base_emissions_file, "PM2_5")
pep_pm25 = read_emissions_data(pep_emissions_file, "PM2_5")
plt.figure()
plt.plot(
    base_pm25.index, base_pm25.values, label="Baseline PM2.5 Concentration"
)
plt.plot(pep_pm25.index, pep_pm25.values, label="PEP PM2.5 Concentration")
plt.xlabel("Year")
plt.ylabel("PM2.5 Concentration (ug/m3)")
plt.title("PM2.5 Concentration over Time")
plt.legend()
plt.grid()
plt.savefig(os.path.join(plot_dir, "PEP_PM2.5_Concentration.png"), dpi=300)
plt.close()

# Plot ability profiles in baseline and PEP (full phase in)
pp.plot_ability_profiles(
    base_params,
    reform_params,
    t=TIME_HORIZON,
    path=os.path.join(plot_dir),
)

# Plot chi_in profiles in baseline and PEP (full phase in)
pp.plot_chi_n(
    [base_params, reform_params],
    labels=["Baseline", "PEP"],
    years_to_plot=[base_params.start_year + TIME_HORIZON],
    path=os.path.join(plot_dir),
)

# Plot mortality rates in baseline and PEP (full phase in)
pp.plot_mort_rates(
    [base_params, reform_params],
    labels=["Baseline", "PEP"],
    years=[base_params.start_year + TIME_HORIZON],
    survival_rates=True,
    include_title=False,
    path=os.path.join(plot_dir),
)
pp.plot_mort_rates(
    [base_params, reform_params],
    labels=["Baseline", "PEP"],
    years=[base_params.start_year + TIME_HORIZON],
    survival_rates=False,
    include_title=False,
    path=os.path.join(plot_dir),
)

################
# OG Model Outcomes
################
# Health:
base_deaths = np.loadtxt(
    os.path.join(base_dir, "baseline_deaths.csv"), delimiter=","
)
reform_deaths = np.loadtxt(
    os.path.join(base_dir, "PEP_deaths.csv"), delimiter=","
)
# * Plot deaths over time in baseline and PEP by year (50 years)
plt.figure()
years = np.arange(
    base_params.start_year, base_params.start_year + TIME_HORIZON
)
plt.plot(
    years,
    base_deaths[:TIME_HORIZON, :].sum(axis=1) / 1e6,
    label="Baseline Deaths",
)
plt.plot(
    years,
    reform_deaths[:TIME_HORIZON, :].sum(axis=1) / 1e6,
    label="PEP Deaths",
)
plt.xlabel("Year")
plt.ylabel("Number of Deaths (Millions)")
# plt.title("Annual Deaths over Time")
plt.legend()
plt.grid()
plt.savefig(os.path.join(plot_dir, "PEP_Annual_Deaths.png"), dpi=300)
plt.close()
# * Plot delta in deaths over time in PEP vs baseline by year (50 years)
plt.figure()
plt.plot(
    years,
    (
        (
            base_deaths[:TIME_HORIZON, :].sum(axis=1)
            - reform_deaths[:TIME_HORIZON, :].sum(axis=1)
        )
        / 1e6
    ).cumsum(),
    label="Cumulative Deaths Averted ((Baseline - PEP))",
)
plt.xlabel("Year")
plt.ylabel("Number of Deaths Averted (Millions)")
# plt.title("Cumulative Deaths Averted over Time")
plt.legend()
plt.grid()
plt.savefig(
    os.path.join(plot_dir, "PEP_Cumulative_Deaths_Averted.png"), dpi=300
)
plt.close()
# * Plot pct change in L over time
op.plot_aggregates(
    base_tpi,
    base_params,
    reform_tpi,
    reform_params,
    var_list=["L"],
    stationarized=False,
    start_year=base_params.start_year,
    num_years_to_plot=TIME_HORIZON,
    path=os.path.join(plot_dir, "PEP_deaths_over_time.png"),
)

# Macro:
# * Plots of pct change K, Y, C, L over time
op.plot_aggregates(
    base_tpi,
    base_params,
    reform_tpi,
    reform_params,
    var_list=["K", "Y", "C", "L"],
    stationarized=False,
    start_year=base_params.start_year,
    num_years_to_plot=TIME_HORIZON,
    path=os.path.join(plot_dir, "PEP_agg_over_time.png"),
)

# * Table with NPV of GDP effects (100 years, under different discount rates -- compare with NPV of assumed investment)
pct_change_gdp = (
    reform_tpi["Y"][:NUM_YEARS_NPV] - base_tpi["Y"][:NUM_YEARS_NPV]
) / base_tpi["Y"][:NUM_YEARS_NPV]
GDP_diff = pct_change_gdp * NEDA_Forecast[:NUM_YEARS_NPV]
NPV_dict = {"Discount Rate": [], "NPV of GDP Effect (Trillions PHP)": []}
for r in [0.01, 0.02, 0.03, 0.04, 0.05]:
    npv = (
        GDP_diff / ((1 + r) ** (np.arange(NUM_YEARS_NPV))[:, np.newaxis])
    ).sum()
    NPV_dict["Discount Rate"].append(r)
    NPV_dict["NPV of GDP Effect (Trillions PHP)"].append(npv)
npv_df = pd.DataFrame(NPV_dict)
npv_df.to_latex(
    os.path.join(table_dir, "PEP_NPV_GDP_Effects_Table.tex"),
    caption="NPV of GDP Effects under Different Discount Rates",
    label="tab:PEP_NPV_GDP_Effects_Table",
    float_format="%.3f",
)

# Fiscal:
# read in data again
base_params = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
reform_params = safe_read_pickle(os.path.join(reform_dir, "model_params.pkl"))
base_tpi = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
reform_tpi = safe_read_pickle(os.path.join(reform_dir, "TPI", "TPI_vars.pkl"))
print(
    "DY ratio = ",
    reform_tpi["D"][:TIME_HORIZON] / reform_tpi["Y"][:TIME_HORIZON],
)

# * Plot D/Y in baseline and PEP
op.plot_gdp_ratio(
    base_tpi,
    base_params,
    reform_tpi,
    reform_params,
    var_list=["D"],
    start_year=base_params.start_year,
    num_years_to_plot=TIME_HORIZON,
    path=os.path.join(plot_dir, "PEP_D_over_Y.png"),
)

# * NPV of tax revenue effects (100 years, under different discount rates)
change_TY = (
    reform_tpi["total_tax_revenue"][:NUM_YEARS_NPV]
    / base_tpi["Y"][:NUM_YEARS_NPV]
) - (
    base_tpi["total_tax_revenue"][:NUM_YEARS_NPV]
    / base_tpi["Y"][:NUM_YEARS_NPV]
)
tax_diff = change_TY * NEDA_Forecast[:NUM_YEARS_NPV]
NPV_dict = {"Discount Rate": [], "NPV of Tax Revenue (Trillions PHP)": []}
for r in [0.01, 0.02, 0.03, 0.04, 0.05]:
    npv = (
        tax_diff / ((1 + r) ** (np.arange(NUM_YEARS_NPV))[:, np.newaxis])
    ).sum()
    NPV_dict["Discount Rate"].append(r)
    NPV_dict["NPV of Tax Revenue (Trillions PHP)"].append(npv)
npv_df = pd.DataFrame(NPV_dict)
npv_df.to_latex(
    os.path.join(table_dir, "PEP_NPV_Tax_Revenue_Effects_Table.tex"),
    caption="NPV of Tax Revenue Effects under Different Discount Rates",
    label="tab:PEP_NPV_Tax_Revenue_Effects_Table",
    float_format="%.3f",
)

# Distributional:
# * Plot pct change in p_i over time
fig, ax = plt.subplots()
for i in range(base_params.I):
    ax.plot(
        years,
        (
            reform_tpi["p_i"][:TIME_HORIZON, i]
            - base_tpi["p_i"][:TIME_HORIZON, i]
        )
        / base_tpi["p_i"][:TIME_HORIZON, i],
        label=list(CONS_DICT.keys())[i],
    )
ax.set_xlabel("Year")
ax.set_ylabel("Percentage Change in Prices")
ax.legend()
# save fig
fig.savefig(os.path.join(plot_dir, "pct_change_p_i.png"), dpi=300)

# * Plot pct change in p_m over time
fig, ax = plt.subplots()
for m in range(base_params.M):
    ax.plot(
        years,
        (
            reform_tpi["p_m"][:TIME_HORIZON, m]
            - base_tpi["p_m"][:TIME_HORIZON, m]
        )
        / base_tpi["p_m"][:TIME_HORIZON, m],
        label=list(PROD_DICT.keys())[m],
    )
ax.set_xlabel("Year")
ax.set_ylabel("Percentage Change in Prices")
ax.legend()
# save fig
fig.savefig(os.path.join(plot_dir, "pct_change_p_m.png"), dpi=300)

# * Plot price of electricity
fig, ax = plt.subplots()
years = np.arange(
    base_params.start_year,
    base_params.start_year + TIME_HORIZON,
)
ax.plot(
    years,
    base_tpi["p_m"][:TIME_HORIZON, 2],
    label="Baseline",
)
ax.plot(
    years,
    reform_tpi["p_m"][:TIME_HORIZON, 2],
    label="PEP Scenario",
)
ax.set_xlabel("Year")
ax.set_ylabel("Price of Electricity")
ax.legend()
# save fig
fig.savefig(os.path.join(plot_dir, "price_of_electricity_plot.png"), dpi=300)

# * Plot pct change in n by ability group (10-20 years out)
op.ability_bar(
    base_tpi,
    base_params,
    reform_tpi,
    reform_params,
    var="n",
    num_years=10,
    start_year=base_params.start_year + 10,
    plot_title=None,
    path=os.path.join(plot_dir, "pct_change_n_by_J.png"),
)
# * Plot pct change in y by ability group (10-20 years out)
op.ability_bar(
    base_tpi,
    base_params,
    reform_tpi,
    reform_params,
    var="before_tax_income",
    num_years=10,
    start_year=base_params.start_year + 10,
    plot_title=None,
    path=os.path.join(plot_dir, "pct_change_before_tax_income_by_J.png"),
)
# * Plot pct change in c by ability group (10-20 years out)
op.ability_bar(
    base_tpi,
    base_params,
    reform_tpi,
    reform_params,
    var="c",
    num_years=10,
    start_year=base_params.start_year + 10,
    plot_title=None,
    path=os.path.join(plot_dir, "pct_change_c_by_J.png"),
)
