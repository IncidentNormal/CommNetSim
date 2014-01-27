'''
Created on Feb 17, 2011

@author: duncantait
'''

class Packet():
    def __init__(self):
        self.birth_time = 0 
        self.internal_last_location = -1 #To find out where Packet came from for knowing which Q to send to
        self.notes = ''
        self.ID = IDU()
        self.meta = MetaData()
        
        self.physical = Physical()
        self.link = Link()
        self.network = Network()
        self.transport = Transport()
        self.session = Session()
        self.presentation = Presentation()
        self.application = Application()
        
class IDU():
    def __init__(self):
        self.Physical_ID = None
        self.Link_ID = None
        self.Network_ID = None
        self.Transport_ID = None
        self.Session_ID = None
        self.Application_ID = None
        self.Destination = None #THIS IS ALWAYS THE COUNTERPART, i.e. the node ID that is NOT self.ID, regardless of being Slave or Master
        self.New_Destination = None
        self.Origin = None
        self.Frequency = None
    def all_IDs(self):
        return 'Dest:'+ str(self.Destination) + 'NewDest:'+ str(self.New_Destination) + 'Origin:'+ str(self.Origin) + 'Frequency:'+ str(self.Frequency) + '|AppID:'+str(self.Application_ID) + '|SessID:'+str(self.Session_ID) + '|TranID:'+str(self.Transport_ID) + '|NetID:'+str(self.Network_ID) + '|LinkID:'+str(self.Link_ID)  + '|PhyID:'+str(self.Physical_ID)

class MetaData():
    linkSNR = 0 #Actual SNR value of link A-B 
    perceivedSNR = 0 #SNR value including interference etc.
    Frequency = 0
    waveform = None
    start_time = None

class Physical():
    frequency = None
    destination = None
    waveform = None
    
    data_rate = None

    bits = []
    time = 0.3
    #pType = -1 #0 = LBT, 1 = Real
    #prop_time_all_nodes = []

    LBT_Free = None
    scanning_call_Rx = False
    Tx_Sent = False
    
    #timeout = 30 #Rx timeout stage
    
class Link():
    #internal_last_location = -1 #To find out where Packet came from for knowing which Q to send to
    #internal_last_time = -1 #for timing, put one of these in each layer
    data = []

    frequency = [] #frequencies???
    
    pType = -1 #0 call , 1 resp, 2 ack, 3 data, 4 eom, 5 data_ack, 6 eow
    destination = None
    origin = None
    size = -1
    link_success = False
    data_success = False
    time_out = False #If the linking times out in the Link Layer (e.g. response packet isn't received), mark this True and send to Physical where it will be immediately changed to Scanning mode.
    master_slave_switch = False
    #backoff section, currently not turned on in main program (29/06/11)

    num_backoffs = 0
    backoff = 0
    
class Network():
    data = []
    msg_ID = None
    consecutive_ID = None
    ARQ_success = None
    ARQ_fail = None
    priority = 0
    ARQ_timeouts = 0
    last_batch = False
    #segment_success = False
    data_rate = None
    
class Transport():
    header = []
    data = None
    payload = []
    origin = None
    
    link_terminated = False
    eom = False
    
class Session():
    data = []
    
class Presentation():
    data = []
    
class Application():
    data = []
    
