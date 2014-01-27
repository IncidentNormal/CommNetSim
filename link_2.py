'''
Created on Feb 16, 2011

@author: duncantait
'''
from SimPy.Simulation import *
from enums import *
from operator import itemgetter, attrgetter
import packet
import copy
import random
import string
import math
import numpy as np
#random.seed(123456)

def getClasses(): #List all main (that need an interface to main simulation) active Process classes in here, this named function will be iterated through by osi_model.py and create instances of them.   
    return [kernel, msg_kernel, Scanning, ALESlave, ALEMaster]

def getNetEvents(iLink): #Events -> Network
    return [iLink.ProcDict['msg_kernel'].M_Link_Failed, \
    iLink.ProcDict['msg_kernel'].M_Link_Started, \
    iLink.ProcDict['msg_kernel'].M_Link_Success, \
    iLink.ProcDict['msg_kernel'].M_Link_Ended, \
    iLink.ProcDict['msg_kernel'].M_Link_Retry, \
    iLink.ProcDict['msg_kernel'].M_Data_Tx_Sent, \
    iLink.ProcDict['msg_kernel'].M_Data_Tx_Fail, \
    iLink.ProcDict['msg_kernel'].M_Data_Rx_Rec, \
    iLink.ProcDict['msg_kernel'].M_Data_Rx_Fail, \
    iLink.ProcDict['msg_kernel'].M_ARQ_Rx_Success, \
    iLink.ProcDict['msg_kernel'].M_Switch_to_Slave, \
    iLink.ProcDict['msg_kernel'].S_Link_Started, \
    iLink.ProcDict['msg_kernel'].S_Link_Failed, \
    iLink.ProcDict['msg_kernel'].S_Link_Success, \
    iLink.ProcDict['msg_kernel'].S_Link_Ended, \
    iLink.ProcDict['msg_kernel'].S_Data_Rx_Rec, \
    iLink.ProcDict['msg_kernel'].S_Data_Rx_Fail, \
    iLink.ProcDict['msg_kernel'].S_Data_Tx_Sent, \
    iLink.ProcDict['msg_kernel'].S_Data_Tx_Fail, \
    iLink.ProcDict['msg_kernel'].S_ARQ_Tx_Success]

def getPhyEvents(iLink): #Events -> Physical
    return [iLink.ProcDict['msg_kernel'].time_out, \
            iLink.ProcDict['msg_kernel'].stop_scanning, \
            iLink.ProcDict['msg_kernel'].start_scanning] 

class msg_kernel(Process):
    '''Process deals with all incoming and outgoing Internal Messaging events
        Outgoing events are listed inside 'interface_events()' (split into two
        sections - one for the above layer (Network) and one for below (Physical)
        The PEM (execute()) waits on incoming events, and acts upon them
        according to current Layer conditions'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)

        self.interface_events()
        
    def interface_events(self):
        #NETWORK
        self.M_Link_Started = SimEvent(sim=self.sim, name='M_Link_Started')
        self.M_Link_Failed = SimEvent(sim=self.sim, name='M_Link_Failed')
        self.M_Link_Success = SimEvent(sim=self.sim, name='M_Link_Success')
        self.M_Link_Ended = SimEvent(sim=self.sim, name='M_Link_Ended')
        self.M_Link_Retry = SimEvent(sim=self.sim, name='M_Link_Retry') #LBT RETRY ONLY AT PRESENT
        self.M_Data_Tx_Sent = SimEvent(sim=self.sim, name='M_Data_Tx_Sent')
        self.M_Data_Tx_Fail = SimEvent(sim=self.sim, name='M_Data_Tx_Fail')
        self.M_Data_Rx_Rec = SimEvent(sim=self.sim, name='M_Data_Rx_Rec')
        self.M_Data_Rx_Fail = SimEvent(sim=self.sim, name='M_Data_Rx_Fail')
        self.M_ARQ_Rx_Success = SimEvent(sim=self.sim, name='M_ARQ_Rx_Success')
        self.M_Switch_to_Slave = SimEvent(sim=self.sim, name='M_Switch_to_Slave')
        self.S_Link_Started = SimEvent(sim=self.sim, name='S_Link_Started')
        self.S_Link_Failed = SimEvent(sim=self.sim, name='S_Link_Failed')
        self.S_Link_Success = SimEvent(sim=self.sim, name='S_Link_Success')
        self.S_Link_Ended = SimEvent(sim=self.sim, name='S_Link_Ended')
        self.S_Data_Rx_Rec = SimEvent(sim=self.sim, name='S_Data_Rx_Rec')
        self.S_Data_Rx_Fail = SimEvent(sim=self.sim, name='S_Data_Rx_Fail')
        self.S_Data_Tx_Sent = SimEvent(sim=self.sim, name='S_Data_Tx_Sent')
        self.S_Data_Tx_Fail = SimEvent(sim=self.sim, name='S_Data_Tx_Fail')
        self.S_ARQ_Tx_Success = SimEvent(sim=self.sim, name='S_ARQ_Tx_Success')
        #PHYSICAL
        self.time_out = SimEvent(sim=self.sim, name='time_out') #physical time out event - becomes abort_event to Physical Layer.
        self.stop_scanning = SimEvent(sim=self.sim, name='stop_scanning') #tells Physical layer to switch to Rx mode
        self.start_scanning = SimEvent(sim=self.sim, name='start_scanning') #tells Physical layer to switch to Tx mode
    def execute(self):
        while True:
            #These two lists being waited upon contain references to Physical and Network's outgoing events:
            yield waitevent, self, self.interface.phyEvents + self.interface.netEvents 
            #PHYSICAL
            if self.eventsFired[0].name=='LBT_Success':
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    self.interface.ProcDict['ALEMaster'].LBT_Success.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, 'Discontinuous State 1', self.sim.now()
            if self.eventsFired[0].name=='LBT_Fail':
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    self.interface.ProcDict['ALEMaster'].LBT_Fail.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, 'Discontinuous State 2', self.sim.now()
            if self.eventsFired[0].name=='Tx_Success':
                if self.sim.debug: print self.ID, 'Link msg_kernel Tx_Success fired', self.sim.now()       
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].Tx_Success.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].Tx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].Tx_Success.waits) > 0:
                        self.interface.ProcDict['ALESlave'].Tx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].LinkedMaster.Tx_Success.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].LinkedMaster.Tx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].LinkedSlave.Tx_Success.waits) > 0:
                        self.interface.ProcDict['ALESlave'].LinkedSlave.Tx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.TERM_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].Tx_Success.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].Tx_Success.signal(self.eventsFired[0].signalparam)
                else:
                    print self.ID, 'Discontinuous State 3. ',self.interface.ProcDict['kernel'].STATE, self.sim.now()
            if self.eventsFired[0].name=='Tx_Fail':
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].Tx_Fail.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].Tx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].Tx_Fail.waits) > 0:
                        self.interface.ProcDict['ALESlave'].Tx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].LinkedMaster.Tx_Fail.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].LinkedMaster.Tx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].LinkedSlave.Tx_Fail.waits) > 0:
                        self.interface.ProcDict['ALESlave'].LinkedSlave.Tx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.TERM_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].Tx_Fail.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].Tx_Fail.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discontinuous State 4', self.interface.ProcDict['kernel'].STATE, self.sim.now()
            if self.eventsFired[0].name=='Rx_Success': #Only used by Linked Slave, but will be fired for EVERY RX, so disable Discontinuous statement for now
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].Rx_Success.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].Rx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].Rx_Success.waits) > 0:
                        self.interface.ProcDict['ALESlave'].Rx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].LinkedMaster.Rx_Success.waits) > 0:
                        if self.sim.debug: print self.ID, 'Link msg_kernel: LM Mode Rx_Success fired', self.sim.now()
                        self.interface.ProcDict['ALEMaster'].LinkedMaster.Rx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE: #Consider using it for all Rx?
                    if len(self.interface.ProcDict['ALESlave'].LinkedSlave.Rx_Success.waits) > 0:
                        if self.sim.debug: print self.ID, 'Link msg_kernel: LS Mode Rx_Success fired', self.sim.now()
                        self.interface.ProcDict['ALESlave'].LinkedSlave.Rx_Success.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.TERM_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].Rx_Success.waits) > 0:
                        self.interface.ProcDict['ALESlave'].Rx_Success.signal(self.eventsFired[0].signalparam)
                else:
                    pass
                    #print self.ID, 'Discontinuous State LS1. ',self.interface.ProcDict['kernel'].STATE, self.sim.now()
            if self.eventsFired[0].name=='Rx_Fail': #Only used by Linked Slave, but will be fired for EVERY RX, so disable Discontinuous statement for now
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].Rx_Fail.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].Rx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].Rx_Fail.waits) > 0:
                        self.interface.ProcDict['ALESlave'].Rx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    if len(self.interface.ProcDict['ALEMaster'].LinkedMaster.Rx_Fail.waits) > 0:
                        self.interface.ProcDict['ALEMaster'].LinkedMaster.Rx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE: #Consider using it for all Rx?
                    if len(self.interface.ProcDict['ALESlave'].LinkedSlave.Rx_Fail.waits) > 0:
                        self.interface.ProcDict['ALESlave'].LinkedSlave.Rx_Fail.signal(self.eventsFired[0].signalparam)
                elif self.interface.ProcDict['kernel'].STATE == nState.TERM_SLAVE:
                    if len(self.interface.ProcDict['ALESlave'].Rx_Fail.waits) > 0:
                        self.interface.ProcDict['ALESlave'].Rx_Fail.signal(self.eventsFired[0].signalparam)
                else:
                    pass
                    #print 'Discontinuous State LS2',self.interface.ProcDict['kernel'].STATE, self.sim.now(), self.sim.now()
            if self.eventsFired[0].name=='scanning_call_ended':
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    self.interface.ProcDict['ALESlave'].scanning_call_ended.signal()
                else:
                    print self.ID, 'Discontinuous State 5', self.interface.ProcDict['kernel'].STATE, self.sim.now()
            if self.eventsFired[0].name=='scanning_call_interrupt':
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    self.interface.ProcDict['ALESlave'].scanning_call_interrupt.signal()
                else:
                    print 'Discontinuous State 5a', self.sim.now()
            #NETWORK
            if self.eventsFired[0].name=='Start_Link':
                if self.interface.ProcDict['kernel'].STATE == nState.SCANNING:
                    yield put, self, self.interface.ProcDict['ALEMaster'].inQ, self.eventsFired[0].signalparam
                else:
                    print 'Discontinuous State 5', self.sim.now()
            if self.eventsFired[0].name=='LM_Terminate':
                if self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    self.interface.ProcDict['ALEMaster'].LinkedMaster.LM_Terminate.signal()
                else:
                    print 'Discontinuous State 55', self.sim.now()
            if self.eventsFired[0].name=='LM_Send_EOF': #This is not actually used!!
                if self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    self.interface.ProcDict['ALEMaster'].LinkedMaster.LM_Send_EOF.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discontinuous State 58', self.sim.now()
            if self.eventsFired[0].name=='LS_Terminate':
                if self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE:
                    if self.sim.debug: print self.ID, 'Link: msg_kernel: LS_Terminate', self.sim.now()
                    self.interface.ProcDict['ALESlave'].LinkedSlave.LS_Terminate.signal()
                else:
                    print 'Discontinuous State 56', self.sim.now()
            if self.eventsFired[0].name=='LS_Send_ARQ':
                if self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE:
                    self.interface.ProcDict['ALESlave'].LinkedSlave.LS_Send_ARQ.signal(self.eventsFired[0].signalparam)
                else:
                    print 'Discontinuous State 58', self.sim.now()
            if self.eventsFired[0].name=='Abort_Link': #Will abort all activity - depending on the current state of the Layer.
                if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    if self.interface.ProcDict['ALEMaster'].abort_signal.waits > 0:
                        self.interface.ProcDict['ALEMaster'].abort_signal.signal()
                    else:
                        print self.ID, 'Link msg_kernel setting ALE Master .abort to True', self.sim.now()
                        self.interface.ProcDict['ALEMaster'].abort = True
                elif self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    if self.interface.ProcDict['ALESlave'].abort_signal.waits > 0:
                        self.interface.ProcDict['ALESlave'].abort_signal.signal()
                    else:
                        print self.ID, 'Link msg_kernel setting ALE Slave .abort to True', self.sim.now()
                        self.interface.ProcDict['ALESlave'].abort = True
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    if self.interface.ProcDict['ALEMaster'].LinkedMaster.abort_signal.waits > 0:
                        self.interface.ProcDict['ALEMaster'].LinkedMaster.abort_signal.signal()
                    else:
                        self.interface.ProcDict['ALEMaster'].LinkedMaster.abort = True
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE:
                    if self.interface.ProcDict['ALESlave'].LinkedSlave.abort_signal.waits > 0:
                        self.interface.ProcDict['ALESlave'].LinkedSlave.abort_signal.signal()
                    else:
                        self.interface.ProcDict['kernel'].LinkedSlave.abort = True
                else:
                    print 'Discontinuous State 6', self.sim.now()
        

class kernel(Process):
    '''Process deals with all incoming and outgoing Packets - that will be sent/were received to/from another Node
        Similarly to msg_kernel, it will forward the packets to the appropriate Process within this Layer,
        depending on current Layer state'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        self.pendingQ = []
        self.no_event = SimEvent(sim=sim, name='no event')
        self.LinkedMaster = None
        self.LinkedSlave = None
        
        self.STATE = nState.SCANNING
    def execute(self):
        #self.MonitorVar = MonitorVar(self.sim, self.ID, self.interface)
        #self.sim.activate(self.MonitorVar, self.MonitorVar.execute())
        while True:
            yield get, self, self.inQ, 1
            rec_packet = self.got[0]
            last_location = rec_packet.internal_last_location
            rec_packet.internal_last_location = Layer.LINK
            if last_location == Layer.PHYSICAL and rec_packet.physical.destination != self.ID:
                #Catch all packets received from environment that are not addressed to me.
                if self.sim.debug: print self.ID, 'Use for LQA data:', self.sim.now()
                #pass
            else:
                if self.interface.ProcDict['kernel'].STATE == nState.SCANNING:
                    if last_location == Layer.PHYSICAL:
                        if self.sim.debug: print self.ID, 'LINK pass to Scanning, STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        yield put, self, self.interface.ProcDict['Scanning'].inQ, [rec_packet]
                    elif last_location == Layer.NETWORK:
                        if self.sim.debug: print self.ID, 'LINK pass to ALE Master, STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        rec_packet.ID.Link_ID = self.createID()
                        yield put, self, self.interface.ProcDict['ALEMaster'].inQ, [rec_packet]
                elif self.interface.ProcDict['kernel'].STATE == nState.ALE_SLAVE:
                    if last_location == Layer.PHYSICAL:
                        if self.sim.debug: print self.ID, 'LINK pass to ALE Slave, STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        yield put, self, self.interface.ProcDict['ALESlave'].inQ, [rec_packet]
                    elif last_location == Layer.NETWORK:
                        print self.ID, 'Discontinuous A', rec_packet.ID.all_IDs(), self.sim.now()
                elif self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
                    if last_location == Layer.PHYSICAL:
                        #If ALE Master is still in LBT stage, it can be overruled if a call is received on that channel.
                        if rec_packet.physical.destination != self.ID:
                            if self.sim.debug: print self.ID, 'Link: packet received, wrong destination (physical still in Scanning mode), passing to Scanning', self.sim.now()
                            if self.sim.debug: print 'notes:', rec_packet.notes
                            yield put, self, self.interface.ProcDict['Scanning'].inQ, [rec_packet]
                        else:
                            if rec_packet.link.pType == 0:
                                if self.sim.debug: print self.ID, 'Link: packet received, this destination (physical was still in Scanning mode, now Rx), TERMINATE ALE MASTER and run ALE Slave', self.sim.now()
                                yield put, self, self.interface.ProcDict['ALESlave'].inQ, [rec_packet]
                            else:
                                if self.interface.ProcDict['ALEMaster'].Rx:
                                    #How to make sure packets don't get in here at the wrong time, for instance during backoff etc.
                                    if self.sim.debug: print self.ID, 'Link: pass to ALE Master, STATE:', self.interface.ProcDict['kernel'].STATE, 'pType:', rec_packet.link.pType, self.sim.now()
                                    yield put, self, self.interface.ProcDict['ALEMaster'].inQ, [rec_packet]
                                else:
                                    print self.ID, 'Link: KERNEL: Packed received at incorrect time (probably response), details:', rec_packet.ID.all_IDs(), 'type:', rec_packet.link.pType, self.sim.now()
                    elif last_location == Layer.NETWORK:
                        print self.ID, 'Discontinuous B'
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE:
                    if last_location == Layer.PHYSICAL:
                        if self.sim.debug: print self.ID, 'LINK pass to Linked Slave, STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        yield put, self, self.interface.ProcDict['ALESlave'].LinkedSlave.inQ, [rec_packet]
                    elif last_location == Layer.NETWORK:
                        print 'Discontinuous C'
                elif self.interface.ProcDict['kernel'].STATE == nState.LINKED_MASTER:
                    if last_location == Layer.PHYSICAL:
                        if self.checkForResponse(rec_packet):
                            if self.sim.debug: print self.ID, 'LINK pass to Linked Master from PHY:',rec_packet.ID.all_IDs(),'STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                            yield put, self, self.interface.ProcDict['ALEMaster'].LinkedMaster.phyQ, [rec_packet]
                        else:
                            print self.ID, 'LINK [kernel] Incorrect packet type received attempting to pass to LM, denied. Type:', rec_packet.link.pType, 'details:', rec_packet.ID.all_IDs(), self.sim.now()
                    elif last_location == Layer.NETWORK:
                        if self.sim.debug: print self.ID, 'LINK pass to Linked Master, STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        yield put, self, self.interface.ProcDict['ALEMaster'].LinkedMaster.netQ, [rec_packet]
                elif self.interface.ProcDict['kernel'].STATE == nState.TERM_SLAVE:
                    if last_location == Layer.PHYSICAL:
                        if self.sim.debug: print self.ID, 'LINK packet received from physical, pass to TERM Slave, STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        yield put, self, self.interface.ProcDict['ALESlave'].inQ, [rec_packet]
                    elif last_location == Layer.NETWORK:
                        print self.ID, 'Discontinuous 8372'
                elif self.interface.ProcDict['kernel'].STATE == nState.TERM_MASTER:
                    if last_location == Layer.PHYSICAL:
                        if self.sim.debug: print self.ID, 'LINK packet received from physical, pass to TERM Master, STATE:', self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        yield put, self, self.interface.ProcDict['ALEMaster'].inQ, [rec_packet]
                    elif last_location == Layer.NETWORK:
                        print self.ID, 'Discontinuous 8373'
                        
    def createID(self): #unique ID for Link Layer appended to packet.
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    def checkForResponse(self, datagram):
        #This is a sanity check, to prevent a non-response packet actually making it to LM's Phy queue (which causes problems as there is no
        #catch for this, as the incorrect packet just waits in the phyQ until LM next 'gets' from it.)
        return datagram.link.pType == 5

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
            yield hold, self, 450
            while True:
                if self.sim.now() > 450 and self.sim.now() < 490:
                    self.sim.debug = True
                    if self.ID == 7:
                        pass
                        #print '---', self.interface.ProcDict['ALESlave'].abort, self.interface.ProcDict['kernel'].STATE, self.sim.now()
                        #print self.sim.allEventNotices() 
                    yield hold, self, 0.1
                else:
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
    
class nState():
    SCANNING = 0
    ALE_SLAVE = 1 #creating link
    ALE_MASTER = 2
    LINKED_SLAVE = 3
    LINKED_MASTER = 4
    TERM_SLAVE = 5 #closing link
    TERM_MASTER = 6 #closing link
    
class State():
    def __init__(self):
        self.STATE = nState.SCANNING
    
class Scanning(Process):
    '''Counterpart to Physical Scanning() Process, Physical does the channel changing and detecting,
        Link decides what to do with any packets that are picked up'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.currentFreq = -1
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', name='Scanning inQ', sim=sim)
    def execute(self):
        while True:
            yield get, self, self.inQ, 1
            rec_packet = self.got[0]
            if self.sim.debug: print self.ID, 'LINK Scanning: packet received, details:', rec_packet.ID.all_IDs(), self.sim.now()
            if rec_packet.physical.destination == self.ID:
                if rec_packet.link.pType == 0:
                    if self.sim.debug: print self.ID, 'LINK Scanning: packet for me, success, start ALE Slave', self.sim.now()
                    yield put, self, self.interface.ProcDict['ALESlave'].inQ, [rec_packet]
                else:
                    print self.ID, 'Link (Scanning): Anomalous packet type:', rec_packet.link.pType, self.sim.now()
                    self.interface.ProcDict['msg_kernel'].time_out.signal('anomalous packet type')
            else:
                if self.sim.debug: print self.ID, 'save info for LQA and discard packet', self.sim.now()

class ALESlave(Process):
    '''This Process is activated when a call is received, and proceeds to respond with a RESPONSE packet, and
        then wait for an ACK packet. If successful, it will pass responsibility to LinkedSlave() Process, and
        change the State to LINKED_SLAVE. If unsuccessful it will abort and inform above and below Layers as
        necessary'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.inQ = Store(capacity='unbounded', name='ALES inQueue', sim=sim)
        self.interface = iLink

        self.Tx_Success = SimEvent(sim=sim, name='ALES_Tx_Success')
        self.Tx_Fail = SimEvent(sim=sim, name='ALES_Tx_Fail')
        self.Rx_Success = SimEvent(sim=sim, name='ALES_Rx_Success')
        self.Rx_Fail = SimEvent(sim=sim, name='ALES_Rx_Fail')

        self.datagram = None
        self.call_details = None
        
        self.scanning_call_ended = SimEvent(sim=sim, name='ALES_SCE')
        self.scanning_call_interrupt = SimEvent(sim=sim, name='ALES_SCI')
        self.abort_event = SimEvent(sim=sim, name='ALES_Abort')
        self.abort = False
    
        self.LinkedSlave = None
    def execute(self):
        while True:
            if self.sim.debug:print self.ID, 'ALE Slave: About to Wait for Packet..', self.sim.now()
            for x in self.waitForPacket():
                yield x
            for x in self.waitforSCRxSuccess():
                yield x
                
            self.interface.ProcDict['msg_kernel'].start_scanning.signal()

    def waitForPacket(self):
        if self.sim.debug: print self.ID, 'ALE Slave: inQ:', self.inQ.theBuffer
        yield get, self, self.inQ, 1
        if self.sim.debug: print self.ID, 'ALE Slave: received packet', self.sim.now()
        self.datagram = copy.deepcopy(self.got[0])
        self.call_details = copy.deepcopy(self.datagram.ID)
        self.call_details.Destination = self.datagram.link.origin #This is a bit of a hack, sort out with Transport
        
        self.checkALEM()
        self.interface.ProcDict['kernel'].STATE = nState.ALE_SLAVE
        self.interface.ProcDict['msg_kernel'].stop_scanning.signal()
        
    def checkALEM(self):
        if self.interface.ProcDict['kernel'].STATE == nState.ALE_MASTER:
            if self.sim.debug: print self.ID, 'ALE Slave: ALE Master Mode detected, cancelling.', self.sim.now()
            switch_details = copy.deepcopy(self.call_details)
            switch_details.New_Destination = switch_details.Destination
            switch_details.Destination =  self.interface.ProcDict['ALEMaster'].call_signal.ID.Destination
            self.interface.ProcDict['msg_kernel'].M_Switch_to_Slave.signal(switch_details)
            
            self.interface.ProcDict['ALEMaster'].abort_event.signal(2)            
            self.call_details.Destination = switch_details.New_Destination
        else:
            self.interface.ProcDict['msg_kernel'].S_Link_Started.signal(self.call_details)
    def waitforSCRxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Slave: waiting for Scanning Call to End/Fail', self.sim.now()
        yield waitevent, self, [self.Rx_Success, self.Rx_Fail, self.abort_event]
        if self.sim.debug: print self.ID, 'ALE Slave: SC Ended somehow.. (Success or Fail?)', self.sim.now()
        if self.eventsFired[0] == self.Rx_Success:
            if self.sim.debug: print self.ID, 'ALE Slave: SC Rx Success', self.sim.now()
            for x in self.sendResponse():
                yield x
        elif self.eventsFired[0] == self.Rx_Fail: 
            if self.sim.debug: print self.ID, 'ALE Slave: SC Rx Fail', self.sim.now()
            self.interface.ProcDict['msg_kernel'].S_Link_Failed.signal(self.call_details)
            self.abortEvent('S_Link_Failed - waitforSCRxSuccess Rx_Fail event')
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def sendResponse(self):
        if self.sim.debug: print self.ID, 'ALE Slave: creating Response..', self.sim.now()
        send_packet = self.makeConf(self.datagram) #Make response packet (using call packet)
        if self.sim.debug: print self.ID, 'ALE Slave: Sending response to PHY..', send_packet.ID.all_IDs(), self.sim.now()
        self.interface.physicalQ.signal(send_packet) #Send to Physical Layer
        for x in self.waitforTxSuccess():
            yield x
    def waitforTxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Slave: Waiting for Response Tx Success/Fail', self.sim.now()
        yield waitevent, self, [self.Tx_Success, self.Tx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Tx_Success:
            if self.sim.debug:print self.ID, 'ALE Slave: Tx Success', self.sim.now()
            for x in self.waitforAck():
                yield x
        elif self.eventsFired[0] == self.Tx_Fail: 
            if self.sim.debug:print self.ID, 'ALE Slave: Tx Fail', self.sim.now()
            self.interface.ProcDict['msg_kernel'].S_Link_Failed.signal(self.call_details)
            self.abortEvent('S_Link_Failed - waitforTxSuccess Tx_Fail event')
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def waitforAck(self):
        if self.sim.debug: print self.ID, 'ALE Slave: Waiting for ack/timeout', self.sim.now()
        TO = TimeOut(self.sim, self.sim.G.link_wait_for_reply)
        self.sim.activate(TO,TO.execute())
        yield (get, self, self.inQ, 1),(waitevent, self, (TO.timeoutEvent, self.abort_event))
        if self.acquired(self.inQ):
            for x in self.eatEvent([self.abort_event],[TO]):
                yield x
            #TO.active = False
            #self.abort_event = SimEvent(sim= self.sim)
            if self.sim.debug: print self.ID, 'ALE Slave: Ack acquired', self.sim.now()
            for x in self.waitforRxSuccess():
                yield x
        if self.eventsFired[0]==TO.timeoutEvent:
                if self.sim.debug: print self.ID, 'ALE Slave: Timeout: S Link Failed', self.sim.now()
                self.interface.ProcDict['msg_kernel'].S_Link_Failed.signal(self.call_details)
                self.abortEvent('S_Link_Failed - waitforAck timeout')
        if self.eventsFired[0]==self.abort_event:
            self.abortEvent()
    def waitforRxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Slave: Waiting for Ack to be received fully', self.sim.now()
        yield waitevent, self, [self.Rx_Success, self.Rx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Rx_Success:
            if self.sim.debug: print self.ID, 'ALE Slave: Ack Rx Success', self.sim.now()
            for x in self.activateLinkedSlave():
                yield x
        elif self.eventsFired[0] == self.Rx_Fail: 
            if self.sim.debug: print self.ID, 'ALE Slave: Ack Rx Fail', self.sim.now()
            self.interface.ProcDict['msg_kernel'].S_Link_Failed.signal(self.call_details)
            self.abortEvent('S_Link_Failed - waitforRxSuccess Rx_Fail event')
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def activateLinkedSlave(self):
        if self.sim.debug: print self.ID, 'ALE Slave: Activate Linked Slave..', self.sim.now()
        self.interface.ProcDict['kernel'].STATE = nState.LINKED_SLAVE
        self.LinkedSlave = LinkedSlave(self.ID, self.sim, self.interface)
        self.sim.activate(self.LinkedSlave, self.LinkedSlave.execute())
        self.LinkedSlave.linkedFreq = self.datagram.physical.frequency
        self.LinkedSlave.linkedDest = self.datagram.physical.origin
        
        self.interface.ProcDict['msg_kernel'].S_Link_Success.signal(self.call_details)
        self.sim.Vis.S_LinkUp2[self.ID].signal(self.call_details)
        if self.sim.debug: print self.ID, 'ALE Slave: Wait for Linked Slave terminate..', self.sim.now()
        for x in self.waitforLinkedTerminate():
            yield x
    def waitforLinkedTerminate(self):
        yield waitevent, self, [self.LinkedSlave.terminate, self.abort_event]
        if self.eventsFired[0] == self.LinkedSlave.terminate:
            if self.sim.debug: print self.ID, 'ALE Slave: Linked Slave Terminate fired', self.sim.now()
            self.interface.ProcDict['kernel'].STATE = nState.TERM_SLAVE
            for x in self.waitforEOM():
                yield x
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def waitforEOM(self):
        if self.sim.debug: print self.ID, 'ALE Slave: Waiting for EOM packet or timeout..', self.sim.now()
        TO = TimeOut(self.sim, self.sim.G.link_wait_for_reply)
        self.sim.activate(TO,TO.execute())
        yield (get, self, self.inQ, 1),(waitevent, self, (TO.timeoutEvent, self.abort_event))
        if self.acquired(self.inQ):
            for x in self.eatEvent([self.abort_event],[TO]):
                yield x
            #TO.active = False
            #self.abort_event = SimEvent(sim=self.sim)
            if self.sim.debug: print self.ID, 'ALE Slave: EOM received', self.sim.now()
            for x in self.waitforEOMRxSuccess():
                yield x
        if self.eventsFired[0]==TO.timeoutEvent:
            if self.sim.debug: print self.ID, 'ALE Slave: EOM timeout', self.sim.now()
            self.linkFinished()
        if self.eventsFired[0]==self.abort_event:
            self.abortEvent()
    def waitforEOMRxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Slave: Waiting for EOM Rx Success / Fail', self.sim.now()
        yield waitevent, self, [self.Rx_Success, self.Rx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Rx_Success:
            if self.sim.debug: print self.ID, 'ALE Slave: EOM Rx Success', self.sim.now()
            self.linkFinished()
        elif self.eventsFired[0] == self.Rx_Fail:
            if self.sim.debug: print self.ID, 'ALE Slave: EOM Rx Fail', self.sim.now()
            self.linkFinished()
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def linkFinished(self):
        if self.sim.debug: print self.ID, 'Link ALES: Termination packet received/not received', self.sim.now()
        self.interface.ProcDict['kernel'].STATE = nState.SCANNING
        #self.interface.ProcDict['msg_kernel'].time_out.signal()
        self.interface.ProcDict['msg_kernel'].S_Link_Ended.signal(self.call_details)

    def makeConf(self, rec_packet):
        send_packet = packet.Packet()
        send_packet.ID = rec_packet.ID
        send_packet.ID.Destination = rec_packet.link.origin
        send_packet.ID.Origin = self.ID
        send_packet.physical.time = 3*self.sim.G.Trw 
        send_packet.link.destination = send_packet.ID.Destination
        send_packet.link.origin = self.ID
        send_packet.link.frequency = rec_packet.link.frequency
        send_packet.physical.frequency = send_packet.link.frequency[0]
        send_packet.link.pType = 1
        send_packet.internal_last_location = 2 #2nd layer
        
        send_packet.meta.waveform = self.sim.G.linking_waveform
        return send_packet
    def abortEvent(self, reason=None):
        if self.sim.debug: print self.ID, 'ALEM: abort_event fired, reason:', reason, self.sim.now()
        self.interface.ProcDict['kernel'].STATE = nState.SCANNING
    def eatEvent(self, events, TOprocs=[]):
        for ev in events:
            ev.signal()
            ev.signal()
            yield waitevent, self, ev
            if self.sim.debug: print ev.name, 'eaten', self.sim.now()
        for tp in TOprocs:
            tp.active = False


class ALEMaster(Process):
    '''Process is activated when a call is received from the above Layer - it will make the call, and if successful,
        wait for a RESPONSE, then send an ACK packet. If this is all successful it will transfer responsibility to
        LinkedMaster() Process and change State to LINKED_MASTER. If unsuccessful it will break out of the Process,
        return to SCANNING mode, inform Transport Layer of this and abort any current activities Physical Layer is doing'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self,name=self.__class__.__name__,sim=sim)
        self.ID = ID
        self.inQ = Store(capacity='unbounded', name='ALEM inQueue', sim=sim)
        self.callQ = Store(capacity='unbounded', name='ALEM callQ', sim=sim)
        self.interface = iLink
        self.LBT_Success = SimEvent(sim=sim, name='ALEM_LBT_Success')
        self.LBT_Fail = SimEvent(sim=sim, name='ALEM_LBT_Fail')
        self.Rx_Success = SimEvent(sim=sim, name='ALEM_Rx_Success')
        self.Rx_Fail = SimEvent(sim=sim, name='ALEM_Rx_Fail')
        self.Tx_Success = SimEvent(sim=sim, name='ALEM_Tx_Success')
        self.Tx_Fail = SimEvent(sim=sim, name='ALEM_Tx_Fail')

        self.abort_event = SimEvent(sim=sim, name='ALEM_Abort')
        self.abort = False
        self.switch_slave = False
        self.linking = True
        
        self.datagram = None
        self.call_signal = None
        self.call_details = None
        self.response_datagram = None
        self.Rx = False
        
        self.LinkedMaster = None

        self.LQA = self.sim.Net.env_container.SNR_matrix
    def execute(self):
        while True:
            for x in self.waitForPacket():
                yield x
            self.addStartTime(self.call_signal)
            while self.linking: 
                if self.sim.debug: print self.ID, 'ALE Master: Sending Call to Phy, chan:', self.call_signal.physical.frequency, 'inQ:', len(self.inQ.theBuffer), self.sim.now()
                self.interface.physicalQ.signal(self.call_signal)
                for x in self.waitforLBT():
                    yield x
                    
            if self.switch_slave:
                self.switch_slave = False
            else:
                self.interface.ProcDict['msg_kernel'].start_scanning.signal() #Tell Phy Scanning to begin

    def waitForPacket(self):
        yield get, self, self.inQ, 1
        if self.sim.debug: print self.ID, 'ALE Master: Packet received from Network', self.sim.now()
        self.linking = True
        self.datagram = copy.deepcopy(self.got[0])
        self.call_details = copy.deepcopy(self.datagram.ID)
        self.call_signal = self.makeCall(self.got[0])
        
        self.interface.ProcDict['kernel'].STATE = nState.ALE_MASTER        
        self.interface.ProcDict['msg_kernel'].stop_scanning.signal() #to PHY
        
        self.interface.ProcDict['msg_kernel'].M_Link_Started.signal(self.call_details)
        #self.watchedFreq = self.call_signal.physical.frequency

    def waitforLBT(self):
        if self.sim.debug: print self.ID, 'ALE Master: Waiting for LBT Success/Fail', self.sim.now()
        yield waitevent, self, [self.LBT_Success, self.LBT_Fail, self.abort_event]
        if self.eventsFired[0] == self.LBT_Success:
            if self.sim.debug: print self.ID, 'ALE Master: LBT Success', self.sim.now()
            for x in self.waitforSCTxSuccess():
                yield x
        elif self.eventsFired[0] == self.LBT_Fail:
            if self.sim.debug: print self.ID, 'ALE Master: LBT Fail', self.sim.now()
            for x in self.resendCall():
                    yield x
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def waitforSCTxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Master: Waiitng for SC Tx Success/Fail', self.sim.now()
        yield waitevent, self, [self.Tx_Success, self.Tx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Tx_Success:
            if self.sim.debug: print self.ID, 'ALE Master: SC Tx Success', self.sim.now()
            for x in self.waitforResponse():
                yield x
        elif self.eventsFired[0] == self.Tx_Fail:
            print self.ID, 'ALE Master: SC Tx Fail', self.sim.now()
            for x in self.resendCall():
                yield x
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def waitforResponse(self):
        self.Rx = True #let kernel know to forward packets
        if self.sim.debug: print self.ID, 'ALE Master: Waiting for Response packet..', self.sim.now()
        TO = TimeOut(self.sim, self.sim.G.link_wait_for_reply)
        self.sim.activate(TO,TO.execute())
        yield (get, self, self.inQ, 1),(waitevent, self, (TO.timeoutEvent, self.abort_event))
        if self.acquired(self.inQ):
            self.Rx = False
            
            if self.sim.debug: print self.ID, 'ALEM: Response packet acquired', self.sim.now()
            for x in self.eatEvent([self.abort_event],[TO]):
                yield x
            self.response_datagram = copy.deepcopy(self.got[0])
            for x in self.waitforRxSuccess():
                yield x
        if self.eventsFired[0]==TO.timeoutEvent:
            self.Rx = False
            
            if self.sim.debug: print self.ID, 'ALE Master: Response timed out', self.sim.now()
            for x in self.resendCall():
                yield x
        if self.eventsFired[0]==self.abort_event:
            self.Rx = False
            
            self.abortEvent()
    def waitforRxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Master: Waiting for response Rx success/fail', self.sim.now()
        yield waitevent, self, [self.Rx_Success, self.Rx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Rx_Success:
            if self.sim.debug: print self.ID, 'ALE Master: Response Rx Success', self.sim.now()
            for x in self.sendAck():
                yield x
        elif self.eventsFired[0] == self.Rx_Fail:
            if self.sim.debug: print self.ID, 'ALE Master: Response Rx Fail', self.sim.now()
            for x in self.resendCall():
                yield x
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def sendAck(self):
        if self.sim.debug: print self.ID, 'ALE Master: creating Ack..', self.sim.now()
        send_packet = self.makeAck(self.response_datagram) #Make response packet (using call packet)
        if self.sim.debug: print self.ID, 'ALE Master: Sending ack to PHY..', self.sim.now()
        self.interface.physicalQ.signal(send_packet) #Send to Physical Layer
        for x in self.waitforTxSuccess():
            yield x
    def waitforTxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Master: Waiting for Ack Tx Success', self.sim.now()
        yield waitevent, self, [self.Tx_Success, self.Tx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Tx_Success:
            if self.sim.debug: print self.ID, 'ALE Master: Ack Tx Success', self.sim.now()
            for x in self.activateLinkedMaster():
                yield x
        elif self.eventsFired[0] == self.Tx_Fail:
            if self.sim.debug: print self.ID, 'ALE Master: Ack Tx Fail', self.sim.now()
            for x in self.resendCall():
                yield x
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()

    def resendCall(self):
        if not self.checkForLinkTimeout(self.call_signal):
            self.call_signal = self.changeFrequencies(self.call_signal)
            self.call_signal = self.calculateBackOff(self.call_signal)
            for x in self.waitBackOff(): #If a backoff needs to be done
                yield x
    
    def addStartTime(self, pkt):
        if pkt.meta.start_time == None:
            pkt.meta.start_time = self.sim.now()
    
    def checkForLinkTimeout(self, pkt):
        total_time = self.sim.now() - pkt.meta.start_time
        if self.sim.debug: print self.ID, 'Link: checking for timeout, total_time =', total_time, self.sim.now()
        if total_time > self.sim.G.link_timeout:
            self.interface.ProcDict['msg_kernel'].M_Link_Failed.signal(self.call_details)
            self.linking = False
            self.interface.ProcDict['kernel'].STATE = nState.SCANNING
            return True
        else:
            return False

    def activateLinkedMaster(self):
        if self.sim.debug: print self.ID, 'ALE Master: Linked Master Activated', self.sim.now()
        self.linking = False
        
        self.interface.ProcDict['kernel'].STATE = nState.LINKED_MASTER
        self.LinkedMaster = LinkedMaster(self.ID, self.sim, self.interface)
        self.sim.activate(self.LinkedMaster, self.LinkedMaster.execute())
        self.LinkedMaster.linkedFreq = self.call_signal.physical.frequency
        self.LinkedMaster.linkedDest = self.call_signal.physical.destination
        self.LinkedMaster.link_ID = self.call_details.Link_ID
        
        self.interface.ProcDict['msg_kernel'].M_Link_Success.signal(self.call_details)
        for x in self.waitforLinkedTerminate():
            yield x
    def waitforLinkedTerminate(self):
        if self.sim.debug: print self.ID, 'ALE Master: Waiting for Linked Master to Terminate', self.sim.now()
        yield waitevent, self, [self.LinkedMaster.terminate, self.abort_event]
        if self.eventsFired[0] == self.LinkedMaster.terminate:
            if self.sim.debug: print self.ID, 'ALE Master: Linked Master Terminated event fired', self.sim.now()
            self.interface.ProcDict['kernel'].STATE = nState.TERM_MASTER
            for x in self.sendEOM():
                yield x
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def sendEOM(self):
        if self.sim.debug: print self.ID, 'ALE Master: Sending EOM', self.sim.now()
        term_packet = self.makeEOM(self.call_signal)
        self.interface.physicalQ.signal(term_packet)
        if self.sim.debug: print self.ID, 'Passed Term Packet to Phy', self.sim.now()
        for x in self.waitforEOMTxSuccess():
            yield x
    def waitforEOMTxSuccess(self):
        if self.sim.debug: print self.ID, 'ALE Master: Wait for EOM Tx Success/Fail', self.sim.now()
        yield waitevent, self, [self.Tx_Success, self.Tx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Tx_Success:
            if self.sim.debug: print self.ID, 'ALE Master: EOM Tx Success', self.sim.now()
            self.linkFinished()
        elif self.eventsFired[0] == self.Tx_Fail:
            if self.sim.debug: print self.ID, 'ALE Master: EOM Tx Fail', self.sim.now()
            self.linkFinished()
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def linkFinished(self):
        if self.sim.debug: print self.ID, 'Link ALEM: Termination packet sent', self.sim.now()
        self.interface.ProcDict['kernel'].STATE = nState.SCANNING
        #self.interface.ProcDict['msg_kernel'].time_out.signal('ALEM ABORT EVENT from above [ALE Terminate]')
        self.interface.ProcDict['msg_kernel'].M_Link_Ended.signal(self.call_details)
        self.sim.Vis.M_LinkEnd2[self.ID].signal(self.call_details)

    
    def makeCall(self, in_packet):
        if in_packet.physical.LBT_Free == None:
            in_packet.physical.time = self.sim.G.num_freq*self.sim.G.dwell_time #compare this with ALE2.xls

            in_packet.link.destination = in_packet.ID.Destination
            in_packet.link.origin = self.ID
            in_packet.link.pType = 0
            
            in_packet.link.frequency = self.getFrequencies(in_packet.link.destination)
            in_packet.ID.Frequency = in_packet.physical.frequency = in_packet.link.frequency[0]
            
            in_packet.meta.waveform = self.sim.G.linking_waveform
        return in_packet

    def makeEOM(self, in_packet):
        termPacket = copy.deepcopy(in_packet)
        termPacket.internal_last_location = Layer.LINK
        termPacket.physical.time = self.sim.G.Trw
        termPacket.link.pType = 6
        
        termPacket.meta.waveform = self.sim.G.linking_waveform
        return termPacket
    
    def makeAck(self, rec_packet):
        send_packet = packet.Packet()
        send_packet.ID = rec_packet.ID
        send_packet.ID.Destination = rec_packet.link.origin
        send_packet.ID.Origin = self.ID
        send_packet.physical.time = 3*self.sim.G.Trw
        send_packet.link.destination = send_packet.ID.Destination
        send_packet.link.origin = self.ID
        send_packet.link.frequency = rec_packet.link.frequency
        send_packet.physical.frequency = send_packet.link.frequency[0]
        send_packet.internal_last_location = Layer.LINK
        send_packet.link.pType = 2 
        
        send_packet.meta.waveform = self.sim.G.linking_waveform
        return send_packet
    
    def getFrequencies(self, destination): #LQA allocation
        #'interrogate LQA'
        freqList = self.LQA[self.ID, destination]
        #print self.ID, 'freqList', freqList
        sortedValList = sorted(freqList,reverse=True)
        sortedList = []
        for val in sortedValList:
            sortedList.append(freqList.index(val))
        #print self.ID, 'sortedList', sortedList
        return sortedList        
    
    def changeFrequencies(self, in_packet): #in the event of an LBT Fail, this will pop the busy frequency off, and return.
        out_packet = copy.deepcopy(in_packet)
        out_packet.internal_last_location = Layer.LINK
        if len(out_packet.link.frequency) > 1:
            del out_packet.link.frequency[0]
            out_packet.ID.Frequency = out_packet.physical.frequency = out_packet.link.frequency[0]
            out_packet.physical.LBT_Free = False
            if self.sim.debug: print self.ID, len(out_packet.link.frequency), 'frequencies left', self.sim.now()
            return out_packet
        else:
            if self.sim.debug: print 'All channels exhausted, start again'
            out_packet.physical.LBT_Free = None
            out_packet = self.makeCall(out_packet)
            return out_packet

    def calculateBackOff(self, in_packet): #Calculate backoff, at present - between 1 and 4 dwell times
        out_packet = copy.deepcopy(in_packet)
        out_packet.internal_last_location = Layer.LINK
        if out_packet.link.num_backoffs < self.sim.G.max_backoff:
            out_packet.link.num_backoffs += 1
            out_packet.link.backoff = random.randint(1, self.sim.G.num_freq) * self.sim.G.Trw
            if self.sim.debug: print self.ID, 'ALEM: Backoff appended to packet, time=', out_packet.link.backoff, self.sim.now()
            return out_packet
        else:
            if self.sim.debug: print 'Backoff limit exceeded'
            return out_packet
    def waitBackOff(self):
        if self.call_signal.link.num_backoffs > 0:
            if self.sim.debug: print self.ID, 'ALE Master: Backoff commencing:', self.sim.now()
            TO = TimeOut(self.sim, self.call_signal.link.backoff)
            self.sim.activate(TO,TO.execute())
            yield waitevent, self, [TO.timeoutEvent, self.abort_event]
            if self.eventsFired[0] == TO.timeoutEvent:
                if self.sim.debug: print 'ALEM: Backoff Completed', self.sim.now()
            else:
                self.abortEvent()

    def abortEvent(self, reason=None):
        if self.sim.debug: print self.ID, 'ALEM: abort_event fired, reason:', reason, self.sim.now()
        self.linking = False
        if self.abort_event.signalparam == 2:
            if self.sim.debug: print self.ID, 'abort_event reason: ALEM/S Switch', reason, self.sim.now()
            self.switch_slave = True
        else:
            self.interface.ProcDict['kernel'].STATE = nState.SCANNING

    def eatEvent(self, events, TOprocs=[]):
        now = self.sim.now()
        for ev in events:
            if self.sim.debug: print 'eatEvent: signalling', ev.name, self.sim.now()
            ev.signal()
            ev.signal()
            if self.sim.debug: print 'eatEvent: waiting for', ev.name, self.sim.now()
            yield waitevent, self, ev
            if self.sim.debug: print 'eatEvent:', ev.name, 'eaten, orig time:', now, self.sim.now()
        for tp in TOprocs:
            if self.sim.debug: print 'eatEvent: deactivating', tp.name, self.sim.now()
            tp.active = False
        if now != self.sim.now():
            if self.sim.debug: print 'ERROR TIME PASSED; start:', now, 'now:', self.sim.now()
            
            
     

    
class LinkedMaster(Process):
    '''Process receives data packets from Transport, and sends them to the Slave Node in the Link, simply a
        send and forget operation. No ACKs involved at this level'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self,name=self.__class__.__name__,sim=sim)
        self.ID = ID
        self.netQ = Store(capacity='unbounded', name='LM NET inQueue', sim=sim) #For data & mgmt packets to send out
        self.phyQ = Store(capacity='unbounded', name='LM PHY inQueue', sim=sim) #For responses only!
        self.link_ID = None
        self.linkedFreq = None
        self.linkedDest = None
        self.interface = iLink
        
        self.Tx_Success = SimEvent(sim=sim, name='LM_Tx_Success')
        self.Tx_Fail = SimEvent(sim=sim, name='LM_Tx_Fail')
        self.LM_Terminate = SimEvent(sim=sim, name='LM_Terminate')
        self.Rx_Success = SimEvent(sim=sim, name='LM_Rx_Success')
        self.Rx_Fail = SimEvent(sim=sim, name='LM_Rx_Fail')
        
        self.abort_event = SimEvent(sim=sim, name='LM_Abort')
        self.abort = False
        
        self.send_data = None
        self.send_details = None

        self.active = True
        self.terminate = SimEvent(sim=sim, name='LM_terminate')

        self.modem_data_rate = 1200. #bps (not bytes)!        
    def execute(self):
        while self.active:
            if self.sim.debug: print self.ID, 'Linked M: Ready and waiting for packet from Network, or for LM Terminate (or send EOF)', self.sim.now()
            yield (get, self, self.netQ, 1),(waitevent, self, self.LM_Terminate)
            if self.acquired(self.netQ):
                if not self.abort:
                    self.send_data = self.got[0]
                    if self.sim.debug: print self.ID, 'Linked M: Got packet, pkts in netQ:', len(self.netQ.theBuffer), 'deets:',[pkt.link.pType for pkt in self.netQ.theBuffer], self.sim.now()
                    if self.checkForEOF(self.send_data):
                        if self.sim.debug: print self.ID, 'Linked M: EOF True - remember LM_Send_EOF is not used anymore', self.sim.now()
                        self.sendData(self.send_data)
                        for x in self.waitforTxSuccess():
                            yield x   
                        for x in self.waitforResponse():
                            yield x
                    else:
                        if self.sim.debug: print self.ID, 'Linked M: Data Packet, pass to Send Data', self.sim.now()
                        self.send_data.link.pType = 3
                        self.sendData(self.send_data)
                        for x in self.waitforTxSuccess():
                            yield x   
                else:
                    self.abortEvent()
            if self.eventsFired[0] == self.LM_Terminate:
                if self.sim.debug: print self.ID, 'Linked Master: Terminate Event received, handing back control to ALE Master', self.sim.now()
                self.terminate.signal(0)
#            elif self.eventsFired[0] == self.LM_Send_EOF:
#                print self.ID, 'Linked Master: Send EOF Event received, Send EOF to Slave', self.sim.now()
#                self.send_data = self.LM_Send_EOF.signalparam
#                self.sendData(self.send_data)
#                for x in self.waitforTxSuccess():
#                    yield x   
#                for x in self.waitforResponse():
#                    yield x
    def checkForEOF(self, send_data): #not implemented in this version
        return send_data.link.pType == 6
    def checkForResponse(self, send_data):
        return send_data.link.pType == 5
    def sendData(self, send_data):
        send_data = self.appendAttributes(send_data)
        self.send_details = send_data.ID
        self.send_data = copy.deepcopy(send_data)
        self.interface.physicalQ.signal(send_data)
    def waitforTxSuccess(self):
        if self.sim.debug: print self.ID, 'Linked Master: Waiting for Tx Success', self.sim.now()
        yield waitevent, self, [self.Tx_Success, self.Tx_Fail, self.abort_event]
        #print self.eventsFired
        if self.eventsFired[0] == self.Tx_Success:
            if self.sim.debug: print self.ID, 'Linked Master: Tx Success', self.sim.now()
            self.interface.ProcDict['msg_kernel'].M_Data_Tx_Sent.signal((self.send_details, self.send_data))
            #self.sim.Vis.M_DataRxRec2[self.ID].signal((send_details,send_data.transport.data))
#            self.terminate.signal(0)
        elif self.eventsFired[0] == self.LM_Terminate:
            #Deleted this from options, as it is best to wait until all packets are sent etc. and Linked Master comes back to the start (where it will see LM_Terminate is fired)
            if self.sim.debug: print self.ID, 'Linked Master: End of Data, Terminate LinkedMaster to allow ALEMaster to send EOM', self.sim.now()
            self.terminate.signal(0)  
        elif self.eventsFired[0] == self.Tx_Fail:
            self.interface.ProcDict['msg_kernel'].M_Data_Tx_Fail.signal(self.send_details)
#            self.terminate.signal(1)
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def waitforResponse(self):
        if self.sim.debug: print self.ID, 'Linked Master: Waiting for Response packet..', self.sim.now()
        TO = TimeOut(self.sim, self.sim.G.link_wait_for_reply)
        self.sim.activate(TO,TO.execute())
        yield (get, self, self.phyQ, 1),(waitevent, self, (TO.timeoutEvent, self.abort_event))
        if self.acquired(self.phyQ):
            possible_response = self.got[0]
            if self.sim.debug: print self.ID, 'LinkedM: Response packet acquired', self.sim.now()
            for x in self.eatEvent([self.abort_event],[TO]):
                yield x
            if self.checkForResponse(possible_response):
                self.response_datagram = copy.deepcopy(possible_response)
                for x in self.waitforRxSuccess():
                    yield x
            else:
                if self.sim.debug: print self.ID, 'Linked Master: Incorrect packet type received, expecting Response', self.sim.now()
                for x in self.waitforResponse():
                    yield x
                #What to do???? Abort Link?? Resend EOF??
        if self.eventsFired[0]==TO.timeoutEvent:
            if self.sim.debug: print self.ID, 'Linked Master: Response timed out', self.sim.now()
            #What to do???? Abort Link?? Resend EOF??
        if self.eventsFired[0]==self.abort_event:
            self.abortEvent()
    def waitforRxSuccess(self):
        if self.sim.debug: print self.ID, 'Linked Master: Waiting for response Rx success/fail', self.sim.now()
        yield waitevent, self, [self.Rx_Success, self.Rx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Rx_Success:
            if self.sim.debug: print self.ID, 'Linked Master: Response Rx Success', self.sim.now()
            #self.interface.networkQ(self.response_datagram)
            self.interface.ProcDict['msg_kernel'].M_ARQ_Rx_Success.signal(self.response_datagram)
        elif self.eventsFired[0] == self.Rx_Fail:
            if self.sim.debug: print self.ID, 'Linked Master: Response Rx Fail', self.sim.now()
            #What to do???? Abort Link?? Resend EOF??
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()

    def abortEvent(self):
        if self.sim.debug: print self.ID, '***Linked Master: aborted from above[2]', self.sim.now()
        self.active = False
        self.terminate.signal(1)
        self.abort = False
            
    def appendAttributes(self, send_packet):
        send_packet.link.frequency = [self.linkedFreq] #This is a bit contrived, as at this stage all packets should really bypass the 'link layer'
        send_packet.link.destination = self.linkedDest
        if send_packet.ID.Destination != self.linkedDest:
            print self.ID, '*** LINK ERROR: TRANSPORT SENT WRONG PACKET', send_packet.ID.Destination, self.linkedDest, self.sim.now() 
        send_packet.ID.Link_ID = self.link_ID
        send_packet.link.origin = self.ID
        send_packet.physical.frequency = self.linkedFreq
        send_packet.physical.time = None
        send_packet = self.calculateTime(send_packet)
        
        send_packet.internal_last_location = Layer.LINK
        #send_packet.link.pType = 3
        return send_packet
    def calculateTime(self, send_data):
        #TP = self.sim.G.Throughput_SNR(self.sim.Net.env_container.SNR_matrix[self.ID,self.linkedDest][self.linkedFreq])
        TP = send_data.network.data_rate
        send_data.physical.time = float(send_data.transport.data)/TP + self.sim.G.interleaver_time #interleaver time (VS)
        if self.sim.debug: print self.ID, 'Link: Time calculated:', send_data.physical.time, '@TP:', TP, '(data=', send_data.transport.data, ')', self.sim.now()
        return send_data
        #optional make it equivalent to 10bits for every byte (AG/ST paper - including overheads)
    def eatEvent(self, events, TOprocs=[]):
        now = self.sim.now()
        for ev in events:
            if self.sim.debug: print 'eatEvent: signalling', ev.name, self.sim.now()
            ev.signal()
            ev.signal()
            if self.sim.debug: print 'eatEvent: waiting for', ev.name, self.sim.now()
            yield waitevent, self, ev
            if self.sim.debug: print 'eatEvent:', ev.name, 'eaten, orig time:', now, self.sim.now()
        for tp in TOprocs:
            if self.sim.debug: print 'eatEvent: deactivating', tp.name, self.sim.now()
            tp.active = False
        if now != self.sim.now():
            if self.sim.debug: print 'ERROR TIME PASSED; start:', now, 'now:', self.sim.now()
    
                
class LinkedSlave(Process):
    '''Process receives all packets that are broadcast on the Linked Frequency, then decides whether they are of the
        correct type and addresed to this Node. If so it forwards it to Transport, if not the Link is aborted (this
        is a Critical behaviour of this current model). This occurs as long as this Layer remains in LINKED_SLAVE state'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self,name=self.__class__.__name__,sim=sim)
        self.ID = ID
        self.inQ = Store(capacity='unbounded', name='LS inQueue', sim=sim)
        self.linkedFreq = None
        self.linkedDest = None
        self.linkedID = None
        self.interface = iLink

        self.Rx_Fail = SimEvent(sim=sim, name='LS_Rx_Fail')
        self.Rx_Success = SimEvent(sim=sim, name='LS_Rx_Success')
        self.LS_Terminate = SimEvent(sim=sim, name='LS_Terminate')
        self.LS_Send_ARQ = SimEvent(sim=sim, name='LS_Send_ARQ')
        self.Tx_Success = SimEvent(sim=sim, name='LS_Tx_Success')
        self.Tx_Fail = SimEvent(sim=sim, name='LS_Tx_Fail')
        
        self.abort_event = SimEvent(sim=sim, name='LS_Abort')
        self.abort = False

        self.active = True
        self.terminate = SimEvent(sim=sim, name='LS_terminate')
        
        self.rec_packet = None
        self.rec_details = None
        self.ARQ_packet = None
        self.ARQ_skeleton = None

        self.modem_data_rate = 1200.
        
    def execute(self):
        while self.active:
            if self.sim.debug: print self.ID, 'Linked Slave Idle, waiting for trigger incoming packet', self.sim.now()
            yield get, self, self.inQ, 1
            if self.sim.debug: print self.ID, 'Linked Slave ACTIVATED', self.sim.now()
            #self.interface.ProcDict['msg_kernel'].switch_Rx.signal(self.linkedFreq) #Make sure Physical is in Rx mode.
            self.linkedID = copy.deepcopy(self.got[0].ID)
            self.linkedID.Destination = self.linkedDest #Get Details
            yield put, self, self.inQ, self.got #Place into queue again (to be picked up immediately:)
            while self.interface.ProcDict['kernel'].STATE == nState.LINKED_SLAVE and self.active: #Now remain in this loop until State changes.
                TO = TimeOut(self.sim, self.sim.G.rx_timeout)
                self.sim.activate(TO,TO.execute())
                if self.sim.debug: print self.ID, 'Linked Slave: Ready and waiting to get packet from inQ, or for rx_timeout, LS_Send_ARQ or LS_Terminate', self.sim.now()
                yield (get, self, self.inQ, 1),(waitevent, self, [TO.timeoutEvent, self.LS_Send_ARQ, self.LS_Terminate]) #potential danger again
                if self.acquired(self.inQ):
                    #success
                    self.rec_packet = self.got[0]
                    self.rec_details = copy.deepcopy(self.rec_packet.ID)
                    if self.sim.debug: print self.ID, 'Linked Slave: Packet recd', self.rec_details.all_IDs(), self.sim.now()
                    if self.rec_packet.link.pType == 3: #data
                        if self.checkPacketDetails():     
                            for x in self.waitforRxSuccess():
                                yield x
                    elif self.rec_packet.link.pType == 6: #EOF
                        if self.sim.debug: print self.ID, '***Linked Slave: EOF received', self.sim.now()
                        if self.checkPacketDetails():     
                            for x in self.waitforRxSuccess():
                                yield x
                    else:
                        if self.sim.debug: print self.ID, '***Linked Slave: Unrecognised packet received', self.sim.now()
                elif self.eventsFired[0] == self.LS_Send_ARQ:
                    for x in self.makeARQ():
                        yield x
                elif self.eventsFired[0] == TO.timeoutEvent:
                    if self.abort:
                        if self.sim.debug: print self.ID, '***Link: ABORT EVENT fired @ LINKED SLAVE', self.sim.now()
                        self.abortEvent()
                        self.abort = False
                    else:
                        if self.sim.debug: print self.ID, '***Link (LS): RX Timed Out, reboot now instead of terminate?', self.sim.now()
                        self.active = False    
                        self.interface.ProcDict['msg_kernel'].S_Data_Rx_Fail.signal(self.linkedID)
                        self.terminate.signal(1)
                elif self.eventsFired[0] == self.LS_Terminate:
                    if self.sim.debug: print self.ID, 'Linked Slave: Terminate Event received, handing back control to ALE Slave', self.sim.now()
                    self.terminate.signal(0)
                    yield hold, self, 0 #waits for terminate event to be received by ALES and mode to change to TERM SLAVE so LS breaks out of this active loop
    def checkPacketDetails(self):
        if self.linkedID.Link_ID == self.rec_packet.ID.Link_ID:
            if self.rec_packet.physical.destination == self.ID:
                self.rec_details.Destination = self.rec_packet.link.origin
                self.rec_packet.internal_last_location = Layer.LINK
                if self.sim.debug: print self.ID, 'Linked Slave: Packet is correct Link_ID and Destination', self.rec_details.all_IDs(), self.sim.now()
                return True
        if self.sim.debug: print self.ID, 'Linked Slave: DISCONT .Packet is INCORRECT Link_ID or Destination', self.rec_details.all_IDs(), self.sim.now()
        return False
    def waitforRxSuccess(self):
        if self.sim.debug: print self.ID, 'Linked Slave: Waiting for packet Rx success/fail', self.sim.now()
        yield waitevent, self, [self.Rx_Success, self.Rx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Rx_Success:
            if self.sim.debug: print self.ID, 'Linked Slave: Packet Rx Success', self.sim.now()
            self.interface.ProcDict['msg_kernel'].S_Data_Rx_Rec.signal(self.rec_details)
            #self.sim.Vis.S_DataTxSent2[self.ID].signal((rec_details,rec_packet.transport.data))
            self.interface.networkQ.signal([self.rec_packet])
#            self.active = False
#            self.terminate.signal(0)
        elif self.eventsFired[0] == self.Rx_Fail:
            if self.sim.debug: print self.ID, 'Linked Slave: Response Rx Fail', self.sim.now()
            self.interface.ProcDict['msg_kernel'].S_Data_Rx_Fail.signal(self.rec_details)
#            self.active = False
#            self.terminate.signal(1)
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()
    def makeARQ(self):
        if self.sim.debug: print self.ID, 'Link: LS: LS_Send_ARQ received, creating packet and passing to sendEOF', self.sim.now()
        self.ARQ_skeleton = self.LS_Send_ARQ.signalparam
        self.ARQ_packet = self.createARQPacket(self.ARQ_skeleton)
        for x in self.sendARQ(self.ARQ_packet):
                    yield x     
    def sendARQ(self,EOF_pkt):
        if self.sim.debug: print self.ID, 'Linked Slave: Sending ARQ to physical now and waiting for Tx Success', self.sim.now() 
        self.interface.physicalQ.signal(EOF_pkt)
        for x in self.waitforTxSuccess():
            yield x
    def createARQPacket(self, packet_skeleton): #ARQ reply
        send_packet = packet.Packet()
        send_packet.ID = self.linkedID
        send_packet.ID.Destination = self.linkedDest
        send_packet.ID.Origin = self.ID
        
        send_packet.physical.time = self.sim.G.Trw #This is arbitrary, it could well be calculated from the data size of the link packet
        send_packet.transport.data = 1024
        send_packet.link.destination = send_packet.ID.Destination
        send_packet.link.origin = self.ID
        send_packet.link.frequency = self.linkedFreq
        send_packet.physical.frequency = send_packet.link.frequency

        send_packet.link.pType = 5
        send_packet.internal_last_location = 2 #2nd layer
        
        send_packet.network.msg_ID = packet_skeleton.network.msg_ID
        send_packet.network.ARQ_success = packet_skeleton.network.ARQ_success
        send_packet.network.ARQ_fail = packet_skeleton.network.ARQ_fail
        
        send_packet.meta.waveform = packet_skeleton.meta.waveform
        send_packet.network.data_rate = packet_skeleton.network.data_rate
        
        return send_packet
    def waitforTxSuccess(self):
        if self.sim.debug: print self.ID, 'Linked Slave: Waiting for Tx Success', self.sim.now()
        yield waitevent, self, [self.Tx_Success, self.Tx_Fail, self.abort_event]
        if self.eventsFired[0] == self.Tx_Success:
            if self.sim.debug: print self.ID, 'Linked Slave: Tx Success', self.sim.now()
            self.interface.ProcDict['msg_kernel'].S_ARQ_Tx_Success.signal(self.ARQ_packet)
        elif self.eventsFired[0] == self.Tx_Fail:
            if self.sim.debug: print self.ID, 'Linked Slave: Tx Fail', self.sim.now()
        elif self.eventsFired[0] == self.abort_event:
            self.abortEvent()

    def abortEvent(self):
        if self.sim.debug: print self.ID, '***ABORT EVENT LS FIRED!!!', self.sim.now()
        self.active = False
        self.terminate.signal(1)
