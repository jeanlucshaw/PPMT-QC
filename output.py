import xarray as xr
import numpy as np


def init_output(data, standard_header):
    """
    Place data from the cnv, csv and xlsx files into a pre-filled structure

    Parameters
    ----------
    data : pandas.DataFrame
        containing the data columns
    standard_header : dict
        containing the attributes from the data file header

    Returns
    -------
    dataset : xarray.Dataset
        containing the data and metadata in the expected output format

    """
    flag_values = '0 1 2 3 4 5 9'
    flag_meanings = 'raw good local_outlier probably_bad bad modified missing'
    template_attributes = {'Deployment_Year': standard_header['deployment_year'],
                           'Station_abbr': standard_header['site_unique_id'],
                           'Station': standard_header['site_long_name'],
                           'Event_Header': {'Start_Date_Time': '',
                                            'End_Date_Time': '',
                                            'RAWFile_Name': '',
                                            'Creation_Date': '',
                                            'Num_Cycle': '',
                                            'Num_Param': ''},
                           'Latitude': standard_header['site_latitude'],
                           'Longitude': standard_header['site_longitude'],
                           'INSTR_DEPTH': standard_header['instrument_depth'],
                           'SITE_DEPTH': standard_header['site_depth'],
                           'SBE': standard_header['SBE'],
                           'Instrument_Header': {'Serial_Number': standard_header['device_serial'],
                                                 'Sampling_Interval': standard_header['interval'],
                                                 'Inst_Type': standard_header['instrument_type'],
                                                 'Model': standard_header['instrument_model']},
                           'General_Cal_Header': {'Units': '',
                                                  'T_C_Calibration_Date': '',
                                                  'Temperature': '',
                                                  'Conductivity': ''}}
    template_variables = {'TE90_01': ('Time',
                                      data.temperature,
                                      dict(long_name='Temperature',
                                           standard_name='sea_water_temperature',
                                           units='degrees Celsius')),
                          'QQQQ_01': ('Time',
                                      np.zeros(data.temperature.size, dtype=int),
                                      dict(long_name='Temperature quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings)),
                          'CNDC_01': ('Time',
                                      data.conductivity,
                                      dict(long_name='Conductivity',
                                           standard_name='sea_water_conductivity',
                                           units='')),
                          'QQQQ_02': ('Time',
                                      np.zeros(data.conductivity.size, dtype=int),
                                      dict(long_name='Conductivity quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings)),
                          'PSAL_01': ('Time',
                                      data.salinity,
                                      dict(long_name='Salinity',
                                           standard_name='sea_water_practical_salinity',
                                           units='practical salinity units')),
                          'QQQQ_03': ('Time',
                                      np.zeros(data.salinity.size, dtype=int),
                                      dict(long_name='Salinity quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings)),
                          'depth': ('Time',
                                    data.depth,
                                    dict(long_name='Depth',
                                    standard_name='sea_water_depth',
                                    positive='down',
                                    units='m')),
                          'QQQQ_04': ('Time',
                                      np.zeros(data.depth.size, dtype=int),
                                      dict(long_name='Depth/pressure quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings)),
                          'pressure': ('Time',
                                       data.pressure,
                                       dict(long_name='Pressure',
                                       standard_name='sea_water_pressure',
                                       units='dbar')),
                          'SIGMAT': ('Time', data.sigma_t)
                          }
    dataset = xr.Dataset(template_variables,
                         coords={'Time': data.time},
                         attrs=template_attributes)

    return dataset
