from glob import glob
import pandas as pd
import re
import os

# ----------
# Parameters
# ----------

# For conversions to/from Julian days
TIME_ORIGIN = pd.Timestamp('2000-01-01T00:00:00')

# Drift correction thresholds
THRESHOLDS = {
    'temperature' : 0.01,       # (degrees Celsius)
    'salinity': 0.05,           # (Practical salinity units)
    'conductivity': 0.009,      # (Siemens / meter)
    'depth': 1.0                # (meters)
}

# Standardize cnv data to these units (as understood by the `pint` module)
UNITS = {
    'temperature': 'degree_Celsius',
    'salinity': 'practical_salinity_unit',
    'depth': 'meter',
    'pressure': 'decibar',
    'conductivity': 'siemens / meter',
    'flag': ''
}

# --------------------
# File path management
# --------------------

TOP = r'S:\Soutien technique DAISS\PPMT'
UNPROCESSED_PPMT_DIR = r'%s\Donnees\non traite' % TOP
UNPROCESSED_MOORING_DIR = r'%s\Donnees\Mouillage\non traite' % TOP

# Working on LAN (local; fast) or through VPN (remote; slow)
LOCAL = False

if LOCAL:

    # Make a list of the unprocessed PPMT files
    UNPROCESSED = [*glob(r'%s\*.csv' % UNPROCESSED_PPMT_DIR),
                   *glob(r'%s\*.cnv' % UNPROCESSED_PPMT_DIR),
                   *glob(r'%s\*.csv' % UNPROCESSED_MOORING_DIR),
                   *glob(r'%s\*.cnv' % UNPROCESSED_MOORING_DIR)]

    # Make a list of the calibration files
    CALFILES = [*glob(r'S:\Etalon\Équipement Océanographique\Seabird\SBE-37\*\*\*.xls'),
                *glob(r'S:\Etalon\Équipement Océanographique\Seabird\SBE-37\*\*\*\*.xls'),
                *glob(r'S:\Etalon\Équipement Océanographique\Seabird\SBE-56\*\*.xls')]

    # Make local copies of the files for when working on this project remotely
    for F in UNPROCESSED:
        os.system(f'copy "{F}" {os.getcwd()}\\local\\unprocessed\\')
    for F in CALFILES:
        os.system(f'copy "{F}" {os.getcwd()}\\local\\calfiles\\')

else:

    # Read local copies
    UNPROCESSED = [*glob(f'{os.getcwd()}\\local\\unprocessed\\*.csv'),
                   *glob(f'{os.getcwd()}\\local\\unprocessed\\*.cnv')]
    CALFILES = glob(f'{os.getcwd()}\\local\\calfiles\\*.xls')


def extract_serial(filename):
    """ get serial number from Calibration file name """
    return int(re.findall('[ _]([0-9]+)[ _]', filename)[0])


# Make a lookup table linking calibration files and device serial numbers
CALFILES_LOOKUP = pd.DataFrame(CALFILES, columns=['fullpath'])
CALFILES_LOOKUP.loc[:, 'basename'] = CALFILES_LOOKUP['fullpath'].apply(os.path.basename)
CALFILES_LOOKUP.loc[:, 'serial'] = CALFILES_LOOKUP['basename'].apply(extract_serial)