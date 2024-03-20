import click

from pathlib import Path
from context import add_path


add_path(Path(".").resolve())

try:
    from post_cdp2 import post_cdp2
    from post_bcpd import post_bcpd
except Exception:
    raise Exception("Issue with dynamic import")


@click.command()
@click.argument("src_p", nargs=1)
@click.option("-t", "--to", help="Path to (alternative) output directory.")
def wrapper(src_p, to):
    """
    Post-processing script for CDP2 and BCPD output files.

    SRC_P is the path to the CDP2/BCPD output directory (required).

    If no output directory path has been given with the "--to" option, the output file will be written in SRC_P along with original output files. If multiple sub-directories exist below the designated path, the first directory with the csv files will be used.
    """
    if not (src_p := Path(src_p)).is_dir():
        raise ValueError("Not a valid CDP2/BCPD output directory path")

    ## Process CDP2
    post_cdp2(src_p, to)

    ## Process BCPD
    post_bcpd(src_p, to)


if __name__ == "__main__":
    wrapper()
