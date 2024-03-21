import pandas as pd
import numpy as np
import re

from pathlib import Path


def get_buf(buf):
    params = {}

    for _, x in enumerate(buf[1:25]):
        key, val = x.rstrip().split("=")

        if key in ["Sizes", "Thresholds"]:
            val = np.fromstring(re.sub("<[0-9]+>", "", val), dtype=np.int64, sep=",")

        params[key] = val

    return params


def _append(item, df, skiprows):
    _df = pd.read_csv(item, skiprows=skiprows)

    if len(_df) > 1:
        _df = pd.concat([_df, df], ignore_index=True)

    with open(item) as f:
        params = get_buf(f.readlines())

    return _df, params


def read_cdp2(csv_list):
    df_cdp2 = pd.DataFrame()
    for item in csv_list:
        item = Path(item)

        if re.search(r"(\w+\s*)CDP(\d+\s*).csv", item.name) is not None:
            df_cdp2, params = _append(item, df_cdp2, skiprows=58)
        elif re.search(r"(\w+\s*)CDP PBP(\d+\s*).csv", item.name) is not None:
            df_cdp2, params = _append(item, df_cdp2, skiprows=60)
        else:
            pass

    return df_cdp2, params


def read_bcpd(csv_list):
    df_bcpd = pd.DataFrame()
    df_pbp = pd.DataFrame()

    for item in csv_list:
        item = Path(item)

        if re.search(r"(\w+\s*)PbP(\s*\w+)", item.name) is not None:
            _df = pd.read_csv(item, skiprows=9)

            if len(_df) > 1:
                df_pbp = pd.concat([df_pbp, _df], ignore_index=True)
        elif re.search(r"(\w+\s*)Beta(\s*\w+)", item.name) is not None:
            df_bcpd, params = _append(item, df_bcpd, skiprows=88)
        else:
            pass

    return df_pbp, df_bcpd, params


def to_csv_desc(df, f_path, desc):
    with open(f_path, "w") as f:
        f.write(desc)
    df.to_csv(f_path, mode="a", index=False)

    print(f"\t--> {f_path}")
