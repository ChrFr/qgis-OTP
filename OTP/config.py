OTP_JAR='/opt/repos/OpenTripPlanner/target/otp-0.20.0-SNAPSHOT-shaded.jar'
GRAPH_PATH='/home/cfr/otp/graphs'
LATITUDE_COLUMN = 'Y'
LONGITUDE_COLUMN = 'X'
ID_COLUMN = 'id'
DATETIME_FORMAT = "%d/%m/%Y-%H:%M:%S"
AGGREGATION_MODES = ["THRESHOLD_SUM_AGGREGATOR", "WEIGHTED_AVERAGE_AGGREGATOR", "THRESHOLD_CUMMULATIVE_AGGREGATOR", "DECAY_AGGREGATOR"]
ACCUMULATION_MODES = ["DECAY_ACCUMULATOR", "THRESHOLD_ACCUMULATOR"]

# needed parameters for aggregation/accumulation modes (=keys) are listed here
# order of parameters in list has to be the same, the specific mode requires them
MODE_PARAMS = {
    "THRESHOLD_CUMMULATIVE_AGGREGATOR": [
        {
            "label": "Schwellwert", # label of the 
            "min": 0, # minimum value
            "max": 10, # maximum value
            "default": 0, # default value
            "step": 1, # size of steps between values (default 1) 
            "decimals": 0 # number of decimals (default 2)
        }
        ],
    "DECAY_AGGREGATOR": [
        {
            "label": "lambda",
            "min": 0,
            "max": 10,
            "default": 0,
            "step": 0.01,
            "decimals": 2
        }
        ],
}

AVAILABLE_TRAVERSE_MODES = [
    'BICYCLE',
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
    'WALK'
]

DEFAULT_MODES = [
    'BUS',
    'BUSISH',
    'RAIL',
    'SUBWAY',
    'TRAINISH',
    'TRAM',
    'TRANSIT',
    'WALK'
]