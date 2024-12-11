import gsw
import re
import numpy as np
from __init__ import UNITS
from reader import *
from pint import UnitRegistry
ureg = UnitRegistry()
ureg.define('practical_salinity_unit = [] = psu')


def manage_file_type(data, metadata):
    """
    Standardize the data format given data and metadata

    Parameters
    ----------
    data : pandas.DataFrame
        columns of the data file obtained from [`read_csv`, `read_cnv`]
    metadata : dict
        header information obtained from [`read_csv`, `read_cnv_metadata`]

    Returns
    -------
    standard_data : pandas.DataFrame
        Columns [datetime, depth, temperature, salinity, conductivity, sigma_t] and
        missing values when these columns cannot be obtained.
    standard_header : dict
        combining information from the data headers and the `suivi` file.

    """
    # Initialize data source dictionary: ['observation', 'metadata', 'teos10', None]
    data_source = {'temperature': None,
                   'salinity': None,
                   'conductivity': None,
                   'depth': None,
                   'pressure': None}

    # Get serial number
    serial, = [v for k, v in metadata.items() if re.match('[Ss]erial', k)]

    # Get start year
    year = data.loc[0, 'time'].year

    # Get `suivi` information
    suivi = get_device_suivi_metadata(serial, year)

    # Figure out what is there or not
    includes = dict()
    includes['depth'] = 'depth' in data.keys()
    includes['pressure'] = 'pressure' in data.keys()
    includes['temperature'] = 'temperature' in data.keys()
    includes['conductivity'] = 'conductivity' in data.keys()
    includes['salinity'] = 'salinity' in data.keys()
    includes['sigma_t'] = 'sigma_t' in data.keys()

    # Update data source dictionary
    for key, value in includes.items():
        if value:
            data_source[key] = 'observation'

    # -------------------
    # Add missing columns
    # -------------------

    # Depth
    if not includes['depth']:
        if includes['pressure']:
            data.loc[:, 'depth'] = gsw.z_from_p(-1 * data['pressure'], 48)
            includes['depth'] = True
            data_source['depth'] = 'teos10'
            data_source['pressure'] = 'observation'
        elif 'instrument_depth' in suivi.keys():
            data.loc[:, 'depth'] = suivi['instrument_depth']
            includes['depth'] = True
            data_source['depth'] = 'metadata'
        else:
            data.loc[:, 'depth'] = np.nan

    # Pressure
    if not includes['pressure']:
        if includes['depth']:
            data.loc[:, 'pressure'] = gsw.p_from_z(-1 * data['depth'], 48)
            includes['pressure'] = True
            data_source['pressure'] = 'teos10'
            data_source['depth'] = 'observation'
        else:
            data.loc[:, 'pressure'] = np.nan

    # Conductivity (mS / cm)
    if not includes['conductivity']:
        if includes['salinity'] and includes['pressure']:
            data.loc[:, 'conductivity'] = gsw.C_from_SP(data['salinity'], data['temperature'], data['pressure'])
            includes['conductivity'] = True
            data_source['conductivity'] = 'teos10'
            data_source['salinity'] = 'observation'
        else:
            data.loc[:, 'conductivity'] = np.nan

    # Salinity (assumes conductivity units of [mS / cm])
    if not includes['salinity'] and includes['pressure']:
        if includes['conductivity']:
            data.loc[:, 'salinity'] = gsw.SP_from_C(data['conductivity'], data['temperature'], data['pressure'])
            includes['salinity'] = True
            data_source['conductivity'] = 'observation'
            data_source['salinity'] = 'teos10'
        else:
            data.loc[:, 'salinity'] = np.nan

    # Sigma t
    required = ['temperature', 'salinity', 'pressure']
    if not includes['sigma_t'] and all([includes[v] for v in required]):

        clean_salinity = data.salinity.copy()
        clean_salinity.loc[data.salinity > 50] = 0
        clean_salinity.loc[data.salinity < 0] = 0
        SA = gsw.SA_from_SP(clean_salinity, data.pressure, -62, 48)
        CT = gsw.CT_from_t(SA, data.temperature, data.pressure)
        data.loc[:, 'sigma_t'] = gsw.sigma0(SA, CT)
        includes['sigma_t'] = True
        data_source['sigma_t'] = 'teos10'
    else:
        data.loc[:, 'sigma_t'] = np.nan

    # ----------------------------------------------------------
    # Create standard header from `suivi` and data file metadata
    # ----------------------------------------------------------
    standard_header = suivi.copy()

    # Instrument header
    standard_header['device_serial'] = int(serial[3:])
    if 'interval' in metadata:
        standard_header['interval'] = int(metadata['interval'])
    else:
        interval = int(data.time.diff().median().seconds)
        standard_header['interval'] = np.round(interval, decimals=-1)
    standard_header['instrument_type'] = 'Seabird'  # no longer any other types
    if serial[:3] == '056':
        standard_header['instrument_model'] = 'SBE56'
    elif serial[:3] == '037':
        if len(serial) == 8 or serial[3:] == '4676':
            version = 'V.2'
        else:
            version = 'V.1'
        standard_header['instrument_model'] = f'SBE37 {version}'

    # Global attributes
    standard_header['deployment_year'] = year
    standard_header['SBE'] = int(serial[:3])
    standard_header['data_source'] = data_source

    # Calibration status
    mli_calibration = {year: probe_calfile(standard_header['device_serial'], year),
                       year - 1: probe_calfile(standard_header['device_serial'], year - 1),
                       year - 2: probe_calfile(standard_header['device_serial'], year - 2)}
    standard_header['mli_calibration'] = mli_calibration

    return data, standard_header


def manage_cnv_units(data, header):
    """
    Ensure cnv data is always in the same units.

    Parameters
    ----------
    data : pandas.DataFrame
        data output of `reader.read_cnv_data`
    header : dict
        metadata output of `reader.read_cnv_metadata`

    Returns
    -------
    data : pandas.DataFrame
        with variables converted as specified in `__init__.py`

    """
    for n_, u_ in zip(header['names'], header['units']):
        if 'time' not in n_:
            if 'julian' in u_:
                u_ = 'days'
            variable = ureg.Quantity(data[n_].values, ureg.parse_expression(u_))
            data[n_] = variable.to(UNITS[n_]).magnitude

    return data

# for f in UNPROCESSED:
#     print(f)
#     _, ext = os.path.splitext(f)
#
#     if ext == '.csv':
#         metadata, data = read_csv(f)
#     elif ext == '.cnv':
#         metadata = read_cnv_metadata(f)
#         data = read_cnv(f)
#
#     data, ssh = manage_file_type(data, metadata)


