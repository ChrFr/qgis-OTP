'''
Created on Mar 16, 2016

@author: Christoph Franke
'''
#!/usr/bin/jython
from org.opentripplanner.scripting.api import OtpsEntryPoint, OtpsCsvOutput
from org.opentripplanner.routing.core import TraverseMode
from org.opentripplanner.scripting.api import OtpsResultSet, OtpsAggregate
from config import GRAPH_PATH, LONGITUDE_COLUMN, LATITUDE_COLUMN, ID_COLUMN, DATETIME_FORMAT, AGGREGATION_MODES
from argparse import ArgumentParser
import time
from java.lang import Double

router_name = ''

class OTPEvaluation(object):
    '''
    Use to calculate the reachability between origins and destinations with OpenTripPlanner
    and to save the results to a csv file
    
    Parameters
    ----------
    print_every_n_lines: optional, determines how often progress in processing origins/destination is written to stdout (default: 50)
    '''   
    def __init__(self, print_every_n_lines = 50):
        self.otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router_name ])
        self.router = self.otp.getRouter()
        self.request = self.otp.createRequest()
    
    def setup(self, date_time, max_time=1800, modes=None, arriveby=False):
        '''
        sets up the routing request
        
        Parameters
        ----------
        date_time: time object (time.struct_time), start respectively arrival time (if arriveby == True)
        modes: optional, list of traverse-modes to use
        max_time: optional, maximum travel-time (the smaller this value, the smaller the shortest path tree, that has to be created; saves processing time) 
        arriveby: optional, if True, given time is arrival time (reverts search tree)
        '''
        self.request.setDateTime(date_time.tm_year, date_time.tm_mon, date_time.tm_mday, date_time.tm_hour, date_time.tm_min, date_time.tm_sec)         
        self.request.setArriveBy(arriveby)
        # has to be set AFTER arriveby (request decides if negative weight or not by checking arriveby)
        self.request.setMaxTimeSec(max_time)
        
        if modes:          
            self.request.setModes(','.join(modes))

    def evaluate_departures(self, origins_csv, destinations_csv, target_csv, oid, did, aggregate_field=None, mode=None, value=None):     
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
        accumulate_field: the field to aggregate
        mode: the aggregation mode (see config.AGGREGATION_MODES)
        value: optional, a value needed by the aggregation mode (e.g. threshold)
        '''   
    
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)       
        
        i = -1                  
        
        header = [ 'origin_id' ]
        if not aggregate_field or len(aggregate_field) == 0:
            header += [ 'destination_id', 'travel_time', 'start_time', 'arrival_time','boardings', 'walk_distance'] 
        else:
            header += [aggregate_field + '_aggregated']            
        out_csv = self.otp.createCSVOutput()
        out_csv.setHeader(header)

        for i, origin in enumerate(origins):
            # Set the origin of the request to this point and run a search
            self.request.setOrigin(origin)
            spt = self.router.plan(self.request)
            
            resultSet = None if spt is None else spt.getResultSet(destinations, aggregate_field)
            
            origin_id = origin.getStringData(oid)    
            times = resultSet.getTimes()
            boardings = resultSet.getBoardings()
            dids = resultSet.getStringData(did)     
            walk_distance = resultSet.getWalkDistances()
            
            if aggregate_field:
                resultSet.setAggregationMode(mode)
                aggregated = resultSet.aggregate()
                out_csv.addRow([origin_id, aggregated]) 
            
            else:            
                for j, t in enumerate(times):
                    if t != Double.MAX_VALUE:
                        out_csv.addRow([origin_id, dids[j], times[j], "", "", boardings[j], walk_distance[j]])                
                
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} origins processed".format(i+1)
                
        print "A total of {} origins processed".format(i+1)   
        
        out_csv.save(target_csv)
        print 'results written to "{}"'.format(target_csv)  
    
    def evaluate_arrival(self, origins_csv, destinations_csv, target_csv, oid, did, accumulate_field=None, mode=None, value=None):   
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
        accumulate_field: the field to accumulate
        mode: the accumulation mode (see config.ACCUMULATION_MODES)
        value: optional, a value needed by the accumulation mode (e.g. threshold)
        '''   
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)        
    
        i = -1       
        
        header = [ 'origin_id' ]
        if not aggregate_field or len(aggregate_field) == 0:
            header += [ 'destination_id', 'travel_time', 'start_time', 'arrival_time','boardings', 'walk_distance'] 
        else:
            header += ['origin_id',  accumulate_field + '_accumulated']            
        out_csv = self.otp.createCSVOutput()
        out_csv.setHeader(header)
        
        for i, destination in enumerate(destinations):
            
            # Set the origin of the request to this point and run a search
            self.request.setDestination(destination)
            spt = self.router.plan(self.request)
            
            resultSet = None if spt is None else spt.getResultSet(origins, accumulate_field)             
            
            dest_id = destination.getStringData(oid)    
            times = resultSet.getTimes()
            boardings = resultSet.getBoardings()
            oids = resultSet.getStringData(did)     
            walk_distance = resultSet.getWalkDistances()
            
            # ToDo: accumulate wit empty set
            if accumulate_field:
                pass
#                 accumulated = resultSet.accumulate()
#                 out_csv.addRow([origin_id, accumulated]) 
            
            else:            
                for j, t in enumerate(times):
                    if t != Double.MAX_VALUE:
                        out_csv.addRow([oids[j], dest_id, times[j], "", "", boardings[j], walk_distance[j]])          
            
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} destinations processed".format(i+1)    
         
        print "A total of {} destinations processed".format(i+1)    
        
        out_csv.save(target_csv)
        print 'results written to "{}"'.format(target_csv)     
    
if __name__ == '__main__':
    parser = ArgumentParser(description="Batch Analysis with OpenTripPlanner")

    parser.add_argument('-r', '--router', action="store",
                        help='name of the router',
                        dest="router", required=True)    
    
    parser.add_argument('--origins', action="store",
                        help="csv file containing the origin points with at least lat/lon and id",
                        dest="origins", required=True)    
    
    parser.add_argument('--oid', action="store",
                        help="id field in origins file",
                        dest="oid", default=ID_COLUMN)    
    
    parser.add_argument('--destinations', action="store",
                        help="csv file containing the destination points with at least lat/lon and id",
                        dest="destinations", required=True)        
    
    parser.add_argument('--did', action="store",
                        help="id field in destinations file (Warning: if not given, resulting destination-ids are unknown)",
                        dest="did", default=ID_COLUMN)   
    
    parser.add_argument('--target', action="store",
                        help="target csv file the results will be saved in (overwrites existing file)",
                        dest="target", default="otp_results.csv")      
    
    parser.add_argument('--datetime', action="store",
                        help="departure/arrival time (format see config.py: day/month/year-hours:minutes:seconds)",
                        dest="datetime", default=time.strftime(DATETIME_FORMAT))      
    
    parser.add_argument('--maxtime', action="store",
                        help="max. travel time (in seconds)",
                        dest="max_time", default=1800, type=int)  
    
    parser.add_argument('--modes', action="store",
                        help="list of modes to use (e.g 'WALK' 'BUS' 'RAIL'",
                        nargs='+',
                        dest="modes")   
    
    parser.add_argument('--arrival', action="store_true",
                        help="given time is arrival time",
                        dest="arriveby")      
    
    parser.add_argument('--nlines', action="store",
                        help="determines how often progress in processing origins/destination is written to stdout (write every n results)",
                        dest="nlines", default=50, type=int)       
    
    parser.add_argument('--aggregate', action="store",
                        help="aggregate the results, set the name of the field you want to aggregate",
                        dest="aggregate", default='')     
    
    parser.add_argument('--aggregation_mode', action="store",
                        help="(ignored, when --aggregate is not set) available aggregation modes: " + str(AGGREGATION_MODES),
                        dest="aggregation_mode", default=AGGREGATION_MODES[0])
    
    parser.add_argument('--agg_value', action="store",
                        help="value needed for aggregation/accumulation (only used as threshold for THRESHOLD_CUMMULATIVE_AGGREGATOR at the moment)",
                        dest="agg_value", default=0, type=int)
        
    parser.set_defaults(arriveby=False)
    
    options = parser.parse_args()
    
    router_name = options.router
    origins_csv = options.origins
    destinations_csv = options.destinations
    target_csv = options.target
    oid = options.oid
    did = options.did
    date_time = time.strptime(options.datetime, DATETIME_FORMAT)
    modes = options.modes
    max_time = options.max_time
    arriveby = options.arriveby
    print_every_n_lines = options.nlines    
    aggregate_field = options.aggregate
    aggregation_mode = options.aggregation_mode
    agg_value = options.agg_value
    
    otpEval = OTPEvaluation(print_every_n_lines)    
    otpEval.setup(date_time, max_time, modes, arriveby)    
    
    if arriveby:
        otpEval.evaluate_arrival(origins_csv, destinations_csv, target_csv, oid, did, accumulate_field=None, mode=None, value=agg_value) 
    else:
        otpEval.evaluate_departures(origins_csv, destinations_csv, target_csv, oid, did, aggregate_field=aggregate_field, mode=aggregation_mode)
