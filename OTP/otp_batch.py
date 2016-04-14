'''
Created on Mar 16, 2016

@author: Christoph Franke
'''
#!/usr/bin/jython
from org.opentripplanner.scripting.api import OtpsEntryPoint
from config import GRAPH_PATH, LONGITUDE_COLUMN, LATITUDE_COLUMN, ID_COLUMN, DATETIME_FORMAT
from argparse import ArgumentParser
import time

router_name = ''
    
def origin_to_dest(origins_csv, destinations_csv, target_csv, date_time, max_time=1800, oid=None, did=None): 
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
    '''   
    
    otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router_name ])
    router = otp.getRouter()
    
    # Create a default request for a given time
    req = otp.createRequest()
    req.setDateTime(date_time.tm_year, date_time.tm_mon, date_time.tm_mday, date_time.tm_hour, date_time.tm_min, date_time.tm_sec)
    req.setMaxTimeSec(max_time)
    
    origins = otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)
    
    destinations = otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)        
    
    # Create a CSV output
    out_csv = otp.createCSVOutput()
    out_csv.setHeader([ 'origin_id', 'destination_id', 'travel_time', 'boardings', 'walk_distance'])
    
    # For each point of the synthetic grid
    for i, origin in enumerate(origins):
    
        print "Processing: ", origin
        # Set the origin of the request to this point and run a search
        req.setOrigin(origin)
        spt = router.plan(req)
        if spt is None: continue
    
        res = spt.eval(destinations)
        if len(res) > 0:    
            if oid:
                origin_id = origin.getFloatData(oid)
            else:
                origin_id = i
                
            for eval_dest in res:
                
                if did:
                    destination_id = eval_dest.getIndividual().getFloatData(did)
                else:
                    destination_id = 'unknown'
            
                travel_time = eval_dest.getTime()
                boardings = eval_dest.getBoardings()
                walk_distance = eval_dest.getWalkDistance()
                out_csv.addRow([origin_id, destination_id,
                                travel_time, boardings, walk_distance])
    # Save the result
    out_csv.save(target_csv)
    print "Done"
    
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
                        dest="max_time", default=1800)   
    
    options = parser.parse_args()
    
    router_name = options.router
    origins_csv = options.origins
    destinations_csv = options.destinations
    target_csv = options.target
    oid = options.oid
    did = options.did
    date_time = time.strptime(options.datetime, DATETIME_FORMAT)
    max_time = int(options.max_time)    
    
    origin_to_dest(origins_csv, destinations_csv, target_csv, date_time, max_time=max_time, oid=oid, did=did)
