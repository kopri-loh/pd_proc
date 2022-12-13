from pathlib import Path

import pandas as pd
import numpy as np

import click


# Set-up local (and temporary) sys.path for import
# All scripts for calculations and plots need this
from context import add_path


add_path(Path(".").resolve())

try:
    import lib.io
    import lib.param
    from lib.conv import g_cov
except Exception:
    raise Exception("Issue with dynamic import")


# Ensure not to include commas (used as delimiter)
desc = """
Measurements from the Cloud Droplet Probe (CDP2) mounted at the Zeppelin 
Observatory in Ny-Alesund Svalbard.

The index is in seconds starting from 0 at the beginning of day.
The dataset consists of 10-minute averages from the probe. For NC and LWC
it includes both the raw output from the probe and the smooth time-series
obtained by convolution with a Gaussian kernel. We recommend the latter
for the sake of analysis and visualization.
Missing measurements are denoted by -1. The dataset has been filtered so
that all rows containing averaged values of LWC less than 1e-5 g/m3 were
suppressed to 0 in order to reduce noise.
The size distribution of the observed particles have been appended after
the cloud properties showing upper boundaries of the corresponding size
bin in diameter.

Dataset Created by Loren Oh (loh@kopri.re.kr)
Last modified on Dec 2022 \n
"""


def to_csv_desc(df, f_path, desc):
    with open(f_path, "w") as f:
        f.write(desc)
    df.to_csv(f_path, mode="a", index=False)

    print(f"--> {f_path}")


def process_cdp(df_cdp2, params):
    # Retrieve and consolidate CDP2 output files

    # Fix empty dataframe
    if len(df_cdp2) == 1:
        df_cdp2["End Seconds"] = np.arange(7, 86400, 10)

    dsm = df_cdp2["Dump Spot Monitor (V)"]

    # Basic filtering with a soft filter
    mask = (
        (dsm > 0.6)
        & (df_cdp2["Avg Transit Time"] < 150)
        & (df_cdp2["Avg Transit Time"] > 0.5)
        & (np.abs(np.gradient(g_cov(dsm))) < 1.5e-3)
    )

    # Adjust measured values based on passing air speed (PAS)
    adj_fac = df_cdp2["Applied PAS (m/s)"] / (150 / df_cdp2["Avg Transit Time"])

    # Take samples from the dataframe
    cdp2_vars = [
        "End Seconds",
        "Number Conc (#/cm^3)",
        "LWC (g/m^3)",
        "MVD (um)",
        "ED (um)",
        "PAS (m/s)"
    ]

    df = pd.DataFrame()
    for item in cdp2_vars:
        if item == "PAS (m/s)":
            df[item] = (150 / df_cdp2["Avg Transit Time"])

            continue
        else:
            _var = df_cdp2[item].copy(deep=True)

        if item == "End Seconds":
            df[item] = _var
            continue

        _var.loc[~mask] = np.nan
        if item in ["Number Conc (#/cm^3)", "LWC (g/m^3)"]:
            df[f"Raw {item}"] = _var * adj_fac
            df[item] = lib.conv.g_cov(_var * adj_fac)
        else:
            df[item] = lib.conv.g_cov(_var)

    # Append size distribution to Dataframe
    bins = params["Sizes"]

    bin_cols = [k for k in df_cdp2.columns if k.startswith('CDP Bin')]
    for i, col in enumerate(bin_cols):
        df.loc[:, f"{bins[i]} um"] = df_cdp2[col]

    # Replace unavailable values with -1
    df.loc[df.isnull().any(axis=1), df.columns[1:]] = -1

    # Filter rows with LWC < 1e-5 kg/m3
    mask = (df["LWC (g/m^3)"] < 1e-5) & (df["LWC (g/m^3)"] > 0)
    df.loc[mask, df.columns[1:]] = 0

    # Replace time with an integer array
    df["End Seconds"] = df["End Seconds"].to_numpy(dtype=int)

    return df


@click.command()
@click.argument("src_p", nargs=1)
@click.option(
    "-t",
    "--to",
    help="Path to (alternative) output directory."
)
def wrapper(src_p, to):
    """
    Post-processing script for CDP2 output files.

    SRC_P is the path to the CDP2 output directory (required).

    If no output directory path has been given with the "--to" option, the output file will be written in SRC_P along with original output files from CDP2. If multiple sub-directories exist below the designated path, the first directory with the csv files will be used.
    """
    if not (src_p := Path(src_p)).is_dir():
        raise ValueError("Not a valid CDP2 output directory path")

    # Look for csv files from directory path
    csv_list = sorted(Path(src_p).rglob("*.csv"))

    df_cdp2 = lib.io.read_cdp(csv_list)

    if len(df_cdp2) == 0:
        print("No record found")
        return

    params = lib.param.get_params(csv_list)

    df = process_cdp(df_cdp2, params)

    # Output options
    if to is None:
        dst_p = csv_list[0].parent
    else:
        if not (to := Path(to)).is_dir():
            raise ValueError("Not a valid CDP2 output directory path")
        dst_p = to

    # Write 10-second dataset
    print("Writing post-processed CSV output files...")
    to_csv_desc(df, f"{dst_p}/CDP2_{src_p.name}.csv", desc)

    # Further process the output dataset for 10-minute version
    df.loc[df["LWC (g/m^3)"] < 0, df.columns[1:]] = np.nan
    df_10min = df[df.columns[1:]].rolling(60, min_periods=1).mean()
    df_10min.insert(0, column="End Seconds", value=df["End Seconds"])
    df_10min.loc[
        (~np.isfinite(df_10min["LWC (g/m^3)"])), df_10min.columns[1:]
    ] = -1

    # Take samples at 10-minute-period
    df_10min = df_10min.iloc[::60]

    # Write 10-minute dataset
    to_csv_desc(df_10min, f"{dst_p}/10MIN_CDP2_{src_p.name}.csv", desc)


if __name__ == "__main__":
    wrapper()
