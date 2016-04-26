'''
Created on Mar 16, 2016

@author: Christoph Franke
'''
#!/usr/bin/jython
from org.opentripplanner.scripting.api import OtpsEntryPoint
from org.opentripplanner.routing.core import TraverseMode
from config import GRAPH_PATH, LONGITUDE_COLUMN, LATITUDE_COLUMN, ID_COLUMN, DATETIME_FORMAT
from argparse import ArgumentParser
import time

router_name = ''
    
def origin_to_dest(origins_csv, destinations_csv, target_csv, date_time, max_time=1800, oid=None, did=None, modes=None, arriveby=False,
                   print_every_n_lines = 50): 
    '''
    calculates reachability between origins and destinations with OpenTripPlanner 
    and saves results to csv file
    
    Parameters
    ----------
    origins_csv: file with origin points
    destinations_csv: file with destination points
    oid: optional, name of id-column in origins-file (if not given, is assigned from 0 to length of origins)
    did: optional, name of id-column in destinations-file (if not given, is assigned as 'unknown'
    date_time: time object (time.struct_time)
    modes: optional, list of modes to use
    arriveby: optional, if True, given time is arrival time (reverts search tree)
    print_every_n_lines: optional, determines how often progress in processing origins/destination is written to stdout (default: 50)
    '''   
    
    otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router_name ])
    router = otp.getRouter()
    
    # Create a default request for a given time
    req = otp.createRequest()
    req.setDateTime(date_time.tm_year, date_time.tm_mon, date_time.tm_mday, date_time.tm_hour, date_time.tm_min, date_time.tm_sec)
     
    if modes:
        if 'LEG_SWITCH' in modes:
            modes.remove('LEG_SWITCH')
            #req.modes.setMode(TraverseMode.LEG_SWITCH, true)            
        req.setModes(','.join(modes))
    
    origins = otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)
    
    destinations = otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)        
    
    # Create a CSV output
    out_csv = otp.createCSVOutput()
    out_csv.setHeader([ 'origin_id', 'destination_id', 'travel_time', 'boardings', 'walk_distance'])
    
    def write_result_row(origin_id, destination_id, evaluation):        
                
        travel_time = evaluation.getTime()
        boardings = evaluation.getBoardings()
        walk_distance = evaluation.getWalkDistance()
        out_csv.addRow([origin_id, destination_id,
                        travel_time, boardings, walk_distance])

    req.setArriveBy(arriveby)
    # has to be set AFTER arriveby (request decides if negative weight or not by checking arriveby)
    req.setMaxTimeSec(max_time)
    n_origins = 0
    n_destinations = 0
    i = -1
    # DEPARTURE
    if not arriveby:
        for i, origin in enumerate(origins):
            if oid:
                origin_id = origin.getStringData(oid)
            else:
                origin_id = i
            # Set the origin of the request to this point and run a search
            req.setOrigin(origin)
            spt = router.plan(req)
            if spt is None: continue
        
            res = spt.eval(destinations)
            if len(res) > 0:    
                    
                for eval_dest in res:
                    
                    if did:
                        destination_id = eval_dest.getIndividual().getStringData(did)
                    else:
                        destination_id = 'unknown'
                        
                    write_result_row(origin_id, destination_id, eval_dest)
             
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} origins processed".format(i+1)
    # ARRIVAL             
    else:
    
        for i, destination in enumerate(destinations):
                        
            if did:
                destination_id = destination.getStringData(did)
            else:
                destination_id = i
            
            # Set the origin of the request to this point and run a search
            req.setDestination(destination)
            spt = router.plan(req)
            if spt is None: continue
        
            res = spt.eval(origins)
            if len(res) > 0:                        
                for eval_orig in res:                    
                    if oid:
                        origin_id = eval_orig.getIndividual().getStringData(oid)
                    else:
                        origin_id = 'unknown'       
                        
                    write_result_row(origin_id, destination_id, eval_orig)    
            
            if not (i + 1) % print_every_n_lines:
                print "Processing: {} destinations processed".format(i+1)
                    
    # Save the result
    out_csv.save(target_csv)
    print "Done - {} {} processed".format(i+1, 'origins' if not arriveby else 'destinations')
    
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
    
    origin_to_dest(origins_csv, destinations_csv, target_csv, date_time, max_time=max_time, oid=oid, did=did, modes=modes, arriveby=arriveby, print_every_n_lines=print_every_n_lines)
