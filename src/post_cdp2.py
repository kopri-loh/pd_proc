import pandas as pd
import numpy as np

from pathlib import Path
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

The index is in seconds from the beginning of day.
This script will produce two sets of CSV files consisting of 10-second
and 10-minute averages from the probe. For NC and LWC it includes both
the raw output from the probe and the smooth time-series obtained by
convolution with a Gaussian kernel. We recommend the latter for the
sake of analysis and visualization.
Missing or faulty measurements have been replaced by -1.
The size distribution of the observed particles have been appended after
the cloud properties showing upper boundaries of the corresponding size
bin in diameter.

Dataset Created by Loren Oh
Last modified on March 2024 \n
"""


def process(df_cdp2, params):
    # Retrieve and consolidate CDP2 output files

    # Fix empty dataframe
    if len(df_cdp2) <= 1:
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
    vars = [
        "End Seconds",
        "Number Conc (#/cm^3)",
        "LWC (g/m^3)",
        "MVD (um)",
        "ED (um)",
        "PAS (m/s)",
    ]

    df = pd.DataFrame()
    for item in vars:
        if item == "PAS (m/s)":
            df[item] = 150 / df_cdp2["Avg Transit Time"]

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

    bin_cols = [k for k in df_cdp2.columns if k.startswith("CDP Bin")]
    for i, col in enumerate(bin_cols):
        df.loc[:, f"{bins[i]} um"] = df_cdp2[col]

    # Replace unavailable values with -1
    df.loc[df.isnull().any(axis=1), df.columns[1:]] = -1

    # Replace time with an integer array
    df["End Seconds"] = df["End Seconds"].to_numpy(dtype=int)

    return df


def post_cdp2(src_p, to):
    # Look for csv files from directory path
    csv_list = sorted(Path(src_p).rglob("*.csv"))
    df_cdp2, params = lib.io.read_cdp2(csv_list)

    if len(df_cdp2) == 0:
        print("No CDP2 record found\n")
        return

    df = process(df_cdp2, params)

    # Output options
    if to is None:
        dst_p = csv_list[0].parent
    else:
        if not (to := Path(to)).is_dir():
            raise ValueError("Invalid CDP2 directory path")
        dst_p = to

    # Write 10-second dataset
    print("Writing post-processed CSV output files...")
    lib.io.to_csv_desc(df, f"{dst_p}/CDP2_{src_p.name}.csv", desc)

    # Further process the output dataset for 10-minute version
    df.loc[df["LWC (g/m^3)"] < 0, df.columns[1:]] = np.nan
    df_10min = df[df.columns[1:]].rolling(60, min_periods=1).mean()
    df_10min.insert(0, column="End Seconds", value=df["End Seconds"])
    df_10min.loc[(~np.isfinite(df_10min["LWC (g/m^3)"])), df_10min.columns[1:]] = -1

    # Take samples at 10-minute-period
    df_10min = df_10min.iloc[::60]

    # Write 10-minute dataset
    lib.io.to_csv_desc(df_10min, f"{dst_p}/10MIN_CDP2_{src_p.name}.csv", desc)

    print("")
