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
                    ACCUMULATION_MODES)
from datetime import datetime
import sys


class OTPEvaluation(object):
    '''
    Use to calculate the reachability between origins and destinations with OpenTripPlanner
    and to save the results to a csv file
    
    Parameters
    ----------
    router: name of the router to use for trip planning
    print_every_n_lines: optional, determines how often progress in processing origins/destination is written to stdout (default: 50)
    calculate_details: optional, if True, evaluates additional informations about itineraries (a little slower)
    '''   
    def __init__(self, router, print_every_n_lines=50, calculate_details=False, smart_search=False):
        self.otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router])
        self.router = self.otp.getRouter()
        self.request = self.otp.createRequest()
        # smart search needs details (esp. start/arrival times), 
        # even if not wanted explicitly
        if smart_search:
            calculate_details = True
        self.calculate_details = calculate_details
        self.smart_search = smart_search     
        self.arrive_by = False   
        self.print_every_n_lines = print_every_n_lines
    
    def setup(self, 
              date_time=None, max_time=None, max_walk=None, walk_speed=None, 
              bike_speed=None, clamp_wait=None, banned='', modes=None, 
              arrive_by=False, max_transfers=None, max_pre_transit_time=None,
              wheel_chair_accessible=False, max_slope=None):
        '''
        sets up the routing request
        
        Parameters
        ----------
        date_time: optional, datetime object, start respectively arrival time (if arriveby == True)
        modes: optional, string with comma-seperated traverse-modes to use
        banned: optional, string with comma-separated route specs, each of the format[agencyId]_[routeName]_[routeId]  
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
        
        if date_time is not None:
            self.request.setDateTime(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute, date_time.second) 
        
        self.request.setArriveBy(arrive_by)
        self.arrive_by = arrive_by
        self.request.setWheelChairAccessible(wheel_chair_accessible)
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
            
    def evaluate(self, times, max_time, origins_csv, destinations_csv, do_merge=False):
        '''
        evaluate the shortest paths between origins and destinations
        uses the routing options set in setup() (run it first!)
        
        Parameters
        ----------
        times: list of date times, the desired start/arrival times for evaluation
        origins_csv: file with origin points
        destinations_csv: file with destination points
        do_merge: merge the results over time, only keeping the best connections    
        max_time: maximum travel-time in seconds (the smaller this value, the smaller the shortest path tree, that has to be created; saves processing time)
        '''                   
    
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)   
        
        time_tables = []
        # create a time-table made of resultSets storing the next detected travel times (constantly updated)
        if self.arrive_by:
            time_note = 'arrival time '   
            if self.smart_search:
                for i in range(destinations.size()):
                    time_tables.append(origins.createResultSet())             
        else:
            time_note = 'start time ' 
            if self.smart_search:
                for i in range(origins.size()):
                    time_tables.append(destinations.createResultSet())            
        
        # dimension: time x individuals (origins resp. destinations)    
        results = []   
        
        # iterate all times
        for t, date_time in enumerate(times):    
            # compare seconds since epoch (different ways to get it from java/python date)
            epoch = datetime.utcfromtimestamp(0)
            time_since_epoch = (date_time - epoch).total_seconds()
            self.request.setDateTime(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute, date_time.second)            
            # has to be set every time after setting datetime (and also AFTER setting arriveby)
            self.request.setMaxTimeSec(max_time)
            msg = 'Starting evaluation of routes with ' + time_note + date_time.strftime(DATETIME_FORMAT)
                
            print msg
                          
            # first iteration no results -> no time table
            tt = time_tables if t > 0 and self.smart_search else None
                
            if self.arrive_by:
                results_dt = self._evaluate_arrival(origins, destinations, time_tables=tt)
            else:
                results_dt = self._evaluate_departures(origins, destinations, time_tables=tt)    
                
            for i, time_table in enumerate(time_tables): 
                if results_dt[i] is not None:               
                    time_table.update(results_dt[i])              
                        
            results.append(results_dt)    
    
        # merge the results
        if do_merge:
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
            
        return results
        

    def _evaluate_departures(self, origins, destinations, time_tables=None):     
        '''
        evaluate the shortest paths from origins to destinations
        uses the routing options set in setup() (run it first!)
        
        Parameters
        ----------
        origins: origin individuals
        destinations: destination individuals
        '''       
        
        i = -1 # in case no origins are processed (increased by 1 when printing total amount of origins)      
        origins_skipped = 0    
        start_time = self.request.getDateTime()
        result_sets = []

        for i, origin in enumerate(origins):
            spt = None
            skip_origin = False
            skip_destinations = None
            if time_tables is not None:
                min_next_time = time_tables[i].getMinStartTime()                
                if min_next_time is not None and min_next_time.compareTo(start_time) >= 0: # is None, if no routes were found at all
                    skip_origin = True
                else:
                    #TODO: check this later
                    skip_destinations = []
                    compare_times = time_tables[i].compareStartTime(start_time)
                    for c in compare_times:
                        skip = True if c >= 0 else False
                        skip_destinations.append(skip)
            if not skip_origin:
                # Set the origin of the request to this point and run a search
                self.request.setOrigin(origin)
                spt = self.router.plan(self.request)
            else:
                origins_skipped += 1
                
            result_set = None
            
            if spt is not None:
            
                result_set = destinations.createResultSet()
                result_set.setEvalItineraries(self.calculate_details)
                if skip_destinations is not None:
                    result_set.setSkipIndividuals(skip_destinations)
                spt.eval(result_set)   
                result_set.setSource(origin)  
                
            result_sets.append(result_set)                                     
                
            if not (i + 1) % self.print_every_n_lines:
                print "Processing: {} origins processed".format(i + 1)
                
        msg = "A total of {} origins processed".format(i + 1)
        if origins_skipped > 0:
            msg += ", {} origins skipped".format(origins_skipped)   
        print msg
        return result_sets
    
    def _evaluate_arrival(self, origins, destinations, time_tables=None):   
        '''
        evaluate the shortest paths from destinations to origins (reverse search)
        uses the routing options set in setup() (run it first!), arriveby has to be set
        
        Parameters
        ----------
        origins: origin individuals
        destinations: destination individuals
        '''        
     
        i = -1       
        destinations_skipped = 0    
        arrival_time = self.request.getDateTime()
        result_sets = []
         
        for i, destination in enumerate(destinations):
            spt = None
            skip_destination = False
            skip_origins = None
            if time_tables is not None:
                min_next_time = time_tables[i].getMinArrivalTime()                
                if min_next_time is not None and min_next_time.compareTo(arrival_time) >= 0: # is None, if no routes were found at all
                    skip_destination = True
                else:
                    #TODO: check this later
                    skip_origins = []
                    compare_times = time_tables[i].compareArrivalTime(arrival_time)
                    for c in compare_times:
                        skip = True if c >= 0 else False
                        skip_origins.append(skip)
            if not skip_destination:
                # Set the destination of the request to this point and run a search
                self.request.setDestination(destination)
                spt = self.router.plan(self.request)   
            else:
                destinations_skipped += 1
                
            result_set = None
                
            if spt is not None:
                result_set = origins.createResultSet()
                result_set.setEvalItineraries(self.calculate_details)
                if skip_origins is not None:
                    result_set.setSkipIndividuals(skip_origins)
                spt.eval(result_set)           
                result_set.setSource(destination) 
            
            result_sets.append(result_set)
             
            if not (i + 1) % self.print_every_n_lines:
                print "Processing: {} destinations processed".format(i+1)    
          
        msg = "A total of {} destinations processed".format(i+1)    
        if destinations_skipped > 0:
            msg += ", {} destinations skipped".format(destinations_skipped) 
        print msg
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
        
        header = [ 'origin id' ]
        do_aggregate = do_accumulate = False
        if not mode:
            header += [ 'destination id', 'travel time (sec)', 'boardings', 'walk/bike distance (m)', 'start time', 'arrival time', 'traverse modes', 'waiting time (sec)', 'elevation gained (m)', 'elevation lost (m)'] 
        elif mode in AGGREGATION_MODES.keys():
            header += [field + '-aggregated']   
            do_aggregate = True
        elif mode in ACCUMULATION_MODES.keys():
            header += [field + '-accumulated']
            do_accumulate = True       
        
        out_csv = self.otp.createCSVOutput()
        out_csv.setHeader(header)
        
        if do_accumulate:
            acc_result_set = self.origins.getEmptyResultSet()
            
        # used for sorting times, times not set will be treated as max values
        def sorter(a):
            if a[1] is None:
                return sys.maxint
            return a[1]
        
        for result_set in result_sets: 
            if result_set is None:
                continue
                
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
                starts = result_set.getStartTimes()#result_set.getSampledStartTimes()
                arrivals = result_set.getArrivalTimes()     
                modes = result_set.getTraverseModes()
                waiting_times = result_set.getWaitingTimes()
                elevationGained = result_set.getElevationGained()
                elevationLost = result_set.getElevationLost()
                
                if bestof is not None:
                    indices = [t[0] for t in sorted(enumerate(times), key=sorter)]
                    indices = indices[:bestof]
                else:
                    indices = range(len(times))
                for j in indices:
                    time = times[j]
                    if time is not None:
                        out_csv.addRow([origin_ids[j], 
                                        dest_ids[j], 
                                        times[j], 
                                        boardings[j], 
                                        walk_distances[j],
                                        starts[j], 
                                        arrivals[j], 
                                        modes[j], 
                                        waiting_times[j], 
                                        elevationGained[j], 
                                        elevationLost[j]])
#                     else:
#                         out_csv.addRow(['None'])
    
        if do_accumulate:
            results = acc_result_set.getResults()
            origin_ids = acc_result_set.getStringData(oid)   
            for i, res in enumerate(results):
                out_csv.addRow([origin_ids[i], res])
            
        out_csv.save(target_csv)
        print 'results written to "{}"'.format(target_csv)  
            