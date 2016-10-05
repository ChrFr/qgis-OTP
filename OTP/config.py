# -*- coding: utf-8 -*-

try:
    from lxml import etree
    import OTP
except:
    pass
import os, sys, copy
from collections import OrderedDict

OTP_JAR='/opt/repos/OpenTripPlanner/target/otp-0.20.0-SNAPSHOT-shaded.jar'
GRAPH_PATH='/home/ggr/gis/otp_graphs'
LATITUDE_COLUMN = 'Y' # field-name used for storing lat values in csv files
LONGITUDE_COLUMN = 'X' # field-name used for storing lon values in csv files
ID_COLUMN = 'id' # field-name used for storing the ids in csv files
VM_MEMORY_RESERVED = 3 # max. memory the virtual machine running OTP can allocate
DATETIME_FORMAT = "%d/%m/%Y-%H:%M:%S" # format of time stored in csv files
CALC_REACHABILITY_MODE = "THRESHOLD_SUM_AGGREGATOR" # agg. mode that is used to calculate number of reachable destinations (note: threshold is taken from set max travel time)
INFINITE = 2147483647 # represents indefinite values in the UI, pyqt spin boxes are limited to max int32

# needed parameters for aggregation/accumulation modes (=keys) are listed here
# order of parameters in list has to be the same, the specific mode requires them
AGGREGATION_MODES = {
    "THRESHOLD_SUM_AGGREGATOR": {
        "description": (u"Summiert die Werte der Ziele auf,\n" + 
                        u"deren Verbindungsdauer den Schwellwert\n" + 
                        u"nicht überschreitet."),
        "params": [            
            {
                "label": "Schwellwert (sek)", # label of the param (UI only)
                "min": 0, # minimum value
                "max": 180 * 60, # maximum value
                "default": 3600, # default value
                "step": 1, # size of steps between values
                "decimals": 0# number of decimals
            }
        ]
    },
    "THRESHOLD_CUMMULATIVE_AGGREGATOR": {
        "description": (u"Summiert die gewichteten Werte der Ziele auf,\n" + 
                        u"deren Verbindungsdauer t den Schwellwert s\n" + 
                        u"nicht überschreitet.\n\n" + 
                        u"Gewichtung: s - t"),
        "params": [
            {
                "label": "Schwellwert (sek)",
                "min": 0,
                "max": 180 * 60,
                "default": 3600,
                "step": 1,
                "decimals": 0
            }
        ]
    },
    "WEIGHTED_AVERAGE_AGGREGATOR": {
        "description": (u"Bildet eine gewichtetes Mittel über die\n" + 
                        u"Werte der erreichbaren Ziele.\n\n" + 
                        u"Gewichtung: Verbindungsdauer"),
        "params": [
        ]
    },
    "DECAY_AGGREGATOR": {
        "description": (u"Summiert die gewichteten Werte der Ziele auf,\n" + 
                        u"deren Verbindungsdauer t den Schwellwert\n" + 
                        u"nicht überschreitet.\n\n" + 
                        u"Gewichtung: e^(lambda * (t / 60))"),        
        "params": [
            {
                "label": "Schwellwert (sek)",
                "min": 0,
                "max": 180 * 60,
                "default": 60 * 60, 
                "step": 1,
                "decimals": 0
            },
            {
                "label": "lambda",
                "min": -10,
                "max": 0,
                "default": -0.1,
                "step": 0.01,
                "decimals": 2
            }
        ],
    }
}

ACCUMULATION_MODES = {    
    "DECAY_ACCUMULATOR": {
        "description": (u"Summiert die gewichteten Werte der Ziele auf.\n\n" + 
                        u"Gewichtung: e^(-lambda * t)\n" + 
                        u"mit lambda = 1 / (Halbwertszeit * 60)"),        
        "params": [
            {
                "label": "Halbwertszeit (min)",
                "min": 1,
                "max": 180 * 60,
                "default": 1,
                "step": 1,
                "decimals": 0
            } 
        ]
    },
    "THRESHOLD_ACCUMULATOR": {
        "description": (u"Summiert die Werte der Ziele auf,\n" + 
                        u"deren Verbindungsdauer den Schwellwert\n" + 
                        u"nicht überschreitet."),        
        "params": [
            {
                "label": "Schwellwert (min)",
                "min": 0,
                "max": 180 * 60,
                "default": 3600, 
                "step": 1,
                "decimals": 0
            }
        ]    
    }
}

AVAILABLE_TRAVERSE_MODES = [
    'AIRPLANE',
    'BICYCLE',
    'BUS',
    #'CABLE_CAR', deactivated: Bug in OtpsRoutingRequest with underscores
    'CAR',
    'FERRY',
    'FUNICULAR',
    'GONDOLA',
    #'LEG_SWITCH', deactivated: it's only used internally in OTP
    'RAIL',
    'SUBWAY',
    'TRAM',
    'TRANSIT',
    'WALK'
]

# QGIS can't handle this one on startup, but will work strangely anyhow. just annoying so different approach next line
#DEFAULT_FILE = os.path.join(os.path.split((sys.argv)[0])[0], "otp_config.xml")
#DEFAULT_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "otp_config.xml")
DEFAULT_FILE = os.path.join(os.environ['HOME'], '.qgis2', 'otp_config.xml')

# structure of config-object, composition of xml is the same
# contains the DEFAULT values as presets for the UI
setting_struct = OrderedDict([
    ('origin', {
        'layer': '',
        'id_field': ''
    }),
    ('destination', {
        'layer': '',
        'id_field': ''
    }),
    ('time', {
        'datetime': '', # == now,        
        'arrive_by': False,        
        'time_batch': {
            'active': False,
            'smart_search': False,
            'datetime_end': '',
            'time_step': ''
        },        
    }),
    ('router_config', {
        'router': '', 
        'traverse_modes': [
            'TRANSIT',
            'WALK'
        ],
        'max_walk_distance': INFINITE,
        'bike_speed': 5,
        'walk_speed': 1.33,
        'clamp_initial_wait_min': -1,
        'max_time_min': 7200,
        'pre_transit_time_min': 30,
        'max_transfers': 5,
        'wheel_chair_accessible': False,
        'max_slope': 0.0833333333333
    }),
    ('post_processing', {
        'best_of': '',
        'details': False,
        'aggregation_accumulation': {
            'active': False,
            'mode': '',
            'params': [],
            'processed_field': ''        
        }
    })
])

'''
Borg pattern, all subclasses share same state (similar to singleton, but without single identity)
'''
class Borg:
    _shared_state = {}
    def __init__(self):
        self.__dict__ = self._shared_state

'''
holds informations about the environment and database settings
'''
class Config(Borg):

    def __init__(self):
        Borg.__init__(self)

    def read(self, filename=None):
        '''
        read the config from given xml file (default config.xml)
        '''

        if not filename:
            filename = DEFAULT_FILE
        
        self.settings = copy.deepcopy(setting_struct)
        # create file with default settings if it does not exist
        if not os.path.isfile(filename):
            self.write(filename)
        tree = etree.parse(filename)
        f_set = xml_to_dict(tree.getroot())
        # update subkeys to match file settings
        for key, value in f_set.iteritems():
            if self.settings.has_key(key):
                self.settings[key].update(value)
            
    def reset(self):        
        self.settings = copy.deepcopy(setting_struct)        

    def write(self, filename=None, hide_inactive=False, meta=None):
        '''
        write the config as xml to given file (default config.xml)
        
        Parameters
        ----------
        filename: file including path to write current settings to
        hide_inactive: hides unused entries for better readability (e.g. don't write aggregation settings if not used)
        meta: dictionary with additional meta-data to write to file
        '''

        if not filename:
            filename = DEFAULT_FILE

        run_set = copy.deepcopy(self.settings)
        if hide_inactive:
            tb_active = run_set['time']['time_batch']['active']
            if tb_active == 'False' or tb_active == False:
                del run_set['time']['time_batch']
            pp_active = run_set['post_processing']['aggregation_accumulation']['active']
            if pp_active == 'False' or pp_active == False:
                del run_set['post_processing']['aggregation_accumulation']
            bestof = run_set['post_processing']['best_of']
            if not bestof:
                del run_set['post_processing']['best_of']
                
        if meta:
            run_set['META'] = meta
        xml_tree = etree.Element('CONFIG')
        dict_to_xml(xml_tree, run_set)
        etree.ElementTree(xml_tree).write(str(filename), pretty_print=True)

def dict_to_xml(element, dictionary):
    '''
    append the entries of a dictionary as childs to the given xml tree element
    '''
    if isinstance(dictionary, list):
        element.text = ','.join(dictionary)
    elif not isinstance(dictionary, dict):
        element.text = str(dictionary)
    else:
        for key in dictionary:
            elem = etree.Element(key)
            element.append(elem)
            dict_to_xml(elem, dictionary[key])

def xml_to_dict(tree):
    '''
    convert a xml tree to a dictionary
    '''
    if len(tree.getchildren()) > 0:
        value = {}
        for child in tree.getchildren():
            value[child.tag] = xml_to_dict(child)
    else:
        value = tree.text
        if not value:
            value = ''            
        value = value.split(',')
        if len(value) == 1:
            value = value[0]
    return value
