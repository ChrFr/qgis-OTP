OTP_JAR='/opt/repos/OpenTripPlanner/target/otp-0.19.0-shaded.jar'
GRAPH_PATH='/home/cfr/otp/graphs'
LATITUDE_COLUMN = 'lat'
LONGITUDE_COLUMN = 'lon'
ID_COLUMN = 'id'
DATETIME_FORMAT = "%d/%m/%Y-%H:%M:%S"
AVAILABLE_MODES = ['BICYCLE',
                   'BUS',
                   'BUSISH',
                   #'CABLE_CAR', deactivated: Bug in OtpsRoutingRequest with underscores
                   'CAR',
                   'FERRY',
                   'FUNICULAR',
                   'GONDOLA',
                   #'LEG_SWITCH', deactivated: Bug in OtpsRoutingRequest with underscores
                   'RAIL',
                   'SUBWAY',
                   'TRAINISH',
                   'TRAM',
                   'TRANSIT',
                   'WALK']
DEFAULT_MODES = ['BUS',
                 'BUSISH',
                 #'LEG_SWITCH', deactivated: Bug in OtpsRoutingRequest with underscores
                 'RAIL',
                 'SUBWAY',
                 'TRAINISH',
                 'TRAM',
                 'TRANSIT',
                 'WALK']