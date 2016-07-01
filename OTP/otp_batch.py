'''
Created on Mar 16, 2016

Batch processing of routes in OpenTripPlanner
to be used with Jython (Java Bindings!)

@author: Christoph Franke
'''
#!/usr/bin/jython
from org.opentripplanner.scripting.api import OtpsEntryPoint, OtpsCsvOutput
from org.opentripplanner.routing.core import TraverseMode
from org.opentripplanner.scripting.api import OtpsResultSet, OtpsAggregate
from config import (GRAPH_PATH, LONGITUDE_COLUMN, LATITUDE_COLUMN, 
                    ID_COLUMN, DATETIME_FORMAT, AGGREGATION_MODES,
                    ACCUMULATION_MODES, INFINITE)
from argparse import ArgumentParser
from datetime import datetime, timedelta
import sys
from xml.dom import minidom

class OTPEvaluation(object):
    '''
    Use to calculate the reachability between origins and destinations with OpenTripPlanner
    and to save the results to a csv file
    
    Parameters
    ----------
    router: name of the router to use for trip planning
    print_every_n_lines: optional, determines how often progress in processing origins/destination is written to stdout (default: 50)
    '''   
    def __init__(self, router, print_every_n_lines = 50, calculate_details = False):
        self.otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router])
        self.router = self.otp.getRouter()
        self.request = self.otp.createRequest()
        self.calculate_details = calculate_details
    
    def setup(self, 
              date_time, max_time=1800, max_walk=None, walk_speed=None, 
              bike_speed=None, clamp_wait=None, banned='', modes=None, 
              arrive_by=False, max_transfers=None, max_pre_transit_time=None,
              wheel_chair_accessible=False, max_slope=None):
        '''
        sets up the routing request
        
        Parameters
        ----------
        date_time: datetime object, start respectively arrival time (if arriveby == True)
        modes: optional, string with comma-seperated traverse-modes to use
        banned: optional, string with comma-separated route specs, each of the format[agencyId]_[routeName]_[routeId] 
        max_time: optional, maximum travel-time in seconds (the smaller this value, the smaller the shortest path tree, that has to be created; saves processing time) 
        arrive_by: optional, if True, given time is arrival time (reverts search tree)
        max_walk: optional, maximum distance (in meters) the user is willing to walk 
        walk_speed: optional, walking speed in m/s
        bike_speed: optional, bike speed in m/s
        clamp_wait: optional, maximum wait time in seconds the user is willing to delay trip start (-1 seems to mean it will be ignored)
        max_transfers: optional, maximum number of transfers (= boardings - 1)
        max_pre_transit_time: optional, maximum time in seconds of pre-transit travel when using drive-to-transit (park andride or kiss and ride)
        wheel_chair_accessible: optional, if True, the trip must be wheelchair accessible (defaults to False)
        max_slope: optional, maximum slope of streets for wheelchair trips
        '''
#         epoch = datetime.utcfromtimestamp(0)
#         epoch_seconds = (date_time - epoch).total_seconds() * 1000
#         self.request.setDateTime(long(epoch_seconds))  
        self.request.setDateTime(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute, date_time.second) 
        
        self.request.setArriveBy(arrive_by)
        self.request.setWheelChairAccessible(wheel_chair_accessible)
        # has to be set AFTER arriveby (request decides if negative weight or not by checking arriveby)
        if max_time is not None:
            self.request.setMaxTimeSec(long(max_time))
        if max_walk is not None:
            self.request.setMaxWalkDistance(max_walk)
        if walk_speed is not None:
            self.request.setWalkSpeedMs(walk_speed)
        if bike_speed is not None:
            self.request.setBikeSpeedMs(bike_speed)
        if clamp_wait is not None:
            self.request.setClampInitialWait(clamp_wait)
        if banned:
            self.request.setBannedRoutes(banned)
        if max_slope is not None:
            self.request.setMaxSlope(max_slope)
        if max_transfers is not None:
            self.request.setMaxTransfers(max_transfers)
        if max_pre_transit_time is not None:
            self.request.setMaxPreTransitTime(max_pre_transit_time)
             
        if modes:          
            self.request.setModes(modes)

    def evaluate_departures(self, origins_csv, destinations_csv):     
        '''
        evaluate the shortest paths from origins to destinations
        uses the routing options set in setup() (run it first!)
        
        Parameters
        ----------
        origins_csv: file with origin points
        destinations_csv: file with destination points
        '''   
    
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)       
        
        i = -1                  
        
        result_sets = []

        for i, origin in enumerate(origins):
            # Set the origin of the request to this point and run a search
            self.request.setOrigin(origin)
            spt = self.router.plan(self.request)
            
            if spt is not None:
            
                result_set = spt.getResultSet(destinations, self.calculate_details)   
                result_set.setSource(origin)
                result_sets.append(result_set)                                
                
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} origins processed".format(i+1)
                
        print "A total of {} origins processed".format(i+1)   
        return result_sets
    
    def evaluate_arrival(self, origins_csv, destinations_csv):   
        '''
        evaluate the shortest paths from destinations to origins (reverse search)
        uses the routing options set in setup() (run it first!), arriveby has to be set
        
        Parameters
        ----------
        origins_csv: file with origin points
        destinations_csv: file with destination points
        '''   
        self.origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        self.destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)        
     
        i = -1       
        result_sets=[]
         
        for i, destination in enumerate(self.destinations):
             
            # Set the origin of the request to this point and run a search
            self.request.setDestination(destination)
            spt = self.router.plan(self.request)            
             
            if spt is not None:
                result_set = spt.getResultSet(self.origins, self.calculate_details)            
                result_set.setSource(destination) 
                result_sets.append(result_set)
             
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} destinations processed".format(i+1)    
          
        print "A total of {} destinations processed".format(i+1)    
        return result_sets
        
    def results_to_csv(self, result_sets, target_csv, oid, did, mode=None, field=None, params=None, bestof=None, arrive_by=False):         
        '''
        write result sets to csv file, may aggregate/accumulate before writing results
        
        Parameters
        ----------
        result_sets: list of result_sets
        target_csv: filename of the file to write to
        oid: name of the field of the origin ids
        did: name of the field of the destination ids
        mode: optional, the aggregation or accumulation mode (see config.AGGREGATION_MODES resp. config.ACCUMULATION_MODES)
        field: optional, the field to aggregate/accumulate
        params: optional, params needed by the aggregation/accumulation mode (e.g. thresholds)
        '''   
        print 'post processing results...'
        
        header = [ 'origin-id' ]
        do_aggregate = do_accumulate = False
        if not mode:
            header += [ 'destination-id', 'travel-time (sec)', 'boardings', 'walk-distance (m)', 'start-time', 'arrival-time', 'traverse-modes', 'waiting-time (sec)'] 
        elif mode in AGGREGATION_MODES:
            header += [field + '-aggregated']   
            do_aggregate = True
        elif mode in ACCUMULATION_MODES:
            header += [field + '-accumulated']
            do_accumulate = True       
        
        out_csv = self.otp.createCSVOutput()
        out_csv.setHeader(header)
        
        if do_accumulate:
            acc_result_set = self.origins.getEmptyResultSet()
            
        def sorter(a):
            if a[1] is None:
                return sys.maxint
            return a[1]
        
        for result_set in result_sets: 
                
            if do_accumulate:
                if acc_result_set is None:
                    acc_result_set = result_set
                else:
                    result_set.setAccumulationMode(mode)
                    result_set.accumulate(acc_result_set, field, params)
                continue
                    
            times = result_set.getTimes()
            
            if arrive_by:
                dest_id = result_set.getSource().getStringData(did)          
                dest_ids = [dest_id for x in range(len(times))]      
                origin_ids = result_set.getStringData(oid)     
            else:
                origin_id = result_set.getSource().getStringData(oid)          
                origin_ids = [origin_id for x in range(len(times))]  
                dest_ids = result_set.getStringData(did)     
             
            if do_aggregate:
                result_set.setAggregationMode(mode)
                aggregated = result_set.aggregate(field, params)
                out_csv.addRow([origin_id, aggregated])  
            
            else:            
                boardings = result_set.getBoardings()
                walk_distances = result_set.getWalkDistances()
                starts = result_set.getStartTimes()
                arrivals = result_set.getArrivalTimes()     
                modes = result_set.getTraverseModes()
                waiting_times = result_set.getWaitingTimes()
                if bestof is not None:
                    indices = [t[0] for t in sorted(enumerate(times), key=sorter)]
                    indices = indices[:bestof]
                else:
                    indices = range(len(times))
                for j in indices:
                    time = times[j]
                    if time is not None:
                        out_csv.addRow([origin_ids[j], dest_ids[j], times[j], boardings[j], walk_distances[j], starts[j], arrivals[j], modes[j], waiting_times[j]])
    
        if do_accumulate:
            results = acc_result_set.getResults()
            origin_ids = acc_result_set.getStringData(oid)   
            for i, res in enumerate(results):
                out_csv.addRow([origin_ids[i], res])
            
        out_csv.save(target_csv)
        print 'results written to "{}"'.format(target_csv)  
            
    
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
    if len(time_batch) > 0 and time_batch[0].getElementsByTagName('active')[0].firstChild.data == 'True':
        dt_end = time_batch[0].getElementsByTagName('datetime_end')[0].firstChild.data
        date_time_end = datetime.strptime(dt_end, DATETIME_FORMAT)
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
    
    # iterate over all times
    for date_time in date_times:        
        otpEval = OTPEvaluation(router, print_every_n_lines, calculate_details)    
        otpEval.setup(date_time, 
                      max_time=max_time, 
                      max_walk=max_walk, 
                      walk_speed=walk_speed, 
                      bike_speed=bike_speed, 
                      clamp_wait=clamp_wait, 
                      modes=traverse_modes, 
                      arrive_by=arrive_by,
                      max_transfers=max_transfers,
                      max_pre_transit_time=pre_transit_time,
                      wheel_chair_accessible=wheel_chair_accessible,
                      max_slope=max_slope)       
        
        
        
        if arrive_by:
            results.append(otpEval.evaluate_arrival(origins_csv, destinations_csv))        
        else:
            results.append(otpEval.evaluate_departures(origins_csv, destinations_csv))     
    
    # merge results over time, if aggregation or accumulation is requested or bestof
    if mode is not None or bestof:
        merged_results = []
        for n_results_per_time in range(len(results[0])):
            merged_result = results[0][n_results_per_time]
            for n_times in range(1, len(results)):
                res = results[n_times][n_results_per_time]
                merged_result = merged_result.merge(res)
            merged_results.append(merged_result)
        results = merged_results
    else:            
        # flatten the results
        results = [r for res in results for r in res] 
                
    otpEval.results_to_csv(results, target_csv, oid, did, mode, field, params, bestof, arrive_by=arrive_by) 
        
