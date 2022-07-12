import pandas as pd
import re

from pathlib import Path


def read_cdp(csv_list):
    df_cdp2 = pd.DataFrame()
    for item in csv_list:
        item = Path(item)

        if re.search("(\w+\s*)CDP(\s*\w+)", item.name) is not None:
            _df = pd.read_csv(item, skiprows=58)
            df_cdp2 = pd.concat([df_cdp2, _df], ignore_index=True)
        else:
            pass

    return df_cdp2


def read_fm(csv_list):
    pass
