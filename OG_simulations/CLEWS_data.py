"""
Script to compare baseline and PEP scenarios
Calculates year-by-year percentage changes and creates time series plots
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Define file paths
BASE_DIR = Path("v6-Base")
PEP_DIR = Path("v6-PEP")

# Cost of electricity generation files
base_cost_file = BASE_DIR / "260108_Cost of electricity generation_PHL_Base_v2.xlsx"
pep_cost_file = PEP_DIR / "260108_Cost of electricity generation_PHL_PEP_v2.xlsx"

# Emissions files
base_emissions_file = BASE_DIR / "260108_Emissions_Base_Sc.xlsx"
pep_emissions_file = PEP_DIR / "260108_Emissions_PEP_Sc.xlsx"


def read_cost_data(file_path, sheet_name, row_index=5):
    """
    Read electricity cost data from Excel file

    Parameters:
    -----------
    file_path : Path
        Path to Excel file
    sheet_name : str
        Name of the sheet to read
    row_index : int
        Row index for the data (default 5 for average electricity cost)

    Returns:
    --------
    pd.Series : Time series of electricity costs indexed by year
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Extract the row with average electricity cost
    data_row = df.iloc[row_index]

    # Extract years (column names starting from index 2)
    years = []
    values = []

    for i in range(2, len(data_row)):
        col_name = df.columns[i]
        if pd.notna(data_row.iloc[i]) and isinstance(col_name, (int, float)):
            years.append(int(col_name))
            values.append(float(data_row.iloc[i]))

    return pd.Series(values, index=years, name='Average electricity cost (USD/kWh)')


def read_investments_data(file_path, sheet_name):
    """
    Read annualized investments data from Excel file

    Parameters:
    -----------
    file_path : Path
        Path to Excel file
    sheet_name : str
        Name of the sheet to read

    Returns:
    --------
    pd.Series : Time series of investments indexed by year
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Extract years from row 1 (starting from column index 2)
    year_row = df.iloc[1]

    # Extract the row with Total Annualized Investments (row index 3)
    data_row = df.iloc[3]

    # Extract years and values
    years = []
    values = []

    for i in range(2, len(data_row)):
        year_value = year_row.iloc[i]
        data_value = data_row.iloc[i]

        if pd.notna(year_value) and pd.notna(data_value):
            try:
                years.append(int(float(year_value)))
                values.append(float(data_value))
            except (ValueError, TypeError):
                continue

    return pd.Series(values, index=years, name='Total Annualized Investments (Million USD)')


def read_emissions_data(file_path, row_name):
    """
    Read emissions data from Excel file

    Parameters:
    -----------
    file_path : Path
        Path to Excel file
    row_name : str
        Name of the emissions type ('CO2e' or 'PM2_5')

    Returns:
    --------
    pd.Series : Time series of emissions indexed by year
    """
    df = pd.read_excel(file_path)

    # Find the row with the specified emissions type
    row_labels = df.iloc[:, 0]
    row_idx = None

    for i, label in enumerate(row_labels):
        if pd.notna(label) and str(label).strip() == row_name:
            row_idx = i
            break

    if row_idx is None:
        raise ValueError(f"Could not find row '{row_name}' in emissions file")

    data_row = df.iloc[row_idx]

    # Extract years and values (years start from column 2)
    years = []
    values = []

    for i in range(2, len(data_row)):
        col_value = df.iloc[2, i]  # Year values are in row 2
        if pd.notna(col_value) and pd.notna(data_row.iloc[i]):
            try:
                year = int(float(col_value))
                value = float(data_row.iloc[i])
                years.append(year)
                values.append(value)
            except (ValueError, TypeError):
                continue

    return pd.Series(values, index=years, name=row_name)


def calculate_percentage_change(base_series, pep_series):
    """
    Calculate percentage change between PEP and baseline scenarios

    Parameters:
    -----------
    base_series : pd.Series
        Baseline scenario data
    pep_series : pd.Series
        PEP scenario data

    Returns:
    --------
    pd.Series : Percentage change ((PEP - Base) / Base * 100)
    """
    # Align the series by index
    aligned_base, aligned_pep = base_series.align(pep_series, join='inner')

    # Calculate percentage change
    pct_change = ((aligned_pep - aligned_base) / aligned_base * 100)

    return pct_change


def create_plots():
    """
    Create time series plots comparing baseline and PEP scenarios
    """
    # Read all data
    print("Reading data files...")

    # Cost of electricity generation
    base_cost = read_cost_data(base_cost_file, 'Grid_cost_Base', row_index=5)
    pep_cost = read_cost_data(pep_cost_file, 'Grid_cost_PEP', row_index=5)

    # Investments
    base_investments = read_investments_data(base_cost_file, 'Investments_Base')
    pep_investments = read_investments_data(pep_cost_file, 'Investments_PEP')

    # Emissions
    base_co2e = read_emissions_data(base_emissions_file, 'CO2e')
    pep_co2e = read_emissions_data(pep_emissions_file, 'CO2e')

    base_pm25 = read_emissions_data(base_emissions_file, 'PM2_5')
    pep_pm25 = read_emissions_data(pep_emissions_file, 'PM2_5')

    # Calculate percentage changes
    print("Calculating percentage changes...")
    cost_pct_change = calculate_percentage_change(base_cost, pep_cost)
    investments_pct_change = calculate_percentage_change(base_investments, pep_investments)
    co2e_pct_change = calculate_percentage_change(base_co2e, pep_co2e)
    pm25_pct_change = calculate_percentage_change(base_pm25, pep_pm25)

    # Create plots
    print("Creating plots...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Percentage Change: PEP vs Baseline Scenarios', fontsize=16, fontweight='bold')

    # Plot 1: Cost of electricity generation
    ax1 = axes[0, 0]
    ax1.plot(cost_pct_change.index, cost_pct_change.values,
             marker='o', linewidth=2, markersize=4, color='#2E86AB')
    ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax1.set_xlabel('Year', fontsize=12)
    ax1.set_ylabel('Percentage Change (%)', fontsize=12)
    ax1.set_title('Average Electricity Cost (USD/kWh)', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(cost_pct_change.index.min(), cost_pct_change.index.max())

    # Plot 2: Total Annualized Investments
    ax2 = axes[0, 1]
    ax2.plot(investments_pct_change.index, investments_pct_change.values,
             marker='s', linewidth=2, markersize=4, color='#A23B72')
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax2.set_xlabel('Year', fontsize=12)
    ax2.set_ylabel('Percentage Change (%)', fontsize=12)
    ax2.set_title('Total Annualized Investments (Million USD)', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(investments_pct_change.index.min(), investments_pct_change.index.max())

    # Plot 3: CO2e emissions
    ax3 = axes[1, 0]
    ax3.plot(co2e_pct_change.index, co2e_pct_change.values,
             marker='^', linewidth=2, markersize=4, color='#F18F01')
    ax3.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax3.set_xlabel('Year', fontsize=12)
    ax3.set_ylabel('Percentage Change (%)', fontsize=12)
    ax3.set_title('CO2e Emissions', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(co2e_pct_change.index.min(), co2e_pct_change.index.max())

    # Plot 4: PM2.5 emissions
    ax4 = axes[1, 1]
    ax4.plot(pm25_pct_change.index, pm25_pct_change.values,
             marker='d', linewidth=2, markersize=4, color='#6A994E')
    ax4.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax4.set_xlabel('Year', fontsize=12)
    ax4.set_ylabel('Percentage Change (%)', fontsize=12)
    ax4.set_title('PM2.5 Emissions', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(pm25_pct_change.index.min(), pm25_pct_change.index.max())

    plt.tight_layout()

    # Save the figure
    output_file = 'scenario_comparison_plots.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nPlots saved to: {output_file}")

    # Display summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    print("\n1. Average Electricity Cost:")
    print(f"   Mean % change: {cost_pct_change.mean():.2f}%")
    print(f"   Min % change: {cost_pct_change.min():.2f}% (Year {cost_pct_change.idxmin()})")
    print(f"   Max % change: {cost_pct_change.max():.2f}% (Year {cost_pct_change.idxmax()})")

    print("\n2. Total Annualized Investments:")
    print(f"   Mean % change: {investments_pct_change.mean():.2f}%")
    print(f"   Min % change: {investments_pct_change.min():.2f}% (Year {investments_pct_change.idxmin()})")
    print(f"   Max % change: {investments_pct_change.max():.2f}% (Year {investments_pct_change.idxmax()})")

    print("\n3. CO2e Emissions:")
    print(f"   Mean % change: {co2e_pct_change.mean():.2f}%")
    print(f"   Min % change: {co2e_pct_change.min():.2f}% (Year {co2e_pct_change.idxmin()})")
    print(f"   Max % change: {co2e_pct_change.max():.2f}% (Year {co2e_pct_change.idxmax()})")

    print("\n4. PM2.5 Emissions:")
    print(f"   Mean % change: {pm25_pct_change.mean():.2f}%")
    print(f"   Min % change: {pm25_pct_change.min():.2f}% (Year {pm25_pct_change.idxmin()})")
    print(f"   Max % change: {pm25_pct_change.max():.2f}% (Year {pm25_pct_change.idxmax()})")
    print("="*60)

    # Save data to CSV (using concat to handle different lengths)
    results_df = pd.concat([
        cost_pct_change.rename('Electricity_Cost_Pct_Change'),
        investments_pct_change.rename('Investments_Pct_Change'),
        co2e_pct_change.rename('CO2e_Pct_Change'),
        pm25_pct_change.rename('PM25_Pct_Change')
    ], axis=1)
    results_df.index.name = 'Year'

    csv_file = 'scenario_comparison_data.csv'
    results_df.to_csv(csv_file)
    print(f"\nData saved to: {csv_file}")

    return fig


if __name__ == "__main__":
    try:
        fig = create_plots()
        plt.show()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
