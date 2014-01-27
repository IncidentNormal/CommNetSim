class Waveform():
    def __init__(self):
        self.name = None
        self.error_profiles = []
        self.linking_profiles = []

class ErrorProfile():
    def __init__(self):
        self.BER_Profile = None
        self.SNR_Poor = []
        self.SNR_AGWN = []

class LinkProfile():
    def __init__(self):
        self.DetectionProbability = []
        self.LinkingProbability_Poor = []
        self.LinkingProbability_AGWN = []

class WaveformDatabase():
    def __init__(self):
        self.waveforms = {}
    def initWaveforms(self):
        W = Waveform()
        W.name = 'MILSTD110C'
        #MIL STD 188 110C (STANAG4539_MILSTD110C_Comparison.xls)
        EP = ErrorProfile()
        EP.BER_Profile = 10**-5
        EP.SNR_Poor = [(75,-1),(150,3),(300,5),(600,7),(1200,10),(1600,11),(3200,14),(4800,19),(6400,23),(8000,27),(9600,31),(12000,None)]
        EP.SNR_AGWN = [(75,-6),(150,-3),(300,0),(600,3),(1200,5),(1600,6),(3200,9),(4800,13),(6400,16),(8000,19),(9600,21),(12000,27)]
        W.error_profiles.append(EP)
        self.waveforms[W.name] = W
        
        W = Waveform()
        W.name = 'STANAG4539'
        #bitrate, required SNR: STANAG 4539, Table 4.6.3-2
        EP = ErrorProfile()
        EP.BER_Profile = 10**-5
        EP.SNR_Poor = [(3200,15),(4800,21),(6400,24),(8000,28),(9600,32)]
        EP.SNR_AGWN = [(3200,9),(4800,14),(6400,16),(8000,19),(9600,22),(12800,28)]
        W.error_profiles.append(EP)
        EP2 = ErrorProfile()
        EP.BER_Profile = 10**-4
        EP2.SNR_Poor = [(3200,14),(4800,20),(6400,23),(8000,26),(9600,30)]
        EP2.SNR_AGWN = [(3200,9),(4800,13),(6400,16),(8000,19),(9600,21),(12800,27)]
        W.error_profiles.append(EP2)
        self.waveforms[W.name] = W
        
        W = Waveform()
        W.name = 'ALE141C'
        LP = LinkProfile()
        LP.DetectionProbability = [(0.80, 0),(0.99, 6)]
        LP.LinkingProbability_AGWN = [(0.25,-2.5),(0.50,-1.5),(0.85,-0.5),(0.95,0.0)]
        LP.LinkingProbability_Poor = [(0.25,1.0),(0.50,3.0),(0.85,6.0),(0.95,11.0)]
        W.linking_profiles.append(LP)
        self.waveforms[W.name] = W
        
        return self.waveforms