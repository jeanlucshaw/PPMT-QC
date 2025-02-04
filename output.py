import xarray as xr
import numpy as np
import json
from datetime import datetime


def apply_flags(dataset, flag_data):
    """
    Apply the specified flags to `dataset`

    Parameters
    ----------
    dataset : xarray.Dataset
        output of `output.init_output`
    flag_data : dict
        containing the flagging instructions

    Returns
    -------
    dataset : xarray.Dataset
        with the modified flag variables

    Note
    ----
        The `flag_data` variable should be structured as follows:

            flag_data = {flag_value: {'variable', [index_1, index_2, ...]}}

        with a key for each flag value, for example

            flag_data = {2: {'all': [30000],
                        'temperature': [157, 312, 405]},
                        4: {'salinity': [10000]}}

        The variable `all` can be used to target `temperature`, `conductivity`, `salinity` and `depth`.

    """
    # Flag variables to target for each variable
    flag_names = {'temperature': 'QQQQ_01',
                  'conductivity': 'QQQQ_02',
                  'salinity': 'QQQQ_03',
                  'depth': 'QQQQ_04'}

    # Loop over flag values
    for flag in flag_data.keys():

        # Loop over entries for this flag value
        for variable, index in flag_data[flag].items():

            # Apply flag to all variables
            if variable == 'all':
                for v_ in flag_names.keys():
                    dataset[flag_names[v_]].values[index] = flag

            # Apply flag to this specific variable
            elif variable in flag_names.keys():
                dataset[flag_names[variable]].values[index] = flag

            # Raise if there is a problem with the requested variable name
            else:
                raise ValueError(f'Variable not recognized in `flag_data`: {variable}')

    return dataset


def init_output(data, standard_header):
    """
    Place data from the cnv, csv and xlsx files into a pre-filled xarray structure

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
    # Determine if depth is from pressure, sensor, or metadata
    if standard_header['data_source']['depth'] == 'observation':
        depth_data_source = 'observation'
    elif standard_header['data_source']['pressure'] == 'observation':
        depth_data_source = 'observation'
    else:
        depth_data_source = 'other'  # just needs to no be `observation` for save_dataset

    flag_values = '0 1 2 3 4 5 9'
    flag_meanings = 'raw good local_outlier probably_bad bad modified missing'
    template_attributes = {'Deployment_Year': standard_header['deployment_year'],
                           'Station_abbr': standard_header['site_unique_id'],
                           'Station': standard_header['site_long_name'],
                           'Event_Header': json.dumps({'Start_Date_Time': standard_header['trip_installation_real_date'],
                                                       'End_Date_Time': standard_header['trip_recovery_real_date'],
                                                       'RAWFile_Name': standard_header['raw_file_name'],
                                                       'Creation_Date': str(datetime.now())[:16],
                                                       'Num_Cycle': int(data.temperature.size),
                                                       'Num_Param': ''}),
                           'Latitude': standard_header['site_latitude'],
                           'Longitude': standard_header['site_longitude'],
                           'INSTR_DEPTH': standard_header['instrument_depth'],
                           'SITE_DEPTH': standard_header['site_depth'],
                           'SBE': standard_header['SBE'],
                           'Instrument_Header': json.dumps({'Serial_Number': int(standard_header['device_serial']),
                                                            'Sampling_Interval': int(standard_header['interval']),
                                                            'Inst_Type': standard_header['instrument_type'],
                                                            'Model': standard_header['instrument_model']
                                                           }
                                                           ),
                           'General_Cal_Header': json.dumps({'Units': '',
                                                             'T_C_Calibration_Date': standard_header['calibration_header']['CalDate'],
                                                             'Temperature': {'A0': standard_header['calibration_header']['TCAL_A0'],
                                                                             'A1': standard_header['calibration_header']['TCAL_A1'],
                                                                             'A2': standard_header['calibration_header']['TCAL_A2'],
                                                                             'A3': standard_header['calibration_header']['TCAL_A3']},
                                                             'Conductivity': {'G': standard_header['calibration_header']['CCAL_G'],
                                                                              'H': standard_header['calibration_header']['CCAL_H'],
                                                                              'I': standard_header['calibration_header']['CCAL_I'],
                                                                              'J': standard_header['calibration_header']['CCAL_J'],
                                                                              'PCOR': standard_header['calibration_header']['CCAL_PCOR'],
                                                                              'TCOR': standard_header['calibration_header']['CCAL_TCOR'],
                                                                              'WBOTC': standard_header['calibration_header']['CCAL_WBOTC'],
                                                                              }})}
    template_variables = {'TE90_01': ('Time',
                                      data.temperature,
                                      dict(long_name='Temperature',
                                           standard_name='sea_water_temperature',
                                           units='degrees Celsius',
                                           source=standard_header['data_source']['temperature'])),
                          'QQQQ_01': ('Time',
                                      np.zeros(data.temperature.size, dtype='int64'),
                                      dict(long_name='Temperature quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings,
                                           source=standard_header['data_source']['temperature'])),
                          'CNDC_01': ('Time',
                                      data.conductivity,
                                      dict(long_name='Conductivity',
                                           standard_name='sea_water_conductivity',
                                           units='S / m',
                                           source=standard_header['data_source']['conductivity'])),
                          'QQQQ_02': ('Time',
                                      np.zeros(data.conductivity.size, dtype='int64'),
                                      dict(long_name='Conductivity quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings,
                                           source=standard_header['data_source']['conductivity'])),
                          'PSAL_01': ('Time',
                                      data.salinity,
                                      dict(long_name='Salinity',
                                           standard_name='sea_water_practical_salinity',
                                           units='practical salinity units',
                                           source=standard_header['data_source']['salinity'])),
                          'QQQQ_03': ('Time',
                                      np.zeros(data.salinity.size, dtype='int64'),
                                      dict(long_name='Salinity quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings,
                                           source=standard_header['data_source']['salinity'])),
                          'depth': ('Time',
                                    data.depth,
                                    dict(long_name='Depth',
                                         standard_name='sea_water_depth',
                                         positive='down',
                                         units='m',
                                         source=standard_header['data_source']['depth'])),
                          'QQQQ_04': ('Time',
                                      np.zeros(data.depth.size, dtype='int64'),
                                      dict(long_name='Depth/pressure quality flags',
                                           flag_values=flag_values,
                                           flag_meanings=flag_meanings,
                                           source=depth_data_source)),
                          'pressure': ('Time',
                                       data.pressure,
                                       dict(long_name='Pressure',
                                            standard_name='sea_water_pressure',
                                            units='dbar',
                                            source=standard_header['data_source']['pressure'])),
                          'SIGMAT': ('Time',
                                     data.sigma_t,
                                     dict(long_name='Density Anomaly',
                                          standard_name='sea_water_sigma_t',
                                          units='kg m-3',
                                          source=standard_header['data_source']['sigma_t']))
                          }
    dataset = xr.Dataset(template_variables,
                         coords={'Time': data.time},
                         attrs=template_attributes)

    # Date and hour variables
    Date, Heure = [], []
    for index, date_string in enumerate(np.datetime_as_string(dataset.Time.values, unit='s')):
        d_, h_ = date_string.split('T')
        Date.append(d_)
        Heure.append(h_)
    dataset = dataset.assign_coords({'Date': ('Time', Date), 'Heure': ('Time', Heure)})

    return dataset



def save_dataset(output_path, dataset, variables='minimal', *args, **kwargs):
    """
    Save the dataset with a specific encoding and keeping only the specified variables

    Parameters
    ----------
    output_path : str
        the path and name where to save the file
    dataset : xarray.Dataset
        containing the data to save
    variables : str
        set of variables to save: 'minimal' for observations only, 'all' for metadata, and TEOS_10 conversions.

    Returns
    -------
    None
    """
    # Select variables to save
    if variables == 'minimal':

        for variable in dataset.data_vars:
            if dataset[variable].source != 'observation':
                dataset = dataset.drop_vars(variable)
    elif variables == 'all':
        pass
    else:
        raise ValueError(f'Unrecognized argument: {variables} must be one of [`all`, `minimal`]')

    # Set compression encoding
    enc = {variable: {'zlib': True, 'complevel': 9} for variable in dataset.data_vars}
    dataset.to_netcdf(output_path, encoding=enc)

    return None
