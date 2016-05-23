OTP_JAR='/opt/repos/OpenTripPlanner/target/otp-0.20.0-SNAPSHOT-shaded.jar'
GRAPH_PATH='/home/cfr/otp/graphs'
LATITUDE_COLUMN = 'lat'
LONGITUDE_COLUMN = 'lon'
ID_COLUMN = 'id'
DATETIME_FORMAT = "%d/%m/%Y-%H:%M:%S"
AGGREGATION_MODES = ["THRESHOLD_SUM_AGGREGATOR", "WEIGHTED_AVERAGE_AGGREGATOR", "THRESHOLD_CUMMULATIVE_AGGREGATOR", "DECAY_AGGREGATOR"]
AVAILABLE_MODES = ['BICYCLE',
                   'BUS',
                   'BUSISH',
                   #'CABLE_CAR', deactivated: Bug in OtpsRoutingRequest with underscores
                   'CAR',
                   'FERRY',
                   'FUNICULAR',
                   'GONDOLA',
                   #'LEG_SWITCH', deactivated: it's only used internally in OTP
                   'RAIL',
                   'SUBWAY',
                   'TRAINISH',
                   'TRAM',
                   'TRANSIT',
                   'WALK']
DEFAULT_MODES = ['BUS',
                 'BUSISH',
                 'RAIL',
                 'SUBWAY',
                 'TRAINISH',
                 'TRAM',
                 'TRANSIT',
                 'WALK']