'''
Created on Mar 1, 2011

@author: duncantait
'''
from SimPy.Simulation import *
from enums import *
import random
import copy
import math
import numpy as np

#class G():
#    debug = False
#    num_nodes = 10
#    num_freq = 10
#    bon_chance = 0.75
#    propagation_time = 0.08
#    min_SNR = 0.0
#    max_SNR = 30.0
#    best_SNR = 100.0

def getClasses(): #List all main (need an interface to main simulation) active Process classes in here, this will be iterated through by OSI stack and create instances of them.   
    return [Environment, msg_kernel]

def getEvents(iLink):
    return iLink.ProcDict['msg_kernel'].channelTaken + \
            iLink.ProcDict['msg_kernel'].channelFree

class msg_kernel(Process):
    def __init__(self, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.interface = iLink
        self.sim = sim
        self.inQ = Store(capacity='unbounded', sim=sim)
        self.interface_events()
    def interface_events(self):
        self.channelTaken = [SimEvent(name='taken'+str(i), sim=self.sim) for i in range(self.sim.G.num_freq)] #List of events (one for each channel), fired when a packet is put on the channel
        self.channelFree = [SimEvent(name='free'+str(i), sim=self.sim) for i in range(self.sim.G.num_freq)] #List of events (one for each channel), fired when a packet is taken off the channel
    def execute(self):
        while True:
            yield waitevent, self, self.interface.phyEvents #phyEvents will be a concatenation of all nodes' envEvents
            if self.eventsFired[0].name=='abort_send':
                ID = self.eventsFired[0].signalparam
                Physical_ID = ID.Physical_ID
                for frame in self.interface.ProcDict['Environment'].OnAirProcesses:
                    if frame.frame_ID == Physical_ID:
                        frame.abort_event.signal()

class Gridder(dict):
    def __getitem__(self, index):
        return super(Gridder, self).__getitem__(tuple(sorted(index)))
    def __setitem__(self, index, value):
        return super(Gridder, self).__setitem__(tuple(sorted(index)), value)

class Environment(Process):
    def __init__(self, sim, iLink):
        Process.__init__(self, name='Environment', sim=sim)
        self.frequencies = [[] for i in range(self.sim.G.num_freq)]
        #self.channelTaken = [SimEvent(name='taken'+str(i),sim=sim) for i in range(G.num_freq)] #List of events (one for each channel), fired when a packet is put on the channel
        #self.channelFree = [SimEvent(name='free'+str(i),sim=sim) for i in range(G.num_freq)] #List of events (one for each channel), fired when a packet is taken off the channel

        self.OnAirProcesses = []
        self.inQ = Store(capacity='unbounded', sim=sim)
        self.interface = iLink
    def execute(self):
        self.calculateSNR()
        while True:
            yield get, self, self.inQ, 1
            frame = self.got[0]
            frame.internal_last_location = Layer.ENVIRONMENT
            #print 'Environment received packet from', frame.physical.origin, 'notes:', frame.notes, self.sim.now()
            #frame = self.retrieveSNR(frame) - do this in Physical now!
            #frame = self.calculateGoNoGo(frame)
            self.putOnChan(frame)
    def retrieveSNR(self, frame):
        frame.meta.linkSNR = self.interface.SNR_matrix[frame.ID.Origin, frame.ID.Destination] #this is a list of SNRs
        if self.sim.debug: print 'Env:, LinkSNR retreived:', frame.meta.linkSNR, '(phyID:', frame.ID.Physical_ID, ')', self.sim.now()
        frame.meta.perceivedSNR = frame.meta.linkSNR
        return frame
    def calculateGoNoGo(self, frame):
        if frame.link.pType==0: #Means it's a call
            if random.random() > self.sim.G.ratio_nogo:
                print 'Nogo!', frame.ID.all_IDs()
                frame.link.destination = -1
                frame.physical.destination = -1 #this is the one that matters to Slave
                frame.ID.Destination = -1
        return frame
    def putOnChan(self, frame):
##        if len(self.interface.frequencies[frame.physical.frequency])!=0:
##            print 'Environment detects collision on channel', frame.physical.frequency, 'origins:', [i.link.origin for i in self.interface.frequencies[frame.physical.frequency]], self.sim.now()
##        else:
        O = OnAir(self.sim, self.interface, frame)
        self.sim.activate(O, O.execute())
        self.OnAirProcesses.append(O)
    def calculateSNR(self):
        for i in range(self.sim.G.num_nodes):
            for j in range(self.sim.G.num_nodes):
                if i != j:
                    #for each co-ord, make sure that each channel set has correct ratio propagating
                    num_prop = int(math.floor(self.sim.G.num_freq*self.sim.G.ratio_propagating))
                    num_not_prop = self.sim.G.num_freq - num_prop
                    num_prop_index = random.sample(range(self.sim.G.num_freq),num_prop)
                    num_not_prop_index = [ind for ind in range(self.sim.G.num_freq) if ind not in num_prop_index]
                    chan_vals = [None]*self.sim.G.num_freq
                    for k in num_prop_index:
                        chan_vals[k] = random.uniform(self.sim.G.min_rec_SNR,self.sim.G.max_SNR)
                    for k in num_not_prop_index:
                        chan_vals[k] = random.uniform(self.sim.G.min_SNR,self.sim.G.min_rec_SNR)
                    self.interface.SNR_matrix[i,j] = chan_vals
                else:
                    self.interface.SNR_matrix[i,j] = [self.sim.G.best_SNR for max in range(self.sim.G.num_freq)] #if the antenna is checking on a packet sent by the same node, the SNR should be very high(unless near-interference)

    def createVOACAPmatrix(self):
        #returns triplet: [dec10,dec50,dec90] = VOACAP_matrix[hr][tx,rx][freq]
        VOACAP_matrix = []
        for hr in range(24):
            hrMatrix = Gridder()
            for i in range(self.sim.G.num_nodes):
                for j in range(self.sim.G.num_nodes):
                    if i != j:
                        #for each co-ord, make sure that each channel set has correct ratio propagating
                        num_prop = int(math.floor(self.sim.G.num_freq*self.sim.G.ratio_propagating))
                        num_not_prop = self.sim.G.num_freq - num_prop
                        num_prop_index = random.sample(range(self.sim.G.num_freq),num_prop)
                        num_not_prop_index = [ind for ind in range(self.sim.G.num_freq) if ind not in num_prop_index]
                        chan_vals = [[None,None,None]]*self.sim.G.num_freq
                        for k in num_prop_index:
                            rVar = sorted([random.uniform(self.sim.G.min_rec_SNR,self.sim.G.max_SNR) for i in range(3)])
                            chan_vals[k] = rVar #dec10,dec50,dec90
                        for k in num_not_prop_index:
                            rVar = sorted([random.uniform(self.sim.G.min_SNR,self.sim.G.min_rec_SNR) for i in range(3)])
                            chan_vals[k] = rVar
                        hrMatrix[i,j] = chan_vals
                    else:
                        hrMatrix[i,j] = [self.sim.G.best_SNR for max in range(self.sim.G.num_freq)] #if the antenna is checking on a packet sent by the same node, the SNR should be very high(unless near-interference)
            VOACAP_matrix.append(hrMatrix)
        return VOACAP_matrix

    def calculateInstSNR(self, hour, freq, tx, rx):
        #Calculate instantaneous SNR
        SNR = None
        
        dec10SNR = self.interface.VOACAP_matrix[hour][tx,rx][0]
        dec50SNR = self.interface.VOACAP_matrix[hour][tx,rx][1]
        dec90SNR = self.interface.VOACAP_matrix[hour][tx,rx][2]
        
        rVar = [random.random() for i in range(3)]
        z = math.cos(2*math.pi*rVar[0])*math.sqrt(-2*math.log(rVar[1]))
        if rVar[2] > 0.5:
            SNR = dec50SNR + z*((dec90SNR - dec50SNR)/1.28)
        else:
            SNR = dec50SNR - z*((dec50SNR - dec10SNR)/1.28)
        
        return SNR
    def createPropData(self):
        #returns: propData[t][tx,rx][freq]
        simTime = self.sim.G.time
        fidelity = self.sim.G.SNR_fidelity
        propSlots = np.arange(0,simTime,fidelity)
        #by default there are 1000 slots for SNR data in propSlots, this needs to be done for
        #all nodes to all nodes, all frequencies.
        propData = []
        for t in propSlots:
            timeSlot = Gridder()
            for i in range(self.sim.G.num_nodes):
                for j in range(self.sim.G.num_nodes):
                    if i != j:
                        chanVals = [self.calculateInstSNR(math.floor(t/3600), freq, i, j) for freq in range(self.sim.G.num_freq)]
                        timeSlot[i,j] = chanVals
                    else:
                        timeSlot[i,j] = [self.sim.G.best_SNR for max in range(self.sim.G.num_freq)]
            propData.append(timeSlot)
        return propData
            
        

class TimeOut(Process):
    """Temporary process, one use only. Initialized with a timeout parameter, fires an event after this amount of time has elapsed and terminates"""
    def __init__(self,sim,time):
        Process.__init__(self, sim=sim, name='EnvTimeOut'+str(time))
        self.time = time
        self.timeoutEvent = SimEvent(name='TimeOut_Env', sim=sim)
    def execute(self):
        yield hold, self, self.time
        self.timeoutEvent.signal()
        #self.timeoutEvent.signal()
            
class OnAir(Process):
    def __init__(self, sim, iLink, datagram):
        Process.__init__(self, name='EnvironmentOnAir'+str(datagram.ID.Physical_ID), sim=sim)
        self.frame_ID = datagram.ID.Physical_ID
        self.interface = iLink
        self.datagram = datagram
        self.abort_event = SimEvent(sim=sim) #need to link this up
    def execute(self):
        #a = self.sim.now()
        copy_datagram = copy.deepcopy(self.datagram)
        if self.sim.debug: print 'Environment: ON AIR RECEIVED PACKET physical ID', self.frame_ID, 'Origin:', self.datagram.physical.origin, 'Destination:', self.datagram.physical.destination, self.sim.now() 
        yield hold, self, self.sim.G.propagation_time #PROPAGATION TIME - THIS COULD BE DONE IN PHYSICAL: i.e. append the propagation time TO EACH NODE to the datagram, make a new section: ENVIRONMENT
        self.interface.frequencies[self.datagram.physical.frequency].append(self.datagram)
        #print 'Environment: prop time waited (!), now officially ON CHANNEL', self.datagram.physical.frequency, self.sim.now()
        if self.sim.debug: print 'ENV firing channelTaken', self.datagram.physical.frequency, 'packet from node', self.datagram.physical.origin, 'to node', self.datagram.physical.destination, self.sim.now()
        self.interface.ProcDict['msg_kernel'].channelTaken[self.datagram.physical.frequency].signal(copy_datagram)
        if self.sim.debug: print 'ENV fired channelTaken, about to wait', self.datagram.physical.time, self.sim.now()
        TO = TimeOut(self.sim, self.datagram.physical.time)
        self.sim.activate(TO,TO.execute())
        yield waitevent, self, [TO.timeoutEvent, self.abort_event]
        if self.eventsFired[0]==self.abort_event:
            print 'ENV PACKET ABORTED by node:', self.datagram.physical.origin, 'ID:', self.datagram.ID.Physical_ID, self.sim.now()
        #if self.sim.debug: print 'Env: All channels:', [x[0].physical.origin for x in self.interface.frequencies if len(x)>0]
        self.removePackets()
        #print 'ENV firing channelFree', self.datagram.physical.frequency, self.sim.now()
        self.interface.ProcDict['msg_kernel'].channelFree[self.datagram.physical.frequency].signal(copy_datagram)
    def removePackets(self):
        if self.sim.debug: print 'Env: Current OnAir Datagram details: origin:', self.datagram.physical.origin, 'frequency:', self.datagram.physical.frequency, self.sim.now()
        if self.sim.debug: print 'Env: All channels:', [len(x) for x in self.interface.frequencies]
        for i in range(len(self.interface.frequencies[self.datagram.physical.frequency])):
            current_num_packets = len(self.interface.frequencies[self.datagram.physical.frequency])
            if self.sim.debug: print 'On this channel (', self.datagram.physical.frequency, '), packet', i, 'of', len(self.interface.frequencies[self.datagram.physical.frequency]), 's details: origin:', self.interface.frequencies[self.datagram.physical.frequency][current_num_packets-1].physical.origin, 'physID:', self.interface.frequencies[self.datagram.physical.frequency][current_num_packets-1].ID.Physical_ID, self.sim.now() 
            if self.sim.debug: print 'On this channel (', self.datagram.physical.frequency, '), packet', i, 'of', len(self.interface.frequencies[self.datagram.physical.frequency]), ': details:', ['origin:'+str(pkt.physical.origin)+' physID:'+str(pkt.ID.Physical_ID) for pkt in self.interface.frequencies[self.datagram.physical.frequency]], self.sim.now() 
            if i < current_num_packets:
                if self.interface.frequencies[self.datagram.physical.frequency][i].ID.Physical_ID == self.frame_ID:
                    if self.sim.debug: print 'Packet just about to be removed from chan:', self.interface.frequencies[self.datagram.physical.frequency][i], self.interface.frequencies[self.datagram.physical.frequency][i].ID.Physical_ID,  self.sim.now()#, '(', a, ')'
                    del self.interface.frequencies[self.datagram.physical.frequency][i]
                    if self.sim.debug: print 'Packets left on channel', self.datagram.physical.frequency,':', len(self.interface.frequencies[self.datagram.physical.frequency])
                    #enumeration of the for loop has now been messed up. If multiple packets did need to be deleted, flag them and delete them AFTER the for loop
                    break
#            if self.interface.frequencies[self.datagram.physical.frequency][current_num_packets-1].ID.Physical_ID == self.frame_ID:
#                if self.sim.debug: print 'Packet just about to be removed from chan:', self.interface.frequencies[self.datagram.physical.frequency][current_num_packets-1], self.interface.frequencies[self.datagram.physical.frequency][current_num_packets-1].ID.Physical_ID,  self.sim.now()#, '(', a, ')'
#                del self.interface.frequencies[self.datagram.physical.frequency][current_num_packets-1]
#                if self.sim.debug: print 'Packets left on channel', self.datagram.physical.frequency,':', len(self.interface.frequencies[self.datagram.physical.frequency])
#                #enumeration of the for loop has now been messed up. If multiple packets did need to be deleted, flag them and delete them AFTER the for loop
#                break
        
    
    
