'''
Created on Mar 16, 2016

@author: Christoph Franke
'''
#!/usr/bin/jython
from org.opentripplanner.scripting.api import OtpsEntryPoint, OtpsCsvOutput
from org.opentripplanner.routing.core import TraverseMode
from org.opentripplanner.scripting.api import OtpsResultSet, OtpsAggregate
from config import GRAPH_PATH, LONGITUDE_COLUMN, LATITUDE_COLUMN, ID_COLUMN, DATETIME_FORMAT
from argparse import ArgumentParser
import time

AGGREGATION_MODES = ["THRESHOLD_SUM_AGGREGATOR", "WEIGHTED_AVERAGE_AGGREGATOR", "THRESHOLD_CUMMULATIVE_AGGREGATOR"]

router_name = ''

class Results(object):
    def __init__(self, arriveby=False):
        self.arriveby = arriveby
        self.individuals = []
        self.evaluated_individuals_2d = []
        self.aggregated = False
        
    def aggregate(self):
        pass    
    
    def add_result(self, individual, evaluated_individuals):
        self.individuals.append(individual)
        self.evaluated_individuals_2d.append(evaluated_individuals)        
    

class OTPEvaluation(object):
    '''
    calculates reachability between origins and destinations with OpenTripPlanner 
    and saves results to csv file
    
    Parameters
    ----------
    origins_csv: file with origin points
    destinations_csv: file with destination points
    date_time: time object (time.struct_time)
    modes: optional, list of modes to use
    arriveby: optional, if True, given time is arrival time (reverts search tree)
    print_every_n_lines: optional, determines how often progress in processing origins/destination is written to stdout (default: 50)
    '''   
    def __init__(self, print_every_n_lines = 50):
        self.otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router_name ])
        self.router = self.otp.getRouter()
        self.request = self.otp.createRequest()
    
    def setup(self, date_time, max_time=1800, modes=None, arriveby=False):
        self.request.setDateTime(date_time.tm_year, date_time.tm_mon, date_time.tm_mday, date_time.tm_hour, date_time.tm_min, date_time.tm_sec)         
        self.request.setArriveBy(arriveby)
        # has to be set AFTER arriveby (request decides if negative weight or not by checking arriveby)
        self.request.setMaxTimeSec(max_time)
        
        if modes:          
            self.request.setModes(','.join(modes))

    def evaluate_departures(self, origins_csv, destinations_csv):        
    
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)       
        
        i = -1        
        results = Results(arriveby=False)
        
        for i, origin in enumerate(origins):
            # Set the origin of the request to this point and run a search
            self.request.setOrigin(origin)
            spt = self.router.plan(self.request)
            
            evaluated_individuals = None if spt is None else spt.eval(destinations)
            
            results.add_result(origin, evaluated_individuals)    
                
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} origins processed".format(i+1)
                
        print "A total of {} origins processed".format(i+1)              
        return results 
    
    def evaluate_arrival(self, origins_csv, destinations_csv):        
        
        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)        
    
        i = -1        
        results = Results(arriveby=True)
        
        for i, destination in enumerate(destinations):
            
            # Set the origin of the request to this point and run a search
            self.request.setDestination(destination)
            spt = self.router.plan(self.request)
            
            evaluated_individuals = None if spt is None else spt.eval(origins)
            
            results.add_result(destination, evaluated_individuals)    
            
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} destinations processed".format(i+1)    
                
        print "A total of {} destinations processed".format(i+1)                
        return results     
        
       
    def write_results_to_csv(self, results, target_csv, oid, did):       
        
        # Create a CSV output
        out_csv = self.otp.createCSVOutput()
        header = [ 'origin_id', 'destination_id', 'travel_time', 'boardings', 'walk_distance']           
        out_csv.setHeader(header)
        
        def add_row(origin_id, destination_id, eval):    
            travel_time = eval.getTime()
            boardings = eval.getBoardings()
            walk_distance = eval.getWalkDistance()
            out_csv.addRow([origin_id, destination_id, travel_time, boardings, walk_distance])
        
        for i, individual in enumerate(results.individuals):
            evaluated_individuals = results.evaluated_individuals_2d[i]
            
            if results.arriveby:
                destination_id = individual.getStringData(oid)
                for evaluated_individual in evaluated_individuals:
                    origin_id = evaluated_individual.getIndividual().getStringData(oid)
                    add_row(origin_id, destination_id, evaluated_individual)
            else:
                origin_id = individual.getStringData(oid)
                for evaluated_individual in evaluated_individuals:
                    destination_id = evaluated_individual.getIndividual().getStringData(did)
                    add_row(origin_id, destination_id, evaluated_individual)       
        
        out_csv.save(target_csv)
        print 'results written to "{}"'.format(target_csv)
        
    def write_aggregated_results_to_csv(self, results, target_csv, oid, did, fieldname, mode, value=None):       
        
        # Create a CSV output
        out_csv = self.otp.createCSVOutput()
        header = [ 'id', fieldname + '_aggregated']            
        out_csv.setHeader(header)
        
        print "aggregating results"
            
        def add_aggregated_row(id, evals):         
            aggregator = OtpsAggregate(mode, value)        
            agg_value = aggregator.computeAggregate(evals)  
            out_csv.addRow([id, agg_value])
        
        for i, individual in enumerate(results.individuals):
            evaluated_individuals = results.evaluated_individuals_2d[i]
            
            if results.arriveby:
                destination_id = individual.getStringData(oid)
                add_aggregated_row(destination_id, evaluated_individuals)
            else:
                origin_id = individual.getStringData(oid)
                add_aggregated_row(origin_id, evaluated_individuals)
            
        out_csv.save(target_csv)
        print 'aggregated results written to "{}"'.format(target_csv)
    
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
                        dest="aggregate", default=None)     
    
    parser.add_argument('--aggregation_mode', action="store",
                        help="(ignored, when --aggregate is not set) available aggregation modes: " + str(AGGREGATION_MODES),
                        dest="aggregation_mode", default=AGGREGATION_MODES[0])
    
    parser.add_argument('--threshold', action="store",
                        help="threshold for aggregation/accumulation, only used for THRESHOLD_CUMMULATIVE_AGGREGATOR",
                        dest="threshold", default=0, type=int)
        
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
    threshold = options.threshold
    
    otpEval = OTPEvaluation(print_every_n_lines)    
    otpEval.setup(date_time, max_time, modes, arriveby)    
    
    results = otpEval.evaluate_arrival(origins_csv, destinations_csv) if arriveby else otpEval.evaluate_departures(origins_csv, destinations_csv)
    
    if aggregate_field:
        results = otpEval.write_aggregated_results_to_csv(results, target_csv, oid, did, aggregate_field, aggregation_mode, threshold)
    else:
        otpEval.write_results_to_csv(results, target_csv, oid, did)
    print
