'''
Created on Mar 16, 2016

@author: Christoph Franke
'''
#!/usr/bin/jython
from org.opentripplanner.scripting.api import OtpsEntryPoint
from config import GRAPH_PATH, LONGITUDE_COLUMN, LATITUDE_COLUMN
from argparse import ArgumentParser
import time

router_name = ''
    
def origin_to_dest(origins_csv, destinations_csv):    
    
    otp = OtpsEntryPoint.fromArgs([ "--graphs", GRAPH_PATH, "--router", router_name ])
    router = otp.getRouter()
    
    # Create a default request for a given time
    req = otp.createRequest()
    req.setDateTime(2016, 3, 17, 10, 00, 00)
    req.setMaxTimeSec(1800)
        
    # Load population files, CSV or GeoTIFF
    origins = otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)
    destinations = otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)    
    
    # Create a CSV output
    out_csv = otp.createCSVOutput()
    out_csv.setHeader([ LATITUDE_COLUMN, LONGITUDE_COLUMN, 'travel_time'])
    
    # For each point of the synthetic grid
    for i, origin in enumerate(origins):
    
        print "Processing: ", origin
        # Set the origin of the request to this point and run a search
        req.setOrigin(origin)
        spt = router.plan(req)
        if spt is None: continue
    
        # Evaluate the SPT for all schools
        res = spt.eval(destinations)
        '''
        # Find the time to nearest school
        if len(res) == 0:    
            minTime = -1
        else:            
            minTime = min([ r.getTime() for r in res ])
        # Find the number of schools < 30mn
        nSchool30 = sum([ 1 for r in res if r.getTime() < 1800 ])
    
        # Add a new row of result in the CSV output
        out_csv.addRow([ spt.getSnappedOrigin().getLat(), spt.getSnappedOrigin().getLon(),
            minTime, nSchool30])
        '''
    # Save the result
    out_csv.save('/home/cfr/otp/graphs/portland/grid30.csv')
    print "Done"
    
if __name__ == '__main__':
    parser = ArgumentParser(description="Batch Analysis with OpenTripPlanner")

    parser.add_argument('-r', '--router', action="store",
                        help='name of the router',
                        dest="router", required=True)    
    
    parser.add_argument('--origins', action="store",
                        help="travel time (hours:minutes:seconds)",
                        dest="origins", required=True)        
    
    parser.add_argument('--destinations', action="store",
                        help="travel time (hours:minutes:seconds)",
                        dest="destinations", required=True)    
    
    parser.add_argument('-t', '--time', action="store",
                        help="travel time (hours:minutes:seconds)",
                        dest="time", default=time.strftime("%H:%M:%S"))    
    
    parser.add_argument('-d', '--date', action="store",
                        help="date of travel (year/month/day)",
                        dest="date", default=time.strftime("%Y/%m/%d"))
    
    options = parser.parse_args()
    
    router_name = options.router
    time = options.time
    date = options.date
    origins_csv = options.origins
    destinations_csv = options.destinations
    
    #TODO: parse date and time to datetime
    print date
    print time
    
    origin_to_dest(origins_csv, destinations_csv)
