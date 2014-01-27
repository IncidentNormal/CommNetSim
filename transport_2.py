'''
Created on Feb 16, 2011

@author: duncantait
'''
from SimPy.Simulation import *
from enums import *
import time, packet
import random
import string
import copy
#random.seed(123456)
        
def getClasses(): #List all main (need an interface to main simulation) active Process classes in here, this will be iterated through by OSI stack and create instances of them.   
    return [kernel, msg_kernel, TransportStore, GateKeeper, NewData] #kernel needs to be first

def getNetEvents(iLink):
    return [iLink.ProcDict['msg_kernel'].Start_Link, \
     iLink.ProcDict['msg_kernel'].Abort_Link]

def getSessEvents(iLink):
    return [iLink.ProcDict['msg_kernel'].abort_send]
    
class nState(): #This ALE protocol will only support 1 session at a time [not any more] 
    FREE = 0
    WAITING_FOR_LINK = 1
    LINKED = 2
    LINKED_RX = 3
    WFL_RX = 4
    
class State():
    STATE = nState.FREE

class msg_kernel(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)

        self.interface_events()
    def interface_events(self):
        #NETWORK
        self.Start_Link = SimEvent(sim=self.sim, name='Start_Link')
        self.Abort_Link = SimEvent(sim=self.sim, name='Abort_Link')
        #SESSION
        self.abort_send = SimEvent(sim=self.sim, name='abort_send')
        self.M_End_Of_Block = SimEvent(sim=self.sim, name='M_End_Of_Block')
        self.S_End_Of_Block = SimEvent(sim=self.sim, name='S_End_Of_Block')
    def execute(self):
        while True:
            yield waitevent, self, self.interface.netEvents + self.interface.sessEvents #env_events!!!! Think about this!
            #NETWORK
            if self.eventsFired[0].name=='M_Link_Failed':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Link_Failed.signal(signal_ID)
            elif self.eventsFired[0].name=='M_Link_Success':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Link_Success.signal(signal_ID)
            elif self.eventsFired[0].name=='M_Data_Tx_Sent':
                signal_ID = self.eventsFired[0].signalparam[0] #Added whole packet as 2nd part of parameter for Vis to monitor data size and data rate etc.
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Data_Tx_Sent.signal(signal_ID)
            elif self.eventsFired[0].name=='M_Data_Tx_Fail':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Data_Tx_Fail.signal(signal_ID)
            elif self.eventsFired[0].name=='M_Data_Rx_Rec':
                if self.sim.debug: print self.ID, 'Transport msg_kernel M_Data_Rx_Rec!!!', self.sim.now()
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Data_Rx_Rec.signal(signal_ID)
            elif self.eventsFired[0].name=='M_Data_Rx_Fail':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Data_Rx_Fail.signal(signal_ID)
            elif self.eventsFired[0].name=='M_Link_Ended':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Link_Ended.signal(signal_ID)
            elif self.eventsFired[0].name=='S_Link_Failed':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Link_Failed.signal(signal_ID)
            elif self.eventsFired[0].name=='S_Link_Ended':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Link_Ended.signal(signal_ID)
            elif self.eventsFired[0].name=='S_Link_Success':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Link_Success.signal(signal_ID)
            elif self.eventsFired[0].name=='M_Switch_to_Slave':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.M_Switch_to_Slave.signal(signal_ID)
            elif self.eventsFired[0].name=='S_Link_Started':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Link_Started.signal(signal_ID)
            elif self.eventsFired[0].name=='S_Data_Rx_Rec':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Data_Rx_Rec.signal(signal_ID)
            elif self.eventsFired[0].name=='S_Data_Rx_Fail':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Data_Rx_Fail.signal(signal_ID)                
            elif self.eventsFired[0].name=='S_Data_Tx_Sent':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Data_Tx_Sent.signal(signal_ID)
            elif self.eventsFired[0].name=='S_Data_Tx_Fail':
                signal_ID = self.eventsFired[0].signalparam
                self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].SessionMsgKernel.S_Data_Tx_Fail.signal(signal_ID)                
            elif self.eventsFired[0].name=='M_Link_Aborted':
                print self.ID, 'Transport: KERNEL: M_Link_Aborted received, placing packets back into Transport Queue', self.sim.now()
                packets = self.eventsFired[0].signalparam
                print 'num_pkts = ', len(packets)
                if len(packets) > 0:
                    signal_ID = packets[0].ID
                    for pkt in packets:
                        if pkt.link.pType == 3:
                            pkt.internal_last_location = Layer.TRANSPORT
                            self.interface.ProcDict['GateKeeper'].session_list[signal_ID.Destination].OutgoingData.dest.datagram_list.append(pkt)
                            if self.sim.debug: print '1 packet into Transport'
                        
            #SESSION
            if self.eventsFired[0].name[0:5]=='taken': #channel taken
                index = int(self.eventsFired[0].name[5:])
            if self.eventsFired[0].name[0:4]=='free': #channel free
                index = int(self.eventsFired[0].name[4:])
    


class kernel(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        
        #self.mode = nState.FREE
    def execute(self):
        #self.MonitorVar = MonitorVar(self.sim, self.ID, self.interface)
        #self.sim.activate(self.MonitorVar, self.MonitorVar.execute())
        while True:
            yield get, self, self.inQ, 1
            rec_packet = self.got[0]
            #print self.ID, 'TRANSPORT packet recd into kernel!!, mode:', self.interface.ProcDict['kernel'].STATE, 'notes:', rec_packet.notes,  self.sim.now()
            last_location = rec_packet.internal_last_location
            rec_packet.internal_last_location = Layer.TRANSPORT
            #So if from above do New Data routine, if from below put in correct session, into relevant SessionKernel
            if last_location == Layer.SESSION:
                if self.sim.debug: print self.ID, 'Transport: passing to NewData', self.sim.now()
                yield put, self, self.interface.ProcDict['NewData'].inQ, [rec_packet]
            elif last_location == Layer.NETWORK:
                if self.sim.debug: print self.ID, 'Transport: passing to Relevant SessionKernel', self.sim.now()
                yield put, self, self.interface.ProcDict['GateKeeper'].session_list[rec_packet.link.origin].SessionKernel.inQ, [rec_packet]
            
                    
class TransportStore(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        self.pendingQ = []
        self.Destinations = [TransportList(i) for i in range(self.sim.G.num_nodes)] #starts with all known nodes but adds possibility of extra nodes being added
    def execute(self):
        while True:
            yield get, self, self.inQ, 1
            #if self.sim.debug: print self.ID, 'TS', self.sim.now()
            if len(self.interface.ProcDict['GateKeeper'].packetAdded.waits) > 0:
                self.interface.ProcDict['GateKeeper'].packetAdded.signal()
            new_datagram = self.got[0]
            dest_found = False
            for transport_list in self.Destinations:
                if new_datagram.ID.Destination == transport_list.destination:
                    if self.sim.debug: print self.ID, 'Transport: Appending to transport_list', self.sim.now()
                    transport_list.datagram_list.append(new_datagram)
                    dest_found = True
            if dest_found == False:
                #if self.sim.debug: print self.ID, 'TRANSPORT STORE dest not found in list, creating new one'
                new_dest = TransportList(new_datagram.ID.Destination)
                new_dest.datagram_list.append(new_datagram)
                self.Destinations.append(new_dest)
class TransportList():
    def __init__(self, destination): #each of these is a list of 'datagrams' for each destination
        self.destination = destination
        self.datagram_list = []  

class DestinationContainer():
    def __init__(self, ID, sim, destination, iLink):
        self.ID = ID
        self.destination = destination
        self.interface = iLink
        self.sim = sim

        self.SessionKernel = SessionKernel(self.ID, sim, self.destination, iLink)
        self.SessionMsgKernel = SessionMsgKernel(self.ID, sim, self.destination, iLink)
        self.OutgoingData = OutgoingData(self.ID, sim, self.destination, iLink)
        self.IncomingData = IncomingData(self.ID, sim, self.destination, iLink)
        #self.TransportDataRec = TransportDataRec(self.ID, sim, self.destination, iLink)
        
        self.sim.activate(self.SessionKernel, self.SessionKernel.execute())
        self.sim.activate(self.SessionMsgKernel, self.SessionMsgKernel.execute())
        self.sim.activate(self.OutgoingData, self.OutgoingData.execute())
        self.sim.activate(self.IncomingData, self.IncomingData.execute())
        #self.sim.activate(self.TransportDataRec, self.TransportDataRec.execute())


class SessionKernel(Process):
    def __init__(self, ID, sim, destination, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.destination = destination
        self.interface = iLink
        self.sim = sim
        self.mode = nState.FREE
        
        self.inQ = Store(sim=sim)

        self.linkUp = False
        self.linkingInstance = [] #will only ever be one in this list
        self.linkedInstance = [] #same here
    def execute(self):
        self.IncomingData = self.interface.ProcDict['GateKeeper'].session_list[self.destination].IncomingData
        while True:
            yield get, self, self.inQ, 1
            rec_packet = self.got[0]
            if self.mode != nState.LINKED_RX: #Only time it would ever RECEIVE a packet directly is in Linked RX mode
                print self.ID, 'Discontinuous 11', self.mode, rec_packet.ID.all_IDs() #Remember, packets from above layers are extracted from TransportStore
            else:
                yield put, self, self.IncomingData.inQ, [rec_packet]


class SessionMsgKernel(Process):
    def __init__(self, ID, sim, destination, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.destination = destination
        self.interface = iLink
        self.sim = sim
        #self.mode = nState.FREE
        
        self.M_Link_Failed = SimEvent(sim=sim, name='M_Link_Failed')
        self.M_Link_Success = SimEvent(sim=sim, name='M_Link_Success')
        self.M_Link_Ended = SimEvent(sim=sim, name='M_Link_Ended')
        self.M_Data_Tx_Sent = SimEvent(sim=sim, name='M_Data_Tx_Sent')
        self.M_Data_Tx_Fail = SimEvent(sim=sim, name='M_Data_Tx_Fail')
        self.M_Data_Rx_Rec = SimEvent(sim=sim, name='M_Data_Rx_Rec')
        self.M_Data_Rx_Fail = SimEvent(sim=sim, name='M_Data_Rx_Fail')
        self.M_Switch_to_Slave = SimEvent(sim=sim, name='M_Switch_to_Slave')
        self.S_Link_Started = SimEvent(sim=sim, name='S_Link_Started')
        self.S_Link_Failed = SimEvent(sim=sim, name='S_Link_Failed')
        self.S_Link_Success = SimEvent(sim=sim, name='S_Link_Success')
        self.S_Link_Ended = SimEvent(sim=sim, name='S_Link_Ended')
        self.S_Data_Rx_Rec = SimEvent(sim=self.sim, name='S_Data_Rx_Rec')
        self.S_Data_Rx_Fail = SimEvent(sim=self.sim, name='S_Data_Rx_Fail')
        self.S_Data_Tx_Sent = SimEvent(sim=self.sim, name='S_Data_Tx_Sent')
        self.S_Data_Tx_Fail = SimEvent(sim=self.sim, name='S_Data_Tx_Fail')

    def execute(self):
        self.kernel = self.interface.ProcDict['GateKeeper'].session_list[self.destination].SessionKernel
        self.IncomingData = self.interface.ProcDict['GateKeeper'].session_list[self.destination].IncomingData
        self.OutgoingData = self.interface.ProcDict['GateKeeper'].session_list[self.destination].OutgoingData
        
        while True:
            yield waitevent, self, [self.M_Link_Failed, self.M_Link_Success, self.M_Link_Ended, self.M_Data_Tx_Sent, self.M_Data_Rx_Rec, self.M_Data_Rx_Fail, self.M_Data_Tx_Fail, self.M_Switch_to_Slave, self.S_Link_Failed, self.S_Link_Success, self.S_Link_Ended, self.S_Link_Started, self.S_Data_Rx_Rec, self.S_Data_Rx_Fail, self.S_Data_Tx_Sent, self.S_Data_Tx_Fail]
            if self.eventsFired[0] == self.M_Link_Failed:
                if self.kernel.mode == nState.WAITING_FOR_LINK:
                    self.OutgoingData.M_Link_Failed.signal(self.eventsFired[0].signalparam) #slightly odd way of calling linkingInstance, but only ever 1 object in the list.
                else:
                    print self.ID, 'Discont1'
                    print self.kernel.mode
            if self.eventsFired[0] == self.M_Link_Success:
                if self.kernel.mode == nState.WAITING_FOR_LINK:
                    self.OutgoingData.M_Link_Success.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, 'Discont2'
                    print self.kernel.mode
            if self.eventsFired[0] == self.M_Link_Ended:
                if self.kernel.mode == nState.LINKED:
                    self.OutgoingData.M_Link_Ended.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discont3'
            if self.eventsFired[0] == self.M_Data_Tx_Sent:
                if self.kernel.mode == nState.LINKED:
                    #print 'Number linkedInstances:', len(self.kernel.linkedInstance) #To maintain 'multiple links' possibility, this should actively search for the correct linked instance using signalparam.Destination
                    self.OutgoingData.M_Data_Tx_Sent.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, self.destination, 'Discont3a'
                    print self.kernel.mode
            if self.eventsFired[0] == self.M_Data_Tx_Fail:
                if self.kernel.mode == nState.LINKED:
                    self.OutgoingData.M_Data_Tx_Fail.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discont3b'
            if self.eventsFired[0] == self.M_Data_Rx_Rec:
                if self.kernel.mode == nState.LINKED:
                    #print 'Number linkedInstances:', len(self.kernel.linkedInstance) #To maintain 'multiple links' possibility, this should actively search for the correct linked instance using signalparam.Destination
                    if self.sim.debug: print self.ID, 'Transport: SessionMsgKernel M_Data_Rx_Rec !!', self.sim.now()
                    self.OutgoingData.M_Data_Rx_Rec.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, self.destination, 'Discont3c'
                    print self.kernel.mode
            if self.eventsFired[0] == self.M_Data_Rx_Fail:
                if self.kernel.mode == nState.LINKED:
                    self.OutgoingData.M_Data_Rx_Fail.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discont3d'
            if self.eventsFired[0] == self.M_Switch_to_Slave:
                if self.kernel.mode == nState.WAITING_FOR_LINK:
                    if self.sim.debug: print self.ID, 'Transport: M SWITCH SLAVE, details:', self.eventsFired[0].signalparam.all_IDs()
                    #REMEMBER: The parameter here is the call_details for the new, SLAVE call, but with this destination as ID.Destination
                    #and the slave destination as ID.New_Destination, this means that all OTHER IDs WILL BE INCONSISTENT WITH THIS DESTINATION.
                    
                    m_call_details = self.eventsFired[0].signalparam
                    s_call_details = copy.deepcopy(m_call_details)
                    s_call_details.Destination = s_call_details.New_Destination
                    self.OutgoingData.M_Switch_to_Slave.signal(m_call_details)
                    yield hold, self, 0 #Wait for OutgoingData to finish first
                    #does not send this to THIS DESTINATIONS S LINK STARTED! But the one specified in parameter destination 
                    self.interface.ProcDict['GateKeeper'].session_list[s_call_details.Destination].IncomingData.S_Link_Started.signal(s_call_details)
                else:
                    print 'Discont4'
                    print self.ID, self.destination, self.kernel.mode
            if self.eventsFired[0] == self.S_Link_Failed:
                if self.kernel.mode == nState.WFL_RX:
                    self.IncomingData.S_Link_Failed.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, self.destination, 'Discont4b'
                    print self.kernel.mode
            if self.eventsFired[0] == self.S_Link_Success:
                if self.kernel.mode == nState.WFL_RX:
                    if self.sim.debug: print self.ID, 'TRANSPORT: S LINK SUCCESS!', self.sim.now()
                    self.IncomingData.S_Link_Success.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, 'Discont5'
                    print self.destination, self.kernel.mode
            if self.eventsFired[0] == self.S_Link_Ended:
                if self.kernel.mode == nState.LINKED_RX:
                    self.IncomingData.S_Link_Ended.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discont6'
            if self.eventsFired[0] == self.S_Link_Started:
                if self.kernel.mode == nState.FREE:
                    if self.sim.debug: print self.ID, self.destination, 'TRANSPORT: S LINK STARTED!', self.sim.now()
                    self.IncomingData.S_Link_Started.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, self.destination, 'Discont7', self.kernel.mode
                    print self.kernel.mode
            if self.eventsFired[0] == self.S_Data_Rx_Rec:
                if self.kernel.mode == nState.LINKED_RX:
                    self.IncomingData.S_Data_Rx_Rec.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, self.destination, 'Discont16', self.kernel.mode
            if self.eventsFired[0] == self.S_Data_Rx_Fail:
                if self.kernel.mode == nState.LINKED_RX:
                    self.IncomingData.S_Data_Rx_Fail.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discont17'
            if self.eventsFired[0] == self.S_Data_Tx_Sent:
                if self.kernel.mode == nState.LINKED_RX:
                    self.IncomingData.S_Data_Tx_Sent.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discont18'
            if self.eventsFired[0] == self.S_Data_Tx_Fail:
                if self.kernel.mode == nState.LINKED_RX:
                    self.IncomingData.S_Data_Tx_Fail.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discont19'

class OutgoingData(Process):
    def __init__(self, ID, sim, destination, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.destination = destination
        self.interface = iLink
        self.sim = sim
        self.mode = nState.FREE
        
        self.packetAdded = SimEvent(sim=sim)
        self.go = SimEvent(sim=sim)

        self.call_packet = None
        self.all_data = None
        self.currentDatagram = None
        self.transport_ID = None
        self.switch_to_slave = False
        
        self.M_Link_Failed = SimEvent(sim=sim, name='M_Link_Failed')
        self.M_Link_Success = SimEvent(sim=sim, name='M_Link_Success')
        self.M_Switch_to_Slave = SimEvent(sim=sim, name='M_Switch_to_Slave')
        
        self.M_Data_Tx_Sent = SimEvent(sim=sim, name='M_Data_Tx_Sent')
        self.M_Data_Tx_Fail = SimEvent(sim=sim, name='M_Data_Tx_Fail')
        self.M_Data_Rx_Rec = SimEvent(sim=sim, name='M_Data_Rx_Rec')
        self.M_Data_Rx_Fail = SimEvent(sim=sim, name='M_Data_Rx_Fail')
        self.M_Link_Ended = SimEvent(sim=sim, name='M_Link_Ended')

        self.abort_event = SimEvent(sim=sim)
    def execute(self):
        #Declare these after initialization (as need to wait for these things to be initialized themselves)
        self.kernel = self.interface.ProcDict['GateKeeper'].session_list[self.destination].SessionKernel
        self.dest = self.interface.ProcDict['TransportStore'].Destinations[self.destination]
        while True:
            if self.sim.debug: print self.ID, self.destination, 'Transport: Outgoing Data, while filtercondition...', self.sim.now()
            while self.filterCond():
                if self.sim.debug: print self.ID, self.destination, 'Transport: OutData Filter Condition Satisfied', self.sim.now()
                self.getPackets()
                if not self.kernel.linkUp:
                    if self.sim.debug: print self.ID, self.destination, 'Transport: OutData Link NOT up', self.sim.now()
                    for x in self.EstablishLink():
                        yield x
                else:
                    if self.sim.debug: print self.ID, self.destination, 'Transport: OutData Link ALREADY up', self.sim.now()
                    for x in self.SendData():
                        yield x
            for x in self.waitCond():
                yield x
    def filterCond(self):
        return len(self.dest.datagram_list) > 0 \
            and self.interface.ProcDict['GateKeeper'].active_session == self.destination \
            and (self.kernel.mode == nState.FREE or self.kernel.mode == nState.LINKED) \
            and not self.switch_to_slave
    def waitCond(self):
        if not (self.kernel.mode == nState.FREE or self.kernel.mode == nState.LINKED):
            #Busy in something, wait for end of session
            if self.sim.debug: print self.ID, self.destination, 'Transport: Not correct mode, wait for session change', self.sim.now()
            yield waitevent, self, self.interface.ProcDict['GateKeeper'].session_change
            if self.sim.debug: print self.ID, self.destination, 'Transport: Session change event fired1', self.sim.now()
        elif len(self.dest.datagram_list) == 0:
            #No packets, wait for packets to be added
            #print [(x.destination, len(x.datagram_list)) for x in self.interface.ProcDict['TransportStore'].Destinations]
            if self.sim.debug: print self.ID, self.destination, 'Transport: No packets, wait for packet added event', self.sim.now()
            yield waitevent, self, self.interface.ProcDict['GateKeeper'].packetAdded
            if self.sim.debug: print self.ID, self.destination, 'Transport: Packet added event fired', self.sim.now()
        elif self.interface.ProcDict['GateKeeper'].active_session != self.destination:
            #Packets exist and correct mode, request session and wait for change.
            if self.sim.debug: print self.ID, self.destination, 'Transport: Active session not this one, request session and wait for session change', self.sim.now()
            self.interface.ProcDict['GateKeeper'].active_request.signal(self.destination)
            yield waitevent, self, self.interface.ProcDict['GateKeeper'].session_change
            if self.sim.debug: print self.ID, self.destination, 'Transport: Session change event fired2', self.sim.now()
        elif self.switch_to_slave:
            #Switched to slave, will now be busy, so wait for session change!
            if self.sim.debug: print self.ID, self.destination, 'Transport: Switch to Slave event fired, wait for session change', self.sim.now()
            self.switch_to_slave = False
            yield waitevent, self, self.interface.ProcDict['GateKeeper'].session_change
            if self.sim.debug: print self.ID, self.destination, 'Transport: Session change event fired3', self.sim.now()
        else:
            if self.sim.debug: print self.ID, self.destination, 'Transport: All filters passed, back to start again', self.sim.now()
    def getPackets(self):
        self.all_data = copy.deepcopy(self.dest.datagram_list)
        self.dest.datagram_list = []
        self.currentDatagram = self.all_data[0]
        self.transport_ID = self.currentDatagram.ID.Transport_ID
        #break into chunks..
        self.call_packet = self.createCallPacket()
    def createCallPacket(self):
        send_packet = packet.Packet()
        send_packet.ID = self.currentDatagram.ID
        send_packet.internal_last_location = Layer.TRANSPORT
        return send_packet
    
    def EstablishLink(self):
        self.interface.networkQ.signal(self.call_packet)
        self.kernel.mode = nState.WAITING_FOR_LINK
        yield waitevent, self, [self.M_Link_Success, self.M_Link_Failed, self.M_Switch_to_Slave]
        if self.eventsFired[0] == self.M_Link_Failed:
            if self.sim.debug: print self.ID, self.destination,'Transport: EstablishLink event Recd: M_Link_Failed', self.sim.now()
            self.endLink()
        elif self.eventsFired[0] == self.M_Link_Success:
            if self.sim.debug: print self.ID, self.destination, 'TRANSPORT Outgoing Data: M Link Success', self.sim.now()
            self.kernel.mode = nState.LINKED
            self.kernel.linkUp = True
            for x in self.SendData():
                yield x
        elif self.eventsFired[0] == self.M_Switch_to_Slave:
            if self.sim.debug: print self.ID, self.destination, 'Transport: EstablishLink event Recd: M_Link_Switching - Cancelling Link', self.sim.now()
            self.switchToSlave()
    def SendData(self):
        long_data = self.createLongData()
        if self.sim.debug: print self.ID, self.destination, 'TRANSPORT Outgoing Data: Sending Data', self.sim.now()
        self.interface.networkQ.signal(long_data)
        yield waitevent, self, [self.M_Data_Tx_Fail, self.M_Data_Rx_Fail, self.M_Data_Rx_Rec, self.M_Link_Ended] #Miss out M_Data_Tx_Sent for now -> use in Vis
        if self.eventsFired[0] == self.M_Data_Tx_Fail:
            if self.sim.debug: print self.ID, self.destination, 'Transport: Tx Data Failed', self.sim.now()
            self.endLink(True)
            yield hold, self, 0 #This is to allow GateKeeper session ended event to be signalled before filterCond is arrived at
        elif self.eventsFired[0] == self.M_Data_Rx_Fail:
            if self.sim.debug: print self.ID, self.destination, 'Transport: Rx Data Response Failed', self.sim.now()
            self.endLink(True) #this node doesnt know if it actually sent or not.
            yield hold, self, 0 #This is to allow GateKeeper session ended event to be signalled before filterCond is arrived at
        elif self.eventsFired[0] == self.M_Data_Rx_Rec or self.eventsFired[0] == self.M_Data_Tx_Sent:
            if self.sim.debug: print self.ID, self.destination, 'Transport: SendData: Success [and Rx Data Response recd]', self.sim.now()            
            self.endLink()
        elif self.eventsFired[0] == self.M_Link_Ended:
            if self.sim.debug: print self.ID, self.destination, 'Transport: Link Ended probably aborted', self.sim.now()            
            self.endLink(True)
            yield hold, self, 0 #This is to allow GateKeeper session ended event to be signalled before filterCond is arrived at

    def createLongData(self):
        #This takes the entire data list and turns it into one packet, for the sake of this model
        firstPacket = self.all_data[0]
        totalDataLength = 0
        for d in self.all_data:
            totalDataLength += d.transport.data
        firstPacket.transport.data = totalDataLength*8
        if self.sim.debug: print self.ID, self.destination, 'totalDataLength:', totalDataLength
        self.all_data = []
        return firstPacket
    def switchToSlave(self):          
        self.switch_to_slave = True
        self.transport_ID = None
        if self.kernel.mode != nState.WFL_RX: #This would only happen if the node that overrode ALE Master was the same as the node ALE Master was trying to link to
            self.kernel.mode = nState.FREE
        self.dest.datagram_list += self.all_data
    def endLink(self, endSess=False):
        if self.sim.debug: print self.ID, 'Transport: Ending Link! data left:', len(self.dest.datagram_list), len(self.all_data), self.sim.now()
        if endSess: self.interface.ProcDict['GateKeeper'].session_ended.signal(self.destination)
        self.kernel.mode = nState.FREE #and this?
        self.transport_ID = None
        self.kernel.linkUp = False
        self.dest.datagram_list += self.all_data
        
        
class GateKeeper(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.sim = sim

        self.active = False
        self.active_session = None
        self.session_change = SimEvent(sim=sim)
        self.session_ended = SimEvent(sim=sim)
        self.active_request = SimEvent(sim=sim)
        self.incoming_call = SimEvent(sim=sim)
        self.session_list = [DestinationContainer(self.ID, sim, i, iLink) for i in range(self.sim.G.num_nodes)]
        
        self.packetAdded = SimEvent(sim=sim)
    def execute(self):
        while True:
            yield waitevent, self, [self.active_request, self.session_ended, self.incoming_call] #When a session requests control it fires this event
            request_dest = self.eventsFired[0].signalparam
            if self.eventsFired[0] == self.active_request:
                if request_dest == self.active_session:
                    pass
                else:
                    if not self.active:
                        if self.sim.debug: print self.ID, 'Transport: GATEKEEPER change session due to ACTIVE REQUEST WHEN NONE ACTIVE to:', request_dest, self.sim.now()
                        self.active =  True
                        self.active_session = request_dest
                        self.session_change.signal() #This will create a bias toward certain destinations, as they will all request
                        #control when the session changes at the same time, and presumably some will be more likely to be heard than others
            elif self.eventsFired[0] == self.session_ended:
                if self.sim.debug: print self.ID, 'Transport: Gatekeeper: Session Ended Detected', self.sim.now()
                self.active = False
                self.active_session = None
                #How to choose? The one with the most packets or the least, or random??
                max_packets = 0 #to prevent choosing an ID if all have zero in their stores.
                store_id = -1
                for i in range(len(self.interface.ProcDict['TransportStore'].Destinations)):
                    if len(self.interface.ProcDict['TransportStore'].Destinations[i].datagram_list) > max_packets:
                        max_packets = len(self.interface.ProcDict['TransportStore'].Destinations[i].datagram_list)
                        store_id = i
                if store_id != -1:
                    if self.sim.debug: print self.ID, 'Transport: GATEKEEPER change session due to SESSION ENDED to:', store_id, self.sim.now()
                    self.active = True
                    self.active_session = store_id
                    self.session_change.signal()
            #So hopefully, if a session has packets in it's store it'll be waiting for self.session_change.signal()
            #and if it doesn't it'll be waiting for self.packetAdded.signal(), which will then trigger off self.active_request()
            #So there should never be a stalemate situation.
            elif self.eventsFired[0] == self.incoming_call:
                if self.active:
                    print 'DISCONTINUOUS CALL REQUEST OCCURRING WHEN ALREADY ACTIVE'
                else:
                    if self.sim.debug: print self.ID, 'Transport: GATEKEEPER change session due to INCOMING CALL to:', request_dest, self.sim.now()
                    self.active_session = request_dest
                    self.session_change.signal()
                    
class NewData(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
    def execute(self):
        while True:
            yield get, self, self.inQ, 1
            new_data_chunk = self.got[0]
            if self.sim.debug: print self.ID, 'TRANSPORT NEWDATA: data CHUNK received:', new_data_chunk.ID.all_IDs(), self.sim.now()
            datagrams = self.createSegments(new_data_chunk)
            yield put, self, self.interface.ProcDict['TransportStore'].inQ, datagrams
            
    def createSegments(self, data_chunk):
        returnDatagrams = []
        timestamp = time.time()
        payload = data_chunk.session.data
        split_payload = self.splitString(payload, 1024)
        for portion in split_payload:
            new_datagram = packet.Packet()
            new_datagram.ID = data_chunk.ID
            new_datagram.ID.Transport_ID = self.createID()
            new_datagram.transport.origin = self.ID
            new_datagram.transport.payload = portion
            new_datagram.transport.data = len(portion)
            new_datagram.transport.header = self.createHeader(new_datagram)
            new_datagram.internal_last_location = Layer.TRANSPORT
            returnDatagrams.append(new_datagram)
        return returnDatagrams
    def splitString(self, s, n):
        return [s[i:i+n] for i in xrange(0, len(s), n)]
    def createHeader(self, pkt):
        return 'test'
    def createID(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    
class MonitorVar(Process):
    '''Purely debug Process - used to print the condition of a particular Node's
        Transport layer every 0.1 seconds for a period of time
        Activated in kernel class'''
    def __init__(self, sim, ID, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.interface = iLink
        self.ID = ID
    def execute(self):         
        while True:
            yield hold, self, 100
            while True:
                if self.sim.now() > 100 and self.sim.now() < 150:
                    self.sim.debug = True
                    if self.ID == 0:
                        print [i.SessionKernel.mode for i in self.interface.ProcDict['GateKeeper'].session_list], self.interface.ProcDict['GateKeeper'].active, self.interface.ProcDict['GateKeeper'].active_session, self.sim.now()
                        #print self.sim.allEventNotices() 
                    yield hold, self, 0.1
                else:
                    yield hold, self, 0.1


class IncomingData(Process):
    def __init__(self, ID, sim, destination, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.destination = destination
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)

        self.S_Link_Started = SimEvent(sim = sim)
        self.S_Link_Failed = SimEvent(sim = sim)
        self.S_Link_Success = SimEvent(sim = sim)

        self.inQ = Store(capacity='unbounded', sim=sim)

        self.transport_ID = None
        self.active = True
        self.S_Link_Ended = SimEvent(sim = sim, name='S_Link_Ended')
        self.S_Data_Rx_Rec = SimEvent(sim = sim, name='S_Data_Rx_Rec')
        self.S_Data_Rx_Fail = SimEvent(sim = sim, name='S_Data_Rx_Fail')
        self.S_Data_Tx_Sent = SimEvent(sim = sim, name='S_Data_Tx_Sent')
        self.S_Data_Tx_Fail = SimEvent(sim = sim, name='S_Data_Tx_Fail')
    def execute(self):
        self.kernel = self.interface.ProcDict['GateKeeper'].session_list[self.destination].SessionKernel
        while True:
            self.active = True
            
            yield waitevent, self, self.S_Link_Started
            if self.sim.debug: print self.ID, self.destination, 'TRANSPORT: Inc Data S Link Started', self.sim.now()
            self.interface.ProcDict['GateKeeper'].active_request.signal(self.destination)
            self.kernel.mode = nState.WFL_RX
            for x in self.waitForLinkSuccess():
                yield x
            while self.active:
                for x in self.waitForData():
                    yield x
    def waitForLinkSuccess(self):
        yield waitevent, self, [self.S_Link_Failed, self.S_Link_Success]
        if self.eventsFired[0] == self.S_Link_Failed:
            if self.sim.debug: print self.ID, self.destination, 'Transport: TransportLinkRec: S Link Failed, end session.', self.sim.now()
            self.interface.ProcDict['GateKeeper'].session_ended.signal(self.destination) #DEACTIVATE
            self.kernel.mode = nState.FREE
            self.active = False
        elif self.eventsFired[0] == self.S_Link_Success:
            if self.sim.debug: print self.ID, self.destination, 'Transport: TransportLinkRec: S Link Success, to Linked_RX mode. Link details:', self.eventsFired[0].signalparam.all_IDs(), self.sim.now()
            self.kernel.mode = nState.LINKED_RX
            self.kernel.linkUp = True
    def waitForData(self):
        if self.sim.debug: print self.ID, self.destination, 'Transport: TransportDataRec: Waiting for Data.', self.sim.now()
        yield (get, self, self.inQ, 1),(waitevent, self, (self.S_Data_Rx_Fail, self.S_Data_Tx_Fail, self.S_Link_Ended))
        if self.acquired(self.inQ):
            incoming = self.got[0]
            self.incoming_details = incoming.ID
            if incoming.link.pType == 1 or incoming.link.pType == 2 or incoming.link.pType == 4 or incoming.link.pType == 6:
                if self.sim.debug: print self.ID, self.destination, 'Transport: TransportDataRec: Some next packet received, ending session.', self.sim.now()
                self.endSession()
            if incoming.link.pType == 3:
                if self.sim.debug: print self.ID, self.destination, 'Transport: TransportDataRec: Data received, passing up to Session.', self.sim.now()
                self.interface.sessionQ.signal(incoming)
            else:
                print 'Discont Anomalous Packet'
                self.endSession()
        elif self.eventsFired[0] == self.S_Link_Ended or self.eventsFired[0] == self.S_Data_Rx_Fail or self.eventsFired[0] == self.S_Data_Tx_Fail:
            if self.sim.debug: print self.ID, self.destination, 'Transport: TransportDataRec: Event recd: End Session.', self.sim.now()
            self.endSession()
        elif self.evernsFired[0] == self.S_Data_Rx_Rec:
            print 'good'
        else:
            print 'Discont wtf'
    def endSession(self):
        self.kernel.mode = nState.FREE
        self.kernel.linkUp = False
        #self.destination = None
        self.transport_ID = None
        #self.kernel = None
        self.active = False
        self.interface.ProcDict['GateKeeper'].session_ended.signal(self.destination) #DEACTIVATE
