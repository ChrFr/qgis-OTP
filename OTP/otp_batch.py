'''
Created on Mar 16, 2016

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
from datetime import datetime
from java.lang import Double
from java.lang import Long
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
    def __init__(self, router, print_every_n_lines = 50):
        self.otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router])
        self.router = self.otp.getRouter()
        self.request = self.otp.createRequest()
    
    def setup(self, date_time, max_time=1800, max_walk=None, walk_speed=None, bike_speed=None, clamp_wait=None, banned='', modes=None, arrive_by=False):
        '''
        sets up the routing request
        
        Parameters
        ----------
        date_time: time object (time.struct_time), start respectively arrival time (if arriveby == True)
        modes: optional, string with comma-seperated traverse-modes to use
        banned: optional, string with comma-separated route specs, each of the format[agencyId]_[routeName]_[routeId] 
        max_time: optional, maximum travel-time in seconds (the smaller this value, the smaller the shortest path tree, that has to be created; saves processing time) 
        arrive_by: optional, if True, given time is arrival time (reverts search tree)
        max_walk: optional, maximum distance (in meters) the user is willing to walk 
        walk_speed: optional, walking speed in m/s
        bike_speed: optional, bike speed in m/s
        clamp_wait: optional, maximum wait time in seconds the user is willing to delay trip start (-1 seems to mean it will be ignored)
        '''
#         epoch = datetime.utcfromtimestamp(0)
#         epoch_seconds = (date_time - epoch).total_seconds() * 1000
#         self.request.setDateTime(long(epoch_seconds))        
        self.request.setDateTime(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute, date_time.second) 
        self.request.setArriveBy(arrive_by)
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
             
        if modes:          
            self.request.setModes(modes)

    def evaluate_departures(self, origins_csv, destinations_csv, target_csv, oid, did, field=None, mode=None, params=None, bestof=None):     
        '''
        evaluate the shortest paths from origins to destinations
        uses the routing options set in setup() (run it first!)
        
        Parameters
        ----------
        origins_csv: file with origin points
        destinations_csv: file with destination points
        target_csv: filename of the file to write to
        oid: name of the field of the origin ids
        did: name of the field of the destination ids
        field: the field to aggregate
        mode: the aggregation mode (see config.AGGREGATION_MODES)
        params: optional, params needed by the aggregation mode (e.g. threshold)
        '''   
    
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)       
        
        i = -1                  
        
        header = [ 'origin_id' ]
        if not field or len(field) == 0:
            header += [ 'destination_id', 'travel_time', 'start_time', 'arrival_time','boardings', 'walk_distance'] 
        else:
            header += [field + '_aggregated']            
        out_csv = self.otp.createCSVOutput()
        out_csv.setHeader(header)

        for i, origin in enumerate(origins):
            # Set the origin of the request to this point and run a search
            self.request.setOrigin(origin)
            spt = self.router.plan(self.request)
            
            if spt is not None:
            
                result_set = spt.getResultSet(destinations, field)            
                
                origin_id = origin.getStringData(oid)    
                times = result_set.getTimes()
                boardings = result_set.getBoardings()
                dids = result_set.getStringData(did)     
                walk_distances = result_set.getWalkDistances()
                starts = result_set.getStartTimes()
                arrivals = result_set.getArrivalTimes()                        
                
                if field:
                    result_set.setAggregationMode(mode)
                    aggregated = result_set.aggregate(params)
                    out_csv.addRow([origin_id, aggregated]) 
                
                else:          
                    if bestof is not None:
                        indices = [t[0] for t in sorted(enumerate(times), key=lambda x:x[1])]
                        indices = indices[:bestof]
                    else:
                        indices = range(len(times))
                    for j in indices:
                        time = times[j]
                        if time < Double.MAX_VALUE:
                            out_csv.addRow([origin_id, dids[j], times[j], starts[j], arrivals[j], boardings[j], walk_distances[j]])                
                
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} origins processed".format(i+1)
                
        print "A total of {} origins processed".format(i+1)   
        
        out_csv.save(target_csv)
        print 'results written to "{}"'.format(target_csv)  
    
    def evaluate_arrival(self, origins_csv, destinations_csv, target_csv, oid, did, field=None, mode=None, params=None, bestof=None):   
        '''
        evaluate the shortest paths from destinations to origins (reverse search)
        uses the routing options set in setup() (run it first!), arriveby has to be set
        
        Parameters
        ----------
        origins_csv: file with origin points
        destinations_csv: file with destination points
        target_csv: filename of the file to write to
        oid: name of the field of the origin ids
        did: name of the field of the destination ids
        field: the field to accumulate
        mode: the accumulation mode (see config.ACCUMULATION_MODES)
        params: optional,params needed by the accumulation mode (e.g. threshold)
        '''   
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)        
    
        i = -1       
        
        header = [ 'origin_id' ]
        if not field or len(field) == 0:
            header += [ 'destination_id', 'travel_time', 'start_time', 'arrival_time','boardings', 'walk_distance'] 
        else:
            header += [field + '_accumulated']            
        out_csv = self.otp.createCSVOutput()
        out_csv.setHeader(header)
        
        for i, destination in enumerate(destinations):
            
            # Set the origin of the request to this point and run a search
            self.request.setDestination(destination)
            spt = self.router.plan(self.request)            
            
            if spt is not None:
                result_set = spt.getResultSet(origins, field)             
            
                dest_id = destination.getStringData(did)    
                times = result_set.getTimes()
                boardings = result_set.getBoardings()
                oids = result_set.getStringData(oid)     
                walk_distances = result_set.getWalkDistances()
                starts = result_set.getStartTimes()
                arrivals = result_set.getArrivalTimes()
            
                # ToDo: accumulate with empty set
                if field:
                    pass
    #                 accumulated = resultSet.accumulate()
    #                 out_csv.addRow([origin_id, accumulated]) 
                
                else:            
                    for j, t in enumerate(times):
                        if t != Double.MAX_VALUE:
                            out_csv.addRow([oids[j], dest_id, times[j], starts[j], arrivals[j], boardings[j], walk_distances[j]])          
            
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} destinations processed".format(i+1)    
         
        print "A total of {} destinations processed".format(i+1)    
        
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
    max_time = long(router_config.getElementsByTagName('maxTimeMin')[0].firstChild.data) 
    # max value -> no need to set it up (is Long.MAX_VALUE in OTP by default), unfortunately you can't pass OTP Long.MAX_VALUE, messes up routing
    if max_time >= INFINITE:
        max_time = None 
    else:
        max_time *= 60 # OTP needs this one in seconds
    max_walk = float(router_config.getElementsByTagName('maxWalkDistance')[0].firstChild.data)
    # max value -> no need to set it up (is Double.MAX_VALUE in OTP by default), same as max_time
    if max_walk >= INFINITE:
        max_walk = None    
    walk_speed = float(router_config.getElementsByTagName('walkSpeed')[0].firstChild.data)
    bike_speed = float(router_config.getElementsByTagName('bikeSpeed')[0].firstChild.data)
    clamp_wait = int(router_config.getElementsByTagName('clampInitialWaitSec')[0].firstChild.data) 
    if clamp_wait == -1:
        clamp_wait = None # i think -1 initial waits are ignored (same like infinite), is -1 by default in OTP   
    banned = router_config.getElementsByTagName('banned_routes')[0].firstChild # None if no text entry
    if banned:
        banned = banned.data   
        
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
    date_time = datetime.strptime(dt, DATETIME_FORMAT)
    ab = times.getElementsByTagName('arrive_by')[0].firstChild.data
    arrive_by = ab == 'True' or ab == True
    
    # post processing
    postproc = config.getElementsByTagName('post_processing')[0]
    bestof = postproc.getElementsByTagName('best_of')[0].firstChild
    if bestof:
        bestof = bestof.data
        
    agg_acc = postproc.getElementsByTagName('aggregation_accumulation')[0]
    mode = field = params = None
    active = agg_acc.getElementsByTagName('active')[0].firstChild.data
    if active == 'True' or active == True:
        mode = agg_acc.getElementsByTagName('mode')[0].firstChild.data
        params = agg_acc.getElementsByTagName('params')[0].firstChild.data
        params = [float(x) for x in params.split(',')]
        field = agg_acc.getElementsByTagName('processed_field')[0].firstChild.data
        
    otpEval = OTPEvaluation(router, print_every_n_lines)    
    otpEval.setup(date_time, 
                  max_time=max_time, 
                  max_walk=max_walk, 
                  walk_speed=walk_speed, 
                  bike_speed=bike_speed, 
                  clamp_wait=clamp_wait, 
                  banned=banned, 
                  modes=traverse_modes, 
                  arrive_by=arrive_by)
    
    #if aggregation_mode and arrive_by:
        #raise ValueError('aggregation only works with departure analysis')
            
    #if accumulation_mode and not arrive_by:
        #raise ValueError('accumulation only works with arriveby analysis')   
    
    #if aggregation_mode and accumulation_mode:
        #raise ValueError("you can't do aggregation and accumulation at the same time")    
    
    #if (aggregation_mode or accumulation_mode) and not field:
        #raise ValueError("the name of the field you want to aggregate/accumulate is missing")  
    
    if arrive_by:
        otpEval.evaluate_arrival(origins_csv, destinations_csv, target_csv, oid, did, field=field, mode=mode, params=params, bestof=bestof) 
    else:
        otpEval.evaluate_departures(origins_csv, destinations_csv, target_csv, oid, did, field=field, mode=mode, params=params, bestof=bestof)
