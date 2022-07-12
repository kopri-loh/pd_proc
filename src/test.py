from pathlib import Path
from pyexpat import ExpatError

import numpy as np
import click


# Set-up local (and temporary) sys.path for import
# All scripts for calculations and plots need this
from context import add_path


add_path(Path(".").resolve())

try:
    from cdp2_post import process_cdp as proc
except Exception:
    raise Exception("Issue with dynamic import")


@click.command()
@click.argument("cdp2_path")
def test(cdp2_path):
    if ~Path(cdp2_path).is_dir():
        raise ValueError("Not a valid CDP2 output directory path")

    df = proc(cdp2_path)
    src_path = Path("/home/loh/Storage/CDP2")
    # Path to CDP2 dataset
    cdp_target = sorted(src_path.glob("201910*"))[1]

    df = proc(cdp_target)

    # Further process the output dataset for 10-minute version
    df.loc[df["LWC (g/m^3)"] < 0, df.columns[1:]] = np.nan
    df_10min = df[df.columns[1:]].rolling(60, min_periods=1).mean()
    df_10min.insert(0, column="End Seconds", value=df["End Seconds"])
    df_10min.loc[
        (~np.isfinite(df_10min["LWC (g/m^3)"])), df_10min.columns[1:]
    ] = -1

    # Take samples at 10-minute-period
    df_10min = df_10min.iloc[::60]

    print(df_10min.head())


if __name__ == "__main__":
    test()
