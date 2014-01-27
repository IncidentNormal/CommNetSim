import sys
import waveforms

class GlobalVars():
    def __init__(self):
        self.numTO = 0
        
        self.time = 1000
        
        self.seed = 123456
        self.num_runs = 500
        self.num_nodes = 2
        self.num_freq = 10

        self.writing = True
        self.filename = '2G'
        self.dirname = '1302_var-data-size-uni'
        self.debug = False
        self.vis_on = False

        #ENVIRONMENT
        self.propagation_time = 0.08
        self.ratio_propagating = 0.6
        self.SNR_fidelity = 1.0 #every how many seconds is SNR recalculated?
        self.min_SNR = 0.0
        self.max_SNR = 30.0
        self.best_SNR = 100.0
        self.ratio_nogo = 0.5

        #WAVEFORMS
        self.waveform_database = waveforms.WaveformDatabase()
        self.waveforms = self.waveform_database.initWaveforms() #waveforms.py  
        self.linking_waveform = 'ALE141C' 
        self.data_waveform = 'MILSTD110C'

        #CODERATES

        #INTERLEAVER SIZES

        #These are node specific: should almost be made into a Class themselves,
        #to be passed to NodeContainer on creation, to enable heterogeneous nodes.
        #Also need:
        #self.scan_set = [0,1,2] (nodes that it will try to talk to) - this could almost be set up as a GUI.
        #see vPython mouse related things.
        #PHYSICAL
        self.scan_time = 0.2
        self.dwell_time = 0.784 #physical
        self.phy_timeout = 1.01 #entirely arbitrary really.
        self.LBT_time = 1.114 #0.33 Tds, detecting signalling tones time (0.2), plus tuning time (0.13 for fast quipment). plus 0.784 for 2Trw for LBT time.
        self.rx_timeout = 20
        self.min_rec_SNR = 10.0 #min rec SNR, #below this, messages won't register with receiver - will simply contribute to noise on channel
        self.Trw = 0.392
        self.phy_jitter_range = (0,0.05) #Phy TX jitter before sending to avoid simultaneous events,
        
    
        #LINK
        #dwell_time = 0.784 #link
        #scan_time = 0.2
        self.addr_length = 3
        self.max_backoff = 4 #max number of backoffs (each is Trw)
        self.link_wait_for_reply = 0.545
        self.interleaver_time = 0.36 #(VS)
        self.link_timeout = 300
        #scanning_call = dwell_time*num_freq #link
        #rx_timeout = 20
        
        #NETWORK
        self.packet_size = 1024 #data is split into packets of how many bits
        self.rate_fidelity = 3 #every 1 second
        self.frame_max_time = 10#should be 120secs
        self.initial_rate = 300
        self.data_rates = [75,150,300,600,1200,3200,4800,6400,8000,9600]
        self.dec_error_thresholds = [None,0.5,0.5,0.5,0.5,0.5,0.35,0.2,0.15,0.05]
        self.inc_error_thresholds = [0.2,0.2,0.2,0.2,0.2,0.1,0.05,0.05,0.02,None]
        self.wait_for_ARQ_Rx = 1.5
        self.ARQ_timeout_n = 3
        self.minReliability = 0.5
        self.targetReliability = 0.9

        #APPLICATION
        self.scan_set = True #All nodes-all nodes
        self.master_set = [0,1,2,3,4,5,6,7,8,9]
        #self.scan_set = [[3],[4],[5],[0],[1],[2]] #0-3, 1-4, 2-5
        #self.scan_set = [[5],[6],[7],[8],[9],[0],[1],[2],[3],[4]] #0-5, 1-6, 2-7, 3-8, 4-9,
        #self.slave_set = [0,1,2,3,4]
        #self.master_set = [0,1,2,3,4,5,6,7,8,9]
        
        #if len(self.scan_set) != self.num_nodes and self.scan_set != True:
        #    print 'SCAN SET NOT EQUAL TO NUM NODES'
        #    sys.exit()
        self.data_size_range = (1000,2000)
        self.data_frequency = (30,500)

    def MaxModemDelay(self, data_rate):
        self.interleaver_delay = 0.853
        self.data_rates = [75,300,1200]
        self.modem_delays = [5.46,2.14,1.57]
        return np.interp(data_rate, self.data_rates, self.modem_delays)
    def Throughput_SNR(self, SNR):
        TP = 6.0 
        if SNR > 2 and SNR < 10:
            TP = (53*SNR - 100)
        elif SNR > 10 and SNR < 30:
            TP = (216*SNR) - 700 #data frame size is 250bytes, interleaver length is 0.36s (VS)
        else:
            'Discont, SNR fallen outside of bounds 2-30, value:', SNR
        return TP
    def feq(self,a,b):
        #Function required to compare floats, as floats are notoriously INACCURATE at high DP (which is default)
        #Change accuracy of number as required...
        if abs(a-b)<0.00000001:
            return 1
        else:
            return 0

#   5066 (ST/AG) --> CCIR Moderate
#    def Throughput_SNR(self, SNR):
#        if SNR > 2 and SNR < 10:
#            TP = (53*SNR - 100)
#        elif SNR > 10 and SNR < 30:
#            TP = (216*SNR) - 700 #data frame size is 250bytes, interleaver length is 0.36s (VS)
#        else:
#            'Discont, SNR fallen outside of bounds 2-30, value:', SNR
#        return TP
#
#   HDL (Harris, 2002) --> 5kb message, CCIR Good [from STANAG 4538]
#    def Throughput_SNR(self, SNR):
#        if SNR > 0 and SNR < 30:
#            TP = (42*SNR) + 250 #data frame size is 250bytes, interleaver length is 0.36s (VS)
#            return TP
#        else:
#            print 'Discont, SNR should be between 0 and 30, actual value:', SNR
#
#   HDL (STANAG 4538) --> 50kb message, CCIR Poor
#    def Throughput_SNR(self, SNR):
#        if SNR > 0 and SNR < 30:
#            TP = (85*SNR + 350)
#        else:
#            'Discont, SNR should be between 0 and 30, actual value:', SNR
#        return TP



    
