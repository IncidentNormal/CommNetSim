from SimPy.Simulation import *
from enums import *
import time, packet
import copy
import random
import string

def getClasses(): #List all main (need an interface to main simulation) active Process classes in here, this will be iterated through by OSI stack and create instances of them.   
    return [kernel, msg_kernel, Scanning, LBT, Tx, Rx] #kernel needs to be first

def getLinkEvents(iLink):
    return [iLink.ProcDict['msg_kernel'].LBT_Success, \
     iLink.ProcDict['msg_kernel'].LBT_Fail, \
     iLink.ProcDict['msg_kernel'].Tx_Success, \
     iLink.ProcDict['msg_kernel'].Tx_Fail, \
     iLink.ProcDict['msg_kernel'].Rx_Success, \
     iLink.ProcDict['msg_kernel'].Rx_Fail, \
     iLink.ProcDict['msg_kernel'].scanning_call_ended, \
     iLink.ProcDict['msg_kernel'].scanning_call_interrupt]

def getEnvEvents(iLink):
    return [iLink.ProcDict['msg_kernel'].abort_send]

class nState():
    SCANNING = 0
    LBT = 1
    RX = 2
    TX = 3

class msg_kernel(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.sim = sim
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        self.SNR = self.sim.Net.env_container.SNR_matrix

        self.interface_events()
    def interface_events(self):
        #LINK
        self.LBT_Success = SimEvent(sim=self.sim, name='LBT_Success')
        self.LBT_Fail = SimEvent(sim=self.sim, name='LBT_Fail')
        self.Tx_Success = SimEvent(sim=self.sim, name='Tx_Success')
        self.Tx_Fail = SimEvent(sim=self.sim, name='Tx_Fail')
        self.Rx_Success = SimEvent(sim=self.sim, name='Rx_Success')
        self.Rx_Fail = SimEvent(sim=self.sim, name='Rx_Fail')
        self.scanning_call_ended = SimEvent(sim=self.sim, name='scanning_call_ended')
        self.scanning_call_interrupt = SimEvent(sim=self.sim, name='scanning_call_interrupt')
        #ENVIRONMENT
        self.abort_send = SimEvent(sim=self.sim, name='abort_send')
    def execute(self):
        while True:
            yield waitevent, self, self.interface.linkEvents + self.interface.envEvents #env_events!!!! Think about this!
            #LINK
            if self.eventsFired[0].name=='time_out': #abort call.
                if len(self.interface.ProcDict['Scanning'].abort_event.waits) > 0:
                    self.interface.ProcDict['Scanning'].abort_event.signal(self.eventsFired[0].signalparam) #ever used?
                if len(self.interface.ProcDict['LBT'].abort_event.waits) > 0:
                    self.interface.ProcDict['LBT'].abort_event.signal(self.eventsFired[0].signalparam)
                if len(self.interface.ProcDict['Rx'].abort_event.waits) > 0:
                    self.interface.ProcDict['Rx'].abort_event.signal(self.eventsFired[0].signalparam)
                if len(self.interface.ProcDict['Tx'].abort_event.waits) > 0:
                    self.interface.ProcDict['Tx'].abort_event.signal(self.eventsFired[0].signalparam)
                self.interface.ProcDict['kernel'].STATE = nState.RX
            #LINK
            if self.eventsFired[0].name=='stop_scanning':
                if len(self.interface.ProcDict['Scanning'].stop_scanning.waits) > 0:
                    self.interface.ProcDict['Scanning'].stop_scanning.signal(self.eventsFired[0].signalparam) #ever used?
            if self.eventsFired[0].name=='start_scanning': 
                if len(self.interface.ProcDict['Scanning'].start_scanning.waits) > 0:
                    self.interface.ProcDict['Scanning'].start_scanning.signal(self.eventsFired[0].signalparam) #ever used?
            #ENVIRONMENT
            if self.eventsFired[0].name[0:5]=='taken': #channel taken   
                index = int(self.eventsFired[0].name[5:])
                datagram = self.eventsFired[0].signalparam
                #if self.SNR[self.ID,datagram.link.origin][index] > self.sim.G.min_rec_SNR: #gets done in Rx now
                if self.interface.ProcDict['kernel'].STATE == nState.TX:
                    #if self.sim.debug: print self.ID, 'Physical TX: Channel Taken Index:', index, self.sim.now()
                    if len(self.interface.ProcDict['Tx'].channelTaken[index].waits) > 0:
                        self.interface.ProcDict['Tx'].channelTaken[index].signal(datagram)
                if self.interface.ProcDict['kernel'].STATE == nState.SCANNING or self.interface.ProcDict['kernel'].STATE == nState.RX:
                    #if self.sim.debug: print self.ID, 'Physical RX: Channel Taken Index:', index, self.sim.now()
                    if len(self.interface.ProcDict['Rx'].channelTaken[index].waits) > 0:
                        self.interface.ProcDict['Rx'].channelTaken[index].signal(datagram)
                #else:
                #    if self.sim.debug: print self.ID, 'PHYSICAL: SNR too low, packet discarded at antenna, channelTaken not fired', self.sim.now()
            if self.eventsFired[0].name[0:4]=='free': #channel free
                index = int(self.eventsFired[0].name[4:])
                datagram = self.eventsFired[0].signalparam
                #if self.SNR[self.ID,datagram.link.origin][index] > self.sim.G.min_rec_SNR:
                if self.interface.ProcDict['kernel'].STATE == nState.TX:
                    #if self.sim.debug: print self.ID, 'Physical TX: Channel Free Index:', index, self.sim.now()
                    if len(self.interface.ProcDict['Tx'].channelFree[index].waits) > 0:
                        self.interface.ProcDict['Tx'].channelFree[index].signal(datagram)
                if self.interface.ProcDict['kernel'].STATE == nState.SCANNING or self.interface.ProcDict['kernel'].STATE == nState.RX:
                    #if self.sim.debug: print self.ID, 'Physical RX: Channel Free Index:', index, self.sim.now()
                    if len(self.interface.ProcDict['Rx'].channelFree[index].waits) > 0:
                        self.interface.ProcDict['Rx'].channelFree[index].signal(datagram)
                #else:
                #    if self.sim.debug: print self.ID, 'PHYSICAL: SNR too low, packet discarded at antenna, channelFree not fired', self.sim.now()
class kernel(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
        self.current_frequency = -1
        
        self.STATE = nState.SCANNING
    def execute(self):
        while True:
            yield get, self, self.inQ
            rec_packet = self.got[0]
            
            last_location = rec_packet.internal_last_location
            rec_packet.internal_last_location = Layer.PHYSICAL
            rec_packet.ID.Physical_ID = self.createID()
            if last_location == Layer.LINK:
                if rec_packet.link.pType == 0: #call
                    if self.sim.debug: print self.ID, 'PHYSICAL [kernel] pass to LBT', self.sim.now()                    
                    yield put, self, self.interface.ProcDict['LBT'].inQ, [rec_packet] 
                else:                   
                    if self.sim.debug: print self.ID, 'PHYSICAL [kernel] pass to Tx', self.sim.now()
                    yield put, self, self.interface.ProcDict['Tx'].inQ, [rec_packet]
            else:
                print 'error: pkt came from environment?'
    def createID(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))



class Scanning(Process): 
    '''Process listens on each frequency for the scan_time (0.2s default), if there is anything being broadcast
        on that channel it will listen for the Triple Redundant Word length (0.384) and forward the packet to Link
        if it is addressed to this node, it assumes it is a call and waits for it to end, upon which time it notifes
        Link if it was a success or a failure'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.currentFreq = random.randint(0,self.sim.G.num_freq-1)
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', name='Scanning inQ', sim=sim)
        
        self.call_signal = None
        self.dwell_start = None
        self.stop_scanning = SimEvent(sim=self.sim, name='stop_scanning')
        self.start_scanning = SimEvent(sim=self.sim, name='start_scanning')

        self.abort_event = SimEvent(sim=self.sim, name='abort_event')
    def execute(self):
        yield hold, self, random.uniform(0,10)
        while True:
            self.call_signal = None #Reset all signals
            self.dwell_start = self.sim.now()
            if not self.readChannel():
                if self.sim.debug: print self.ID, 'Scanning: Nothing immediately seen on channel', self.currentFreq, 'keep looking:', self.sim.now()
                for x in self.watchChannelOn(self.sim.G.dwell_time):
                    yield x
            else:
                if self.sim.debug: print self.ID, 'Scanning: Something found on channel', self.currentFreq, 'is it a call and to me?', self.sim.now()
                #CHECK IF ACTUALLY A CALL AND ADDRESSED ?? Not good enough leaving it to Link really as then Link has too much to deal with.
                if self.checkCall(self.interface.ProcDict['Rx'].currentSignal)==True:
                    if self.sim.debug: print self.ID, 'Scanning: Yes'
                    for x in self.watchChannelOff(2*self.sim.G.num_freq*self.sim.G.dwell_time):
                        yield x
                else:
                    if self.sim.debug: print self.ID, 'Scanning: No'
                    for x in self.waitEndSlot():
                        yield x
    def waitEndSlot(self):
        if self.sim.debug: print self.ID, 'waiting until end of slot:', self.calculateSlotTimeRemaining(self.dwell_start)
        TO = TimeOut(self.sim, self.calculateSlotTimeRemaining(self.dwell_start))
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, (TO.timeoutEvent, self.stop_scanning)
        if self.eventsFired[0]==self.stop_scanning:
            for x in self.stopScanning():
                yield x
        else:
            self.changeFreq()
            if self.sim.debug: print self.ID, 'Scanning TimeOut: FREQ Changing now (2):', self.currentFreq, 'Rx:', self.interface.ProcDict['Rx'].currentFreq, self.sim.now()
            yield hold, self, 0
                        
    def changeFreq(self):
        if self.interface.ProcDict['kernel'].STATE == nState.SCANNING:
            if self.currentFreq != self.sim.G.num_freq-1:
                self.currentFreq += 1
            else:
                self.currentFreq = 0
            self.interface.ProcDict['Rx'].freqChange.signal(self.currentFreq)
    def checkCall(self, signal):
        #Check if a call and addressed to me
        if signal.ID.Destination == self.ID and signal.link.pType == 0:
            return True
        else:
            return False
    def calculateSlotTimeRemaining(self, dwell_start):
        remaining_time = self.sim.G.dwell_time - (self.sim.now() - dwell_start)
        return remaining_time    
    def readChannel(self):
        if self.interface.ProcDict['Rx'].currentSignal != None:
            if self.sim.debug: print self.ID, 'Rx of possible call'
            return True
        return False
    def stopScanning(self):
        if self.sim.debug: print self.ID, 'Phy: Scanning: Told to stop Scanning.', self.sim.now()
        yield waitevent, self, self.start_scanning
        if self.sim.debug: print self.ID, 'Phy: Scanning: Told to start Scanning.', self.sim.now()
        self.interface.ProcDict['kernel'].STATE = nState.SCANNING
        
    def watchChannelOn(self, dur):
        TO = TimeOut(self.sim, dur)
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [self.interface.ProcDict['Rx'].signalStart, TO.timeoutEvent, self.abort_event, self.stop_scanning]
        if self.eventsFired[0] == TO.timeoutEvent:
            self.changeFreq()
            if self.sim.debug: print self.ID, 'Scanning TimeOut: FREQ Changing now:', self.currentFreq, 'Rx:', self.interface.ProcDict['Rx'].currentFreq, self.sim.now()
            yield hold, self, 0
        elif self.eventsFired[0] == self.interface.ProcDict['Rx'].signalStart:
            if self.sim.debug: print self.ID, 'Scanning, signal seen! (signalStart fired)', self.sim.now()
            if self.checkCall(self.interface.ProcDict['Rx'].currentSignal)==True:
                for x in self.watchChannelOff(2*self.sim.G.num_freq*self.sim.G.dwell_time):
                    yield x
            else:
                for x in self.waitEndSlot():
                        yield x
        elif self.eventsFired[0] == self.stop_scanning:
            for x in self.stopScanning():
                yield x
        else:
            self.abortEvent(self.abort_event.signalparam)
    def watchChannelOff(self, dur):
        #wait for call to en
        self.interface.ProcDict['kernel'].STATE = nState.RX
        self.call_signal = copy.deepcopy(self.interface.ProcDict['Rx'].currentSignal) #take a copy of the call signal for later
        
        if self.sim.debug: print self.ID, 'Signal found, now waiting for it to complete', self.sim.now()
        if self.sim.debug: print self.call_signal.ID.all_IDs()
        TO = TimeOut(self.sim, dur)
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [self.interface.ProcDict['Rx'].signalComplete, self.interface.ProcDict['Rx'].signalBreak, TO.timeoutEvent, self.abort_event, self.stop_scanning]
        if self.eventsFired[0] == TO.timeoutEvent:
            if self.sim.debug: print self.ID, 'call timed out', self.sim.now()
            self.interface.ProcDict['kernel'].STATE = nState.SCANNING
            #self.interface.ProcDict['msg_kernel'].scanning_call_ended.signal(self.interface.ProcDict['Rx'].currentSignal.ID)
        elif self.eventsFired[0] == self.interface.ProcDict['Rx'].signalBreak:
            if self.sim.debug: print self.ID, 'call interupted', self.sim.now()
            self.interface.ProcDict['msg_kernel'].scanning_call_interrupt.signal(self.call_signal.ID)
            self.interface.ProcDict['kernel'].STATE = nState.SCANNING
        elif self.eventsFired[0] == self.interface.ProcDict['Rx'].signalComplete:
            if self.sim.debug: print self.ID, 'call completed', self.sim.now()
            self.interface.ProcDict['msg_kernel'].scanning_call_ended.signal(self.call_signal.ID)
        elif self.eventsFired[0] == self.stop_scanning:
            for x in self.stopScanning():
                yield x
        else:
            self.abortEvent(self.abort_event.signalparam)
    def abortEvent(self, reason):
        if self.sim.debug: print self.ID, 'Scanning abort event', reason
        self.interface.ProcDict['kernel'].STATE = nState.SCANNING
             

class LBT(Process):
    '''Process that listens on a prospective channel for an amount of time. If frequency is free and remains free
        for duration of this time, it notifies Link of this success, if it is not free initially it notifies Link of this
        failure. If it is interrupted during this time by a call addressed to this node, it adopts the behaviour of
        Scanning, and waits for the call to end (whilst notifying Link of the incoming call immediately - Link will then
        take care of this itself and cancel any ALEMaster() Process). If it is not addressed to this node, Link is
        notified of the LBT Failure'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.watchedFreq = None
        self.interface = iLink  
        self.inQ = Store(capacity='unbounded', name='Tx inQ', sim=sim)
        self.datagram = -1
        self.call_details = -1
        self.incoming = -1
        
        self.abort_event = SimEvent(sim=self.sim, name='abort_event')
    def execute(self):
        while True:
            self.datagram = None
            for x in self.waitForPacket():
                yield x
            for x in self.watchChannel(self.sim.G.LBT_time):
                yield x
    def waitForPacket(self):
        yield get, self, self.inQ, 1
        self.interface.ProcDict['kernel'].STATE = nState.RX
        self.datagram = self.createDetails(self.got[0])
        self.call_details = copy.deepcopy(self.datagram.ID)
        self.watchedFreq = self.datagram.physical.frequency
    def abortEvent(self, reason):
        if self.sim.debug: print self.ID, 'LBT abort event', reason

    def readChannel(self):
        if self.interface.ProcDict['Rx'].currentSignal != None:
            self.interface.ProcDict['msg_kernel'].LBT_Fail.signal((0,self.call_details))
            return True
        return False
    def watchChannel(self, dur):
        self.interface.ProcDict['Rx'].freqChange.signal(self.watchedFreq)
        yield hold, self, 0
        if not self.readChannel():
            TO = TimeOut(self.sim, dur)
            self.sim.activate(TO,TO.execute())
            yield waitevent, self, [self.interface.ProcDict['Rx'].signalStart, TO.timeoutEvent, self.abort_event]
            if self.eventsFired[0] == TO.timeoutEvent:
                self.interface.ProcDict['msg_kernel'].LBT_Success.signal(self.call_details)
                yield put, self, self.interface.ProcDict['Tx'].inQ, [self.datagram]
            elif self.eventsFired[0] == self.interface.ProcDict['Rx'].signalStart:
                if self.sim.debug: print self.ID, 'signalstart deteced', self.sim.now()
                if self.checkCall(self.interface.ProcDict['Rx'].currentSignal)==True: #means it is a call to me
                    self.interface.ProcDict['msg_kernel'].LBT_Fail.signal((1,self.call_details))
                else:
                    self.interface.ProcDict['msg_kernel'].LBT_Fail.signal((0,self.call_details))
            else:
                self.abortEvent(self.abort_event.signalparam)
    def checkCall(self, signal):
        #Check if a call and addressed to me
        if signal.ID.Destination == self.ID and signal.link.pType == 0:
            return True
        else:
            return False
    def createDetails(self, in_packet):
        in_packet.physical.destination = in_packet.link.destination
        #in_packet.physical.origin = self.ID
        in_packet.ID.Origin = self.ID
        return in_packet


class Rx(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink 
        
        self.currentFreq = -1
        self.freqChange = SimEvent(sim=self.sim, name='freqChange')
        self.Tx = SimEvent(sim=self.sim, name='Tx')
        self.resumeRx = SimEvent(sim=self.sim, name='resumeRx')
        self.abort_event = SimEvent(sim=self.sim, name='abort_event')
        
        self.signalGrid = [[]]*self.sim.G.num_freq
        self.signalProcGrid = [[]]*self.sim.G.num_freq

        self.currentSignal = None
        self.primary_checked = False
        self.signalStart = SimEvent(sim=self.sim, name='signalStart')
        self.signalComplete = SimEvent(sim=self.sim, name='signalComplete')
        self.signalBreak = SimEvent(sim=self.sim, name='signalBreak')
        
        self.channelTaken = [SimEvent(sim=sim, name='ct'+str(i)) for i in range(self.sim.G.num_freq)]
        self.channelFree = [SimEvent(sim=sim, name='cf'+str(i)) for i in range(self.sim.G.num_freq)]
        
    def execute(self):
        while True:
            yield waitevent, self, [self.channelTaken[self.currentFreq], self.freqChange, self.Tx, self.abort_event]
            if self.eventsFired[0]==self.freqChange:

                self.currentFreq = self.freqChange.signalparam
                #wipe events, make sure all signal processes are closed/reset.
                self.signalGrid = [[]]*self.sim.G.num_freq #reset signal grid
                for s in self.signalProcGrid[self.currentFreq]:
                    s.abort_event.signal()
                self.currentSignal = None
                if self.sim.debug: print self.ID, 'Rx freq Change to', self.currentFreq, self.sim.now()
                self.readSignal()
            elif self.eventsFired[0] == self.Tx:
                if self.sim.debug: print self.ID, 'Rx got Tx signal, passivated', self.sim.now()
                yield waitevent, self, self.resumeRx
                self.interface.ProcDict['kernel'].STATE = nState.RX
                if self.sim.debug: print self.ID, 'Rx Resumed, currentChannel:', self.currentFreq, self.sim.now()
                self.readSignal()
            elif self.eventsFired[0] == self.channelTaken[self.currentFreq]:
                if self.sim.debug: print self.ID, 'Rx channelTaken fired', self.sim.now()
                self.readSignal()
            elif self.eventsFired[0] == self.abort_event:
                self.abortEvent(self.abort_event.signalparam)
        #job is to watch a channel and build up a picture of all signals on that frequency
    def readSignal(self):
        if self.sim.debug: print self.ID, 'readSignal: current on_air channel contents:', [sig.ID.Physical_ID for sig in self.interface.env_cont.frequencies[self.currentFreq]]
        channel_contents = copy.deepcopy(self.interface.env_cont.frequencies[self.currentFreq]) #contents at time of reading
        #difference check against signalGrid, this enables this to be called multiple times
        channel_contents = self.retriveSNRs(channel_contents)
        channel_contents = self.calculateInterference(channel_contents)
        channel_contents.sort(key=lambda x:x.meta.perceivedSNR, reverse=True) #sort signals on channel by SNR, largest first.
       
        if self.sim.debug: print self.ID, 'readSignal: channel contents after interference calculated:', [sig.ID.Physical_ID for sig in channel_contents]
        for signal in channel_contents:
            if self.sim.debug: print self.ID, 'readSignal: signal being checked against and GRID contents:', signal.ID.Physical_ID, [sig.ID.Physical_ID for sig in self.signalGrid[self.currentFreq]]
            if signal.ID.Physical_ID not in [sig.ID.Physical_ID for sig in self.signalGrid[self.currentFreq]]: 
                if self.sim.debug: print self.ID, 'Rx readSignal found new packet..', self.sim.now()
                signal = self.processForeignPackets(signal)
                
                primary_signal = self.checkSNR(signal)
                self.primary_checked = True #Flag this so if multiple signals are checked at once, checkSNR won't rescan the primary for each one.
                
                WS = WatchSignal(self.sim, self.ID, self, self.currentFreq, signal, primary_signal)
                self.sim.activate(WS, WS.execute())
                self.signalProcGrid[self.currentFreq].append(WS)
            else:
                if self.sim.debug: print self.ID, 'Rx readSignal already seen this packet..', self.sim.now()
        self.primary_checked = False
            
    def retriveSNRs(self, packets):
        #if multiple packets, calculate effect the interference has on each of their perceived SNR score
        #should be more like, the smaller one is, the greater the other one has of being recieved (logairthmically)
        for pkt in packets:
            #RetreiveSNR;
            pkt.meta.linkSNR = self.interface.env_cont.SNR_matrix[pkt.ID.Origin, self.ID]
        return packets
    def calculateInterference(self, packets):
        link_SNRs = []
        for pkt in packets:
            link_SNRs.append(pkt.meta.linkSNR[self.currentFreq]) #linkSNR is a list (all channels for that particular origin/destination combination)
        #algorithm:
        for pkt in packets:
            pkt.meta.perceivedSNR = (pkt.meta.linkSNR[self.currentFreq]/sum(link_SNRs)) * pkt.meta.linkSNR[self.currentFreq]
            if self.sim.debug: print self.ID, 'Phy: CalculateInterference: Packet Phy ID:', pkt.ID.Physical_ID, 'perceivedSNR:', pkt.meta.perceivedSNR, self.sim.now() 
        return packets  
    def processForeignPackets(self, pkt):
        if self.sim.debug: print self.ID, 'processing foreign packets', self.sim.now()
        #check packet has come from another node
        if pkt.ID.Origin != self.ID:
            pkt.internal_last_location = Layer.PHYSICAL
            pkt.notes += ' ,Rx '+str(self.sim.now())
            return pkt
        else:
            if self.sim.debug: print self.ID, 'error: same origin as self.ID:', pkt.ID.all_IDs(), self.sim.now()
            return False      
    def checkSNR(self, signal):
        if self.sim.debug: print self.ID, 'checkSNR beginning, perceivedSNR:', signal.meta.perceivedSNR, self.sim.now()
        #if another signal interrupts the primary signal, check to see if the SNR is affected.
        if self.currentSignal == None:
            if self.checkWaveform(signal):
            #if signal.meta.perceivedSNR > self.sim.G.min_SNR:
                if self.sim.debug: print self.ID, 'Signal has enough SNR, pass to link and fire Signal Start', self.sim.now()
                self.currentSignal = signal
                if self.sim.debug: print 'self.currentSignal (primary):', self.currentSignal.ID.all_IDs()
                self.interface.linkQ.signal(signal) #or whatever
                #print 'signal:', signal
                if len( self.signalStart.waits) > 0:
                    self.signalStart.signal()
                return True
            return False
        else: #If develop this to CHANGE the primary signal, remember to update the .primary attribute in the appropriate WatchSignal process (the one that was primary before..)
            if self.sim.debug: print self.ID, 'signal found (self.currentSignal), recheck if perceived SNR is above minimum SNR', self.sim.now()
            if self.sim.debug: print 'self.currentSignal (primary):', self.currentSignal.ID.all_IDs()
            if self.sim.debug: print 'signal (this new one):', signal.ID.all_IDs()
            #the super complicated SNR comparison/interference algorithm:
            if not self.primary_checked:
                if not self.checkWaveform(self.currentSignal):
                #if self.currentSignal.meta.perceivedSNR < self.sim.G.min_SNR:
                    if self.sim.debug: print self.ID, 'perceived SNR is below minimum SNR, removing signal', self.sim.now() #Thing about this is, it causes all sorts of problems.
                    #self.interface.ProcDict['msg_kernel'].Rx_Fail.signal(self.currentSignal)
                    self.currentSignal = None
                    if len(self.signalBreak.waits) > 0:
                        self.signalBreak.signal()
                    for WS in self.signalProcGrid[self.currentFreq]:
                        #print WS.ID, signal.ID.Physical_ID
                        if WS.signal.ID.Physical_ID == signal.ID.Physical_ID:
                            WS.primary = False
            else:
                if self.sim.debug: print self.ID, 'PHY RX: Primary signal has already been tagged as Received or Not, no point running this again!', self.sim.now()
            return False

    def checkWaveform(self, signal):
        #profile of waveform: SNR/throughput/reliability
        #modulation mode aswell...
        rVar = random.random()
        currentWaveform = self.sim.G.waveforms[signal.meta.waveform]
        if currentWaveform.name == self.sim.G.linking_waveform:
            if self.sim.debug: print self.ID, 'Phy: Linking waveform found', self.sim.now()
            linkingProb = self.calculateLinkingProbability(signal)
            result = rVar < linkingProb
            if self.sim.debug: print self.ID, 'Phy: Linking Probability:', linkingProb,'rVar:', rVar, 'RESULT=', result, self.sim.now()
            return result
        elif currentWaveform.name == self.sim.G.data_waveform:
            if self.sim.debug: print self.ID, 'Phy: Data waveform found', self.sim.now()
            dataRxProb = self.calculateDataRxProbability(signal)
            result = rVar < dataRxProb
            if self.sim.debug: print self.ID, 'Phy: Data Rx Probability:', dataRxProb,'rVar:', rVar, 'RESULT=', result, self.sim.now()
            return result
        else:
            return None
                    
    def calculateDataRxProbability(self, signal):
        perceivedSNR = signal.meta.perceivedSNR
        bitrate = signal.physical.data_rate
        if self.sim.debug: print self.ID, 'Phy: data_rate of waveform:', bitrate, self.sim.now()
        errorProb = 1.0
        required_SNRs = []
        for error_profile in self.sim.G.waveforms[signal.meta.waveform].error_profiles:
            for index, val in enumerate(error_profile.SNR_Poor):
                if val[0] == bitrate:
                    if self.sim.debug: print self.ID, 'Phy: Data Rx Required SNR found:', val[1], error_profile.BER_Profile, self.sim.now()
                    required_SNRs.append((val[1],error_profile.BER_Profile))
        required_SNRs = sorted(required_SNRs)
        for reqSNR in required_SNRs:
            if perceivedSNR > reqSNR[0]:
                if self.sim.debug: print self.ID, 'Phy: Data Rx BER found:', reqSNR[1], '(higher than', reqSNR[0], 'dB)', self.sim.now()
                errorProb = self.calculateBERProbability(signal, reqSNR[1])
        if self.sim.debug: print self.ID, 'Phy: Data Rx BER Error probability for whole packet:', errorProb, '(packet size=', signal.transport.data, ')', self.sim.now()
        dataRxProb = 1.0 - errorProb
        return dataRxProb
    
    def calculateBERProbability(self, signal, BER_Profile):
        #Probability that there is an error within the packet size
        bits = signal.transport.data
        bitErrorProb = bits*BER_Profile
        return bitErrorProb
    
    def calculateLinkingProbability(self, signal):
        linkingProb = None
        perceivedSNR = signal.meta.perceivedSNR
        if self.sim.debug: print self.ID, 'Phy: Perceived SNR of waveform:', perceivedSNR, self.sim.now()
        for linking_profile in self.sim.G.waveforms[signal.meta.waveform].linking_profiles:
            for index, val in enumerate(linking_profile.LinkingProbability_Poor):
                if perceivedSNR > val[1]:
                    if self.sim.debug: print self.ID, 'Phy: Linking probability found:', val[0], '(higher than', val[1], 'dB)', self.sim.now()
                    linkingProb = val[0]
        return linkingProb
    
    def abortEvent(self, reason):
        print self.ID, '***Rx: abort_event occurred', reason, self.sim.now()
        self.abortSignalWatch(self.currentSignal)
        self.interface.ProcDict['kernel'].STATE=nState.SCANNING
        
    def abortSignalWatch(self, signal):
        if signal != None:
            phy_ID = signal.ID.Physical_ID
            for WS in self.signalProcGrid[self.currentFreq]:
                #print WS.ID, signal.ID.Physical_ID
                if WS.signal.ID.Physical_ID == phy_ID:
                    WS.abort_event.signal()

class WatchSignal(Process):
    def __init__(self, sim, ID, rx, channel, pkt, primary):
        Process.__init__(self, name='WatchSignal'+str(pkt.ID.Physical_ID), sim=sim)
        self.sim = sim
        self.ID = ID
        self.rx = rx
        self.signal = pkt
        self.dur = self.signal.physical.time
        self.channel = channel
        self.active = True
        self.primary = primary
        
        self.abort_event = SimEvent(sim=self.sim, name='abort_event')
    def execute(self):
        if self.sim.debug: print self.ID, 'WatchSignal begins', self.sim.now()
        self.rx.signalGrid[self.channel].append(self.signal)
        TO = TimeOut(self.sim, self.dur) #Start timer
        self.sim.activate(TO,TO.execute())
        start_time = self.sim.now()

        while self.active:
            yield waitevent, self, [TO.timeoutEvent, self.rx.channelFree[self.channel], self.abort_event]
            if self.eventsFired[0] == self.abort_event:
                if self.sim.debug: print self.ID, 'signal aborted', self.sim.now()
                self.active = False
            elif self.eventsFired[0] == self.rx.channelFree[self.channel]:
                if self.rx.channelFree[self.channel].signalparam.ID.Physical_ID == self.signal.ID.Physical_ID:
                    if self.sim.debug: print self.ID, 'WatchSignal: Signal being watched ended:', self.signal.ID.Physical_ID, self.sim.now()
                    self.active = False
                    if self.isComplete(start_time):
                        if self.sim.debug: print self.ID, 'Rx: packet received OK in entirety', self.sim.now()
                        self.removeFromGrid(self.signal)
                        if self.primary: #is it STILL PRIMARY?
                            self.rx.interface.ProcDict['Rx'].currentSignal = None
                            if len(self.rx.interface.ProcDict['Rx'].signalComplete.waits) > 0:
                                self.rx.interface.ProcDict['Rx'].signalComplete.signal(self.signal.ID)
                            self.rx.interface.ProcDict['msg_kernel'].Rx_Success.signal(self.signal.ID)
                    else:
                        if self.sim.debug: print self.ID, 'Rx: Incomplete Message Received, original msg length:', self.dur, 'channel free after:', self.sim.now() - start_time, self.sim.now()
                        self.removeFromGrid(self.signal)
                        if self.primary: 
                            self.rx.interface.ProcDict['Rx'].currentSignal = None
                            if len(self.rx.interface.ProcDict['Rx'].signalBreak.waits) > 0:
                                self.rx.interface.ProcDict['Rx'].signalBreak.signal(self.signal.ID)
                            self.rx.interface.ProcDict['msg_kernel'].Rx_Fail.signal(self.signal.ID)
                else:
                    if self.sim.debug: print self.ID, 'channel freed but not the signal we are watching', self.sim.now()
            elif self.eventsFired[0] == TO.timeoutEvent:
                self.active = False
                if self.primary: self.rx.interface.ProcDict['Rx'].currentSignal = None
                if self.sim.debug: print self.ID, 'Rx: packet received OK in entirety (2)', self.sim.now()
                self.removeFromGrid(self.signal)
                #if self.primary: self.interface.ProcDict['msg_kernel'].Rx_Success.signal(rec_packet.ID) #Only used by Linked Slave at present
    def isComplete(self, start_time):
        if self.signal.link.pType == 0: #if it is a call, this could be dealt with in scanning...
            return True
        else:
            if self.sim.G.feq((self.sim.now() - start_time), self.dur):
                return True
            else:
                return False
        
    def removeFromGrid(self, pkt):
        if self.sim.debug: print 'current GRID:', [sig.ID.Physical_ID for sig in self.rx.signalGrid[self.channel]]
        if self.sim.debug: print 'removingFromGrid:', pkt.ID.Physical_ID
        if pkt in self.rx.signalGrid[self.channel]:
            self.rx.signalGrid[self.channel].remove(pkt)
        if self.sim.debug: print 'current GRID post removal:', [sig.ID.Physical_ID for sig in self.rx.signalGrid[self.channel]]
            
class Tx(Process):
    '''Process to send the packet to Environment, which puts it on the air. After a random tiny Jitter (0-50ms) to
        avoid programmatic synchronisation, the packet is put on air and this Process awaits the event to show
        it has successfully been put onto the channel (from Environment), it then waits the designated amount
        of time for the packet to send fully, and listens to see if anything else is broadcast onto the channel.
        If so it detects a collision and aborts the Transmission. If not then it is deemed a success and notifies Link'''
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.currentFreq = -1
        self.interface = iLink  
        self.inQ = Store(capacity='unbounded', name='Tx inQ', sim=sim)
        self.datagram = -1
        self.call_details = None
        self.abort_event = SimEvent(sim=self.sim, name='abort_event')

        self.channelTaken = [SimEvent(sim=self.sim) for i in range(self.sim.G.num_freq)]
        self.channelFree = [SimEvent(sim=self.sim) for i in range(self.sim.G.num_freq)]
    def execute(self):
        while True:
            self.datagram = None
            for x in self.waitForPacket():
                yield x
            for x in self.jitter():
                yield x
            for x in self.sendPacket():
                yield x
            if self.sim.debug: print self.ID, 'Tx completed, sending resume Rx signal', self.sim.now()
            self.interface.ProcDict['Rx'].resumeRx.signal()
            yield hold, self, 0
    def waitForPacket(self):
        yield get, self, self.inQ, 1
        if self.sim.debug: print self.ID, 'Tx received packet, sending Tx signal to Rx.. TX Q size:', len(self.inQ.theBuffer), self.sim.now()
        self.interface.ProcDict['kernel'].STATE = nState.TX
        self.interface.ProcDict['Rx'].Tx.signal()
        self.datagram = self.createDetails(self.got[0])
        self.call_details = copy.deepcopy(self.datagram.ID)
        self.currentFreq = self.datagram.physical.frequency
    def jitter(self):
        if self.sim.debug: print self.ID, 'jitter beginning...', self.sim.now()
        TO = TimeOut(self.sim, random.uniform(self.sim.G.phy_jitter_range[0],self.sim.G.phy_jitter_range[1])) #Up to 50ms, mainly to avoid exact synchronising between Nodes.
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [TO.timeoutEvent, self.abort_event]
        if self.eventsFired[0] == self.abort_event:
            if self.sim.debug: print 'abort'
        else:
            if self.sim.debug: print self.ID, 'jitter ending...', self.sim.now()
    def sendPacket(self):
        if self.sim.debug: print self.ID, 'sending packet to envQ...', self.sim.now()
        self.interface.envQ.signal(self.datagram)          
        for x in self.waitForPacketOnAir():
            yield x
        for x in self.watchChannel(self.datagram.physical.time):
            yield x
    def waitForPacketOnAir(self):
        TO = TimeOut(self.sim, self.sim.G.phy_timeout) #Start timer
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [TO.timeoutEvent, self.channelTaken[self.currentFreq], self.abort_event]
        if self.eventsFired[0] == TO.timeoutEvent:
            print self.ID, '***Physical TX: channel never got taken - datagram never started sending, problem on channel (possibly busy)', self.sim.now()
            self.interface.ProcDict['msg_kernel'].Tx_Fail.signal(self.call_details)
            #self.interface.ProcDict['msg_kernel'].abort_send.signal(self.datagram.ID.Physical_ID)
        elif self.eventsFired[0] == self.abort_event:
            if self.sim.debug: print 'abort'
        else:
            #channelTaken fired - but need a quick check to see if it is the packet we're talking about and not another
            #that has just been placed on the channel by another node
            if not self.checkCorrectPacket():
                for x in self.waitForPacketOnAir():
                    yield x
    def checkCorrectPacket(self):
        datagram = self.channelTaken[self.currentFreq].signalparam
        if datagram.ID.Physical_ID == self.call_details.Physical_ID:
            return True
        else:
            return False
    def watchChannel(self, dur):
        TO = TimeOut(self.sim, dur) #Start timer
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [TO.timeoutEvent, self.abort_event]
        if self.eventsFired[0] == TO.timeoutEvent: #Success
            if self.sim.debug: print self.ID, 'Physical TX: datagram successfully sent: sending Tx Success signal up to Link', self.sim.now()
            self.interface.ProcDict['msg_kernel'].Tx_Success.signal(self.call_details)
        elif self.eventsFired[0] == self.abort_event:
            if self.sim.debug: print self.ID, '***PHYSICAL [Tx] ABORT 03', self.abort_event.signalparam, self.sim.now()
            #self.interface.ProcDict['kernel'].STATE = nState.SCANNING
            self.interface.ProcDict['msg_kernel'].abort_send.signal(self.datagram.ID.Physical_ID)
    def abortEvent(self, reason):
        if self.sim.debug: print 'abort event', reason
    def createDetails(self, in_packet):
        in_packet.ID.Origin = self.ID
        in_packet.physical.origin = self.ID
        in_packet.physical.destination = in_packet.link.destination
        in_packet.physical.data_rate = in_packet.network.data_rate
        return in_packet

class TimeOut(Process):
    """Temporary process, one use only. Initialized with a timeout parameter, fires an event after this amount of time has elapsed and terminates"""
    def __init__(self,sim,time):
        Process.__init__(self, sim=sim,name='TimeOutPhyProc'+str(time))
        self.time = time
        self.sim = sim
        self.timeoutEvent = SimEvent(name='TimeOut_Phy', sim=sim)
    def execute(self):
        yield hold, self, self.time
        self.timeoutEvent.signal()
                        

            












                    

