import pandas as pd
import re

# Read name/unit database
seabird_names = pd.read_csv('data/seabird_names.csv')


def seabird_name_to_unit(seabird_name):
    """
    Get a string representing the units of this seabird variable.

    Parameters
    ----------
    seabird_name : str
        as printed in the cnv file

    Returns
    -------
    unit : str
        the corresponding units (SI).

    """
    for i_, e_ in enumerate(seabird_names.expression):
        unit = ''
        if re.match(e_, seabird_name):
            unit = seabird_names.iloc[i_, :].units
            break
    return unit


