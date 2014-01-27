'''
Created on 8 Nov 2011

@author: DT
'''
#import visual as vp
from SimPy.Simulation import *
from enums import *
import math
import numpy as np

class MLinkTimer(Process):
    def __init__(self, sim, vLink, ID, origin, event_list_tuples):
        Process.__init__(self, sim=sim)
        self.sim = sim
        self.ID = ID
        self.Link_ID = self.ID.Link_ID
        self.vLink = vLink
        self.origin = origin
        self.chan = None
        
        self.LBT_Success = SimEvent(sim = self.sim)
        self.LBT_Fail = SimEvent(sim = self.sim)
        self.M_Link_Success = SimEvent(sim = self.sim)
        self.M_Link_Fail = SimEvent(sim = self.sim)
        self.M_Link_Retry = SimEvent(sim = self.sim)
        self.Tx_Success = SimEvent(sim = self.sim)
        self.Rx_Success = SimEvent(sim = self.sim)
        self.M_Link_Ended = SimEvent(sim = self.sim)

        self.dataSent = 0
        self.unfinished = True
        
        self.endEvents = []
        self.appendLists = []
        for e in event_list_tuples:
            self.endEvents.append(e[0]) #specify the event that will terminate the process
            self.appendLists.append(e[1]) #specify the list that this timer will append to
    def execute(self):
        if self.sim.debug: print 'Vis: Link Started'
        start_time = self.sim.now()

        self.chan = self.ID.Frequency
        if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.blue
        while self.unfinished:
            yield waitevent, self, (self.LBT_Success, self.LBT_Fail)
            if self.eventsFired[0] == self.LBT_Success:
                if self.sim.debug: print 'Vis: (M) LBT Success'
                if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.black
                if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.blue
                yield waitevent, self, (self.Tx_Success, self.M_Link_Fail)
                if self.eventsFired[0] == self.Tx_Success:
                    if self.sim.debug: print 'Vis: (M) Tx Success'
                    if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.black
                    #So can't tell if its received or not, but slave should be running a similar Timer.. (need to add events for this).
                    yield waitevent, self, (self.Rx_Success, self.M_Link_Fail)
                    if self.eventsFired[0] == self.Rx_Success:
                        if self.sim.debug: print 'Vis: (M) Rx Success'
                        if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.blue
                        yield waitevent, self, (self.M_Link_Success, self.M_Link_Fail)    
                        if self.eventsFired[0] == self.M_Link_Success:
                            print 'Vis: M Link Success:', self.Link_ID, self.sim.now()
                            link_time = self.sim.now() - start_time
                            self.sim.Monitors[self.origin].m_link_latency.append(link_time)
                            data_start_time = self.sim.now()
                            if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.black
                            if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.green
                            
                            yield waitevent, self, self.M_Link_Ended
                            if self.sim.debug: print 'Vis: M Link Ended', self.Link_ID, self.sim.now()
                            data_time = self.sim.now() - data_start_time
                            self.sim.Monitors[self.origin].m_data_time.append(data_time)
                            total_time = self.sim.now() - start_time
                            self.sim.Monitors[self.origin].m_total_time.append(total_time)
                            if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.black
                            self.sim.Monitors[self.origin].m_data_length.append(self.dataSent)
                            if self.dataSent != 0:
                                self.sim.Monitors[self.origin].m_throughput.append(float(self.dataSent)/total_time)
                            else:
                                self.sim.Monitors[self.origin].m_throughput.append(0.0)
                            self.unfinished = False
                        else:
                            if self.sim.debug: print 'Vis: M Link Fail'
                            if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.black
                            self.unfinished = False
                    else:
                        print 'Vis: M Link Fail'
                        link_time = self.sim.now() - start_time
                        self.sim.Monitors[self.origin].m_link_latency.append(link_time)
                        if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.black
                        self.unfinished = False
                else:
                    if self.sim.debug: print 'Vis: M Link Fail'
                    if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.black
                    self.unfinished = False
            else:
                if self.sim.debug: print 'Vis: LBT Fail'

class SLinkTimer(Process):
    def __init__(self, sim, vLink, ID, origin, event_list_tuples):
        Process.__init__(self, sim=sim)
        self.sim = sim
        self.ID = ID
        self.Link_ID = self.ID.Link_ID
        self.vLink = vLink

        self.chan = None
        self.origin = origin
        self.scanning_call_ended = SimEvent(sim = self.sim)
        self.Tx_Success = SimEvent(sim = self.sim)
        self.Rx_Success = SimEvent(sim = self.sim)
        self.S_Link_Success = SimEvent(sim = self.sim)
        self.S_Link_Fail = SimEvent(sim = self.sim)
        self.S_Link_Ended = SimEvent(sim = self.sim)

        self.dataRec = 0
        self.unfinished = True

        self.appendLists = []
        self.endEvents = []
        for e in event_list_tuples:
            self.endEvents.append(e[0]) #specify the event that will terminate the process
            self.appendLists.append(e[1]) #specify the list that this timer will append to
    def execute(self):
        start_time = self.sim.now()
        if self.sim.debug: print 'Vis: S Link Started'

        self.chan = self.ID.Frequency
        if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.red
        yield waitevent, self, (self.scanning_call_ended, self.S_Link_Fail)
        if self.eventsFired[0] == self.scanning_call_ended:
            if self.sim.debug: print 'Vis: Scanning Call Ended'
            if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.black
            if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.red
            yield waitevent, self, (self.Tx_Success, self.S_Link_Fail)
            if self.eventsFired[0] == self.Tx_Success:
                if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.red
                if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.black
                yield waitevent, self, (self.S_Link_Success, self.S_Link_Fail)
                if self.eventsFired[0] == self.S_Link_Success:
                    if self.sim.debug: print 'Vis: S Link Success'
                    link_time = self.sim.now() - start_time
                    self.sim.Monitors[self.origin].s_link_latency.append(link_time)
                    data_start_time = self.sim.now()
                    if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.black
                    if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.magenta
                    
                    yield waitevent, self, self.S_Link_Ended
                    if self.sim.debug: print 'Vis: S Link Ended'
                    data_time = self.sim.now() - data_start_time
                    self.sim.Monitors[self.origin].s_data_time.append(data_time)
                    total_time = self.sim.now() - start_time
                    self.sim.Monitors[self.origin].s_total_time.append(total_time)
                    if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.black
                    self.sim.Monitors[self.origin].s_data_length.append(self.dataRec)
                    if self.dataRec != 0:
                        self.sim.Monitors[self.origin].s_throughput.append(float(self.dataRec)/total_time)
                    else:
                        self.sim.Monitors[self.origin].s_throughput.append(0.0)
                    
                else:
                    if self.sim.debug: print 'Vis: S Link Failed'
                    if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.black
            else:
                if self.sim.debug: print 'Vis: S Link Failed'
                if self.sim.vis_on: self.vLink.node_spheres_freq[self.origin][self.chan].color = vp.color.black
        else:
            if self.sim.debug: print 'Vis: S Link Failed'
            if self.sim.vis_on: self.vLink.node_squares_freq[self.origin][self.chan].color = vp.color.black

        
##        while self.unfinished:
##            yield waitevent, self, self.endEvents
##            finish_time = self.sim.now() - start_time
##            for i,e in enumerate(self.endEvents):
##                if self.eventsFired[0] == e:
##                    if e.signalparam.Destination == self.ID.Destination:
##                        if e.signalparam.Link_ID == self.ID.Link_ID: 
##                            self.appendLists[i].append(finish_time)
##


class Timer(Process):
    def __init__(self, sim, ID, origin, event_list_tuples):
        Process.__init__(self, sim=sim)
        self.sim = sim
        self.ID = ID
        self.endEvents = []
        self.appendLists = []
        self.unfinished = True
        for e in event_list_tuples:
            self.endEvents.append(e[0]) #specify the event that will terminate the process
            self.appendLists.append(e[1]) #specify the list that this timer will append to
    def execute(self):
        start_time = self.sim.now()
        while self.unfinished:
            yield waitevent, self, self.endEvents
            finish_time = self.sim.now() - start_time
            for i,e in enumerate(self.endEvents):
                if self.eventsFired[0] == e:
                    if e.signalparam.Destination == self.ID.Destination:
                        if e.signalparam.Link_ID == self.ID.Link_ID: 
                            self.appendLists[i].append(finish_time)
                            
class DataTimer(Process):
    def __init__(self, sim, vLink, ID, origin):
        Process.__init__(self, sim=sim)
        self.sim = sim
        self.vLink = vLink
        
        self.ID = ID
        self.origin = origin
        
        self.incrEvent = SimEvent(sim=self.sim)
        self.endEvent = SimEvent(sim=self.sim)
        self.idChange = SimEvent(sim=self.sim)
        self.incrTotal = 0
        
        self.unfinished = True

    def execute(self):
        start_time = self.sim.now()
        while self.unfinished:
            yield waitevent, self, (self.endEvent, self.incrEvent, self.idChange)
            finish_time = self.sim.now() - start_time
            
            for e in self.eventsFired:
                if e == self.incrEvent:#
                    if e.signalparam.Destination == self.ID.Destination: 
                        if e.signalparam.Transport_ID == self.ID.Transport_ID:
                            if self.sim.debug: print '*****VIS Data Detected:', self.ID.Transport_ID
                            self.incrTotal += 1
                if e == self.idChange:
                    if e.signalparam.Destination == self.ID.Destination:
                        if self.sim.debug: print '*****VIS Transport ID change:', self.ID.Transport_ID, 'to', e.signalparam.Transport_ID
                        self.ID.Transport_ID = e.signalparam.Transport_ID
                if e == self.endEvent:
                    if e.signalparam.Destination == self.ID.Destination:
                        if e.signalparam.Transport_ID == self.ID.Transport_ID:
                            if self.sim.debug: print '*****VIS EOM Detected:', self.ID.Transport_ID
                            self.unfinished = False
                            if self.sim.vis_on:
                                self.vLink.node_spheres[self.origin].color = vp.color.green
                                self.vLink.node_spheres[self.ID.Destination].color = vp.color.green
                                i, j = self.order_index(self.origin,self.ID.Destination)
                                self.vLink.link_rods[i][j].color = vp.color.black
                                         
    def order_index(self,i,j):
        i2 = i
        j2 = j
        if j2>i2:
            i = j
            j = i2
        return i, j
    
class Visualisation(Process):
    def __init__(self, sim):
        Process.__init__(self, name='Vis', sim=sim)

        self.timer_list = []
        self.nodes = [n for n in self.sim.Net.nodes]
        
        self.M_LinkStartedEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Link_Started for x in self.nodes]
        self.S_LinkStartedEvents = [x.LinkContainer.ProcDict['msg_kernel'].S_Link_Started for x in self.nodes]

        self.M_LinkFailedEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Link_Failed for x in self.nodes]
        self.S_LinkFailedEvents = [x.LinkContainer.ProcDict['msg_kernel'].S_Link_Failed for x in self.nodes]

        self.M_LinkUpEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Link_Success for x in self.nodes]
        self.S_LinkUpEvents = [x.LinkContainer.ProcDict['msg_kernel'].S_Link_Success for x in self.nodes]
        
        self.M_LinkRetryEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Link_Retry for x in self.nodes]

        self.M_LinkEnd2 = [SimEvent(sim=sim, name='M_LinkEnd2') for e in range(self.sim.G.num_nodes)]
        self.M_DataRxRec2 = [SimEvent(sim=sim, name='M_DataRxRec2') for e in range(self.sim.G.num_nodes)]
        self.S_DataTxSent2 = [SimEvent(sim=sim, name='S_DataTxSent2') for e in range(self.sim.G.num_nodes)]
        self.S_LinkUp2 = [SimEvent(sim=sim, name='S_LinkUp2') for e in range(self.sim.G.num_nodes)]
        
        self.M_LinkEndedEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Link_Ended for x in self.nodes]
        self.S_LinkEndedEvents = [x.LinkContainer.ProcDict['msg_kernel'].S_Link_Ended for x in self.nodes]

        self.M_LBT_Success = [x.PhysicalContainer.ProcDict['msg_kernel'].LBT_Success for x in self.nodes]
        self.M_LBT_Fail = [x.PhysicalContainer.ProcDict['msg_kernel'].LBT_Fail for x in self.nodes]
        self.Tx_Success = [x.PhysicalContainer.ProcDict['msg_kernel'].Tx_Success for x in self.nodes]
        self.Tx_Fail = [x.PhysicalContainer.ProcDict['msg_kernel'].Tx_Fail for x in self.nodes]
        self.Rx_Success = [x.PhysicalContainer.ProcDict['msg_kernel'].Rx_Success for x in self.nodes]
        self.Rx_Fail = [x.PhysicalContainer.ProcDict['msg_kernel'].Rx_Fail for x in self.nodes]

        self.M_DataTxSentEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Data_Tx_Sent for x in self.nodes]
        self.M_DataTxFailEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Data_Tx_Fail for x in self.nodes]
        self.M_DataRxRecEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Data_Rx_Rec for x in self.nodes]
        self.M_DataRxFailEvents = [x.LinkContainer.ProcDict['msg_kernel'].M_Data_Rx_Fail for x in self.nodes]

        self.S_Scanning_Call_Success = [x.PhysicalContainer.ProcDict['msg_kernel'].scanning_call_ended for x in self.nodes]
        
        self.S_DataTxSentEvents = [x.LinkContainer.ProcDict['msg_kernel'].S_Data_Tx_Sent for x in self.nodes]
        self.S_DataTxFailEvents = [x.LinkContainer.ProcDict['msg_kernel'].S_Data_Tx_Fail for x in self.nodes]
        self.S_DataRxFailEvents = [x.LinkContainer.ProcDict['msg_kernel'].S_Data_Rx_Fail for x in self.nodes]
        
        self.M_TransportIDChangeEvents = [x.TransportContainer.ProcDict['msg_kernel'].M_End_Of_Block for x in self.nodes]
        self.S_TransportIDChangeEvents = [x.TransportContainer.ProcDict['msg_kernel'].S_End_Of_Block for x in self.nodes]

        self.m_link_timer_list = [[] for i in range(self.sim.G.num_nodes)]
        self.s_link_timer_list = [[] for i in range(self.sim.G.num_nodes)]
        
        #index is node first, then frequency:
        self.node_spheres_freq = [[] for i in range(self.sim.G.num_nodes)]
        self.node_squares_freq = [[] for i in range(self.sim.G.num_nodes)]
        self.text_IDs = []
        self.link_rods = [[] for i in range(self.sim.G.num_nodes)]
    def execute(self):
        if self.sim.vis_on:
            origin_x = -5
            origin_y = 6
            dx = origin_x
            dy = origin_y
            grid_size = 1.0 #length and width of grid
            sphere_r = 1.0 #radius of spheres that appears inside grid
            r_text = 1.2 #radius of circle text ID numbers are in
        
            for n in range(self.sim.G.num_nodes+1):
                rod_1 = vp.cylinder(pos=(vp.vector(dx,origin_y,0)),axis=(vp.vector(0,-1*self.sim.G.num_freq,0)), radius=0.05, color=vp.color.white)
                #s_1 = vp.sphere(pos=(vp.vector(dx-0.5,origin_y-0.5,0)),radius=0.5, color=vp.color.green)
                #rod_2 = vp.cylinder(pos=(vp.vector(dx,-1*(G.num_freq+1) + origin_y,0)),axis=(vp.vector(0,-1*G.num_freq,0)), radius=0.05, color=vp.color.white)
                #s_2 = vp.sphere(pos=(vp.vector(dx-0.5-1*(G.num_cfreq+1) + origin_y-0.5,0)),radius=0.5, color=vp.color.green)                
                dx = dx + grid_size           
            dx = origin_x
            for m in range(self.sim.G.num_freq+1):
                rod_1 = vp.cylinder(pos=(vp.vector(origin_x,dy,0)),axis=(vp.vector(self.sim.G.num_nodes,0,0)), radius=0.05, color=vp.color.white)
                dy = dy - grid_size

            dx = origin_x
            dy = origin_y
            
            for i in range(self.sim.G.num_nodes):
                for j in range(self.sim.G.num_freq):
                    s_1 = vp.sphere(pos=(vp.vector(dx+0.5,dy-0.5,0)),radius=0.3, color=vp.color.black)
                    sq_1 = vp.box(pos=(vp.vector(dx+0.5,dy-0.5,-0.1)), length=0.9, height = 0.9, width = 0.1, color=vp.color.black)
                    dy = dy - grid_size
                    self.node_spheres_freq[i].append(s_1)
                    self.node_squares_freq[i].append(sq_1)
                dy = origin_y
                dx = dx + 1
                
            text_nodes = vp.text(text='nodes',pos=(vp.vector(origin_x+math.floor((self.sim.G.num_nodes*grid_size)/2),dy+0.2,0)),align='center',size=0.2) 
            text_freq = vp.text(text='frequencies',pos=(vp.vector(origin_x-1.2,0,0)),size=0.2,axis=(vp.vector(1,0,0)))    
            #origin_y+math.floor((G.num_freq*grid_size)/2)
        
        while True:
            yield waitevent, self, self.M_LinkStartedEvents + \
                  self.S_LinkStartedEvents + \
                  self.M_LinkFailedEvents + \
                  self.S_LinkFailedEvents + \
                  self.M_LinkRetryEvents + \
                  self.M_LinkUpEvents + \
                  self.M_LBT_Success + \
                  self.M_LBT_Fail + \
                  self.Tx_Success + \
                  self.Tx_Fail + \
                  self.Rx_Success + \
                  self.Rx_Fail + \
                  self.M_DataTxSentEvents + \
                  self.M_DataTxFailEvents + \
                  self.M_DataRxFailEvents + \
                  self.S_Scanning_Call_Success + \
                  self.S_LinkEndedEvents + \
                  self.S_DataTxFailEvents + \
                  self.S_DataRxFailEvents + \
                  self.S_DataTxSentEvents + \
                  self.M_TransportIDChangeEvents + \
                  self.S_TransportIDChangeEvents + \
                  self.M_LinkEnd2 + \
                  self.M_DataRxRec2 + \
                  self.S_DataTxSent2 + \
                  self.S_LinkUp2
                  
                  #self.M_LinkEndedEvents + \
                  #self.M_DataRxRecEvents + \
                  #self.S_LinkUpEvents + \
                  
            for e in self.eventsFired:
                if e.name == 'M_Link_Started':
                    for i,x in enumerate(self.M_LinkStartedEvents):
                        if x==e:
                            if self.sim.debug: print 'Node', i, ': M_Link_started', self.eventsFired[0].signalparam, self.sim.now()
                            LT = MLinkTimer(self.sim, self, self.eventsFired[0].signalparam, i, [(self.M_LinkUpEvents[i], self.sim.Monitors[i].m_link_latency),(self.M_LinkFailedEvents[i], self.sim.Monitors[i].m_link_fail_time)])
                            self.sim.activate(LT,LT.execute())
                            self.m_link_timer_list[i].append(LT)
                            
                elif e.name == 'S_Link_Started':
                    for i,x in enumerate(self.S_LinkStartedEvents):
                        if x==e:
                            if self.sim.debug: print 'Node', i, ': S_Link_started', self.eventsFired[0].signalparam, self.sim.now()
                            LT = SLinkTimer(self.sim, self, self.eventsFired[0].signalparam, i, [(self.S_LinkUpEvents[i], self.sim.Monitors[i].s_link_latency),(self.S_LinkFailedEvents[i], self.sim.Monitors[i].s_link_fail_time)])
                            self.sim.activate(LT,LT.execute())
                            self.s_link_timer_list[i].append(LT)
                elif e.name == 'M_Link_Failed':
                    for i,x in enumerate(self.M_LinkFailedEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': M_Link_Failed', ID.all_IDs(), self.sim.now()
                            self.sim.Monitors[i].num_m_links_failed += 1
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.M_Link_Fail.signal(ID)
                elif e.name == 'S_Link_Failed':
                    for i,x in enumerate(self.S_LinkFailedEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': S_Link_Failed', ID.all_IDs(), self.sim.now()
                            self.sim.Monitors[i].num_s_links_failed += 1
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.S_Link_Fail.signal(ID)
                elif e.name == 'M_Link_Retry':
                    for i,x in enumerate(self.M_LinkRetryEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': M_Link_Retry', ID.all_IDs(), self.sim.now()
                            self.sim.Monitors[i].num_m_links_failed += 1
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.M_Link_Retry.signal(ID)
                elif e.name == 'M_Link_Success':
                    for i,x in enumerate(self.M_LinkUpEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': M_Link_Up', ID.all_IDs(), self.sim.now()
                            self.sim.Monitors[i].num_m_links_up += 1
                            #T = DataTimer(self.sim, self, self.eventsFired[0].signalparam, i, [(self.M_LinkEndedEvents[self.eventsFired[0].signalparam.Destination], self.sim.Monitor.m_data_length),(self.M_DataFailedEvents[i], self.sim.Monitor.m_data_fail_length)], self.M_DataSentEvents[i])
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.M_Link_Success.signal(ID)    
                elif e.name == 'S_Link_Success':
                    for i,x in enumerate(self.S_LinkUpEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            print 'Node', i, ': S_Link_Up', ID.all_IDs(), self.sim.now()
                            self.sim.Monitors[i].num_s_links_up += 1
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.S_Link_Success.signal(ID)
####################### New events
                elif e.name == 'scanning_call_ended':
                    for i,x in enumerate(self.S_Scanning_Call_Success):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': S_Scanning_Call_Success', ID.all_IDs(), self.sim.now()
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.scanning_call_ended.signal(ID)
                elif e.name == 'LBT_Success':
                    for i,x in enumerate(self.M_LBT_Success):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': M_LBT_Success', ID.all_IDs(), self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.LBT_Success.signal(ID)
                elif e.name == 'LBT_Fail':
                    for i,x in enumerate(self.M_LBT_Fail):
                        if x==e:
                            ID = self.eventsFired[0].signalparam[1]
                            if self.sim.debug: print 'Node', i, ': M_LBT_Fail', ID.all_IDs(), self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.LBT_Fail.signal(ID)
                                    
                elif e.name == 'Tx_Success':
                    for i,x in enumerate(self.Tx_Success):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': Tx_Success', ID.all_IDs(), self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    if self.sim.debug: print 'MASTER, fired?'
                                    if len(link_timer.Tx_Success.waits)>0:
                                        if self.sim.debug: print 'YES'
                                        link_timer.Tx_Success.signal(ID)
                                    else: 
                                        if self.sim.debug: print 'no'
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    if self.sim.debug: print 'SLAVE, fired?'
                                    if len(link_timer.Tx_Success.waits)>0:
                                        if self.sim.debug: print 'YES'
                                        link_timer.Tx_Success.signal(ID)
                                    else: 
                                        if self.sim.debug: print 'no'
                elif e.name == 'Tx_Fail':
                    for i,x in enumerate(self.Tx_Fail):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': Tx_Fail', ID.all_IDs(), self.sim.now()
                            #for link_timer in self.m_link_timer_list[i]:
                            #    if link_timer.Link_ID == ID.Link_ID:
                            #        link_timer.Tx_Fail.signal(ID)
                            
                elif e.name == 'Rx_Success':
                    for i,x in enumerate(self.Rx_Success):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': Rx_Success', ID.all_IDs(), self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    if self.sim.debug: print 'MASTER, fired?'
                                    if len(link_timer.Rx_Success.waits)>0:
                                        if self.sim.debug: print 'YES'
                                        link_timer.Rx_Success.signal(ID)
                                    else: 
                                        if self.sim.debug: print 'no'
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    if self.sim.debug: print 'SLAVE'
                                    if len(link_timer.Rx_Success.waits)>0:
                                        if self.sim.debug: print 'YES'
                                        link_timer.Rx_Success.signal(ID)
                                    else: 
                                        if self.sim.debug: print 'no'
                elif e.name == 'Rx_Fail':
                    for i,x in enumerate(self.Rx_Fail):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': Rx_Fail', ID.all_IDs(), self.sim.now()
                            #for link_timer in self.m_link_timer_list[i]:
                            #    if link_timer.Link_ID == ID.Link_ID:
                            #        link_timer.Tx_Fail.signal(ID)
                                    
                elif e.name == 'M_Data_Tx_Sent':
                    for i,x in enumerate(self.M_DataTxSentEvents):
                        if x==e:
                            signal_ID = self.eventsFired[0].signalparam[0]
                            signal = self.eventsFired[0].signalparam[1]
                            if self.sim.debug: print 'Node', i, ': M_Data_Tx_Sent', signal_ID.all_IDs(), 'data_size:', signal.transport.data, 'data_rate:', signal.network.data_rate, self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == signal_ID.Link_ID and link_timer.unfinished:
                                    link_timer.dataSent += signal.transport.data
                            
#                            for timer in self.m_link_timer_list[i]:
#                                timer.incrEvent.signal(x.signalparam)
                elif e.name == 'M_Data_Tx_Fail':
                    for i,x in enumerate(self.M_DataTxFailEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': M_Data_Tx_Fail', self.eventsFired[0].signalparam, self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.M_Link_Ended.signal(ID) #at present this is what is going on.
#                elif e.name == 'M_Data_Rx_Rec':
#                    for i,x in enumerate(self.M_DataRxRecEvents):
#                        if x==e:
#                            print 'Node', i, ': M_Data_Rx_Rec', self.eventsFired[0].signalparam.all_IDs(), self.sim.now()
#                            for link_timer in self.m_link_timer_list[i]:
#                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
#                                    link_timer.dataSent += 1
                elif e.name == 'M_Data_Rx_Fail':
                    for i,x in enumerate(self.M_DataRxFailEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': M_Data_Rx_Fail', self.eventsFired[0].signalparam, self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.M_Link_Ended.signal(ID) #at present this is what is going on.
##############
#                elif e.name == 'M_Link_Ended':
#                    for i,x in enumerate(self.M_LinkEndedEvents):
#                        if x==e:
#                            ID = self.eventsFired[0].signalparam
#                            print 'Node', i, ': M_Link_Ended', ID.all_IDs(), self.sim.now()
#                            for link_timer in self.m_link_timer_list[i]:
#                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
#                                    link_timer.M_Link_Ended.signal(ID)
                elif e.name == 'S_Link_Ended':
                    for i,x in enumerate(self.S_LinkEndedEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': S_Link_Ended', self.eventsFired[0].signalparam.all_IDs(), self.sim.now()
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.S_Link_Ended.signal(ID)
                elif e.name == 'S_Data_Tx_Sent':
                    for i,x in enumerate(self.S_DataTxSentEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': S_Data_Tx_Sent', self.eventsFired[0].signalparam.all_IDs(), self.sim.now()
#                            for link_timer in self.s_link_timer_list[i]:
#                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
#                                    link_timer.dataRec += 1
                elif e.name == 'S_Data_Rx_Fail':
                    for i,x in enumerate(self.S_DataRxFailEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': S_Data_Rx_Fail', self.eventsFired[0].signalparam.all_IDs(), self.sim.now()
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.S_Link_Ended.signal(ID)
                elif e.name == 'S_Data_Tx_Fail':
                    for i,x in enumerate(self.S_DataTxFailEvents):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': S_Data_Tx_Fail', self.eventsFired[0].signalparam.all_IDs(), self.sim.now()
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.S_Link_Ended.signal(ID)
#############
                elif e.name == 'M_End_Of_Block':
                    for i,x in enumerate(self.M_TransportIDChangeEvents):
                        if x==e:
                            if self.sim.debug: print 'Node', i, ': M_End_Of_Block', self.eventsFired[0].signalparam, self.sim.now()
#                            for timer in self.M_node_timers[i]:
#                                timer.idChange.signal(x.signalparam)
                elif e.name == 'S_End_Of_Block':
                    for i,x in enumerate(self.S_TransportIDChangeEvents):
                        if x==e:
                            if self.sim.debug: print 'Node', i, ': S_End_Of_Block', self.eventsFired[0].signalparam, self.sim.now()
#                            for timer in self.S_node_timers[i]:
#                                timer.idChange.signal(x.signalparam)
                elif e.name == 'M_LinkEnd2':
                    for i,x in enumerate(self.M_LinkEnd2):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': M_Link_Ended2', ID.all_IDs(), self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.M_Link_Ended.signal(ID)
                                    if self.sim.debug: print 'fired:', link_timer.Link_ID
                elif e.name == 'M_DataRxRec2':
                    for i,x in enumerate(self.M_DataRxRec2):
                        if x==e:
                            ID = self.eventsFired[0].signalparam[0]
                            if self.sim.debug: print 'Node', i, ': M_Data_Rx_Rec2', self.eventsFired[0].signalparam[0].all_IDs(), self.sim.now()
                            for link_timer in self.m_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.dataSent += self.eventsFired[0].signalparam[1]
                elif e.name == 'S_DataTxSent2':
                    for i,x in enumerate(self.S_DataTxSent2):
                        if x==e:
                            ID = self.eventsFired[0].signalparam[0]
                            if self.sim.debug: print 'Node', i, ': S_Data_Tx_Sent2', self.eventsFired[0].signalparam[0].all_IDs(), self.sim.now()
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.dataRec += self.eventsFired[0].signalparam[1]
                elif e.name == 'S_LinkUp2':
                    for i,x in enumerate(self.S_LinkUp2):
                        if x==e:
                            ID = self.eventsFired[0].signalparam
                            if self.sim.debug: print 'Node', i, ': S_Link_Up2', ID.all_IDs(), self.sim.now()
                            self.sim.Monitors[i].num_s_links_up += 1
                            for link_timer in self.s_link_timer_list[i]:
                                if link_timer.Link_ID == ID.Link_ID and link_timer.unfinished:
                                    link_timer.S_Link_Success.signal(ID)

    def order_index(self,i,j):
        i2 = i
        j2 = j
        if j2>i2:
            i = j
            j = i2
        return i, j

#    def results(self):
#        print '------------------------------------'
#        print 'NUM M LINKS MADE:', self.sim.Monitor.num_m_links_up
#        print 'NUM S LINKS MADE:', self.sim.Monitor.num_s_links_up
#        print 'NUM M LINKS FAILED:', self.sim.Monitor.num_m_links_failed
#        print 'NUM S LINKS FAILED:', self.sim.Monitor.num_s_links_failed
#        print '--'
#        #print 'M LINK LAT', self.sim.Monitor.m_link_latency, '[len]', len(self.sim.Monitor.m_link_latency)
#        #print 'S LINK LAT', self.sim.Monitor.s_link_latency, '[len]', len(self.sim.Monitor.s_link_latency)
#        print '--'
#        m_link_lat_ave = sum(self.sim.Monitor.m_link_latency)/float(len(self.sim.Monitor.m_link_latency))
#        s_link_lat_ave = sum(self.sim.Monitor.s_link_latency)/float(len(self.sim.Monitor.s_link_latency))
#        m_link_lat_std = np.std(self.sim.Monitor.m_link_latency)
#        s_link_lat_std = np.std(self.sim.Monitor.s_link_latency)
#        print 'M LINK LAT (ave):', m_link_lat_ave, '(std dev)', m_link_lat_std 
#        print 'S LINK LAT (ave):', s_link_lat_ave, '(std dev)', s_link_lat_std
#        print '--'
#        #print 'M BUSY TIMES', self.sim.Monitor.m_total_time, '[len]', len(self.sim.Monitor.m_total_time)
#        #print 'S BUSY TIMES', self.sim.Monitor.s_total_time, '[len]', len(self.sim.Monitor.s_total_time)
#        print '--'
#        m_busy_time_ave = sum(self.sim.Monitor.m_total_time)/float(len(self.sim.Monitor.m_total_time))
#        m_busy_time_std = np.std(self.sim.Monitor.m_total_time)
#        s_busy_time_ave = sum(self.sim.Monitor.s_total_time)/float(len(self.sim.Monitor.s_total_time))
#        s_busy_time_std = np.std(self.sim.Monitor.s_total_time)
#        print 'M BUSY TIME (ave)', m_busy_time_ave, '(std dev)', m_busy_time_std 
#        print 'S BUSY TIME (ave):', s_busy_time_ave, '(std dev)', s_busy_time_std 
#        print '--'
##        print 'M LINK FAIL T', self.sim.Monitor.m_link_fail_time, 'len', len(self.sim.Monitor.m_link_fail_time)
##        print 'S LINK FAIL T', self.sim.Monitor.s_link_fail_time, 'len', len(self.sim.Monitor.s_link_fail_time)
##        print '--'
#        #print 'M DATA LENGTH:', self.sim.Monitor.m_data_length
#        #print 'S DATA LENGTH:', self.sim.Monitor.s_data_length
#        print '--'
#        m_data_length_total = np.sum(self.sim.Monitor.m_data_length)
#        s_data_length_total = np.sum(self.sim.Monitor.s_data_length)
#        print 'M DATA LENGTH TOTAL:', m_data_length_total
#        print 'S DATA LENGTH TOTAL:', s_data_length_total
#        print '--'
#        m_t_per_data = [self.sim.Monitor.m_total_time[i]/self.sim.Monitor.m_data_length[i] for i in range(len(self.sim.Monitor.m_total_time)) if self.sim.Monitor.m_data_length[i] > 0]
#        m_ave_t_per_data = sum([self.sim.Monitor.m_total_time[i]/self.sim.Monitor.m_data_length[i] for i in range(len(self.sim.Monitor.m_total_time)) if self.sim.Monitor.m_data_length[i] > 0])/float(len(self.sim.Monitor.m_total_time))
#        s_t_per_data = [self.sim.Monitor.s_total_time[i]/self.sim.Monitor.s_data_length[i] for i in range(len(self.sim.Monitor.s_total_time)) if self.sim.Monitor.s_data_length[i] > 0]
#        s_ave_t_per_data = sum([self.sim.Monitor.s_total_time[i]/self.sim.Monitor.s_data_length[i] for i in range(len(self.sim.Monitor.s_total_time)) if self.sim.Monitor.s_data_length[i] > 0])/float(len(self.sim.Monitor.s_total_time))
#        #print 'M TIME PER DATA LENGTH:', m_t_per_data, 'ave:', m_ave_t_per_data
#        #print 'S TIME PER DATA LENGTH:', s_t_per_data, 'ave:', s_ave_t_per_data
#        print '--'
#        #print 'M DATA TIME:', self.sim.Monitor.m_data_time, '[len]', len(self.sim.Monitor.m_data_time)
#        #print 'S DATA TIME:', self.sim.Monitor.s_data_time, '[len]', len(self.sim.Monitor.s_data_time)
#        print '--'
#        m_data_time_ave = sum(self.sim.Monitor.m_data_time)/float(len(self.sim.Monitor.m_data_time))
#        m_data_time_std = np.std(self.sim.Monitor.m_data_time)
#        s_data_time_ave = sum(self.sim.Monitor.s_data_time)/float(len(self.sim.Monitor.s_data_time))
#        s_data_time_std = np.std(self.sim.Monitor.s_data_time)
#        print 'M DATA TIME (ave)', m_data_time_ave, '(std dev)', m_data_time_std  
#        print 'S DATA TIME (ave):', s_data_time_ave, '(std dev)', s_data_time_std  
#        print '--'
#        #print 'M TIME PER DATA LENGTH:', [self.sim.Monitor.m_data_time[i]/self.sim.Monitor.m_data_length[i] for i in range(len(self.sim.Monitor.m_data_time)) if self.sim.Monitor.m_data_length[i] > 0], 'ave:', sum([self.sim.Monitor.m_data_time[i]/self.sim.Monitor.m_data_length[i] for i in range(len(self.sim.Monitor.m_data_time)) if self.sim.Monitor.m_data_length[i] > 0])/float(len(self.sim.Monitor.m_data_time))
#        #print 'S TIME PER DATA LENGTH:', [self.sim.Monitor.s_data_time[i]/self.sim.Monitor.s_data_length[i] for i in range(len(self.sim.Monitor.s_data_time)) if self.sim.Monitor.s_data_length[i] > 0], 'ave:', sum([self.sim.Monitor.s_data_time[i]/self.sim.Monitor.s_data_length[i] for i in range(len(self.sim.Monitor.s_data_time)) if self.sim.Monitor.s_data_length[i] > 0])/float(len(self.sim.Monitor.s_data_time))
#        print '--'
#        
#        return (self.sim.Monitor.num_s_links_up,self.sim.Monitor.num_m_links_up,self.sim.Monitor.num_s_links_failed,self.sim.Monitor.num_m_links_failed,m_link_lat_ave,s_link_lat_ave,m_link_lat_std,s_link_lat_std,m_busy_time_ave,m_busy_time_std,s_busy_time_ave,s_busy_time_std,m_ave_t_per_data,s_ave_t_per_data,m_data_time_ave,m_data_time_std,s_data_time_ave,s_data_time_std,m_data_length_total,s_data_length_total)

    def results(self):
        for n_i in range(self.sim.G.num_nodes):
            print ''
            print 'NODE', n_i
            print '------------------------------------'
            print 'NUM M LINKS MADE:', self.sim.Monitors[n_i].num_m_links_up
            print 'NUM S LINKS MADE:', self.sim.Monitors[n_i].num_s_links_up
            print 'NUM M LINKS FAILED:', self.sim.Monitors[n_i].num_m_links_failed
            print 'NUM S LINKS FAILED:', self.sim.Monitors[n_i].num_s_links_failed
            print '--'
        return [(self.sim.Monitors[n_i].num_s_links_up,self.sim.Monitors[n_i].num_m_links_up,self.sim.Monitors[n_i].num_s_links_failed,self.sim.Monitors[n_i].num_m_links_failed,self.sim.Monitors[n_i].m_link_latency,self.sim.Monitors[n_i].s_link_latency,self.sim.Monitors[n_i].m_data_length,self.sim.Monitors[n_i].s_data_length,self.sim.Monitors[n_i].m_data_time,self.sim.Monitors[n_i].s_data_time,self.sim.Monitors[n_i].m_total_time,self.sim.Monitors[n_i].s_total_time, self.sim.Monitors[n_i].m_throughput, self.sim.Monitors[n_i].s_throughput) for n_i in range(self.sim.G.num_nodes)]
