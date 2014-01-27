'''
Created on Feb 16, 2011

@author: duncantait
'''
from SimPy.Simulation import *
from enums import *
import string
import packet
import random
#random.seed(123456)
   
class instance(Process):
    def __init__(self, ID, sim):
        Process.__init__(self, sim=sim)
        self.ID = ID
    def execute(self):
        yield hold, self, 1
        print self.ID, self.sim.now()
        
def getClasses(): #List all main (need an interface to main simulation) active Process classes in here, this will be iterated through by OSI stack and create instances of them.   
    return [kernel, DataCreation]

class kernel(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self,name=self.__class__.__name__,sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', name='kernel inQueue', sim=sim)
    def execute(self):
        while True:
            yield get, self, self.inQ, 1
            if self.sim.debug: print self.ID, 'APPLICATION: DATA RECEIVED', self.sim.now()
            rec_data = self.got[0]
            self.interrupt(self.interface.ProcDict['DataCreation'])
        
class DataCreation(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self,name=self.__class__.__name__,sim=sim)
        self.ID = ID
        self.interface = iLink
    def execute(self):
        if self.ID in self.sim.G.master_set: 
            while True:
                yield hold, self, random.uniform(self.sim.G.data_frequency[0],self.sim.G.data_frequency[1])
                if self.interrupted():
                    pass
                else:
                    self.data = self.createData()
                    if self.sim.debug: print self.ID, '* Application: Data Created, destination:', self.data.ID.Destination, 'datasize:', len(self.data.application.data), 'ID:', self.data.ID.Application_ID , self.sim.now()
                    self.interface.presentationQ.signal(self.data)
    def createData(self):
        data = packet.Packet()
        data.ID.Application_ID = self.createID()
        data.ID.Destination = self.findDestination()
        data.ID.Origin = self.ID
        data.internal_last_location = Layer.APPLICATION
        
        data_size = random.randint(self.sim.G.data_size_range[0],self.sim.G.data_size_range[1])
        data.application.data = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(data_size))
        return data
    def findDestination(self):
        #THIS IS WHERE SCAN SET IS DETERMINED
        scan_set = range(self.sim.G.num_nodes)
        if self.sim.G.scan_set != True:
            scan_set = self.sim.G.scan_set[self.ID]
        destination = -1
        while (destination == -1) or (destination == self.ID):
            destination = random.choice(scan_set)
        #print self.ID, 'Application: destination:', destination, self.sim.now()
        return destination
    def createID(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))

