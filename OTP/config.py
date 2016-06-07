from lxml import etree
import os, sys, copy
from collections import OrderedDict
import OTP

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
    "THRESHOLD_SUM_AGGREGATOR": [
        {
            "label": "Schwellwert (sek)",
            "min": 0,
            "max": 180 * 60,
            "default": 3600, 
            "step": 1,
            "decimals": 0
        }        
    ],
    "THRESHOLD_CUMMULATIVE_AGGREGATOR": [
        {
            "label": "Schwellwert (sek)", # label of the param (UI only)
            "min": 0, # minimum value
            "max": 180 * 60, # maximum value
            "default": 3600, # default value
            "step": 1, # size of steps between values (default 1) 
            "decimals": 0 # number of decimals (default 2)
        }
        ],
    "DECAY_AGGREGATOR": [
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

# QGIS can't handle this one on startup, but will work strangely anyhow. just annoying so different approach next line
#DEFAULT_FILE = os.path.join(os.path.split((sys.argv)[0])[0], "otp_config.xml")
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "otp_config.xml")

# structure of config-object, composition of xml is the same, contains default values 
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
            'datetime_end': '',
            'time_step': ''
        },        
    }),
    ('router_config', {
        'router': '', 
        'traverse_modes': [
            'BUS',
            'BUSISH',
            'RAIL',
            'SUBWAY',
            'TRAINISH',
            'TRAM',
            'TRANSIT',
            'WALK'
        ],
        'maxWalkDistance': 1000000000,
        'bikeSpeed': 5,
        'walkSpeed': 1.33,
        'clampInitialWaitSec': 1000000000, # -1?
        'maxTimeMin': 1000000000,
        'banned_routes': []
    }),
    ('post_processing', {
        'best_of': '',
        'target_file': '',
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

        # create file if it does not exist
        if not os.path.isfile(filename):
            self.settings = copy.deepcopy(setting_struct)
            self.write(filename)
        tree = etree.parse(filename)
        self.settings = copy.deepcopy(setting_struct)
        f_set = xml_to_dict(tree.getroot())
        for key, value in f_set.iteritems():
            self.settings[key].update(value)
            
    def reset(self):        
        self.settings = copy.deepcopy(setting_struct)        

    def write(self, filename=None, hide_inactive=False):
        '''
        write the config as xml to given file (default config.xml)
        '''

        if not filename:
            filename = DEFAULT_FILE

        settings = copy.deepcopy(self.settings)
        if hide_inactive:
            if not bool(settings['time']['timebatch']['active']):
                del settings['time']['timebatch']
            if not bool(settings['post_processing']['aggregation_accumulation']['active']):
                del settings['post_processing']['aggregation_accumulation']
        xml_tree = etree.Element('CONFIG')
        dict_to_xml(xml_tree, settings)
        etree.ElementTree(xml_tree).write(str(filename), pretty_print=True)

def dict_to_xml(element, dictionary):
    '''
    append the entries of a dictionary as childs to the given xml tree element
    '''
    if isinstance(dictionary, list):
        print dictionary
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
