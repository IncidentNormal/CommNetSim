'''
Created on Feb 16, 2011
@author: duncantait

If the simulation aborts before the end then this is usually because a different simulation instance is called
e.g. is a SimEvent is fired that doesn't have (sim=sim) in its instantiation parameters
'''
from SimPy.Simulation import *
from enums import *
import packet
import random
import string
import math
import copy
#random.seed(123456)

class instance(Process):
    def __init__(self, ID, sim):
        Process.__init__(self, sim=sim)
        self.ID = ID
    def execute(self):
        yield hold, self, 1
        print self.ID, self.sim.now()

class nState():
    IDLE = 0
    LINKING_RX = 1
    LINKING_TX = 2
    LINKED_RX = 3
    LINKED_TX = 4 

class kernel(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        
        self.STATE = nState.IDLE
    def execute(self):
#        self.WP = WatchProperty(self.sim, self.ID, self.interface)
#        self.sim.activate(self.WP, self.WP.execute())
        while True:
            yield get, self, self.inQ, 1
            if self.sim.debug: print self.ID, 'Network: packet recd, State:', self.STATE, self.sim.now()
            rec_packet = self.got[0]
            last_location = rec_packet.internal_last_location
            rec_packet.internal_last_location = Layer.NETWORK
            if self.STATE == nState.IDLE:
                if last_location == Layer.LINK:
                    yield put, self, self.interface.ProcDict['SlaveBuffer'].inQ, [rec_packet]
                elif last_location == Layer.TRANSPORT:
                    if self.sim.debug: print 'packet type', rec_packet.link.pType
                    #if in IDLE mode this means its the first packet, so must be a call...
                    self.sendCall(rec_packet)
                else:
                    print 'flamin error mate'               
            elif self.STATE == nState.LINKED_TX:
                if last_location == Layer.LINK:
                    print self.ID, 'Discont N0'
                elif last_location == Layer.TRANSPORT:
                    rec_packet = self.getData(rec_packet)
                    rec_packet.ID.Network_ID = self.createID()
                    yield put, self, self.interface.ProcDict['MainQ'].inQ, [rec_packet]
                else:
                    print 'flamin error mate', last_location
            elif self.STATE == nState.LINKED_RX:
                if last_location == Layer.LINK:
                    yield put, self, self.interface.ProcDict['SlaveBuffer'].inQ, [rec_packet]
                elif last_location == Layer.TRANSPORT:
                    print 'Discont NK1'
                else:
                    print 'flamin error mate', last_location
    def sendCall(self, in_packet):
        r_p = copy.deepcopy(in_packet)
        r_p.network.msg_ID = self.createID()
        r_p.link.pType = 0
        r_p.meta.waveform = self.sim.G.linking_waveform
        if self.sim.debug: print self.ID, 'Network: sending call to Link', self.sim.now()
        self.interface.linkQ.signal([r_p])                 
    def getData(self, in_packet):
        in_packet.network.data = in_packet.transport.data
        in_packet.link.pType = 3
        return in_packet
    def createID(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    
class msg_kernel(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=self.sim)

        self.interface_events()
        
    def interface_events(self):
        #TRANSPORT
        self.M_Link_Started = SimEvent(sim=self.sim, name='M_Link_Started')
        self.M_Link_Failed = SimEvent(sim=self.sim, name='M_Link_Failed')
        self.M_Link_Success = SimEvent(sim=self.sim, name='M_Link_Success')
        self.M_Link_Ended = SimEvent(sim=self.sim, name='M_Link_Ended')
        self.M_Link_Aborted = SimEvent(sim=self.sim, name='M_Link_Aborted')
        #self.M_Link_Retry = SimEvent(sim=self.sim, name='M_Link_Retry') #LBT RETRY ONLY AT PRESENT
        self.M_Data_Tx_Sent = SimEvent(sim=self.sim, name='M_Data_Tx_Sent')
        self.M_Data_Tx_Fail = SimEvent(sim=self.sim, name='M_Data_Tx_Fail')
        self.M_Data_Rx_Rec = SimEvent(sim=self.sim, name='M_Data_Rx_Rec')
        self.M_Data_Rx_Fail = SimEvent(sim=self.sim, name='M_Data_Rx_Fail')
        self.M_Switch_to_Slave = SimEvent(sim=self.sim, name='M_Switch_to_Slave')
        self.S_Link_Started = SimEvent(sim=self.sim, name='S_Link_Started')
        self.S_Link_Failed = SimEvent(sim=self.sim, name='S_Link_Failed')
        self.S_Link_Success = SimEvent(sim=self.sim, name='S_Link_Success')
        self.S_Link_Ended = SimEvent(sim=self.sim, name='S_Link_Ended')
        self.S_Data_Rx_Rec = SimEvent(sim=self.sim, name='S_Data_Rx_Rec')
        self.S_Data_Rx_Fail = SimEvent(sim=self.sim, name='S_Data_Rx_Fail')
        self.S_Data_Tx_Sent = SimEvent(sim=self.sim, name='S_Data_Tx_Sent')
        self.S_Data_Tx_Fail = SimEvent(sim=self.sim, name='S_Data_Tx_Fail')
        #LINK
        self.Start_Link = SimEvent(sim=self.sim, name='Start_Link')
        self.LM_Terminate = SimEvent(sim=self.sim, name='LM_Terminate')
        #self.LM_Send_EOF = SimEvent(sim=self.sim, name='LM_Send_EOF')
        self.LS_Terminate = SimEvent(sim=self.sim, name='LS_Terminate')
        self.LS_Send_ARQ = SimEvent(sim=self.sim, name='LS_Send_ARQ')
        self.Abort_Link = SimEvent(sim=self.sim, name='Abort_Link')

    def execute(self):
        while True:
            yield waitevent, self, self.interface.linkEvents + self.interface.transportEvents
            evFired = self.eventsFired[0]
            param = self.eventsFired[0].signalparam
            if self.interface.ProcDict['kernel'].STATE == nState.IDLE:
                if evFired.name == 'M_Link_Started':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_Link_Started, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['kernel'].STATE = nState.LINKING_TX
                    self.M_Link_Started.signal(param)
                elif evFired.name == 'S_Link_Started':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: S_Link_Started, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['kernel'].STATE = nState.LINKING_RX
                    self.S_Link_Started.signal(param)
                else:
                    print self.ID, 'Network: msg_kernel:', evFired.name, 'Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
            elif self.interface.ProcDict['kernel'].STATE == nState.LINKING_TX:
                if evFired.name == 'M_Link_Started':
                    print self.ID, 'Network: msg_kernel: M_Link_Started, Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                elif evFired.name == 'M_Link_Success':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_Link_Success, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['kernel'].STATE = nState.LINKED_TX
                    self.M_Link_Success.signal(param)
                elif evFired.name == 'M_Link_Failed':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_Link_Failed, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['kernel'].STATE = nState.IDLE
                elif evFired.name == 'M_Switch_to_Slave':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_Switch_to_Slave, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['kernel'].STATE = nState.LINKING_RX
                    self.M_Switch_to_Slave.signal(param)
                else:
                    print self.ID, 'Network: msg_kernel:', evFired.name, 'Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
            elif self.interface.ProcDict['kernel'].STATE == nState.LINKING_RX:
                if evFired.name == 'S_Link_Started':
                    print self.ID, 'Network: msg_kernel: S_Link_Started, Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                elif evFired.name == 'S_Link_Success':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: S_Link_Success, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    if self.sim.debug: print 'S_Link_Success parameter: packet with IDs:', param.all_IDs()
                    self.interface.ProcDict['kernel'].STATE = nState.LINKED_RX
                    self.S_Link_Success.signal(param)
                elif evFired.name == 'S_Link_Failed':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: S_Link_Failed, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['kernel'].STATE = nState.IDLE
                    self.S_Link_Failed.signal(param)
                else:
                    print self.ID, 'Network: msg_kernel:', evFired.name, 'Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
            elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_TX:
                if evFired.name == 'M_Link_Success':
                    print self.ID, 'Network: msg_kernel: M_Link_Success, Invalid Event, freq_ID:, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                elif evFired.name == 'M_Link_Failed':
                    print self.ID, 'Network: msg_kernel: M_Link_Failed, Invalid Event, freq_ID:, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    #self.interface.ProcDict['kernel'].STATE = nState.IDLE
                elif evFired.name == 'M_Link_Ended':
                    self.interface.ProcDict['kernel'].STATE = nState.IDLE
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_Link_Ended, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.M_Link_Ended.signal(param)
                elif evFired.name == 'M_Data_Tx_Sent':
                    #Do not forward this as it is currently not even used in Transport 
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_Data_Tx_Sent, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                elif evFired.name == 'M_Data_Tx_Fail':
                    #Do not forward this to Transport as it will result in Transport (OutgoingData) ending the session
                    #This should be handled with actual M_Link_Ended type events
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_Data_Tx_Fail, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                elif evFired.name == 'M_ARQ_Rx_Success':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: M_ARQ_Rx_Success, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    if len(self.interface.ProcDict['RateController'].M_ARQ_Rx_Success.waits) > 0:
                        self.interface.ProcDict['RateController'].M_ARQ_Rx_Success.signal(param)
                else:
                    print self.ID, 'Network: msg_kernel:', evFired.name, 'Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
            elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_RX:
                if evFired.name == 'S_Link_Started':
                    print self.ID, 'Network: msg_kernel: S_Link_Started, Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                elif evFired.name == 'S_Link_Success':
                    print self.ID, 'Network: msg_kernel: S_Link_Success, Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()  
                elif evFired.name == 'S_Link_Failed':
                    print self.ID, 'Network: msg_kernel: S_Link_Failed, Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()  
                elif evFired.name == 'S_Link_Ended':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: S_Link_Ended, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['kernel'].STATE = nState.IDLE
                    self.S_Link_Ended.signal(param)
                elif evFired.name == 'S_Data_Rx_Rec':
                    #Do not forward this to Transport as it is unnecessary with the Packet going up.
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: S_Data_Rx_Rec, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                elif evFired.name == 'S_Data_Rx_Fail':
                    #Do not forward this to Transport as it is will cause Transport (IncomingData) to abort the session. 
                    #Session aborting should be handled  with actual S_Link_Ended type events.
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: S_Data_Rx_Fail, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()                                             
                elif evFired.name == 'S_ARQ_Tx_Success':
                    if self.sim.debug: print self.ID, 'Network: msg_kernel: S_ARQ_Tx_Success, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                    self.interface.ProcDict['SlaveBuffer'].S_ARQ_Tx_Success.signal(param)
                else:
                    print self.ID, 'Network: msg_kernel:', evFired.name, 'Invalid Event, mode:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                  
def getClasses(): #List all main (need an interface to main simulation) active Process classes in here, this will be iterated through by OSI stack and create instances of them.   
    return [kernel, msg_kernel, MainQ, RateController, SortingF, ARQ, SlaveBuffer]

def getLinkEvents(iLink): #events to be sent TO link
    return [iLink.ProcDict['msg_kernel'].Start_Link, \
            iLink.ProcDict['msg_kernel'].LM_Terminate, \
            #iLink.ProcDict['msg_kernel'].LM_Send_EOF, \
            iLink.ProcDict['msg_kernel'].LS_Terminate, \
            iLink.ProcDict['msg_kernel'].LS_Send_ARQ, \
            iLink.ProcDict['msg_kernel'].Abort_Link]

def getTransportEvents(iLink): #events to be sent TO transport
    return [iLink.ProcDict['msg_kernel'].M_Link_Failed, \
    iLink.ProcDict['msg_kernel'].M_Link_Started, \
    iLink.ProcDict['msg_kernel'].M_Link_Success, \
    iLink.ProcDict['msg_kernel'].M_Link_Ended, \
    iLink.ProcDict['msg_kernel'].M_Link_Aborted, \
    #iLink.ProcDict['msg_kernel'].M_Link_Retry, \
    iLink.ProcDict['msg_kernel'].M_Data_Tx_Sent, \
    iLink.ProcDict['msg_kernel'].M_Data_Tx_Fail, \
    iLink.ProcDict['msg_kernel'].M_Data_Rx_Rec, \
    iLink.ProcDict['msg_kernel'].M_Data_Rx_Fail, \
    iLink.ProcDict['msg_kernel'].M_Switch_to_Slave, \
    iLink.ProcDict['msg_kernel'].S_Link_Started, \
    iLink.ProcDict['msg_kernel'].S_Link_Failed, \
    iLink.ProcDict['msg_kernel'].S_Link_Success, \
    iLink.ProcDict['msg_kernel'].S_Link_Ended, \
    iLink.ProcDict['msg_kernel'].S_Data_Rx_Rec, \
    iLink.ProcDict['msg_kernel'].S_Data_Rx_Fail, \
    iLink.ProcDict['msg_kernel'].S_Data_Tx_Sent, \
    iLink.ProcDict['msg_kernel'].S_Data_Tx_Fail]

class MainQ(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        
        self.consecutive_ID = 0
    def execute(self):
        while True:
            yield get, self, self.inQ, 1
            pkt = self.got[0]
            pkts_to_send = []
            if self.sim.debug: print self.ID, 'Network: MainQ got packet:', pkt.ID.all_IDs(), self.sim.now()
            if self.checkLongPacket(pkt):
                pkts_to_send = self.splitPackets(pkt)
            else:
                pkts_to_send = [pkt]
            for pkt_to_send in pkts_to_send: #Takes a long time!
                pkt_to_send = self.establishPriority(pkt_to_send)
                pkt_to_send = self.markPacket(pkt_to_send)
                yield put, self, self.interface.ProcDict['RateController'].inQ, [pkt_to_send]
    def establishPriority(self, pkt):
        #compare against buffer, has it been sent before?
        #if yes, priority high,
        #if no, priority normal.
        ID = pkt.ID
        if pkt.network.consecutive_ID != None:
            pkt.network.priority += 1
        else:
            pkt.network.consecutive_ID = self.consecutive_ID
            self.consecutive_ID += 1
        return pkt
    def checkLongPacket(self, pkt):
        return pkt.network.data > self.sim.G.packet_size
    def splitPackets(self, long_packet):
        #When Transport delivers a long data packet, this must be broken down into appropriately sized packets for sending
        #The size of these packets is defined by self.sim.G.packet_size
        orig_packet = copy.deepcopy(long_packet)
        num_packets = int(math.ceil(float(long_packet.network.data/self.sim.G.packet_size)))
        return_packets = []
        for i in range(num_packets):
            pkt = copy.deepcopy(orig_packet)
            pkt.network.data = pkt.transport.data = self.sim.G.packet_size
            return_packets.append(pkt)
        return return_packets
    def markPacket(self, pkt):
        pkt.internal_last_location = Layer.NETWORK
        return pkt

class RateController(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        
        self.totalRate = 0 #bytes/s
        self.packetSize = self.sim.G.packet_size #bytes
        self.rate_fidelity = self.sim.G.rate_fidelity #in seconds, how often it is reevaluated...
        self.frame_max_time = self.sim.G.frame_max_time

        self.packetsToSendPerInterval = 0
        
        self.overallPacketsSent = 0
        self.overallPacketsFail = 0
        self.previousNetRates = 0
        self.rateProportions = 0
        
        self.storedLQA = [0.0 for i in range(self.sim.G.num_freq)] #really need to be specific for each destination!
        self.channelProportions = [1.0/self.sim.G.num_freq for i in range(self.sim.G.num_freq)]
        self.targetReliability = self.sim.G.targetReliability
        self.minReliability = self.sim.G.minReliability

        self.frame_timer = None
        self.eof_packet = None
        self.packets_to_send = None
        self.EOM = False
        
        self.M_ARQ_Rx_Success = SimEvent(sim=sim)
        self.abort_event = SimEvent(sim=sim)
        self.inQ = Store(capacity='unbounded', sim=sim)
    def orderByPriority(self, a, par):
        #High priority packets to front of Q
        tmplist = [(x.network.priority,x) for x in par]
        tmplist.sort(reverse=True)
        return [x for (key, x) in tmplist]
    def execute(self):
        self.inQ.addSort(self.orderByPriority) #This means the Q is sorted by packet.network.priority
        
        yield hold, self, 0.0000001 #Allow all other initialization to occur first, as SNR Matrix initialises last.
        self.initialiseLQA()
        self.initialiseTotalRate()
        self.establishInitialRates()
        #This possibly needs to be re-evaluated as a Process, to deal with longer amounts of time between responses
        #This recalculates loss every second, whereas in reality will only know about failed packets every 127 seconds.
        while True:
            #Other process (ARQ): if packet fails, self.overallPacketsFail[channel] += 1
            #Other process (Tx): if packet sent (at all), self.overallPacketsSent += 1
            self.resetCache()
            num_pkts_to_get = self.calculatePacketsToGet()
            
            self.checkForTimer()
            
            yield get, self, self.inQ, num_pkts_to_get
            self.packets_to_send = copy.deepcopy(self.got)
            self.checkForEOF()
            
            for x in self.configurePacketsToSend(self.packets_to_send):
                yield x
            yield hold, self, 0 #Make sure data packets are sent ahead to Link first
            if self.eof_packet != None:
                if self.sim.debug: print self.ID, 'Net: EOF Packet exists!', self.sim.now()
                self.sendEOF(self.eof_packet)
                for x in self.waitforRxSuccess():
                    yield x     
                    
                if self.EOM:
                    self.EOM = False
                else:
                    self.adaptiveNewRates() #after ARQ!!

            yield hold, self, self.rate_fidelity
#            self.frame_timer += self.rate_fidelity
#            
#            #figure out when frame is finished! Timer..?
#            if self.frame_timer <= self.frame_max_time:
#                self.adaptiveNewRates()
#                self.frame_timer = 0

    def abortLink(self):
        yield get, self, self.inQ, len(self.inQ.theBuffer)
        all_pkts = self.got
        self.interface.ProcDict['msg_kernel'].M_Link_Aborted.signal(all_pkts)
        yield hold, self, 0
        self.interface.ProcDict['ARQ'].sendEOMEvents()
    def waitforRxSuccess(self): #What are the events to wait for?! Rx_Success?
        if self.sim.debug: print self.ID, 'Network [RC]: Waiting for EOF ACK (ARQ:S) Received Success', self.sim.now()
        ARQ_TO = self.calculate_ARQ_Rx_Timeout()
        #TO = TimeOut(self.sim, self.sim.G.wait_for_ARQ_Rx)
        TO = TimeOut(self.sim, ARQ_TO)
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [self.M_ARQ_Rx_Success, TO.timeoutEvent, self.abort_event]
        if self.eventsFired[0] == self.M_ARQ_Rx_Success:
            if self.sim.debug: print self.ID, 'Network [RC]: ARQ Received, now send to ARQ', self.sim.now()
            ARQ_packet = self.eventsFired[0].signalparam
            yield put, self, self.interface.ProcDict['ARQ'].inQ, [ARQ_packet]
            yield hold, self, 0 #Make sure ARQ business is done first.
        elif self.eventsFired[0] == TO.timeoutEvent:
            print self.ID, 'num ARQ timeouts:', self.eof_packet.network.ARQ_timeouts, self.sim.now()
            if self.eof_packet.network.ARQ_timeouts > self.sim.G.ARQ_timeout_n:
                print self.ID, 'ARQ timed out, waited too many times (', self.sim.G.ARQ_timeout_n,'), abort link', self.sim.now()
                for x in self.abortLink():
                    yield x
            else:
                if self.sim.debug: print self.ID, 'Network [RC]: No ARQ received, try again [reinsert EOF packet into RC Queue]', self.sim.now()
                self.eof_packet.network.ARQ_timeouts += 1
                self.eof_packet.network.priority = 999
                yield put, self, self.inQ, [self.eof_packet]
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def calculate_ARQ_Rx_Timeout(self):
        ARQ_TO = self.packetsToSendPerInterval*(float(self.packetSize)/float(self.totalRate)) + self.sim.G.wait_for_ARQ_Rx
        if self.sim.debug: print self.ID, 'Net: RC: ARQ TO calculated', ARQ_TO, self.sim.now()
        return ARQ_TO
            
    def checkForTimer(self):
        if len(self.inQ.theBuffer) == 0:
            if self.frame_timer != None:
                if self.sim.debug: print self.ID, 'Net: RC: Timer deactivated (not more packets in inQ)', self.sim.now()
                self.frame_timer.active = False
                self.frame_timer = None
        else:
            if self.frame_timer == None:
                if self.sim.debug: print self.ID, 'Net: Timer started', self.sim.now()
                self.frame_timer = MasterFrameTimer(self.ID, self.sim, self.interface, self.inQ.theBuffer[0].ID)
                self.sim.activate(self.frame_timer, self.frame_timer.execute())
                
    def checkForEOF(self): #At this point the EOF for each channel is reduced to 1 EOF
        data_pkts = []
        for pkt in self.packets_to_send:
            if pkt.link.pType == 6:
                if self.sim.debug: print self.ID, 'Net [RC]: EOF found, now self.eof_packet, and stripped off data_pkts!', self.sim.now()
                
                if self.eof_packet != None:
                    if self.eof_packet.network.ARQ_timeouts > pkt.network.ARQ_timeouts:
                        pkt.network.ARQ_timeouts = self.eof_packet.network.ARQ_timeouts
                
                self.eof_packet = pkt
            else:
                data_pkts.append(pkt)
        self.packets_to_send = data_pkts
    def resetCache(self):
        if self.sim.debug: print self.ID, 'Network: Resetting Cache (any stored eof_packet and stored packets_to_send)', self.sim.now()
        self.eof_packet = None
        self.packets_to_send = None
                
                
    def sendEOF(self, eof_packet):
        #Bypasses buffer, EOF packets don't need buffering.
        if self.sim.debug: print self.ID, 'Network: sending EOF', self.sim.now()
        if len(self.inQ.theBuffer) == 0: #Check if its a final EOF or just a normal one
            if self.sim.debug: print self.ID, 'Network: *** Last Batch', self.sim.now()
            eof_packet.network.last_batch = True
        eof_packet = self.addWaveformDetails(eof_packet)
        eof_copy = copy.deepcopy(eof_packet)
        self.interface.linkQ.signal([eof_copy])
    def addWaveformDetails(self, pkt):
        pkt.network.data_rate = self.interface.ProcDict['RateController'].totalRate #Append data_rate to packet, for SNR
        pkt.meta.waveform = self.sim.G.data_waveform
        return pkt    
            #self.interface.ProcDict['msg_kernel'].LM_Send_EOF[chan].signal(eof_copy)

        #THIS COULD ACTUALLY BE AN EVENT LIKE LS_Send_ARQ

#        if (self.inQ.theBuffer) == 0: #Check if its a final EOF or just a normal one
#            eof_packet.network.last_batch = True
#        for channel in self.interface.ProcDict['msg_kernel'].getModeChans(nState.LINKED_TX):
#            eof_copy = copy.deepcopy(eof_packet)
#            self.interface.linkQ[channel].signal(eof_copy)
                
    def calculatePacketsToGet(self):
        if self.sim.debug: print self.ID, 'Network math.floor: packetsToSendPerInterval:', math.floor(self.packetsToSendPerInterval), 'num packets in Q:', len(self.inQ.theBuffer)
        if math.floor(self.packetsToSendPerInterval) > len(self.inQ.theBuffer):
            return len(self.inQ.theBuffer)
        else:
            return int(math.floor(self.packetsToSendPerInterval))
         
    def adaptiveNewRates(self):
        #Called every frame... (every 120 seconds for 5066)
        self.previousNetRates = self.overallPacketsSent - self.overallPacketsFail #This is the number of successful packets sent.
        if (self.overallPacketsSent != 0): 
            self.rateProportions = float(self.previousNetRates)/float(self.overallPacketsSent) 
        #this is success ratio of channel! Needs to be floats as needs to be a %, numbers of packets is always in integers  
        #need to combine it with the actual rate though... So if its only 50% success but doing the same actual rate as a slower channel..
        if self.sim.debug: print self.ID, 'Network: prevNetRates:', self.previousNetRates, 'overallPacketsFail:', self.overallPacketsFail, self.sim.now()
        if self.sim.debug: print self.ID, 'Network: rateProportions:', self.rateProportions, 'overallPacketsSent:', self.overallPacketsSent ,self.sim.now()
        if self.sim.debug: print self.ID, 'Network: targetReliability:', self.targetReliability, 'current PPI:', self.packetsToSendPerInterval, self.sim.now()
        self.changeDataRate()
        self.calculatePPIRate()
        if self.sim.debug: print self.ID, 'Network: new Data Rate:', self.totalRate, 'new PPI:', self.packetsToSendPerInterval, self.sim.now()
        self.resetRates()
    def changeDataRate(self):
        for rate_index, val in enumerate(self.sim.G.data_rates):
            if val == self.totalRate:
                if self.sim.debug: print 'totalRate=', val, 'rateIndex=', rate_index
                if self.rateProportions < self.sim.G.dec_error_thresholds[rate_index]: #Decrease Rate
                    if rate_index != 0:
                        self.totalRate = self.sim.G.data_rates[rate_index-1]
                        break
                elif self.rateProportions > self.sim.G.inc_error_thresholds[rate_index]: #Increase Rate
                    if self.sim.debug: print 'increase Rate, rateProportions =', self.rateProportions
                    if rate_index != len(self.sim.G.data_rates)-1:
                        self.totalRate = self.sim.G.data_rates[rate_index+1]
                        break 
##    def changeDataRate(self):
##        for rate_index, val in enumerate(self.sim.G.data_rates):
##            if val == self.totalRate:
##                if self.rateProportions < self.minReliability: #Decrease Rate
##                    if rate_index != 0:
##                        self.totalRate = self.sim.G.data_rates[rate_index-1]
##                elif self.rateProportions > self.targetReliability: #Increase Rate
##                    if rate_index != len(self.sim.G.data_rates)-1:
##                        self.totalRate = self.sim.G.data_rates[rate_index+1] 
    def calculatePPIRate(self):
        #calculate packets per interval from data rate
        PPI = int(math.floor((self.totalRate/self.sim.G.packet_size)*self.sim.G.rate_fidelity)) #remember rate is per second not per interval
        if PPI == 0: PPI = 1 #If it's 0 , make it at least 1
        self.packetsToSendPerInterval = PPI
    def configurePacketsToSend(self, pkts_to_send):
        counter = 0
        if self.sim.debug: print self.ID, 'Network: Configuring packets to send. pkts_to_send:', [pkt.link.pType for pkt in pkts_to_send], self.sim.now()
        #print self.ID, 'Network: pkts_to_send consecutive_IDs:', [pkt.network.consecutive_ID for pkt in pkts_to_send], self.sim.now()
        #print self.ID, 'Network: ILL:', [pkt.internal_last_location for pkt in pkts_to_send], self.sim.now()
        #print self.ID, 'Network: Physical ID:', [pkt.ID.Physical_ID for pkt in pkts_to_send], self.sim.now()
        if self.sim.debug: print self.ID, 'Network: self.inQ.theBuffer (packet types):', [pkt.link.pType for pkt in self.inQ.theBuffer], self.sim.now()
        #print self.ID, 'Network: self.inQ.theBuffer (ILL):', [pkt.internal_last_location for pkt in self.inQ.theBuffer], self.sim.now()
        #print self.ID, 'Network: self.inQ.theBuffer (Physical ID):', [pkt.ID.Physical_ID for pkt in self.inQ.theBuffer], self.sim.now()
        if self.sim.debug: print self.ID, 'Network: PPI', self.packetsToSendPerInterval, self.sim.now()
        pkts = pkts_to_send[counter:counter+self.packetsToSendPerInterval]
        
        if self.interface.ProcDict['kernel'].STATE == nState.LINKED_TX:
            if self.sim.debug: print self.ID, 'Network, putting All', len(pkts),'packets in SortingF', self.sim.now()
            if len(pkts) > 0: #If the pkts_to_send amount is not enough to go around, some channels will be left without - especially when EOF's take away from the total!    
                yield put, self, self.interface.ProcDict['SortingF'].inQ, [pkts]
        else:
            yield put, self, self.interface.ProcDict['MainQ'].inQ, pkts
            #as it now has a consecutive_ID, it will be bumped up the priority list.
        counter = counter+self.packetsToSendPerInterval

    def resetRates(self):
        self.overallPacketsSent = 0
        self.overallPacketsFail = 0
    def initialiseLQA(self):
        #SNR matrix is as follows: First SNR_matrix[origin,destination][frequency]
        #So this gives an average of each channel's LQA across all destinations
        for freq in range(self.sim.G.num_freq):
            self.storedLQA[freq] = sum([self.sim.Net.env_container.SNR_matrix[self.ID,dest][freq] for dest in range(self.sim.G.num_nodes) if dest != self.ID])/float(self.sim.G.num_nodes)        
    def initialiseTotalRate(self):
        self.totalRate = self.sim.G.initial_rate
    def establishInitialRates(self):
        self.calculatePPIRate()
        if self.sim.debug: print self.ID, 'totalRate', self.totalRate
        if self.sim.debug: print self.ID, 'packetsToSendPerInterval:', self.packetsToSendPerInterval
                    
#OLD FUNCTIONS::

    def initTotalRate(self, pkt_details):
        TP = self.sim.G.Throughput_SNR(self.sim.Net.env_container.SNR_matrix[self.ID,pkt_details.Destination][pkt_details.Frequency])
        self.totalRate += TP

    def deductTotalRate(self, pkt_details):
        TP = self.sim.G.Throughput_SNR(self.sim.Net.env_container.SNR_matrix[self.ID,pkt_details.Destination][pkt_details.Frequency])
        self.totalRate -= TP

class SortingF(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.buffers = []
        self.inQ = Store(capacity='unbounded', sim=sim)
        self.consecutive_ID = 0
    def execute(self):
        while True:
            yield get, self, self.inQ, 1 #Need to get all the packets from one timeslot and then send them all together
            pkts = self.got[0]
            for pkt in pkts:
                pkt = self.addWaveformDetails(pkt)
                if not self.checkInBuffer(pkt):
                    self.buffers.append(copy.deepcopy(pkt)) #This is for resending individual packets.
                    
                self.interface.ProcDict['ARQ'].lastBatchPackets.append(copy.deepcopy(pkt)) #This one is for potentially resending an entire frame (regardless of channels)
                #append to buffer for ARQ
                self.interface.ProcDict['RateController'].overallPacketsSent += 1
            if self.sim.debug: print self.ID, 'Network: SortingF putting', len(pkts),'packets into linkQ', self.sim.now()
            self.interface.linkQ.signal(copy.deepcopy(pkts))
    def addWaveformDetails(self, pkt):
        pkt.network.data_rate = self.interface.ProcDict['RateController'].totalRate #Append data_rate to packet, for SNR
        pkt.meta.waveform = self.sim.G.data_waveform
        return pkt
    def checkInBuffer(self, pkt):
        inBuf = pkt.network.consecutive_ID in [buf.network.consecutive_ID for buf in self.buffers]
        if self.sim.debug: print self.ID, 'consecutiveID:', pkt.network.consecutive_ID,'inBuf', inBuf
        return inBuf

class ARQ(Process): #MASTER RECEIVES ARQ FROM SLAVE
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.lastBatchPackets = []
        self.inQ = Store(capacity='unbounded', sim=sim)
    def execute(self):
        while True:
            yield get, self, self.inQ, 1
            if self.sim.debug: print self.ID, 'Network: [ARQ] Packet received from Slave!', self.sim.now()
            packet = self.got[0]
            success = packet.network.ARQ_success
            failure = packet.network.ARQ_fail
            failed_pkts = []

#This is not the original mechanism and in fact negates the point of storing the buffers as seperate channels!
#However, as ARQs are now universal, and duplicates are deleted, this needs to search all channel buffers
#For all potential failures and add them all. 
#Note if we change the 4G ARQ mechanism this will probably change, hence keeping the old mechanism below
            if self.sim.debug: print self.ID, 'Network (M): [ARQ] failure packets:', failure, 'success:', success, self.sim.now()
#This does actually work, tested.

            for pkt in self.interface.ProcDict['SortingF'].buffers:
                if pkt.network.consecutive_ID in failure:
                    failed_pkts.append(pkt)
                    self.interface.ProcDict['RateController'].overallPacketsFail += 1
                        
##This mechanism works by only ARQing the packets for each frequency individually, should it be universal?
##Yes because these packets will get deleted for being universal!                    

            if len(failure) == 0 and len(success) != 0 and len(self.interface.ProcDict['RateController'].inQ.theBuffer) == 0:
                #So if there are no failures, and it was not a dud (i.e. no successes), as well as RC inQ being empty, end the session:
                if self.sim.debug: print self.ID, 'Network [ARQ]: No Failed Packets and No More Packets in inQ, send EOM to Link', self.sim.now()
                self.sendEOMEvents()
            elif len(failure) == 0 and len(success) == 0:
                #If entire batch failed, resend entire thing
                if self.sim.debug: print self.ID, 'Network [ARQ]: Entire batch failed, resend all', self.sim.now()
                failed_pkts += self.lastBatchPackets
            
            if self.sim.debug: print self.ID, 'Network [ARQ]: Putting failed packets back into MainQ, num of failed pkts:', len(failed_pkts), self.sim.now()
            yield put, self, self.interface.ProcDict['MainQ'].inQ, failed_pkts
            self.wipeLastBatch()

    def sendEOMEvents(self):
        self.interface.ProcDict['RateController'].EOM = True
        self.interface.ProcDict['RateController'].frame_timer.abort = True
        self.interface.ProcDict['RateController'].frame_timer = None
        self.interface.ProcDict['RateController'].initialiseTotalRate() #Reset rates
        self.interface.ProcDict['RateController'].establishInitialRates()
        self.interface.ProcDict['msg_kernel'].LM_Terminate.signal()
    def wipeLastBatch(self):
        #Now wipe the batch ready for next one
        self.lastBatchPackets = []


class MasterFrameTimer(Process):
    #Start this when each freq is Init, and repeat each time it expires
    def __init__(self, ID, sim, iLink, send_details):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.send_details = send_details
        self.interface = iLink
        self.active = True
        self.abort = False
    def execute(self):
        if self.sim.debug: print self.ID, 'Net: MFV started', self.sim.now()
        while self.active:
            yield hold, self, self.sim.G.frame_max_time
            if self.interface.ProcDict['kernel'].STATE == nState.LINKED_TX and not self.abort: #abort occurs if EOM (not EOF)
                if self.sim.debug: print self.ID, 'Net: MFV active', self.active, self.sim.now()
                pkt = self.createEOW()
                pkt.network.priority = 999
                #Not MainQ as it bypasses the priority check and consecutive ID
                yield put, self, self.interface.ProcDict['RateController'].inQ, [pkt]
                if self.sim.debug: print self.ID, 'Net: EOF Placed into RC Q', self.sim.now()
    def createEOW(self):
        eot_packet = packet.Packet()
        eot_packet.internal_last_location = 3 #2nd layer
        eot_packet.ID = self.send_details
        eot_packet.link.pType = 6
        eot_packet.network.msg_ID = self.createID() 
        #eot_packet.physical.time = 3*self.sim.G.Trw
        eot_packet.transport.data = 32 #(256 bits/8 = 32 bytes) 
        return eot_packet
    def createID(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    

class SlaveBuffer(Process):
    #may need to move this to Link
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        
        self.incoming = None
        self.data_rate = None
        
        self.window = []
        self.window_packets = []
        self.window_success_packets = []
        
        self.temp_window_fail = []
        self.temp_window_success = []
        
        self.last_batch = False
        self.FrameTimer = None
        
        self.EOM = SimEvent(sim=self.sim)
        self.S_ARQ_Tx_Success = SimEvent(sim=sim)
        self.abort_event = SimEvent(sim=sim)
    def execute(self):
        while True:
            yield (get, self, self.inQ, 1),(waitevent, self, self.EOM)
            if self.acquired(self.inQ):
                self.incoming = copy.deepcopy(self.got[0])
                self.data_rate = self.incoming.physical.data_rate
                self.addToWindow()               
                if self.checkEOF(self.incoming): 
                    if self.sim.debug: print self.ID, 'Network: SlaveBuffer: EOF identified, sorting Window', self.sim.now()
                    self.sortWindow()
                    self.sendConf() #respond with ARQ list / success & fail
                    for x in self.waitforTxSuccess():
                        yield x
                    self.checkEOM()
                    self.resetWindow()
    def addToWindow(self):
        if self.incoming.network.consecutive_ID != None: #This will happen if it is EOF packet!
            if self.sim.debug: print self.ID, 'Network: SlaveBuffer: Packet acquired, appending to window:', len(self.window), 'packet consecutive_ID:', self.incoming.network.consecutive_ID, self.sim.now()
            self.window.append(copy.deepcopy(self.incoming.network.consecutive_ID))
            self.window_packets.append(copy.deepcopy(self.incoming))
        else:
            if self.sim.debug: print self.ID, 'Not adding to window, EOF packet', self.sim.now()
    def sortWindow(self):
        if len(self.window) > 0: 
            if self.sim.debug: print self.ID, 'Network: SlaveBuffer: About to Sort Window, presently [0] and [-1] = ', self.window[0], self.window[-1], self.sim.now()
            self.window = sorted(self.window)
            if self.sim.debug: print self.ID, 'Network: SlaveBuffer: Sorted Window, now [0] and [-1] = ', self.window[0], self.window[-1], 'len:', len(self.window), 'len packets:', len(self.window_packets), self.sim.now()
        else:
            if self.sim.debug: print self.ID, 'Network: SlaveBuffer: Window Size Zero, carry on.', self.sim.now()
            
        window_index = 0
        if len(self.window) > 0: #for end of frame, this won't happen if no success packets at all?
            for poss_index in range(self.window[0],self.window[-1]+1):
                if poss_index == self.window[window_index]:
                    #print self.ID, 'sortWindow: index:', poss_index, 'window_index:', window_index
                    self.temp_window_success.append(poss_index)
                    self.window_success_packets.append(self.window_packets[window_index])
                    window_index += 1
                else:
                    if len(self.temp_window_fail) == 0:
                        self.temp_window_fail.append(poss_index)
                    elif self.temp_window_fail[-1] != poss_index:
                        self.temp_window_fail.append(poss_index)
     
    def sendConf(self):
        conf_packet = self.makeConf()
        conf_packet.network.ARQ_success = self.temp_window_success
        conf_packet.network.ARQ_fail = self.temp_window_fail
        #Need to work out ARQ Plan - which channel? All of them?
        if self.sim.debug: print self.ID, 'Network [SB]: Sending LS_Send_ARQ to Link', self.sim.now()
#       Want this to actually be an event that sends down to LinkContainer
#       LinkContainer then makes and sends the packets
        conf_copy = copy.deepcopy(conf_packet)
        self.interface.ProcDict['msg_kernel'].LS_Send_ARQ.signal(conf_copy)
        
    def waitforTxSuccess(self): #What are the events to wait for?! Rx_Success?
        if self.sim.debug: print self.ID, 'Network [SB]: Waiting for ARQ Sent Success', self.sim.now()
        TO = TimeOut(self.sim, self.sim.G.wait_for_ARQ_Rx)
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [self.S_ARQ_Tx_Success, TO.timeoutEvent, self.abort_event]
        if self.eventsFired[0] == self.S_ARQ_Tx_Success:        
            if self.sim.debug: print self.ID, 'Network [SB]: ARQ Sent', self.sim.now()
        elif self.eventsFired[0] == TO.timeoutEvent:
            print self.ID, 'Network [SB]: DISCONT .Some terrible error, no packets were sent at all from SlaveBuffer ', self.sim.now()
            self.sendEOMEvents()
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()

    def checkEOF(self, incoming):
        return incoming.link.pType == 6   
    def checkEOM(self):
        if self.incoming.network.last_batch:
            if self.sim.debug: print self.ID, 'Network: SlaveBuffer: Last Batch = True', self.sim.now()
            if len(self.temp_window_fail) == 0 and len(self.temp_window_success) != 0:
                if self.sim.debug: print self.ID, 'Network [SB]: EOM Time', self.sim.now()
                #if its the last batch, and there are no failures (and its not a dud run - i.e. there are successes) send EOM
                self.sendEOMEvents()
                return True
            else:
                print self.ID, 'Network [SB]: Last Batch but not perfect, try again with ARQ', self.sim.now()
        return False
        
    def sendEOMEvents(self): #When its all over
        self.interface.ProcDict['msg_kernel'].LS_Terminate.signal()
        self.last_batch = False

    def makeConf(self):
        send_packet = packet.Packet()
        send_packet.link.pType = 5
        send_packet.internal_last_location = 3 #2nd layer

        send_packet.network.msg_ID = self.createID()
        
        send_packet.meta.waveform = self.sim.G.data_waveform
        send_packet.network.data_rate = self.data_rate
        return send_packet
    def resetWindow(self):
        if self.sim.debug: print self.ID, 'Network [SB]: Reset Window etc.', self.sim.now()
        self.window = []
        self.window_packets = []
        self.window_success_packets = []
        self.temp_window_fail = []
        self.temp_window_success = []
        
        self.data_rate = None
        
    def createID(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))


class WatchProperty(Process):
    def __init__(self,sim, ID, iLink):
        Process.__init__(self, sim=sim,name='WatchProp')
        self.ID = ID
        self.interface = iLink
        self.sim = sim
    def execute(self):
        while True:
            if self.sim.now() > 153:
                print '!', self.ID, [pkt.ID.Physical_ID for pkt in self.interface.ProcDict['RateController'].inQ.theBuffer], self.sim.now()
            yield hold, self, 0.1
        
class TimeOut(Process):
    """Temporary process, one use only. Initialized with a timeout parameter,
        fires an event after this amount of time has elapsed and terminates.
        This is core to the functionality of this event driven architecture
        It replaces 'yield hold' (which can only be interrupted by an 'interrupt'
        This can be merely one of many events that a Process can be waiting upon"""
    def __init__(self,sim,time,ev=0):
        Process.__init__(self, sim=sim,name='LinkTimeOutProc'+str(time))
        self.time = time
        self.active = True
        if ev==0:
            self.timeoutEvent = SimEvent(name='TimeOut_Link'+str(self.sim.G.numTO), sim=sim)
            self.sim.G.numTO += 1
        else:
            self.timeoutEvent = ev
        if self.sim.debug: print 'TO timeout expires:', self.sim.now()+self.time, 'name:', self.timeoutEvent.name
    def execute(self):
        yield hold, self, self.time
        if self.active:
            self.timeoutEvent.signal()
            if self.sim.debug: print 'TimeOutFired', self.sim.now()
        else:
            if self.sim.debug: print 'TimeOutNotFired', self.sim.now()
