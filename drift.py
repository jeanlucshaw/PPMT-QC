from __init__ import TIME_ORIGIN, THRESHOLDS
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
            else:
                message = f"""
                No valid calibration case for
                variable: {variable},
                deployment year:  {header["deployment_year"]}, 
                device_serial: {header["device_serial"]}
                """
                print(message)
                # raise FileNotFoundError(message)

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
        # Post deployment calibration exists (on deployment year)
        if header['mli_calibration'][year][f'{variable}_calibration']:
            """ post deployment exist """
            # Pre deployment calibration exists (one year back)
            if header['mli_calibration'][year - 1][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 1), 'post': (variable, year)}
            # Pre deployment calibration exists (two years back)
            elif header['mli_calibration'][year - 2][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 2), 'post': (variable, year)}
            # Post deployment is on a new device (single calibration)
            elif header['mli_calibration']['single_year']:
                calibrations = {'ok': True, 'pre': (variable, 'blank'), 'post': (variable, year)}
            # Pre deployment calibration does not exists
            else:
                calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

        # Post deployment calibration exists (the year after deployment year)
        elif header['mli_calibration'][year + 1][f'{variable}_calibration']:
            """ post deployment exist """
            # Pre deployment calibration exists (one year back)
            if header['mli_calibration'][year - 1][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 1), 'post': (variable, year + 1)}
            # Pre deployment calibration exists (two years back)
            elif header['mli_calibration'][year - 2][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 2), 'post': (variable, year + 1)}
            # Post deployment is on a new device (single calibration)
            elif header['mli_calibration']['single_year']:
                calibrations = {'ok': True, 'pre': (variable, 'blank'), 'post': (variable, year + 1)}
            # Pre deployment calibration does not exists
            else:
                calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

        # Post deployment calibration does not exist
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

        # Post deployment calibration does not exist
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


def manage_drift_correction(data, header, calibration_data):
    """
    Apply the sensor drift correction if required.

    Parameters
    ----------
    data : pandas.DataFrame
        data output of `input.manage_file_type`
    header : dict
        metadata output of `input.manage_file_type`
    calibration_data : pandas.DataFrame
        output of `drift.get_calibration_data`.

    Returns
    -------
    data : pandas.DataFrame
        with the drift correction selectively applied to the required columns.
    header : dict
        with an added `drift_correction` field documenting for which observed variables
        drift correction was applied or not.

    Note
    ----
        1) Drift correction is applied to the whole time series for a given variable if the
           corresponding threshold is met for at least one value in the calibration range, before
           or after the deployment.
        2) The difference between calibration and sensor values are written in the calibration
           files as `calibration - sensor`. To correct drift, this difference is therefore added
           to the sensor time series.

    """
    # Loop over observed variables
    header['drift_correction'] = dict()
    for variable, source in header['data_source'].items():

        # This variable has calibration data
        if variable in calibration_data.keys():

            # Determine if drift correction must be applied
            if (calibration_data[variable]['deviation'].abs() > THRESHOLDS[f'{variable}']).any():

                # Save drift correction decision in metadata
                header['drift_correction'][variable] = True

                # Interpolate the calibration data -> deviation(time, variable)
                deviation = interpolate_deviation(calibration_data[variable],
                                                  data,
                                                  variable)

                # Apply drift correction
                data[f'{variable}'] += deviation

            else:
                # Save drift correction decision in metadata
                header['drift_correction'][variable] = False

    return data, header
