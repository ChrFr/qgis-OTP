'''
Created on Mar 16, 2016

Batch processing of routes in OpenTripPlanner
to be used with Jython (Java Bindings!)

@author: Christoph Franke
'''
#!/usr/bin/jython
from config import (DATETIME_FORMAT, INFINITE)
from otp_eval import OTPEvaluation
from argparse import ArgumentParser
from datetime import datetime, timedelta
import sys
from xml.dom import minidom

if __name__ == '__main__':
    parser = ArgumentParser(description="Batch Analysis with OpenTripPlanner")
    
    parser.add_argument('--origins', action="store",
                        help="csv file containing the origin points with at least lat/lon and id",
                        dest="origins", required=True)    
    
    parser.add_argument('--destinations', action="store",
                        help="csv file containing the destination points with at least lat/lon and id",
                        dest="destinations", required=True)    
    
    parser.add_argument('--config', action="store",
                        help="xml file containing the configuration for trip planning (for xml-structure see Config.setting_struct)",
                        dest="config_file", required=True)       
    
    parser.add_argument('--target', action="store",
                        help="target csv file the results will be written to (overwrites existing file)",
                        dest="target", default="otp_results.csv")        
    
    parser.add_argument('--nlines', action="store",
                        help="determines how often progress in processing origins/destination is written to stdout (write every n results)",
                        dest="nlines", default=50, type=int)       
    
        
    parser.set_defaults(arriveby=False)
    
    options = parser.parse_args()
    
    origins_csv = options.origins
    destinations_csv = options.destinations
    target_csv = options.target    
    print_every_n_lines = options.nlines 
    
    # read configuration from xml-file
    # unfortunately you can't use lxml in jython (because parts are compiled in c) as in Config (config.py)
    # so i had to use xml.minidom instead (ugly but inevitable)
    
    # config.read(options.config_file)
    
    dom = minidom.parse(options.config_file)
    config = dom.firstChild
    
    # router
    router_config = config.getElementsByTagName('router_config')[0]
    router = router_config.getElementsByTagName('router')[0].firstChild.data
    max_time = long(router_config.getElementsByTagName('max_time_min')[0].firstChild.data) 
    # max value -> no need to set it up (is Long.MAX_VALUE in OTP by default), unfortunately you can't pass OTP Long.MAX_VALUE, messes up routing
    if max_time >= INFINITE:
        max_time = None 
    else:
        max_time *= 60 # OTP needs this one in seconds
    max_walk = float(router_config.getElementsByTagName('max_walk_distance')[0].firstChild.data)
    # max value -> no need to set it up (is Double.MAX_VALUE in OTP by default), same as max_time
    if max_walk >= INFINITE:
        max_walk = None    
    walk_speed = float(router_config.getElementsByTagName('walk_speed')[0].firstChild.data)
    bike_speed = float(router_config.getElementsByTagName('bike_speed')[0].firstChild.data)
    clamp_wait = int(router_config.getElementsByTagName('clamp_initial_wait_min')[0].firstChild.data) 
    if clamp_wait > 0:
        clamp_wait *= 60   
    pre_transit_time = int(router_config.getElementsByTagName('pre_transit_time_min')[0].firstChild.data) 
    pre_transit_time *= 60
    max_transfers = int(router_config.getElementsByTagName('max_transfers')[0].firstChild.data) 
    wheel_chair_accessible = router_config.getElementsByTagName('wheel_chair_accessible')[0].firstChild.data == 'True'
    max_slope = float(router_config.getElementsByTagName('max_slope')[0].firstChild.data) 
        
    traverse_modes = router_config.getElementsByTagName('traverse_modes')[0].firstChild
    if traverse_modes:
        traverse_modes = traverse_modes.data
    
    # layer ids
    origin = config.getElementsByTagName('origin')[0]
    oid = origin.getElementsByTagName('id_field')[0].firstChild.data
    destination = config.getElementsByTagName('destination')[0]
    did = destination.getElementsByTagName('id_field')[0].firstChild.data
    
    # times
    times = config.getElementsByTagName('time')[0]
    dt = times.getElementsByTagName('datetime')[0].firstChild.data
    date_times = [datetime.strptime(dt, DATETIME_FORMAT)]
    arrive_by = times.getElementsByTagName('arrive_by')[0].firstChild.data == 'True'
    time_batch = times.getElementsByTagName('time_batch')
    smart_search = False
    if len(time_batch) > 0 and time_batch[0].getElementsByTagName('active')[0].firstChild.data == 'True':
        smart_search = time_batch[0].getElementsByTagName('smart_search')[0].firstChild.data == 'True'
        
        dt_end = time_batch[0].getElementsByTagName('datetime_end')[0].firstChild.data
        date_time_end = datetime.strptime(dt_end, DATETIME_FORMAT)
#         if smart_search:
#             time_step = 1
#         else:
        time_step = int(time_batch[0].getElementsByTagName('time_step')[0].firstChild.data)
        
        dt = date_times[0]
        step_delta = timedelta(0, time_step * 60) # days, seconds ...
        while dt < date_time_end:
            dt += step_delta
            date_times.append(dt)                            
    
    # post processing
    postproc = config.getElementsByTagName('post_processing')[0]
    bestof = postproc.getElementsByTagName('best_of')
    if len(bestof) > 0 and bestof[0].firstChild: # avoid error if key does not exist or data is empty
        bestof = int(bestof[0].firstChild.data)
    else:
        bestof = None
        
    details = postproc.getElementsByTagName('details')[0].firstChild.data
    calculate_details = details == 'True' # avoid error if key does not exist or data is empty
        
    mode = field = params = None
    agg_acc = postproc.getElementsByTagName('aggregation_accumulation')
    if len(agg_acc) > 0:  # avoid error if key does not exist
        agg_acc = agg_acc[0]
        active = agg_acc.getElementsByTagName('active')[0].firstChild.data
        if active == 'True':
            mode = agg_acc.getElementsByTagName('mode')[0].firstChild.data
            params = agg_acc.getElementsByTagName('params')[0].firstChild
            if params:
                params = params.data
                params = [float(x) for x in params.split(',')]
            field = agg_acc.getElementsByTagName('processed_field')[0].firstChild.data
            
    # results will be stored 2 dimensional to determine to which time the results belong, flattened later
    results = []
    
    otpEval = OTPEvaluation(router, print_every_n_lines, calculate_details, smart_search)    
    
    otpEval.setup(max_walk=max_walk, 
                  walk_speed=walk_speed, 
                  bike_speed=bike_speed, 
                  clamp_wait=clamp_wait, 
                  modes=traverse_modes, 
                  arrive_by=arrive_by,
                  max_transfers=max_transfers,
                  max_pre_transit_time=pre_transit_time,
                  wheel_chair_accessible=wheel_chair_accessible,
                  max_slope=max_slope)     
    
    # merge results over time, if aggregation or accumulation is requested or bestof
    do_merge = True if mode is not None or bestof else False
    
    results = otpEval.evaluate(date_times, long(max_time), origins_csv, destinations_csv, do_merge=do_merge)
                
    otpEval.results_to_csv(results, target_csv, oid, did, mode, field, params, bestof, arrive_by=arrive_by) 
        
