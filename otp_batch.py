'''
Created on Mar 16, 2016

Batch processing of routes in OpenTripPlanner
to be used with Jython (Java Bindings!)

@author: Christoph Franke
'''
#!/usr/bin/jython
from config import (DATETIME_FORMAT, INFINITE)
from otp_eval import OTPEvaluation, CSVWriter
from argparse import ArgumentParser
from datetime import datetime, timedelta
import sys
from config import Config

if __name__ == '__main__':
    parser = ArgumentParser(description="Batch Analysis with OpenTripPlanner")

    parser.add_argument('--origins', action="store",
                        help="csv file containing the origin points " +
                        "with at least lat/lon and id",
                        dest="origins", required=True)

    parser.add_argument('--destinations', action="store",
                        help="csv file containing the destination points " +
                        "with at least lat/lon and id",
                        dest="destinations", required=True)

    parser.add_argument('--config', action="store",
                        help="xml file containing the configuration for trip " +
                        "planning (for xml-structure see Config.setting_struct)",
                        dest="config_file", required=True)

    parser.add_argument('--target', action="store",
                        help="target csv file the results will be written to " +
                        "(overwrites existing file)",
                        dest="target", default="otp_results.csv")

    parser.add_argument('--nlines', action="store",
                        help="determines how often progress in processing " +
                        "origins/destination is written to stdout " +
                        "(write every n results)",
                        dest="nlines", default=50, type=int)


    parser.set_defaults(arriveby=False)

    options = parser.parse_args()

    origins_csv = options.origins
    destinations_csv = options.destinations
    target_csv = options.target
    print_every_n_lines = options.nlines

    # read configuration from xml-file
    # unfortunately you can't use lxml in jython (because parts are compiled
    # in c) as in Config (config.py)
    # so i had to use xml.minidom instead (ugly but inevitable)

    # config.read(options.config_file)

    config = Config()
    config.read(options.config_file)

    # router
    router_config = config.settings['router_config']
    graph_path = router_config['path']
    router = router_config['router']
    max_time = long(router_config['max_time_min'])
    # max value -> no need to set it up (is Long.MAX_VALUE in OTP by default),
    # unfortunately you can't pass OTP Long.MAX_VALUE, messes up routing
    if max_time >= INFINITE:
        max_time = None
    else:
        max_time *= 60 # OTP needs this one in seconds
    max_walk = float(router_config['max_walk_distance'])
    # max value -> no need to set it up (is Double.MAX_VALUE in OTP by default),
    # same as max_time
    if max_walk >= INFINITE:
        max_walk = None
    walk_speed = float(router_config['walk_speed'])
    bike_speed = float(router_config['bike_speed'])
    clamp_wait = int(router_config['clamp_initial_wait_min'])
    if clamp_wait > 0:
        clamp_wait *= 60
    pre_transit_time = int(router_config['pre_transit_time_min'])
    pre_transit_time *= 60
    max_transfers = int(router_config['max_transfers'])
    wheel_chair_accessible = router_config['wheel_chair_accessible'] == 'True'
    max_slope = float(router_config['max_slope'])

    traverse_modes = router_config['traverse_modes']

    # layer ids
    origin = config.settings['origin']
    oid = origin['id_field']
    destination = config.settings['destination']
    did = destination['id_field']

    # times
    times = config.settings['time']
    dt = times['datetime']
    date_times = [datetime.strptime(dt, DATETIME_FORMAT)]
    arrive_by = times['arrive_by'] == 'True'
    smart_search = False
    if 'time_batch' in times and times['time_batch']['active'] == 'True':

        time_batch = times['time_batch']
        smart_search = time_batch['smart_search'] == 'True'

        dt_end = time_batch['datetime_end']
        date_time_end = datetime.strptime(dt_end, DATETIME_FORMAT)
#         if smart_search:
#             time_step = 1
#         else:
        time_step = int(time_batch['time_step'])

        dt = date_times[0]
        step_delta = timedelta(0, time_step * 60) # days, seconds ...
        while True:
            dt += step_delta
            if dt > date_time_end:
                break
            date_times.append(dt)

    # post processing
    postproc = config.settings['post_processing']
    if 'best_of' in postproc and len(postproc['best_of']) > 0:
        bestof = int(postproc['best_of'])
    else:
        bestof = None

    details = postproc['details']
    calculate_details = details == 'True' # avoid error if key does not exist or
                                          # data is empty

    dest_data = postproc['dest_data']
    write_dest_data = dest_data == 'True' # avoid error if key does not exist or
                                          # data is empty

    mode = field = params = None
    if 'aggregation_accumulation' in postproc:
        agg_acc = postproc['aggregation_accumulation']
        active = agg_acc['active']
        if active == 'True':
            mode = agg_acc['mode']
            params = agg_acc['params']
            if isinstance(params, list):
                params = [float(x) for x in params]
            if isinstance(params, str):
                params = [float(x) for x in params.split(',')]
            field = agg_acc['processed_field']

    # system settings
    sys_settings = config.settings['system']
    n_threads = int(sys_settings['n_threads'])

    # results will be stored 2 dimensional to determine to which time the
    # results belong, flattened later
    results = []

    otpEval = OTPEvaluation(graph_path, router, print_every_n_lines,
                            calculate_details, smart_search)

    otpEval.setup(max_walk=max_walk,
                  walk_speed=walk_speed,
                  bike_speed=bike_speed,
                  clamp_wait=clamp_wait,
                  modes=traverse_modes,
                  arrive_by=arrive_by,
                  max_transfers=max_transfers,
                  max_pre_transit_time=pre_transit_time,
                  wheel_chair_accessible=wheel_chair_accessible,
                  max_slope=max_slope,
                  n_threads=n_threads)

    # merge results over time, if aggregation or accumulation is requested or
    # bestof
    do_merge = True if mode is not None or bestof else False

    csv_writer = CSVWriter(target_csv, oid, did, mode, field,
                           params, bestof, arrive_by=arrive_by,
                           write_dest_data=write_dest_data,
                           calculate_details=calculate_details)

    results = otpEval.evaluate(date_times, long(max_time),
                               origins_csv, destinations_csv,
                               csv_writer,
                               do_merge=do_merge)

    #otpEval.results_to_csv(results, target_csv, oid, did, mode, field, params,
    #                       bestof, arrive_by=arrive_by,
    #                       write_dest_data=write_dest_data)

