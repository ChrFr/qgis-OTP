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
                    ACCUMULATION_MODES, OUTPUT_DATE_FORMAT)
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
        self.request = self.otp.createManyToManyRequest()
        self.request.setEvalItineraries(calculate_details)
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
        self.request.setOrigins(origins)
        self.request.setDestinations(destinations)
        self.request.setLogProgress(self.print_every_n_lines)
        
        if len(times) > 1:
            cutoff = times[-1]
            self.request.setCutoffTime(cutoff.year, cutoff.month, cutoff.day, cutoff.hour, cutoff.minute, cutoff.second)
            
        if self.arrive_by:
            time_note = ' arrival time '             
        else:
            time_note = 'start time ' 
            
        # iterate all times
        results = [] # dimension (if not merged): times x targets (origins resp. destinations)
        for t, date_time in enumerate(times):    
            # compare seconds since epoch (different ways to get it from java/python date)
            epoch = datetime.utcfromtimestamp(0)
            time_since_epoch = (date_time - epoch).total_seconds()
            self.request.setDateTime(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute, date_time.second)            
            # has to be set every time after setting datetime (and also AFTER setting arriveby)
            self.request.setMaxTimeSec(max_time)
            
            msg = 'Starting evaluation of routes with ' + time_note + date_time.strftime(DATETIME_FORMAT)                
            print msg
                          
            results_dt = self.router.plan(self.request)
            
            # if there already was a calculation: merge it with new results
            if do_merge and len(results) > 0:
                for i, prev_result in enumerate(results[0]):
                    prev_result.merge(results_dt[i])    
            else:        
                results.append(results_dt)    
    
        # flatten the results
        results = [r for res in results for r in res] 
            
        return results      
        
    def results_to_csv(self, result_sets, target_csv, oid, did, mode=None, field=None, params=None, bestof=None, arrive_by=False, write_dest_data=False):         
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
        
        if len(result_sets) == 0:
            return
        
        header = [ 'origin id' ]
        do_aggregate = do_accumulate = False
        if not mode:
            header += [ 'destination id', 'travel time (sec)', 'boardings', 'walk/bike distance (m)', 
                       'start time', 'arrival time', 'start transit', 'arrival transit', 
                       'transit time', 'traverse modes', 'waiting time (sec)', 'elevation gained (m)', 
                       'elevation lost (m)'] 
        elif mode in AGGREGATION_MODES.keys():
            header += [field + '-aggregated']   
            do_aggregate = True
        elif mode in ACCUMULATION_MODES.keys():
            header += [field + '-accumulated']
            do_accumulate = True    
        
        # add header for data of destinations
        if write_dest_data:
            # all results share the same data names, cause they originate from the same csv file
            # you just have to find a valid result
            for i, res in enumerate(result_sets):
                if res is None:
                    continue
                if arrive_by:
                    data_fields = result_sets[i].getSource().getDataFields()
                else:
                    data_fields = result_sets[i].getPopulation().getDataFields()
                data_fields.remove(did)
                for field in data_fields:
                    header.append('destination_' + field)
                break
        
        out_csv = self.otp.createCSVOutput()
        out_csv.setHeader(header)
        
        if do_accumulate:
            acc_result_set = self.origins.getEmptyResultSet()
        
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
                                
            if arrive_by:
                destination = result_set.getSource()
                dest_id = destination.getStringData(did)      
            else:
                origin_id = result_set.getSource().getStringData(oid)       
                      
            if do_aggregate: 
                result_set.setAggregationMode(mode)
                # origin_id is known here, because !arriveby when aggregating
                aggregated = result_set.aggregate(field, params)
                out_csv.addRow([origin_id, aggregated])  
            
            else:      
                if bestof is not None:
                    results = result_set.getBestResults(bestof)
                else:
                    results = result_set.getResults();
                    
                for result in results: 
                    
                    if result is None: #unreachable
                        continue
                        
                    if arrive_by:
                        origin_id = result.getIndividual().getStringData(oid)
                    else:
                        destination = result.getIndividual()
                        dest_id = destination.getStringData(did)
                        
                    row = [origin_id,
                           dest_id, 
                           result.getTime(),
                           result.getBoardings(), 
                           result.getWalkDistance(),
                           result.getStartTime(OUTPUT_DATE_FORMAT), 
                           result.getArrivalTime(OUTPUT_DATE_FORMAT), 
                           result.getStartTransit(OUTPUT_DATE_FORMAT), 
                           result.getArrivalTransit(OUTPUT_DATE_FORMAT),
                           result.getTransitTime(),
                           result.getModes(), 
                           result.getWaitingTime(), 
                           result.getElevationGained(), 
                           result.getElevationLost()]
                    
                    if write_dest_data:    
                        for field in data_fields:
                            row.append(destination.getStringData(field))
                        
                    out_csv.addRow(row)
    
        if do_accumulate:
            results = acc_result_set.getResults()
            origin_ids = acc_result_set.getStringData(oid)   
            for i, res in enumerate(results):
                out_csv.addRow([origin_ids[i], res])
            
        out_csv.save(target_csv)
        print 'results written to "{}"'.format(target_csv)  
            