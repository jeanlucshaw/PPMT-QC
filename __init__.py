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

TOP = os.path.join('S:', u'Soutien technique DAISS', 'PPMT')
UNPROCESSED_PPMT_DIR = os.path.join(TOP, 'Donnees', u'non traite')
UNPROCESSED_MOORING_DIR = os.path.join(TOP, 'Donnees', 'Mouillage', u'non traite')
SEABIRD_DIR = os.path.join('S:', 'Etalon', u'\311quipement Oc\351anographique', 'Seabird')
INSTALL_DIR = os.path.dirname(__file__)

# Working on LAN (local; fast) or through VPN (remote; slow)
LOCAL = False

if LOCAL:

    # Make a list of the unprocessed PPMT files
    UNPROCESSED = [*glob(os.path.join(UNPROCESSED_PPMT_DIR, '*.csv')),
                   *glob(os.path.join(UNPROCESSED_PPMT_DIR, '*.cnv')),
                   *glob(os.path.join(UNPROCESSED_MOORING_DIR, '*.csv')),
                   *glob(os.path.join(UNPROCESSED_MOORING_DIR, '*.cnv'))]

    # Make a list of the calibration files
    CALFILES = [*glob(os.path.join(SEABIRD_DIR, 'SBE-56', '*', '*.xls')),
                *glob(os.path.join(SEABIRD_DIR, 'SBE-37', 'V1', '*', '*.xls')),
                *glob(os.path.join(SEABIRD_DIR, 'SBE-37', 'V1', '*', '*', '*.xls')),
                *glob(os.path.join(SEABIRD_DIR, 'SBE-37', 'V2', '*', '*.xls')),
                *glob(os.path.join(SEABIRD_DIR, 'SBE-37', 'V2', '*', '*', '*.xls'))]

    # Make local copies of the files for when working on this project remotely
    for F in UNPROCESSED:
        os.system(f'copy "{F}" "{os.path.join(INSTALL_DIR, "local", "unprocessed")}"')

    for F in CALFILES:
        os.system(f'copy "{F}" "{os.path.join(INSTALL_DIR, "local", "calfiles")}"')

else:

    # Read local copies
    UNPROCESSED = [*glob(f'{os.path.join(INSTALL_DIR, "local", "unprocessed", "*.csv")}'),
                   *glob(f'{os.path.join(INSTALL_DIR, "local", "unprocessed", "*.cnv")}')]
    CALFILES = glob(f'{os.path.join(INSTALL_DIR, "local", "calfiles", "*.xls")}')


def extract_serial(filename):
    """ get serial number from Calibration file name """
    return str(re.findall('[ _]([0-9]+)[ _]', filename)[0])  # must be a string: some serials start with zero


# Make a lookup table linking calibration files and device serial numbers
CALFILES_LOOKUP = pd.DataFrame(CALFILES, columns=['fullpath'])
CALFILES_LOOKUP.loc[:, 'basename'] = CALFILES_LOOKUP['fullpath'].apply(os.path.basename)
CALFILES_LOOKUP.loc[:, 'serial'] = CALFILES_LOOKUP['basename'].apply(extract_serial)
