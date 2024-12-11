import pandas as pd
import re
from __init__ import CALFILES_LOOKUP

# ----------
# Parameters
# ----------

"""
Suivi Excel file columns (translated and simplified) column 0 -- 6 rows
are doubled up (merged) -> reading from 7 to the last is simplest.
"""
suivi_columns = ['station',
                 'buoy_name',
                 'SIPA_number',
                 'buoy_type',
                 'trip_id_installation',
                 'trip_id_recovery',
                 'trip_installation_nominal_date',
                 'site_long_name',
                 'site_latitude',
                 'site_longitude',
                 'instrument_depth',
                 'site_depth',
                 'site_unique_id',
                 'instrument_unique_id',
                 'platform_type',
                 'sbe56_id',
                 'sbe37_id',
                 'vr2w_id',
                 'programmed',
                 'delivered',
                 'trip_installation_real_date',
                 'recovered',
                 'trip_recovery_real_date',
                 'trip_recovery_nominal_date', # some rows doubled up
                 'data_extracted',
                 'comment',
                 'physical_storage_location',
                 'varargin1',
                 'varargin2',
                 'varargin3',
                 'varargin4',
                 'varargin5']

# -------
# Helpers
# -------


def flag_no_yes_lost(value):
    """ Convert `X`, `nothing`, and `lost` to numeric """
    if isinstance(value, str):
        value = value.strip()

    if value in ['Perdu', 'perdu', 'PERDU']:
        flag = 2
    elif value in ['x', 'X']:
        flag = 1
    else:
        flag = 0

    return flag


def get_device_suivi_metadata(serial, year):
    """
    Get `suivi` information on a specific device for a given deployment year

    Parameters
    ----------
    serial : str
        the serial number read from the csv or cnv file (056[0-9]+ or 037[0-9]+)
    year : int
        deployment year, i.e., when the device starts recording.

    Returns
    -------
    metadata : dict
        containing the line of the `suivi` spreadsheet. Keys are column names.

    """
    # Separate instrument type and device number
    inst_type, inst_num = int(serial[:3]), int(serial[3:])

    # Read the appropriate "suivi" spreadsheet give the deployment year
    suivi = read_suivi(year)

    # Select the line corresponding to this device
    id_col = f'sbe{inst_type}_id'
    line = suivi.query(f'{id_col} == {inst_num}')

    # Format as a dictionary with values unpacked
    metadata = line.to_dict(orient='list')
    metadata = {k: v[0] for k, v in metadata.items()}

    return metadata


def julian2timestamp(julian, year):
    """
    Convert Julian dates (starting on Jan 0 of `year`) to Timestamp

    Parameters
    ----------
    julian : 1D array of float
        the Julian dates to convert
    year : int
        the reference year for these Julian dates

    Returns
    -------
    timestamps : 1D array of Timestamps
        the converted Julian dates

    """
    january_0 = pd.Timestamp(f'{year - 1}-12-31T00:00:00')
    return january_0 + pd.to_timedelta(julian, 'd')


# -------
# Readers
# -------


def probe_calfile(device_serial, deployment_year):
    """
    Check a calibration file for dates of calibration and calibration data

    Parameters
    ----------
    device_serial : str or int
        serial number of the device (excluding 056 or 057)
    deployment_year : int
        year the device started recording.

    Returns
    -------
    calfile_params: dict
        containing the boolean switches related to calibration file content

    """
    def is_date_str(string):
        """ helper to check strings for convertibility to Timestamp """
        return pd.notnull(pd.to_datetime(string, errors='coerce'))

    # Init output
    calfile_params = {'temperature_calibration': False,
                      'conductivity_raw_calibration': False,
                      'conductivity_clean_calibration': False,
                      'salinity_raw_calibration': False,
                      'salinity_clean_calibration': False,
                      'depth_calibration': False,
                      'temperature_calibration_date': False,
                      'conductivity_raw_calibration_date': False,
                      'conductivity_clean_calibration_date': False,
                      'depth_calibration_date': False}

    # Find the right calibration file
    calfile, = CALFILES_LOOKUP.query(f'serial == "{device_serial}"')['fullpath']

    # Find the number of rows
    nrows = pd.read_excel(calfile, sheet_name=f'{deployment_year}').shape[0]

    # ----------------------------------------
    # Check if calibration dates are available
    # ----------------------------------------

    if nrows > 4:
        t_date_str = pd.read_excel(calfile, sheet_name=f"{deployment_year}").iloc[1, 4]
        calfile_params['temperature_calibration_date'] = is_date_str(t_date_str)
    if nrows >= 20:
        c_raw_date_str = pd.read_excel(calfile, sheet_name=f"{deployment_year}").iloc[20, 4]
        calfile_params['conductivity_raw_calibration_date'] = is_date_str(c_raw_date_str)
    if nrows >= 31:
        c_clean_date_str = pd.read_excel(calfile, sheet_name=f"{deployment_year}").iloc[31, 4]
        calfile_params['conductivity_clean_calibration_date'] = is_date_str(c_clean_date_str)
    if nrows >= 49:
        d_date_str = pd.read_excel(calfile, sheet_name=f"{deployment_year}").iloc[49, 4]
        calfile_params['depth_calibration_date'] = is_date_str(d_date_str)

    # --------------------------------------
    # Check if calibration data is available
    # --------------------------------------

    if nrows > 10:
        calfile_params['temperature_calibration'] = (pd
                                           .read_excel(calfile, sheet_name=f"{deployment_year}")
                                           .iloc[slice(5, 10), 3]
                                           .notna()
                                           .all())
    if nrows > 29:
        calfile_params['conductivity_raw_calibration'] = (pd
                                               .read_excel(calfile, sheet_name=f"{deployment_year}")
                                               .iloc[slice(26, 30), 2]
                                               .notna()
                                               .all())
        calfile_params['salinity_raw_calibration'] = (pd
                                               .read_excel(calfile, sheet_name=f"{deployment_year}")
                                               .iloc[slice(26, 30), 6]
                                               .notna()
                                               .all())
    if nrows > 40:
        calfile_params['conductivity_clean_calibration'] = (pd
                                                 .read_excel(calfile, sheet_name=f"{deployment_year}")
                                                 .iloc[slice(35, 39), 2]
                                                 .notna()
                                                 .all())
        calfile_params['salinity_clean_calibration'] = (pd
                                                 .read_excel(calfile, sheet_name=f"{deployment_year}")
                                                 .iloc[slice(35, 39), 6]
                                                 .notna()
                                                 .all())
    if nrows > 64:
        """ only checking 0-500 PSI, 600 and 700 are often null """
        calfile_params['depth_calibration'] = (pd
                                           .read_excel(calfile, sheet_name=f"{deployment_year}")
                                           .iloc[slice(55, 62), 6]
                                           .notna()
                                           .all())

    return calfile_params


def read_calfile(device_serial, sheet=None, variable='temperature'):
    """
    Read the device calibration data given its serial number

    Parameters
    ----------
    device_serial : int
        serial number of the device (excluding 056 or 057)
    sheet : None or int
        determines what deployment year to consider as the calibration points. If
        `None`, the latest year is considered. If `int`, the specified year is considered.
    variable : str
        name of the variable for which to get the calibration data: one of [`temperature`,
        `salinity`, `conductivity`, `depth`].

    Returns
    -------
    calibration_data : pd.DataFrame
        containing the dates, standard values, and deviations.

    """
    # Manage which temperature calibration to get
    if variable == 'temperature':
        date_cell = (1, 4)
        rdxl_kw = dict(names=['standard',
                              'nominal',
                              'instrument',
                              'deviation'],
                       skiprows=5,
                       nrows=6,
                       usecols=[1, 2, 3, 5])
    elif variable == 'conductivity_raw':
        date_cell = (20, 4)
        rdxl_kw = dict(names=['standard',
                              'instrument',
                              'deviation',
                              'nominal'],
                       skiprows=26,
                       nrows=4,
                       usecols=[1, 2, 3, 4])
    elif variable == 'salinity_raw':
        # date_cell = (31, 4)
        date_cell = (20, 4)
        rdxl_kw = dict(names=['nominal',
                              'standard',
                              'instrument',
                              'deviation'],
                       skiprows=26,
                       nrows=4,
                       usecols=[4, 5, 6, 7])
    elif variable == 'conductivity_clean':
        date_cell = (31, 4)
        rdxl_kw = dict(names=['standard',
                              'instrument',
                              'deviation',
                              'nominal'],
                       skiprows=35,
                       nrows=4,
                       usecols=[1, 2, 3, 4])
    elif variable == 'salinity_clean':
        date_cell = (31, 4)
        rdxl_kw = dict(names=['nominal',
                              'standard',
                              'instrument',
                              'deviation'],
                       skiprows=35,
                       nrows=4,
                       usecols=[4, 5, 6, 7])
    elif variable == 'depth':
        date_cell = (49, 4)
        rdxl_kw = dict(names=['standard',
                              'instrument',
                              'deviation'],
                       skiprows=55,
                       nrows=10,
                       usecols=[4, 5, 6])
    else:
        allowed_values = ['temperature',
                          'salinity_raw',
                          'salinity_clean',
                          'conductivity_raw',
                          'conductivity_clean',
                          'depth']
        raise ValueError(f'read_calfile arg `variable` must be in {allowed_values}')

    # Find the right calibration file
    calfile, = CALFILES_LOOKUP.query(f'serial == "{device_serial}"')['fullpath']

    # Get the sheet names for this serial number
    sheet_names = pd.ExcelFile(calfile).sheet_names

    if sheet == None:
        sheet = sheet_names[0]
    elif isinstance(sheet, (int, float)):
        sheet = str(sheet)

    # Get calibration date
    date = pd.Timestamp(pd.read_excel(calfile, sheet_name=sheet).iloc[date_cell])

    # Read the spreadsheets
    data = pd.read_excel(calfile, sheet_name=sheet, **rdxl_kw)

    # Add times to data arrays
    data.loc[:, 'time'] = date

    return data


def read_cnv_metadata(filename, short_names=True):
    """
    Get information from cnv file header.

    Parameters
    ----------
    filename: str
        Name and path of cnv file.
    short_names: bool
        Return short variable names.

    Returns
    -------
    NAMES: list of str

    """
    # Read the file as a list of lines
    LINES = open(filename, 'r', errors='replace').readlines()

    # Parameters
    metadata = dict(names=[],
                    seabird_names=[],
                    units=[],
                    date=None,
                    lon=None,
                    lat=None,
                    missing_values=None,
                    header_lines=0)

    # Parse header
    for LN, L in enumerate(LINES):

        # Scan for metadata
        if re.search('\* Date:', L):
            day_ = re.findall('\d{4}-\d{2}-\d{2}', L)[0]
            hour = re.findall('\d{2}:\d{2}[:0-9]*', L)[0]
            metadata['date'] = np.datetime64('%sT%s' % (day_, hour))
        if re.search('# start_time', L):
            date_fmt = '[a-zA-Z]{3} [0-9]+ \d{4} \d{2}:\d{2}:\d{2}'
            date_str = re.findall(date_fmt, L)[0]
            if metadata['date'] is None:
                metadata['date'] = pd.Timestamp(date_str)
        if re.search('\* Longitude:', L):
            degree = float(L.split()[-3])
            minute = float(L.split()[-2])
            direction = L.split()[-1]
            metadata['lon'] = dmd2dd(degree, minute, direction)
        if re.search('\* Latitude:', L):
            degree = float(L.split()[-3])
            minute = float(L.split()[-2])
            direction = L.split()[-1]
            metadata['lat'] = dmd2dd(degree, minute, direction)
        if re.search('# bad_flag', L):
            metadata['missing_values'] = L.split()[-1]
        if re.search('# interval', L):
            if 'seconds' not in L:
                print('Warning: `interval` may not be in seconds.')
            metadata['interval'] = float(L.split()[-1])
        if re.search('\* <HardwareData', L):
            metadata['device'] = re.findall("DeviceType='([A-Za-z0-9- ]+)'", L)[0]
            metadata['serial'] = re.findall("SerialNumber='([A-Za-z0-9- ]+)'", L)[0]

        # Scan for variables
        if re.search('# name', L):
            full_name = L.split('=')[1].strip()
            short_name = re.findall(r': ([a-zA-Z0-9+. ]+)(,| \[|$)', full_name)[0][0]
            if short_names:
                name = short_name
                if '000e+00' in name:
                    name = 'flag'
            else:
                name = full_name
            metadata['names'].append(name.lower())
            metadata['seabird_names'].append(full_name.split(':')[0])

            if re.findall('\[.*\]', L):
                units = re.findall('\[.*\]', L)[0].strip('[]')
                metadata['units'].append(units)
            else:
                metadata['units'].append('')

        # Scan for end of header
        if re.search('\*END\*', L):
            metadata['header_lines'] = LN + 1
            break

    return metadata


def read_cnv(FNAME,
                sep=r'\s+',
                usecols=None,
                metadata_cols=True,
                short_names=True,
                **kw_read_csv):
    """
    Read seabird(like) files into a pandas dataframe.

    Parameters
    ----------
    FNAME: str
        Path and name of odf file.
    sep: str
        Data delimiter of odf file. Default is whitespace.
    usecols: list of int
        Index of columns to extract from odf file. Passed to pd.read_csv.
        By default all columns are returned.
    metadata_cols: bool
        Add columns with date, lon, lat repeated from header.
    short_names: bool
        Give output columns shorter names.

    Returns
    -------
    pandas.DataFrame
        A dataframe containing the requested data columns of the cnv file.

    """

    # Read the file as a list of lines
    LINES = open(FNAME, 'r', errors='replace').readlines()

    # Get metadata from header
    md = read_cnv_metadata(FNAME, short_names=short_names)

    # Select columns to read
    if usecols is None:
        usecols = [i_ for i_, _ in enumerate(md['names'])]

    # Read the data
    DF = pd.read_csv(FNAME,
                     skiprows=md['header_lines'],
                     sep=sep,
                     usecols=usecols,
                     names=md['names'],
                     na_values=md['missing_values'],
                     **kw_read_csv)

    # Detect and manage Julian days
    if 'time' in DF.keys():
        time_col = DF.keys().to_list().index('time')
        time_units = md['units'][time_col]
        if re.match('[Jj]ulian', time_units):
            DF['time'] = julian2timestamp(DF['time'], md['date'].year)

    # Add metadata columns
    if metadata_cols:
        if 'time' not in DF.keys() and 'date' not in DF.keys():
            if 'date' in md.keys() and 'interval' in md.keys():
                # Convert interval to nanoseconds
                dt_ns = np.floor(md['interval'] * 10 ** 9)
                dt_ = dt_ns * np.ones(DF.shape[0] - 1)
                dt_ = [0, *np.cumsum(dt_)]
                dt_ = np.array([np.timedelta64(int(t_), 'ns') for t_ in dt_])
                DF.loc[:, 'time'] = np.datetime64(md['date']) + dt_
            elif 'date' in md.keys():
                DF.loc[:, 'date'] = md['date']
        if md['lon']:
            DF.loc[:, 'Longitude'] = md['lon']
        if md['lat']:
            DF.loc[:, 'Latitude'] = md['lat']

    return DF


# SBE56 data files
def read_csv(filename):
    """
    Read the csv (often SBE56) files
    :param filename: str
        path and name to the PPMT data file.
    :return: header, data
    """
    # Initialize
    headerlines, header = 0, dict()

    # Read header line by line
    with open(filename, 'r') as ifile:
        for line in ifile.readlines():

            # Extract metadata
            lineinfo = re.findall(r'% (.*) = (.*)$', line)
            if lineinfo != []:
                key, value = lineinfo[0]
                header[key.strip()] = value.strip()

            # Break if end of header
            if not line.startswith('%'):
                break
            headerlines += 1

    # Read file data
    data = pd.read_csv(filename,
                       skiprows=headerlines)

    # Lowercase column names
    data = data.rename(columns={k: k.lower() for k in data.keys()})

    # Add Timestamp column
    time = pd.to_datetime(data['date'] + ' ' + data['time'], format='%Y-%m-%d %H:%M:%S')
    data = data.drop(columns=['date', 'time'])
    data['time'] = time

    # Commas as a decimal point in some cases
    if data.temperature.dtype == 'O':
        data.loc[:, 'temperature'] = data.temperature.apply(lambda x: float(x.replace(',', '.')))

    return header, data


def read_suivi(year):
    """ Read the `suivi` Excel file for the provided deployment year """
    # Manage excel sheet file name
    if year == 2022:
        sheet = 'PPMT'
    else:
        sheet = 'Feuil1'

    # Read the file
    #filepath = '%s\Liste suivi thermographe\ppmt%d.xlsx' % (TOP, year)
    filepath = 'local\suivi\ppmt%d.xlsx' % year
    suivi = pd.read_excel(filepath,
                          sheet_name=sheet,
                          names=suivi_columns[7:],
                          index_col=None,
                          usecols=range(7, len(suivi_columns)),
                          skiprows=2)

    # Remove lines with no values (separators)
    suivi = suivi.query('~site_long_name.isnull()')

    # convert columns to flags (0=no, 1=yes, 2=lost)
    for col in ['programmed', 'delivered', 'recovered', 'data_extracted']:
        suivi.loc[:, col] = suivi[col].apply(flag_no_yes_lost)

    return suivi
