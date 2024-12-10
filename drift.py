from __init__ import TIME_ORIGIN
from scipy.interpolate import LinearNDInterpolator as LNDI
from reader import read_calfile
import pandas as pd

# -------
# Helpers
# -------


def numeric2timestamp(numeric):
    """ decimal days since Jan 1, 2000 to timestamp """
    return TIME_ORIGIN + pd.to_timedelta(numeric, 'd')


def timestamp2numeric(timestamp):
    """ timestamp to decimal days since Jan 1, 2000 """
    if isinstance(timestamp, pd.Timestamp):
        numeric = (timestamp - TIME_ORIGIN).total_seconds() / 24 / 3600
    elif isinstance(timestamp, pd.Series):
        timestamp = pd.Series(timestamp)
        numeric = (timestamp - TIME_ORIGIN).apply(lambda x: x.total_seconds() / 24 / 3600)
    else:
        raise TypeError('timestamp2numeric requires input be type: [pd.Timestamp, pd.Series]')
    return numeric


# ---------
# Functions
# ---------


def get_calibration_data(header):
    """
    Get the best available calibration data for this device

    Parameters
    ----------
    header : dict
        output of `input.manage_file_types`

    Returns
    -------
    calibration_data : dict
        containing a `pandas.DataFrame` for each observed variable.

    """
    # Init the calibration data dictionary
    calibration_data = dict()

    # Loop over observed variables
    for variable, source in header['data_source'].items():
        if source == 'observation':
            calibrations = get_calibration_data_setup(variable, header)

            # Check that appropriate calibration data are available
            if calibrations['ok']:
                # Pre deployment calibration
                df_pre = read_calfile(header['device_serial'],
                                      variable=calibrations['pre'][0],
                                      sheet=calibrations['pre'][1])

                # Post deployment calibration
                df_post = read_calfile(header['device_serial'],
                                       variable=calibrations['post'][0],
                                       sheet=calibrations['post'][1])

                # Stack the pre and post data into a single dataframe and save
                calibration_data[variable] = pd.concat((df_pre, df_post))

    return calibration_data


def get_calibration_data_setup(variable, header):
    """
    Determine which (raw/clean) calibration and year combination to correct drift on variable

    Parameters
    ----------
    variable : str
        one of `temperature`, `salinity`, `conductivity`, `depth`
    header : dict
        output of `input.manage_file_types`

    Returns
    -------
    calibrations : dict
        with the input values to supply `reader.read_calfile` at the `sheet` and `variable` arguments
        to get the recommended calibrations for pre and post-deployment.

    """
    # For readability
    year = header['deployment_year']

    # ------------------------------------------------------------------
    # Temperature and depth are together because they have simpler logic
    # ------------------------------------------------------------------
    if variable in ['temperature', 'depth']:
        # Post deployment calibration exists
        if header['mli_calibration'][year][f'{variable}_calibration']:
            """ post deployment exist """
            # Pre deployment calibration exists (one year back)
            if header['mli_calibration'][year - 1][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 1), 'post': (variable, year)}
            # Pre deployment calibration exists (two years back)
            elif header['mli_calibration'][year - 2][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 2), 'post': (variable, year)}
            # Pre deployment calibration does not exists
            else:
                calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

        # Post deployment calibration exists
        else:
            calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

    # --------------------------------------------------------------------------------
    # Salinity and conductivity are separate because of the clean/raw added complexity
    # --------------------------------------------------------------------------------
    elif variable in ['salinity', 'conductivity']:
        # Post deployment calibration exists
        if header['mli_calibration'][year][f'{variable}_raw_calibration']:
            # Pre deployment calibration exists (one year back; clean)
            if header['mli_calibration'][year - 1][f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year - 1), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration exists (one year back; raw)
            elif header['mli_calibration'][year - 1][f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year - 1), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration exists (two years back; clean)
            elif header['mli_calibration'][year - 2][f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year - 2), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration exists (two years back; raw)
            elif header['mli_calibration'][year - 2][f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year - 2), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration does not exists
            else:
                calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

        # Post deployment calibration exists
        else:
            calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

    return calibrations


def interpolate_deviation(caldata, data, param, time='time'):
    """
    Perform 2D interpolation (`time`, `param`) of the calibration deviation

    Parameters
    ----------
    caldata : pd.DataFrame
        output of `reader.read_calfile` containing the calibration points
    data : pd.DataFrame
        output of `reader.read_cnv` or `reader.read_csv`, containing the raw device data
    param : str
        name of the parameter for which to interpolate the deviation
    time : str
        name of the time axis in `data`.

    Returns
    -------
    deviation : 1D array of float
        the interpolated deviation as a function of `time` and `param`.

    """
    # Create the deviation interpolant
    caldata.loc[:, 'time_num'] = timestamp2numeric(caldata.time)
    interpolant = LNDI(caldata[['time_num', 'standard']], caldata['deviation'])

    # Calculate the interpolated drift time series
    data.loc[:, 'time_num'] = timestamp2numeric(data[time])
    return interpolant(data[['time_num', param]])
