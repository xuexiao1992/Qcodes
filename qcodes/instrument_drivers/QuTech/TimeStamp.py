# Instrument generating a timestamp
#

import time
import datetime
from qcodes import Instrument


class TimeStampInstrument(Instrument):
    '''
    Instrument that generates timestamps
    
    Currently available are:
    
        * timestamp: Time in seconds sich epoch
        * timestr: String representation of the current time
    '''
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.add_parameter('timediff', units='s', get_cmd=self.get_time_diff, docstring='Timestamp based on number of seconds since epoch.')
        self.add_parameter('timestamp', units='s', get_cmd=time.time, docstring='Timestamp based on number of seconds since epoch.')
        self.add_parameter('timestring', get_cmd=self.get_timestring, docstring='Time string based on number of seconds since epoch.')
        
        self.set_time_offset()
        _ = self.timestamp.get()
        _ = self.timestring.get()

    def set_time_offset(self, t0=None):
        if t0 is None:
            t0 = time.time()
        self.t0 = t0
    def get_time_diff(self):
        return time.time()-self.t0        

    def get_timestring(self):
        """ Return string representation of current time """
        return str(datetime.datetime.now())