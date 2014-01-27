'''
Created on Feb 16, 2011

@author: duncantait
'''
from SimPy.Simulation import *
from enums import *
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
    return [passData]
        
class passData(Process):
    def __init__(self, ID, sim, iLink):
        Process.__init__(self, name=self.__class__.__name__, sim=sim)
        self.ID = ID
        self.interface = iLink
        self.inQ = Store(capacity='unbounded', sim=sim)
    def execute(self):
        while True:
            yield get, self, self.inQ, 1
            rec_packet = self.got[0]
            last_location = rec_packet.internal_last_location
            rec_packet.internal_last_location = Layer.SESSION
            if last_location == Layer.TRANSPORT:
                self.interface.presentationQ.signal(rec_packet)
            elif last_location == Layer.PRESENTATION:
                rec_packet = self.getData(rec_packet)
                self.interface.transportQ.signal(rec_packet)
            else:
                if self.sim.debug: print self.ID, 'flamin error mate', self.sim.now()
    def getData(self, in_packet):
        in_packet.session.data = in_packet.application.data
        return in_packet
        
