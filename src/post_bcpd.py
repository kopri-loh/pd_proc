import pandas as pd
import numpy as np

from pathlib import Path
from context import add_path


add_path(Path(".").resolve())

try:
    import lib.io
    import lib.param
except Exception:
    raise Exception("Issue with dynamic import")


# Ensure not to include commas (used as delimiter)
desc = """
Measurements from the Back-scatter Cloud Probe with Polarization Detection
(BCPD) mounted at the Zeppelin Observatory in Ny-Alesund Svalbard.

The index is in seconds starting from the beginning of day.
This script will produce two sets of CSV files consisting of 10-second
and 10-minute averages from the probe.
Missing or faulty measurements have been replaced by -1.
The size distribution of the observed particles have been appended after
the cloud properties showing upper boundaries of the corresponding size
bin in diameter.

Dataset Created by Loren Oh
Last modified on March 2024 \n
"""


thresholds = np.zeros((20))
bins = np.zeros((20))
m_bins = np.zeros((20))

# Size of the sampling region
sample_area = 0.342 / 1e6  # [m^2]


def calc_LWC(grp):
    p_sig = np.nansum((grp["S Peak"], grp["P Peak"]), axis=0)
    pas = calc_PAS(grp)

    lwc = 0
    for i, _ in enumerate(thresholds[0:-2]):
        b_mask = (p_sig >= thresholds[i]) & (p_sig <= thresholds[i + 1])

        if np.nansum(b_mask) == 0:
            continue

        # Re-define sample volume with laser width and true PAS
        sample_vol = pas * sample_area  # [m^3]

        c_i = np.nansum(b_mask) / sample_vol  # [#/m^3]

        lwc_i = c_i * np.pi / 6 * m_bins[i] ** 3 * 1e-12  # [g/m^3]
        lwc = np.nansum((lwc, lwc_i))

    return lwc


def calc_NC(grp):
    p_sig = np.nansum((grp["S Peak"], grp["P Peak"]), axis=0)
    pas = calc_PAS(grp)

    # Count all qualifying signals
    b_mask = (p_sig > thresholds[0]) & (p_sig <= thresholds[-1])

    sample_vol = pas * sample_area  # [m^3]

    return np.nansum(b_mask) / sample_vol / 10**6  # [#/cm^3]


def calc_MVD(grp):
    # I could probably avoid redundant calculations, but unfortunately I am not getting paid for this
    if (lwc := calc_LWC(grp)) == 0:
        return 0

    p_sig = np.nansum((grp["S Peak"], grp["P Peak"]), axis=0)
    pas = calc_PAS(grp)

    cum = 0
    for i, _ in enumerate(thresholds[0:-2]):
        b_mask = (p_sig >= thresholds[i]) & (p_sig <= thresholds[i + 1])

        if np.nansum(b_mask) == 0:
            continue

        pro_i = 0

        sample_vol = pas * sample_area  # [m^3]

        c_i = np.nansum(b_mask) / sample_vol  # [#/m^3]
        lwc_i = c_i * np.pi / 6 * m_bins[i] ** 3 * 1e-12  # [g/m^3]
        pro_i = lwc_i / lwc

        if (cum := np.nansum((cum, pro_i))) >= 0.5:
            mvd = bins[i] + ((0.5 - cum) / pro_i) * (bins[i + 1] - bins[i])

            return mvd
    return np.nan


def calc_ED(grp):
    p_sig = np.nansum((grp["S Peak"], grp["P Peak"]), axis=0)

    _t, _b = 0, 0
    for i, _ in enumerate(thresholds[0:-2]):
        b_mask = (p_sig >= thresholds[i]) & (p_sig <= thresholds[i + 1])

        if (c_i := np.nansum(b_mask)) == 0:
            continue

        r_i = 0.5 * m_bins[i]  # Radius as 1/2 bin midpoint # [um]

        _t = _t + (c_i * r_i**3)
        _b = _b + (c_i * r_i**2)

    if _b == 0:
        return 0
    else:
        return 2 * (_t / _b)


def calc_PAS(grp):
    p_sig = np.nansum((grp["S Peak"], grp["P Peak"]), axis=0)

    # Re-calculate sampling volume based on S&P transit times
    # Transit times are always in units of 25 ns
    s_time = grp["S Transit Time"] * 25  # [ns]
    p_time = grp["P Transit Time"] * 25  # [ns]

    t_sig = np.nansum((s_time, p_time), axis=0)

    # Count all qualifying signals
    b_mask = (p_sig > thresholds[0]) & (p_sig <= thresholds[-1])

    if (_tt := np.nanmean(t_sig[b_mask])) > 0:
        return 50 / _tt * 1e3  # [/s]
    else:
        return np.nan


def process(df, df_bcpd, params):
    # Retrieve and consolidate BCPD output files

    # Fix empty dataframe
    if len(df) <= 1:
        df["End Seconds"] = np.arange(7, 86400, 10)

    # Take samples from the dataframe
    vars = [
        "End Seconds",
        "Number Conc (#/cm^3)",
        "LWC (g/m^3)",
        "MVD (um)",
        "ED (um)",
        "PAS (m/s)",
    ]

    # Filter particles based on S and P transit times
    # Use relative tolerance of 25%
    s_time = df["S Transit Time"] * 25
    p_time = df["P Transit Time"] * 25

    mask = np.isclose(p_time, s_time, rtol=0.25, atol=0)
    mask = mask | np.isclose(s_time, p_time, rtol=0.25, atol=0)

    df.drop(df[~mask].index, inplace=True)
    df.reset_index(inplace=True, drop=True)

    # Signal thresholds
    global thresholds
    thresholds = np.concatenate(([0], params["Thresholds"]))

    # Bin midpoints
    global bins, m_bins
    bins = params["Sizes"]
    m_bins = (bins[1:] + bins[:-1]) / 2  # [um]

    ## Groupby-apply
    groups = df.groupby(df["PADS Time"])

    # LWC
    _df = groups.apply(calc_LWC).reset_index(name="LWC (g/m^3)")

    # NC
    _df = pd.merge(
        _df,
        groups.apply(calc_NC).reset_index(name="Number Conc (#/cm^3)"),
        on="PADS Time",
    )

    # ED
    _df = pd.merge(
        _df, groups.apply(calc_ED).reset_index(name="ED (um)"), on="PADS Time"
    )

    # MVD
    _df = pd.merge(
        _df, groups.apply(calc_MVD).reset_index(name="MVD (um)"), on="PADS Time"
    )

    # PAS
    _df = pd.merge(
        _df, groups.apply(calc_PAS).reset_index(name="PAS (m/s)"), on="PADS Time"
    )

    # Append size distribution to Dataframe
    bin_cols = [k for k in df_bcpd.columns if k.startswith("BCPD Beta Bin")]
    for i, col in enumerate(bin_cols):
        _df.loc[:, f"{bins[i]} um"] = df_bcpd[col]

    # Replace unavailable values with -1
    _df.loc[_df.isnull().any(axis=1), _df.columns[1:]] = -1

    # Replace time with an integer array
    _df = _df.rename(columns={"PADS Time": "End Seconds"})
    _df["End Seconds"] = _df["End Seconds"].astype(dtype=int)

    return _df


def post_bcpd(src_p, to):
    # Look for csv files from directory path
    csv_list = sorted(Path(src_p).rglob("*.csv"))
    df_pbp, df_bcpd, par_bcpd = lib.io.read_bcpd(csv_list)

    if len(df_pbp) == 0:
        print("No BCPD record found\n")
        return

    df = process(df_pbp, df_bcpd, par_bcpd)

    # Output options
    if to is None:
        dst_p = csv_list[0].parent
    else:
        if not (to := Path(to)).is_dir():
            raise ValueError("Invalid BCPD directory path")
        dst_p = to

    # Write 10-second dataset
    print("Writing post-processed CSV output files...")
    lib.io.to_csv_desc(df, f"{dst_p}/BCPD_{src_p.name}.csv", desc)

    # Further process the output dataset for 10-minute version
    df.loc[df["LWC (g/m^3)"] < 0, df.columns[1:]] = np.nan
    df_10min = df[df.columns[1:]].rolling(60, min_periods=1).mean()
    df_10min.insert(0, column="End Seconds", value=df["End Seconds"])
    df_10min.loc[(~np.isfinite(df_10min["LWC (g/m^3)"])), df_10min.columns[1:]] = -1

    # Take samples at 10-minute-period
    df_10min = df_10min.iloc[::60]

    # Write 10-minute dataset
    lib.io.to_csv_desc(df_10min, f"{dst_p}/10MIN_BCPD_{src_p.name}.csv", desc)

    print("")
