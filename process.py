import os.path
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import xarray as xr
from __init__ import UNPROCESSED, CALFILES, CALFILES_LOOKUP, TIME_ORIGIN
from input import manage_file_type
from output import init_output
from reader import *
from drift import *


filename = UNPROCESSED[-2]
cf = r'C:\\Users\\SHAWJE\\Desktop\\home\\PPMT\\local\\calfiles\\Vérification sbe37SMP_ODO_15609_jan_2021.xls'

# -------------------------------
# Read data file and its metadata
# -------------------------------

# Read data file
_, ext = os.path.splitext(filename)
if ext == '.csv':
    header, data = read_csv(filename)
elif ext == '.cnv':
    header = read_cnv_metadata(filename)
    data = read_cnv(filename)
else:
    print('Unknown file format', ext)

# Funnel to uniform file format
data, header = manage_file_type(data, header)

# Clip times before and after the recovery date
start_date = str(header['trip_installation_real_date'])
end_date = str(header['trip_recovery_real_date'])
data = data.query(f'"{start_date}" < time < "{end_date}"')

# Get the calibrations for this device
calibration_data = get_calibration_data(header)

# ----------------
# Drift correction
# ----------------

# Loop over observed variables
for variable, source in header['data_source'].items():

    # This variable has calibration data
    if variable in calibration_data.keys():

        # Interpolate the calibration data -> deviation(time, variable)
        deviation = interpolate_deviation(calibration_data[variable],
                                          data,
                                          variable)

        # Add deviation to the data frame
        data[f'{variable}_deviation'] = deviation

        # Determine if drift correction must be applied

        # Apply drift correction

        # Save drift correction decision in metadata