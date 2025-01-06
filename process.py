import os.path
import pathlib
import matplotlib
matplotlib.use('TkAgg')
from __init__ import UNPROCESSED
from input import *
from visualize import plot_processed
from output import init_output, apply_flags
from glob import glob
from reader import *
from drift import *


# ----------------
# helper functions
# ----------------


def read_any(file_name, read_data=True):
    """ isolated as a helper because used multiple times"""
    # Read data file
    _, ext = os.path.splitext(file_name)
    if ext == '.csv':
        header, data = read_csv(file_name, data=read_data)
    elif ext == '.cnv':
        header = read_cnv_metadata(file_name)
        data = read_cnv(file_name, data=read_data)
        data = manage_cnv_units(data, header)
    else:
        print('Unknown file format', ext)

    return header, data


def standard_file_name_from_header(header):
    """ Form QYY[A-Z]{4}[0-9]{1} """
    return f'Q{header["deployment_year"] - 2000}{header["site_unique_id"]}{header["instrument_unique_id"]}'


def standard_file_name_from_input_file(input_file):
    """ Form QYY[A-Z]{4}[0-9]{1} """
    header, data = read_any(input_file, read_data=False)
    data, header = manage_file_type(data, header)
    return f'Q{header["deployment_year"] - 2000}{header["site_unique_id"]}{header["instrument_unique_id"]}'


# ---------
# Functions
# ---------


def process_ppmt(file_name,
                 flag_data=None,
                 dry_run=True,
                 out_dir=None):

    # -------------------------------
    # Read data file and its metadata
    # -------------------------------

    # Read
    header, data = read_any(file_name)

    # Funnel to uniform file format
    data, header = manage_file_type(data, header)

    # Clip times before and after the recovery date
    start_date = str(header['trip_installation_real_date'])
    end_date = str(header['trip_recovery_real_date'])
    data = data.query(f'"{start_date}" < time < "{end_date}"').reset_index()

    # Get the calibrations for this device
    calibration_data = get_calibration_data(header)

    # Drift correction
    data, header = manage_drift_correction(data, header, calibration_data)

    # -------------
    # Visualization
    # -------------

    # --- Variable time series ---
    if 'temperature' in header['drift_correction'].keys():  # most likely always true
        _, outside_std_envelope_t = plot_processed(data, header, 'temperature', user_flags=flag_data)
    if 'salinity' in header['drift_correction'].keys():     # not always true
        _, outside_std_envelope_s = plot_processed(data, header, 'salinity', user_flags=flag_data)

    # -----
    # Flags
    # -----

    # Generate output structure
    ds = init_output(data, header)

    # Auto flag data outside the
    if 'temperature' in header['drift_correction'].keys():  # most likely always true
        ds['QQQQ_01'].values[outside_std_envelope_t] = 4
    if 'salinity' in header['drift_correction'].keys():     # not always true
        ds['QQQQ_03'].values[outside_std_envelope_s] = 4

    # Modify flag values
    if isinstance(flag_data, dict):
        ds = apply_flags(ds, flag_data)

    # ------
    # Output
    # ------

    # Determine the output file name
    output_name = standard_file_name_from_header(header)
    # output_name, _ = os.path.splitext(os.path.basename(file_name))

    # Determine if/where to save the processed nc file
    if out_dir is None:
        out_dir = os.path.join(os.getcwd(), 'processed')
    output_path = os.path.join(out_dir, f'{output_name}.nc')

    # Save output or print what you would save
    if dry_run is True:
        print(output_path)
    else:
        enc = {v_: {'zlib': True, 'complevel': 9} for v_ in ds.data_vars}
        ds.to_netcdf(output_path, encoding=enc)

    return ds


def generate_processing_script(input_file,
                               run_dir='run',
                               out_dir='processed'):
    """
    Generate the script template for a thermograph file (.csv or .cnv)

    Parameters
    ----------
    input_file : str
        the path and name of the file to process
    run_dir : str
        the path of the directory where to save the processing script
    out_dir : str
        the path of the directory where the processed files should be saved

    Returns
    -------
    None

    """

    file_name = standard_file_name_from_input_file(input_file)
    py_file_path = run_dir
    py_file_name = f'{file_name}.py'

    with open(os.path.join(py_file_path, py_file_name), 'w') as pyfile:
        pyfile.write("from process import process_ppmt\n\n")
        pyfile.write('# Switch this to `True` when the processing is completed and the files managed\n')
        pyfile.write("finalized = False\n\n")
        pyfile.write('# The file which this script processes\n')
        pyfile.write(f"filename = r'{input_file}'\n\n")
        pyfile.write("if finalized is False:\n\n")
        pyfile.write('    # Iteratively process and add flags to this block\n')
        pyfile.write("    # flag_data = {flag_value: {'variable': [index_1, index_2, ...]}}\n\n")
        pyfile.write(f"    ds = process_ppmt(filename, dry_run=False, out_dir='{out_dir}')\n\n")

    return None


def run_actions(action,
                run_dir='run',
                out_dir='processed',
                archive_dir='archive'):
    """
    Act on the the `run` directory, where the active processing scripts are stored.

    Parameters
    ----------
    action : str
        one of [clean, populate, update, run, archive].
            * clean: delete python scripts in `run_dir` and .nc files in `out_dir`;
            * populate: generate the processing scripts for the available unprocessed files in `run_dir`;
            * update: generate new processing scripts in `run_dir` for newly available unprocessed files;
            * run: sequentially execute all the processing scripts in `run_dir`;
            * archive: move the unprocessed files to the appropriate deployment year folder on S:/ ;
    run_dir : str
        path of the folder to use for storing the active processing scripts.
    out_dir : str
        path of the folder to use for storing the active .nc processed files.
    archive_dir : str
        path of the folder to use for archiving the processing scripts and .nc files.

    Returns
    -------
    None
    """
    if action == 'clean':
        """ Delete all files in the run and processed directories (start fresh) """
        for py_file in glob(os.path.join(run_dir, '*.py')):
            py_file_path = pathlib.Path(py_file)
            py_file_path.unlink()
        for nc_file in glob(os.path.join(out_dir, '*.nc')):
            nc_file_path = pathlib.Path(nc_file)
            nc_file_path.unlink()
    elif action == 'populate':
        """ Generate processing script templates for all the files in the unprocessed directory """
        for file_name in UNPROCESSED:
            generate_processing_script(file_name, run_dir=run_dir, out_dir=out_dir)
    elif action == 'update':
        """ Generate processing script templates for files in the unprocessed directory that don't exist in run """
        for file_name in UNPROCESSED:
            prospect_file_name = standard_file_name_from_input_file(file_name)
            if not os.path.exists(os.path.join(run_dir, f'{prospect_file_name}.py')):
                print(f'generating {prospect_file_name} for input {file_name}')
                generate_processing_script(file_name, run_dir=run_dir, out_dir=out_dir)
    elif action == 'run':
        """ Excute all the processing scripts """
        pass
    elif action == 'archive':
        """ Move the python scripts to the archive directory and empty the unprocessed directory (log file created) """
        raise NotImplementedError('Archiving not yet implemented')
    else:
        raise ValueError('`action` must be one of [clean, populate, update, run, archive]')

    return None
