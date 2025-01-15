from ppmt.__init__ import TIME_ORIGIN, THRESHOLDS, CALFILES_LOOKUP
from scipy.interpolate import LinearNDInterpolator as LNDI
from ppmt.reader import read_calfile, probe_calfile
import pandas as pd
import numpy as np

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
    elif isinstance(timestamp, (pd.Series, np.ndarray)):
        ts = pd.to_datetime(timestamp)         # This seems like overkill but it solves some nasty bugs
        origin = pd.to_datetime(TIME_ORIGIN)
        numeric = (ts - origin).apply(lambda x: x.total_seconds() / 24 / 3600)
    else:
        raise TypeError('timestamp2numeric requires input be type: [pd.Timestamp, pd.Series]')
    return numeric


# ---------
# Functions
# ---------


def get_calibration_data(header, year_pre=None):
    """
    Get the best available calibration data for this device

    Parameters
    ----------
    header : dict
        output of `input.manage_file_types`
    year_pre : None or int
        passed to `get_calibration_data_setup`; the year to use for pre-deployment calibration

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
            calibrations = get_calibration_data_setup(variable, header, year_pre=year_pre)

            # Check that appropriate calibration data are available
            if calibrations['ok']:
                # Pre deployment calibration
                df_pre = read_calfile(header['device_serial'],
                                      variable=calibrations['pre'][0],
                                      sheet=calibrations['pre'][1])

                # Assume factory calibration was perfect on deployment date (new device)
                if 'deployment' in df_pre.time.unique():
                    df_pre.loc[:, 'time'] = np.datetime64(header['trip_installation_real_date'], '[us]')

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


def get_calibration_data_setup(variable,
                               header,
                               year_pre=None):
    """
    Determine which (raw/clean) calibration and year combination to correct drift on variable

    Parameters
    ----------
    variable : str
        one of `temperature`, `salinity`, `conductivity`, `depth`
    header : dict
        output of `input.manage_file_types`
    year_pre : None or int
        user specified year to use for the pre-deployment calibration

    Returns
    -------
    calibrations : dict
        with the input values to supply `reader.read_calfile` at the `sheet` and `variable` arguments
        to get the recommended calibrations for pre and post-deployment.

    """
    # For readability
    year = header['deployment_year']
    mli_cal = header['mli_calibration']
    if isinstance(year_pre, int):
        mli_cal_year_pre = probe_calfile(header['device_serial'], year_pre)

    # ------------------------------------------------------------------
    # Temperature and depth are together because they have simpler logic
    # ------------------------------------------------------------------

    if variable in ['temperature', 'depth']:
        # Post deployment calibration exists (on deployment year)
        if mli_cal[year][f'{variable}_calibration']:
            """ post deployment exist """
            # Pre deployment calibration year is user specified
            if isinstance(year_pre, int) and mli_cal_year_pre[f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year_pre), 'post': (variable, year)}
            # Pre deployment calibration exists (one year back)
            elif mli_cal[year - 1][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 1), 'post': (variable, year)}
            # Pre deployment calibration exists (two years back)
            elif mli_cal[year - 2][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 2), 'post': (variable, year)}
            # Post deployment is on a new device (single calibration)
            elif mli_cal['single_year']:
                calibrations = {'ok': True, 'pre': (variable, 'blank'), 'post': (variable, year)}
            # Pre deployment calibration does not exists
            else:
                calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

        # Post deployment calibration exists (the year after deployment year)
        elif mli_cal[year + 1][f'{variable}_calibration']:
            """ post deployment exist """
            # Pre deployment calibration year is user specified
            if isinstance(year_pre, int)  and mli_cal_year_pre[f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year_pre), 'post': (variable, year + 1)}
            # Pre deployment calibration exists (one year back)
            elif mli_cal[year - 1][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 1), 'post': (variable, year + 1)}
            # Pre deployment calibration exists (two years back)
            elif mli_cal[year - 2][f'{variable}_calibration']:
                calibrations = {'ok': True, 'pre': (variable, year - 2), 'post': (variable, year + 1)}
            # Post deployment is on a new device (single calibration)
            elif mli_cal['single_year']:
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
        # Post deployment calibration exists (on deployment year)
        if mli_cal[year][f'{variable}_raw_calibration']:
            # Pre deployment calibration year is user specified
            if isinstance(year_pre, int) and mli_cal_year_pre[f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year_pre), 'post': (f'{variable}_raw', year)}
            elif isinstance(year_pre, int) and mli_cal_year_pre[f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year_pre), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration exists (one year back; clean)
            elif mli_cal[year - 1][f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year - 1), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration exists (one year back; raw)
            elif mli_cal[year - 1][f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year - 1), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration exists (two years back; clean)
            elif mli_cal[year - 2][f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year - 2), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration exists (two years back; raw)
            elif mli_cal[year - 2][f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year - 2), 'post': (f'{variable}_raw', year)}
            # Post deployment is on a new device (single calibration)
            elif mli_cal['single_year']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', 'blank'), 'post': (f'{variable}_raw', year)}
            # Pre deployment calibration does not exists
            else:
                calibrations = {'ok': False, 'pre': (f'{variable}_raw', None), 'post': (f'{variable}_raw', None)}

        # Post deployment calibration exists (the year after deployment year)
        elif mli_cal[year + 1][f'{variable}_raw_calibration']:
            # Pre deployment calibration year is user specified
            if isinstance(year_pre, int) and mli_cal_year_pre[f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year_pre), 'post': (f'{variable}_raw', year + 1)}
            elif isinstance(year_pre, int) and mli_cal_year_pre[f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year_pre), 'post': (f'{variable}_raw', year + 1)}
            # Pre deployment calibration exists (one year back; clean)
            elif mli_cal[year - 1][f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year - 1), 'post': (f'{variable}_raw', year + 1)}
            # Pre deployment calibration exists (one year back; raw)
            elif mli_cal[year - 1][f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year - 1), 'post': (f'{variable}_raw', year + 1)}
            # Pre deployment calibration exists (two years back; clean)
            elif mli_cal[year - 2][f'{variable}_clean_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_clean', year - 2), 'post': (f'{variable}_raw', year + 1)}
            # Pre deployment calibration exists (two years back; raw)
            elif mli_cal[year - 2][f'{variable}_raw_calibration']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', year - 2), 'post': (f'{variable}_raw', year + 1)}
            # Post deployment is on a new device (single calibration)
            elif mli_cal['single_year']:
                calibrations = {'ok': True, 'pre': (f'{variable}_raw', 'blank'), 'post': (f'{variable}_raw', year + 1)}
            # Pre deployment calibration does not exists
            else:
                calibrations = {'ok': False, 'pre': (f'{variable}_raw', None), 'post': (f'{variable}_raw', None)}

        # Post deployment calibration does not exist
        else:
            calibrations = {'ok': False, 'pre': (variable, None), 'post': (variable, None)}

    # No pressure calibration at this stage
    elif variable in ['pressure']:
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
    caldata.loc[:, 'time_num'] = timestamp2numeric(caldata.time)  # represent time as a number
    caldata = caldata.query('~standard.isnull()')                 # ensure there are no missing values
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

            # Interpolate the calibration data -> deviation(time, variable)
            deviation = interpolate_deviation(calibration_data[variable],
                                              data,
                                              variable)

            # Apply drift correction
            data[f'{variable}_deviation'] = deviation

            # Determine if drift correction must be applied
            if (calibration_data[variable]['deviation'].abs() > THRESHOLDS[f'{variable}']).any():

                # Save drift correction decision in metadata
                header['drift_correction'][variable] = True

                # Interpolate the calibration data -> deviation(time, variable)
                # deviation = interpolate_deviation(calibration_data[variable],
                #                                   data,
                #                                   variable)

                # Apply drift correction
                data[f'{variable}_raw'] = data[f'{variable}'].copy()
                # data[f'{variable}_deviation'] = deviation
                data[f'{variable}'] += deviation

            else:
                # Save drift correction decision in metadata
                header['drift_correction'][variable] = False

    return data, header
