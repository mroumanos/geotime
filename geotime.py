"""
A Python 3 library that allows you to generate a base64-encoded
geographic + time box, or "geotime" box, which can be used to compare
the cumulative space and time differences between entities. This can 
be considered a combined indexing scheme for both geo-coordinates and 
their associated times.
"""
import time

MAX_ERR_GEO = 40075161.2 # crude earth circumference, in meters
MAX_ERR_TIME = 2**32 # epoch time max, in seconds
DEFAULT_PRECISION_SIZE = 120
DEFAULT_PRECISION_CHUNK_SIZE = 3

def encode(geo,time,geo_precision,time_precision,
          precision_size=DEFAULT_PRECISION_SIZE,
          precision_chunk_size=DEFAULT_PRECISION_CHUNK_SIZE):
    
    binary_geo = buffer(generate_binary_geo(geo,geo_precision),precision_size,precision_chunk_size)
    binary_time = buffer(generate_binary_time(time,time_precision),precision_size,precision_chunk_size)
    
    binary = ''
    for i in range(int(precision_size/precision_chunk_size)):
        binary_chunk = binary_geo[i*precision_chunk_size:(i+1)*precision_chunk_size]
        binary_chunk += binary_time[i*precision_chunk_size:(i+1)*precision_chunk_size]
        binary += generate_base64(binary_chunk)
        
    return binary

def generate_base64(binary_string):
    """
    Creates base64 character from a given binary string
    """
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    BASE = len(ALPHABET)

    binary_string = reversed(binary_string)
    n = sum([2**i if int(b) else 0 for i,b in enumerate(binary_string)])
    s = []
    while True:
        n, r = divmod(n, BASE)
        s.append(ALPHABET[r])
        if n == 0:
            break
    return ''.join(reversed(s))

def generate_binary_geo(geo,precision):
    """
    Creates an alternating binary index (compared to a Z-curve 
    or Hilbert indices) of a given geolocation.
    """
    bounds = [{'max':90,'min':-90},{'max':180,'min':-180}]
    binary_geo = ''
    curr_precision = 1
    modulus = 2
    while curr_precision <= precision:
        i = curr_precision % 2 # alternates between splitting N-S or E-W
        center = (bounds[i]['max'] + bounds[i]['min'] ) / 2
        if geo[i] > center:
            binary_geo += '1'
            bounds[i]['min'] = center
        else:
            binary_geo += '0'
            bounds[i]['max'] = center
        
        curr_precision += 1
        
    return binary_geo

def generate_binary_time(time,precision):
    """
    Translated an input epoch time (in seconds) to binary format.
    Padding is used to achieve precision length.
    """
    binary_time = '{0:b}'.format(time)[0:precision]
    if precision > len(binary_time):
        binary_time = '0' * (precision - len(binary_time)) + binary_time
    
    return binary_time

def buffer(binary,precision_size,precision_chunk_size):
    """
    Buffers an input binary string to allow it to fit in a larger string
    of 'precision_size' in length
    """
    chunk_count = int(precision_size/precision_chunk_size)
    chunks = chunk(binary,chunk_count)
    buffered_binary = ''
    i = 0
    for c in chunks:
        buffered_binary += '0' * (precision_chunk_size - c) + binary[i:i+c]
        i += c
    
    return buffered_binary
    
def chunk(binary,chunk_count):
    """
    Chunks the input into approximately even-sized bins, returning 
    the bin sizes in the form of an integer array
    """
    length = len(binary)
    base_chunk_size = int(length / chunk_count)
    chunks = [ base_chunk_size for i in range(chunk_count)]
    xs = length - (base_chunk_size * chunk_count)
    for i in range(xs): chunks[i] += 1
        
    return chunks

class geotime():
    
    def __init__(self,
                geo=[0,0],time=int(time.time()*100000),
                geo_precision=60,time_precision=60,
                precision_size=DEFAULT_PRECISION_SIZE,
                precision_chunk_size=DEFAULT_PRECISION_CHUNK_SIZE):
        self.geo = geo
        self.time = time
        self.geo_precision = geo_precision
        self.time_precision = time_precision
        self.precision_size = precision_size
        self.precision_chunk_size = precision_chunk_size
    
    def generate_binary_geo(self):
        return generate_binary_geo(self.geo,self.geo_precision)
    
    def generate_binary_time(self):
        return generate_binary_time(self.time,self.time_precision)
    
    def encode(self):
        return encode(self.geo,self.time,
                     self.geo_precision,self.time_precision,
                     precision_size=self.precision_size,
                     precision_chunk_size=self.precision_chunk_size)

    def get_precision(self):
        chunk_count = int(self.precision_size/self.precision_chunk_size)

        binary_geo = self.generate_binary_geo()
        chunks_geo = chunk(binary_geo,chunk_count)
        geo_precision = []
        i = 0
        for c in chunks_geo:
            i += c
            geo_precision.append((1/2**(i-1))*MAX_ERR_GEO)
                    
        binary_time = self.generate_binary_time()
        chunks_time = chunk(binary_time,chunk_count)
        time_precision = []
        i = 0
        for c in chunks_time:
            i += c
            time_precision.append((1/2**i)*MAX_ERR_TIME)
        
        precision = '<precision>: <geo precision> m, <time precision> s | '
        for c in range(chunk_count):
            precision += ('%s: %s m, %s s' % (c+1,geo_precision[c],time_precision[c]))
            if c != chunk_count - 1: precision += ' | '
            
        return precision