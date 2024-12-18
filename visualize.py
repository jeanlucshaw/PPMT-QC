from __init__ import THRESHOLDS
import pandas as pd
import matplotlib.transforms as transforms
import matplotlib.pyplot as plt
import os

# -------
# Helpers
# -------


def get_station_climatology(variable, header):
    """
    Get the long-term average for the station from which this data header is from.

    Parameters
    ----------
    variable : str
        either `temperature` or `climatology`
    header : dict
        output of `input.manage_file_types`.

    Returns
    -------
    station_clim : pandas.DataFrame
        long-term average statistics for this variable/station combination.

    """
    daily_clim = get_variable_climatology(variable)
    station_id = f'{header["site_unique_id"]}{header["instrument_unique_id"]}'[:4]
    station_clim = daily_clim.query(f'station_id == "{station_id}"')
    return station_clim


def get_timeseries_climatology(station_clim, time, n_std=2):
    """
    Reindex the long-term mean values to match the time axis

    Parameters
    ----------
    station_clim : pandas.DataFrame
        output of `get_station_climatology`
    time : pandas.Series
        the time axis of the `data` dataframe
    n_std : int or float
        determines the width of the climatology envelope (multiples of daily STD)

    Returns
    -------
    clim_min, clim_max : numpy.ndarray (1D)
        daily minimum and maximum of the climatology envelope
    data_min, data_max : numpy.ndarray (1D)
        daily minimum and maximum observed values

    """
    input_doy = time.dt.dayofyear.values
    time_series_df = station_clim.set_index('dayofyear').loc[input_doy, :].reset_index()
    clim_min = time_series_df.iloc[:, 1].values - n_std * time_series_df.iloc[:, 2].values
    clim_max = time_series_df.iloc[:, 1].values + n_std * time_series_df.iloc[:, 2].values
    data_min = time_series_df.iloc[:, 4].values
    data_max = time_series_df.iloc[:, 7].values

    return clim_min, clim_max, data_min, data_max


def get_variable_climatology(variable='temperature'):
    """
    Load the long-term daily averages for this variable

    Parameters
    ----------
    variable : str
        one of `temperature` or `salinity`

    Returns
    -------
    dailyClim : pandas.DataFrame
        containing daily long-term averages for all stations
    """
    names = [f'dayofyear',
             f'{variable[0].upper()}mean',
             f'SD{variable[0].upper()}mean',
             f'Nmean',
             f'{variable[0].upper()}min',
             f'SD{variable[0].upper()}min',
             f'Nmin',
             f'{variable[0].upper()}max',
             f'SD{variable[0].upper()}max',
             f'Nmax',
             'station_id']
    df = pd.read_csv(f'{os.getcwd()}\\data\\{variable[0].upper()}.dailyClim.dat',
                     skiprows=1,
                     names=names,
                     na_values=[-99],
                     sep=r'\s+')

    return df


def rolling_filter(data, variable, threshold=3):
    """
    Apply a rolling mean and std filter and test that input is outside range

    Parameters
    ----------
    data : pandas.DataFrame
        output of `input.manage_file_type` containing a `variable` column
    variable : str
        the name of the variable to process
    threshold : float or int
        define the test range in multiples of local standard deviation around mean

    Returns
    -------
    rolling_mean : pandas.Series
        result of the rolling mean applied to the `variable` time series
    rolling_std : pandas.Series
        result of the rolling std applied to the `variable` time series
    outside : pandas.Series
        boolean time series; true if outside range

    """
    # Define filter parameters
    filter_params = dict(window=11, center=True, min_periods=11)

    # Get filtered output
    rolling_mean = data[variable].rolling(**filter_params).mean()
    rolling_std = data[variable].rolling(**filter_params).std()

    # Test the input against the requested envelope
    above_envelope = data[variable] > (rolling_mean + threshold * rolling_std)
    below_envelope = data[variable] < (rolling_mean - threshold * rolling_std)
    outside = above_envelope | below_envelope

    return rolling_mean, rolling_std, outside

# -----
# Plots
# -----


def plot_processed(data,
                   header,
                   variable,
                   print_flags=True,
                   draw_plot=True,
                   save_plot=False):
    """
    Visualize the processed time series and identify suspicious data

    Parameters
    ----------
    data : pandas.DataFrame
        output of `drift.manage_drift_correction` (data)
    header : dict
        output of `drift.manage_drift_correction` (metadata)
    variable : str
        the variable to visualize; one of [`temperature`, `salinity`]
    print_flags : bool
        display index of data values outside the rolling STD envelope
    draw_plot : bool
        make the analysis plot
    save_plot : bool
        by default, show the plot (False). Save and don't show (True)

    Returns
    -------
    outside_time : numpy.ndarray (1D)
        timestamps of data points outside the rolling STD envelope
    outside_index : numpy.ndarray (1D)
        index of data points outside the rolling STD envelope
    """

    # Get the climatology information for this station and variable
    station_clim = get_station_climatology(variable, header)
    clim_min, clim_max, data_min, data_max = get_timeseries_climatology(station_clim, data.time)

    # Calculate the rolling mean and std, and compare data to the generated envelope
    r_mean, r_std, outside = rolling_filter(data, variable)
    outside_time, outside_index = [], []
    for index, time in enumerate(data.time[outside]):
        outside_time.append(time)
        outside_index.append(index)
        if print_flags:
            print(f"Value outside rolling STD envelope: index = {index}")

    if draw_plot:
        # init plot
        gskw = dict(left=0.1, right=0.95, bottom=0.1, top=0.9)
        _, ax = plt.subplots(2, figsize=(10, 5), sharex=True, gridspec_kw=gskw)

        # (Panel 1): climatology envelope + daily average min and max
        ax[0].fill_between(data.time, clim_min, clim_max, color='lightgrey', step='mid')
        ax[0].plot(data.time, data_max, 'r')
        ax[0].plot(data.time, data_min, 'b')

        # (Panel 1): time series in black, rolling mean in green, and rolling std envelope in blue
        ax[0].plot(data.time, r_mean, 'g', lw=1)
        data.plot(x='time', y=f'{variable}', c='k', lw=0.5, ax=ax[0], legend=False)
        ax[0].fill_between(data.time, r_mean + 3*r_std, r_mean - 3*r_std, color='lightskyblue')

        # (Panel 1): mark data points outside the rolling std envelope with orange vertical lines
        for time in outside_time:
            ax[0].axvline(time, color='orange', zorder=0)

        # (Panel 1): installation and recovery markers
        ax[0].axvline(pd.Timestamp(header['trip_installation_real_date']), color='b')
        ax[0].axvline(pd.Timestamp(header['trip_recovery_real_date']), color='b')
        trans = transforms.blended_transform_factory(ax[0].transData, ax[0].transAxes)
        ax[0].text(pd.Timestamp(header['trip_installation_real_date']), 1.05, 'Installation', ha='center', transform=trans)
        ax[0].text(pd.Timestamp(header['trip_recovery_real_date']), 1.05, 'Recovery', ha='center', transform=trans)

        # (Panel 1): annotations and plot formatting
        long_name = header["site_long_name"]
        station_id = f'{header["site_unique_id"]}{header["instrument_unique_id"]}'
        depth = f'{header["site_depth"]}m'
        ax[0].set_title(f'{long_name}; {station_id}; {depth}')
        ax[0].set(ylabel=f'{variable.capitalize()}')

        # (Panel 2): interpolated sensor drift and thresholds
        ax[1].axhline(THRESHOLDS[variable], color='gray', ls='--')
        ax[1].axhline(0, color='gray', ls='-')
        ax[1].axhline(THRESHOLDS[variable] * -1, color='gray', ls='--')
        data.plot(x='time', y=f'{variable}_deviation', c='k', ax=ax[1], legend=False)

        # (Panel 2): annotations and plot formatting
        corrected = header['drift_correction'][variable]
        ax[1].text(0, 1.05, f'Drift correction: {corrected}', ha='left', transform=ax[1].transAxes)
        ax[1].set(ylabel='Sensor drift')

        if save_plot:
            raise NotImplementedError("Figure saving not implemented yet")
        else:
            plt.show()

        return outside_time, outside_index
