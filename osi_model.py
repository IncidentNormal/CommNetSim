#from SimPy.Simulation import *
from SimPy.SimulationRT import *
from enums import *
import physical_2, link_2, network_2, transport_2, session, presentation, application, environment_2
import visualisation_2
import GlobalVars
import random, os, datetime

class Network(): #Not to be confused with 'network' or 'NetworkContainer', that both refer to the Network OSI Layer
    def __init__(self, sim):
        self.sim = sim
        self.nodes = []
        self.frequencies = []
        self.env_mod = environment_2
    def populate(self):
        self.env_container = EnvironmentContainer(self.env_mod, self.sim)
        self.sim.activate(self.env_container, self.env_container.execute(), at=0.0)
        
        for i in range(self.sim.nrNodes):
            node = NodeContainer(ID=i, sim=self.sim, env_container=self.env_container)
            self.nodes.append(node)
            self.nodes[i].activate()
        for i in range(self.sim.nrFreq):
            self.frequencies.append([])

        self.env_container.activate()
            
class EnvironmentContainer(Process):
    def __init__(self, env_module, sim):
        Process.__init__(self, name='EnvironmentContainer', sim=sim)

        self.mod_classes = env_module.getClasses() #Module reference
        self.Processes = [proc(sim, self) for proc in self.mod_classes] #Instance of Process (from module)
        self.ProcDict = dict([(x.name, x) for x in self.Processes])
        self.physicalQ = SimEvent(sim=sim)
        
        self.frequencies = [[] for i in range(G.num_freq)]
        #SNR_matrix: [origin][dest][channel]
        #self.SNR_matrix = [[[0 for k in range(G.num_freq)] for j in range(G.num_nodes)] for i in range(G.num_nodes)] #so there is an SNR score for each channel between all nodes.
        self.SNR_matrix = env_module.Gridder()

        self.channelTaken = [SimEvent(name='taken'+str(i), sim=sim) for i in range(G.num_freq)] #List of events (one for each channel), fired when a packet is put on the channel
        self.channelFree = [SimEvent(name='free'+str(i), sim=sim) for i in range(G.num_freq)] #List of events (one for each channel), fired when a packet is taken off the channel
        
        self._phyEvents = [proc for proc in env_module.getEvents(self)]
        
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0)
        self.phyEvents = []
        for i in range(G.num_nodes):
            self.phyEvents += self.sim.Net.nodes[i].PhysicalContainer._envEvents
    def execute(self):
        while True:
            yield waitevent, self, self.physicalQ
            if self.sim.debug: print 'ENVIRONMENT packet received from physical Q', self.sim.now()
            rec_packet = self.physicalQ.signalparam
            if rec_packet.internal_last_location == Layer.PHYSICAL:
                if self.sim.debug: print 'EnvironmentContainer received packet from a Physical layer, origin:', rec_packet.link.origin
                #print self.Processes[0]
                yield put, self, self.Processes[0].inQ, [rec_packet]
            elif rec_packet.internal_last_location == Layer.ENVIRONMENT:
                for node in Network.nodes:
                    node.PhysicalContainer.envQ.signal(rec_packet)

class PhysicalContainer(Process):
    def __init__(self, ID, phy_module, sim, env_container):
        Process.__init__(self, name='PhysicalContainer'+str(ID), sim=sim)
        self.ID = ID
        self.mod_classes = phy_module.getClasses() #Module reference
        self.Processes = [proc(self.ID, sim, self) for proc in self.mod_classes] #Instance of Process (from module)
        self.ProcDict = dict([(x.name, x) for x in self.Processes])
        self.env_cont = env_container

        self.linkQ = SimEvent(sim=sim)
        self.envQ = SimEvent(sim=sim)
        
        self._linkEvents = [proc for proc in phy_module.getLinkEvents(self)]
        self._envEvents = [proc for proc in phy_module.getEnvEvents(self)]
        #self.EventDict = dict([x.name, x) for x in self.Events])
        
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0)
        self.Node = [i for i in self.sim.Net.nodes if i.ID==self.ID][0]
        self.linkEvents = self.Node.LinkContainer._phyEvents
        self.envEvents = self.Node.EnvironmentContainer._phyEvents
    def execute(self):
        while True:
            yield waitevent, self, [self.linkQ, self.envQ]
            if self.eventsFired[0] == self.linkQ:
                if self.sim.debug: print self.ID, 'PHYSICAL packet recd @ linkQ, sending to Link or Physical...', self.sim.now()
                rec_packet = self.linkQ.signalparam
                if self.sim.debug: print self.ID, 'phy last_int_location:', rec_packet.internal_last_location, self.sim.now()
                if rec_packet.internal_last_location == Layer.LINK:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.PHYSICAL:
                    self.Node.LinkContainer.physicalQ.signal(rec_packet)
            elif self.eventsFired[0] == self.envQ:
                #if self.sim.debug: print self.ID, 'PHYSICAL packet received from env Q', self.sim.now()
                rec_packet = self.envQ.signalparam
                if rec_packet.internal_last_location == Layer.PHYSICAL:
                    self.Node.EnvironmentContainer.physicalQ.signal(rec_packet)
                elif rec_packet.internal_last_location == Layer.ENVIRONMENT:
                    yield put, self, self.Processes[0].inQ, [rec_packet]

class LinkContainer(Process):
    def __init__(self, ID, link_module, sim):
        Process.__init__(self, name='LinkContainer'+str(ID), sim=sim)
        self.ID = ID
        #self.sim = sim #Don't need this anymore now this is itself a Process
        self.mod_classes = link_module.getClasses() #Module reference
        self.Processes = [proc(self.ID, sim, self) for proc in self.mod_classes] #Instances of Processes for activation
        self.ProcDict = dict([(x.name, x) for x in self.Processes])

        self.physicalQ = SimEvent(sim=sim)
        self.networkQ = SimEvent(sim=sim)

        self._netEvents = [proc for proc in link_module.getNetEvents(self)]
        self._phyEvents = [proc for proc in link_module.getPhyEvents(self)]
        #self.EventDict = dict([x.name, x) for x in self.Events])
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0) #activate all processes
        self.Node = [i for i in self.sim.Net.nodes if i.ID==self.ID][0] #Optional reference to the overall NodeContainer
        self.Nodes = self.sim.Net.nodes #HMMMMM... Shouldn't need this anymore, after the advent of this:
        self.phyEvents = self.Node.PhysicalContainer._linkEvents
        self.netEvents = self.Node.NetworkContainer._linkEvents
    def execute(self):
        while True:
            yield waitevent, self, [self.physicalQ, self.networkQ]
            if self.eventsFired[0] == self.physicalQ:
                #if self.sim.debug: print self.ID, 'LINK packet received from physical Q', self.sim.now()
                rec_packet = self.physicalQ.signalparam
                #print self.ID, 'linkContainer: last_int_location:', rec_packet.internal_last_location, self.sim.now()
                if rec_packet.internal_last_location == Layer.PHYSICAL:
                    #print self.ID, 'LinkContainer: passing to module...', self.sim.now()
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.LINK:
                    self.Node.PhysicalContainer.linkQ.signal(rec_packet)
            if self.eventsFired[0] == self.networkQ:
                #if self.sim.debug: print self.ID, 'LINK packet received from network Q', self.sim.now()
                rec_packets = self.networkQ.signalparam
                if rec_packets[0].internal_last_location == Layer.NETWORK:
                    yield put, self, self.Processes[0].inQ, rec_packets
                elif rec_packets[0].internal_last_location == Layer.LINK:
                    self.Node.NetworkContainer.linkQ.signal(rec_packets)

class NetworkContainer(Process):
    def __init__(self, ID, net_module, sim):
        Process.__init__(self, name='NetworkContainer'+str(ID), sim=sim)
        self.ID = ID
        #self.sim = sim
        self.mod_classes = net_module.getClasses() #Module reference
        self.Processes = [proc(self.ID, sim, self) for proc in self.mod_classes] #Instances of Processes for activation
        self.ProcDict = dict([(x.name, x) for x in self.Processes])
        self.linkQ = SimEvent(sim=sim)
        self.transportQ = SimEvent(sim=sim)

        self._linkEvents = [proc for proc in net_module.getLinkEvents(self)]
        self._transportEvents = [proc for proc in net_module.getTransportEvents(self)]
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0) #activate all processes
        self.Node = [i for i in self.sim.Net.nodes if i.ID==self.ID][0]
        self.linkEvents = self.Node.LinkContainer._netEvents
        self.transportEvents = self.Node.TransportContainer._netEvents
    def execute(self):
        while True:
            yield waitevent, self, [self.linkQ, self.transportQ]
            if  self.eventsFired[0] == self.linkQ:
                #if self.sim.debug: print self.ID, 'NETWORK packet received from link Q', self.sim.now()
                rec_packets = self.linkQ.signalparam
                if rec_packets[0].internal_last_location == Layer.LINK:
                    yield put, self, self.Processes[0].inQ, rec_packets
                elif rec_packets[0].internal_last_location == Layer.NETWORK:
                    self.Node.LinkContainer.networkQ.signal(rec_packets)
            if self.eventsFired[0] == self.transportQ:
                #if self.sim.debug: print self.ID, 'NETWORK packet received from transport Q', self.sim.now()
                rec_packet = self.transportQ.signalparam
                if rec_packet.internal_last_location == Layer.TRANSPORT:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.NETWORK:
                    self.Node.TransportContainer.networkQ.signal(rec_packet)

class TransportContainer(Process):
    def __init__(self, ID, transp_module, sim):
        Process.__init__(self, name='TransportContainer'+str(ID), sim=sim)
        self.ID = ID
        #self.sim = sim
        self.mod_classes = transp_module.getClasses() #Module reference
        self.Processes = [proc(self.ID, sim, self) for proc in self.mod_classes] #Instances of Processes for activation
        self.ProcDict = dict([(x.name, x) for x in self.Processes])
        self.networkQ = SimEvent(sim=sim)
        self.sessionQ = SimEvent(sim=sim)

        self._netEvents = [proc for proc in transp_module.getNetEvents(self)]
        self._sessEvents = [proc for proc in transp_module.getSessEvents(self)]
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0) #activate all processes
        self.Node = [i for i in self.sim.Net.nodes if i.ID==self.ID][0]
        self.netEvents = self.Node.NetworkContainer._transportEvents
        self.sessEvents = self.Node.SessionContainer._transportEvents
    def execute(self):
        while True:
            yield waitevent, self, [self.networkQ, self.sessionQ]
            if self.eventsFired[0] == self.networkQ:
                #if self.sim.debug: print self.ID, 'TRANSPORT packet received from network Q', self.sim.now()
                rec_packet = self.networkQ.signalparam
                if rec_packet.internal_last_location == Layer.NETWORK:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.TRANSPORT:
                    self.Node.NetworkContainer.transportQ.signal(rec_packet)
            if self.eventsFired[0] == self.sessionQ:
                #if self.sim.debug: print self.ID, 'TRANSPORT packet received from session Q', self.sim.now()
                rec_packet = self.sessionQ.signalparam
                if rec_packet.internal_last_location == Layer.SESSION:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.TRANSPORT:
                    self.Node.SessionContainer.transportQ.signal(rec_packet)
        
class SessionContainer(Process):
    def __init__(self, ID, sess_module, sim):
        Process.__init__(self, name='SessionContainer'+str(ID), sim=sim)
        self.ID = ID
        #self.sim = sim
        self.mod_classes = sess_module.getClasses() #Module reference
        self.Processes = [proc(self.ID, sim, self) for proc in self.mod_classes] #Instances of Processes for activation
        self.ProcDict = dict([(x.name, x) for x in self.Processes])
        self.transportQ = SimEvent(sim=sim)
        self.presentationQ = SimEvent(sim=sim)

        self._transportEvents = []
        self._appEvents = []
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0) #activate all processes
        self.Node = [i for i in self.sim.Net.nodes if i.ID==self.ID][0]
    def execute(self):
        while True:
            yield waitevent, self, [self.transportQ, self.presentationQ]
            if self.eventsFired[0] == self.transportQ:
                #if self.sim.debug: print self.ID, 'SESSION packet received from transport Q', self.sim.now()
                rec_packet = self.transportQ.signalparam
                if rec_packet.internal_last_location == Layer.TRANSPORT:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.SESSION:
                    self.Node.TransportContainer.sessionQ.signal(rec_packet)
            if self.eventsFired[0] == self.presentationQ:
                #if self.sim.debug: print self.ID, 'SESSION packet received from presentation Q', self.sim.now()
                rec_packet = self.presentationQ.signalparam
                if rec_packet.internal_last_location == Layer.PRESENTATION:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.SESSION:
                    self.Node.PresentationContainer.sessionQ.signal(rec_packet)
        
class PresentationContainer(Process):
    def __init__(self, ID, pres_module, sim):
        Process.__init__(self, name='PresentationContainer'+str(ID), sim=sim)
        self.ID = ID
        #self.sim = sim
        self.mod_classes = pres_module.getClasses() #Module reference
        self.Processes = [proc(self.ID, sim, self) for proc in self.mod_classes] #Instances of Processes for activation
        self.ProcDict = dict([(x.name, x) for x in self.Processes])
        self.sessionQ = SimEvent(sim=sim)
        self.applicationQ = SimEvent(sim=sim)
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0) #activate all processes
        self.Node = [i for i in self.sim.Net.nodes if i.ID==self.ID][0]
    def execute(self):
        while True:
            yield waitevent, self, [self.sessionQ, self.applicationQ]
            if self.eventsFired[0] == self.sessionQ:
                #if self.sim.debug: print self.ID, 'PRESENTATION packet received from session Q', self.sim.now()
                rec_packet = self.sessionQ.signalparam
                if rec_packet.internal_last_location == Layer.SESSION:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.PRESENTATION:
                    self.Node.SessionContainer.presentationQ.signal(rec_packet)
            if self.eventsFired[0] == self.applicationQ:
                #if self.sim.debug: print self.ID, 'PRESENTATION packet received from application Q', self.sim.now()
                rec_packet = self.applicationQ.signalparam
                if rec_packet.internal_last_location == Layer.APPLICATION:
                    yield put, self, self.Processes[0].inQ, [rec_packet]
                elif rec_packet.internal_last_location == Layer.PRESENTATION:
                    self.Node.ApplicationContainer.presentationQ.signal(rec_packet)
        
class ApplicationContainer(Process):
    def __init__(self, ID, app_module, sim):
        Process.__init__(self, name='ApplicationContainer'+str(ID), sim=sim)
        self.ID = ID
        #self.sim = sim
        self.mod_classes = app_module.getClasses() #Module reference
        self.Processes = [proc(self.ID, sim, self) for proc in self.mod_classes] #Instances of Processes for activation
        self.ProcDict = dict([(x.name, x) for x in self.Processes])
        self.presentationQ = SimEvent(sim=sim)
    def activate(self):
        for proc in self.Processes:
            self.sim.activate(proc, proc.execute(),at=0.0) #activate all processes
        self.Node = [i for i in self.sim.Net.nodes if i.ID==self.ID][0]
    def execute(self):
        while True:
            yield waitevent, self, self.presentationQ
            #if self.sim.debug: print self.ID, 'APPLICATION packet received from presentation Q', self.sim.now()
            rec_packet = self.presentationQ.signalparam
            if rec_packet.internal_last_location == Layer.PRESENTATION:
                yield put, self, self.Processes[0].inQ, [rec_packet]
            elif rec_packet.internal_last_location == Layer.APPLICATION:
                self.Node.PresentationContainer.applicationQ.signal(rec_packet)
        
class NodeContainer():
    #Where each node's reference structure and all instances of internals are created.
    #Also where links OF external modules are passed to the respective Containers. 
    def __init__(self, ID, sim, env_container):
        self.ID = ID
        self.sim = sim
        self.EnvironmentContainer = env_container
        self.PhysicalContainer = PhysicalContainer(ID, physical_2, self.sim, env_container)
        self.LinkContainer = LinkContainer(ID, link_2, self.sim)
        self.NetworkContainer = NetworkContainer(ID, network_2, self.sim)
        self.TransportContainer = TransportContainer(ID, transport_2, self.sim)
        self.SessionContainer = SessionContainer(ID, session, self.sim)
        self.PresentationContainer = PresentationContainer(ID, presentation, self.sim)
        self.ApplicationContainer = ApplicationContainer(ID, application, self.sim)
    def activate(self): 
        #Runs all interface's activate scripts (to activate all instances in SimPy)
        #Also set up internal references.
        #ACTIVATE actual containers
        self.sim.activate(self.PhysicalContainer, self.PhysicalContainer.execute(), at=0.0)
        self.sim.activate(self.LinkContainer, self.LinkContainer.execute(), at=0.0)
        self.sim.activate(self.NetworkContainer, self.NetworkContainer.execute(), at=0.0)
        self.sim.activate(self.TransportContainer, self.TransportContainer.execute(), at=0.0)
        self.sim.activate(self.SessionContainer, self.SessionContainer.execute(), at=0.0)
        self.sim.activate(self.PresentationContainer, self.PresentationContainer.execute(), at=0.0)
        self.sim.activate(self.ApplicationContainer, self.ApplicationContainer.execute(), at=0.0)
        #Activate those processes inside containers
        self.PhysicalContainer.activate()
        self.LinkContainer.activate()
        self.NetworkContainer.activate()
        self.TransportContainer.activate()
        self.SessionContainer.activate()
        self.PresentationContainer.activate()
        self.ApplicationContainer.activate()
        
class Model(SimulationRT):
    def __init__(self,name,GVars):
        self.G = GVars
        self.debug = self.G.debug
        self.vis_on = self.G.vis_on
        SimulationRT.__init__(self)
        self.name = name
        self.nrNodes = self.G.num_nodes
        self.nrFreq = self.G.num_freq        
        self.results = None
    def runModel(self):
        ## Initialize Simulation instance
        self.initialize()
        self.Net = Network(self)
        self.Net.populate()
        
        self.Monitors = [Monitor() for i in range(self.G.num_nodes)]
        self.Vis = visualisation_2.Visualisation(self)
        self.activate(self.Vis, self.Vis.execute(), at=0.0)
        
        ratio=10000
        self.simulate(real_time=True, rel_speed=ratio, until=self.G.time)
        self.results = self.Vis.results()
        
#class Model(Simulation):
#    def __init__(self,name,nrNodes,nrFreq):
#        self.debug = True
#        self.vis_on = True
#        self.G = G()
#        #Simulation.__init__(self)
#        self.name = name
#        self.nrNodes = nrNodes
#        self.nrFreq = nrFreq
#    def runModel(self):
#        ## Initialize Simulation instance
#        self.initialize()
#        self.Net = Network(self)
#        self.Net.populate()
#
#        self.Vis = visualisation_2.Visualisation(self)
#        self.activate(self.Vis, self.Vis.execute(), at=0.0)
#        
#        self.simulate(until=1000)
#        self.Vis.results()

#this is for raw, 1 line for each variable per simulation data
class dataWrite():
    def __init__(self, GVars,dt_dir):
        if not os.path.exists(GVars.dirname):
            os.makedirs(GVars.dirname)
        os.makedirs(os.path.join(GVars.dirname, dt_dir))    
        filename = os.path.join(GVars.dirname,dt_dir,GVars.filename)
        self.writeFiles = [filename + '_data' + str(f_i) + '.csv' for f_i in range(GVars.num_nodes)]
        for writeFile in self.writeFiles:
            wfid = open(writeFile, 'w')
            #firstLine = "run,seed,num_s_links_up,num_m_links_up,num_s_links_failed,num_m_links_failed,m_link_lat_ave,s_link_lat_ave,m_link_lat_std,s_link_lat_std,m_busy_time_ave,m_busy_time_std,s_busy_time_ave,s_busy_time_std,m_ave_t_per_data,s_ave_t_per_data,m_data_time_ave,m_data_time_std,s_data_time_ave,s_data_time_std,m_data_length_total,s_data_length_total\n"
            #wfid.write(firstLine)
    def writeNewExperiment(self, input, run, seed):
        n_node = 0
        vars = ('num_s_links_up','num_m_links_up','num_s_links_failed','num_m_links_failed','m_link_lat','s_link_lat','m_data_length','s_data_length','m_data_time','s_data_time','m_total_time','s_total_time','m_throughput','s_throughput')
        for writeFile in self.writeFiles:
            wfid = open(writeFile, 'a')
            writeString = str(run)+','+str(seed)+"\n"
            n_var = 0
            for i in input[n_node]:
                if type(i).__name__ == 'list':
                    writeString += vars[n_var] + ','
                    for val in i:
                        writeString += str(val) + ','
                else:
                    writeString += vars[n_var] + ','
                    writeString += str(i)
                writeString += "\n"
                n_var += 1
            writeString += "\n"
            wfid.write(writeString)
            wfid.close()
            n_node += 1

#This is for regular, post processed data
#class dataWrite():
#    def __init__(self, filename, dirname, num_nodes):
#        if not os.path.exists(dirname):
#            os.makedirs(dirname)
#        filename = os.path.join(dirname,filename)
#        self.writeFiles = [filename + '_data' + str(f_i) + '.csv' for f_i in range(num_nodes)]
#        for writeFile in self.writeFiles:
#            wfid = open(writeFile, 'w')
#            firstLine = "run,seed,num_s_links_up,num_m_links_up,num_s_links_failed,num_m_links_failed,m_link_lat_ave,s_link_lat_ave,m_link_lat_std,s_link_lat_std,m_busy_time_ave,m_busy_time_std,s_busy_time_ave,s_busy_time_std,m_ave_t_per_data,s_ave_t_per_data,m_data_time_ave,m_data_time_std,s_data_time_ave,s_data_time_std,m_data_length_total,s_data_length_total\n"
#            wfid.write(firstLine)
#    def writeNewExperiment(self, input, run, seed):
#        n_node = 0
#        for writeFile in self.writeFiles:
#            wfid = open(writeFile, 'a')
#            writeString = str(run)+','+str(seed)+','
#            for i in input[n_node]:
#                writeString += str(i)+','
#            writeString += "\n"
#            wfid.write(writeString)
#            wfid.close()
#            n_node += 1

class paramWrite():
    def __init__(self, GVars, dt_dir):
        self.GVars = GVars
        filename = GVars.filename + '_params.txt'
        self.writeFile = os.path.join(GVars.dirname,dt_dir,filename)
        self.wfid = open(self.writeFile, 'w')
        self.wfid.write(filename + "\n\n")
    def writeParams(self):
        self.wfid = open(self.writeFile, 'a')
        writeString = ''
        for attr,val in self.GVars.__dict__.iteritems():
            writeString += str(attr) + ' = ' + str(val) + '\n'
        self.wfid.write(writeString)
        self.wfid.close()
        
class Monitor():
    def __init__(self):
        self.num_s_links_up = 0
        self.num_m_links_up = 0
        self.num_s_links_failed = 0
        self.num_m_links_failed = 0
    
        self.m_data_length = []
        self.m_data_fail_length = []
        self.s_data_length = []
        self.s_data_fail_length = []
    
        self.m_link_latency = []
        self.s_link_latency = []
        self.m_link_fail_time = []
        self.s_link_fail_time = []
        
        self.m_data_time = []
        self.s_data_time = []
        
        self.m_total_time = []
        self.s_total_time = []

        self.m_throughput = []
        self.s_throughput = []
        
        self.link_fail_latency = []
          
if __name__=="__main__":
    G = GlobalVars.GlobalVars()

    ## Experiment ----------------------------------
    #Can decide all run parameters here? Or leave in G?
    #Can't access them here... So probably

    n_nodes_set = [2,4,6,8,10]
    #n_nodes_set = [10]
    
    two_scan_set = [[1],[0]]
    two_master_set = [0]
    four_scan_set = [[2],[3],[0],[1]]
    four_master_set = [0,1]
    six_scan_set = [[3],[4],[5],[0],[1],[2]]
    six_master_set = [0,1,2]
    eight_scan_set = [[4],[5],[6],[7],[0],[1],[2],[3]]
    eight_master_set = [0,1,2,3]
    ten_scan_set = [[5],[6],[7],[8],[9],[0],[1],[2],[3],[4]]
    ten_master_set = [0,1,2,3,4,5]
    
    scan_set_set = [two_scan_set, four_scan_set, six_scan_set, eight_scan_set, ten_scan_set]
    master_set_set = [two_master_set, four_master_set, six_master_set, eight_master_set, ten_master_set]
    
    for i, n_nodes in enumerate(n_nodes_set):
        G.num_nodes = n_nodes
        G.scan_set = scan_set_set[i]
        G.master_set = master_set_set[i]
        
        load_set = [(1000,2000),(2000,4000),(4000,8000),(8000,16000)]
        #load_set = [(8000,16000)]
        for load in load_set:
            G.data_size_range = load
            if G.writing:
                now_dt = datetime.datetime.now()
                dt_dir = str(now_dt.day)+str(now_dt.month)+str(now_dt.year)+'_'+str(now_dt.hour)+str(now_dt.minute)+str(now_dt.second)
                dataWriting = dataWrite(G, dt_dir)
                paramWriting = paramWrite(G, dt_dir)
                paramWriting.writeParams()
            for run in range(G.num_runs):
                random.seed(G.seed)
                myModel = Model(name="Experiment"+str(run), GVars=G)
                print '-------------- RUNNING', myModel.name
                print 'random seed:', G.seed
                myModel.runModel()
                if G.writing: dataWriting.writeNewExperiment(myModel.results, run, G.seed)
            
                del myModel
                G.seed += 1
    
