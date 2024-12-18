import os.path
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import xarray as xr
from __init__ import UNPROCESSED
from input import *
from visualize import plot_processed
from output import init_output
from reader import *
from drift import *

filename = r'C:\Users\SHAWJE\Desktop\home\PPMT\local\unprocessed\SBE05606943_2024-11-19_SHEDIAC.csv'
# filename = r'C:\Users\SHAWJE\Desktop\home\PPMT\local\unprocessed\Q22SHEZ2.csv'



filename = UNPROCESSED[-1] # Serial must be a string because the first digit can be zero
# cf = r'C:\\Users\\SHAWJE\\Desktop\\home\\PPMT\\local\\calfiles\\Vérification sbe37SMP_ODO_15609_jan_2021.xls'


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
    data = manage_cnv_units(data, header)
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

# Drift correction
data, header = manage_drift_correction(data, header, calibration_data)

# -------------
# Visualization
# -------------

# --- Variable time series ---
if 'temperature' in header['drift_correction'].keys():  # most likely always true
    plot_processed(data, header, 'temperature')
if 'salinity' in header['drift_correction'].keys():     # not always true
    plot_processed(data, header, 'salinity')

# -----------
# Apply flags
# -----------

# ------
# Output
# ------