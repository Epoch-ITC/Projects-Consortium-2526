# src/segment.py

class Segment:
    """
    Represents one beat-aligned audio segment.
    This class becomes the basic state in our discrete Hilbert space.
    """

    def __init__(self, id, parent_song, start_time, end_time):
        # Identity metadata
        self.id = id
        self.parent_song = parent_song
        self.start = start_time
        self.end = end_time

        
        self.spectrogram = None          
        self.wavelet_energy = None       
        self.key = None                  
        self.features = None             
        self.global_index = None         

    def __repr__(self):
        return f"<Segment {self.id} | {self.parent_song} | {self.start}-{self.end}s>"
