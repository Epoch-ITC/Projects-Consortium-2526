"""
compute_physchem.py
Compute a broad set of sequence-derived physicochemical features for a single amino-acid sequence.

"""

from collections import Counter, defaultdict
import math
import json
import sys

AA1 = "ACDEFGHIKLMNPQRSTVWY"
AA_SET = set(AA1)

# residue masses (average) in Da
RES_MASS = {
 'A':  71.0788,'C': 103.1388,'D': 115.0886,'E': 129.1155,'F': 147.1766,
 'G':  57.0519,'H': 137.1411,'I': 113.1594,'K': 128.1741,'L': 113.1594,
 'M': 131.1926,'N': 114.1038,'P': 97.1167,'Q': 128.1307,'R': 156.1875,
 'S':  87.0782,'T': 101.1051,'V': 99.1326,'W': 186.2132,'Y': 163.1760
}

# Kyte-Doolittle hydrophobicity
KD = {'A':1.8,'C':2.5,'D':-3.5,'E':-3.5,'F':2.8,'G':-0.4,'H':-3.2,'I':4.5,'K':-3.9,
      'L':3.8,'M':1.9,'N':-3.5,'P':-1.6,'Q':-3.5,'R':-4.5,'S':-0.8,'T':-0.7,'V':4.2,'W':-0.9,'Y':-1.3}

# Hopp-Woods hydrophilicity (higher = more hydrophilic)
HW = {'A':-0.5,'C':-1.0,'D':3.0,'E':3.0,'F':-2.5,'G':0.0,'H':-0.5,'I':-1.8,'K':3.0,
      'L':-1.8,'M':-1.3,'N':0.2,'P':0.0,'Q':0.2,'R':3.0,'S':0.3,'T':-0.4,'V':-1.5,'W':-3.4,'Y':-2.3}

# Chou-Fasman propensities (alpha-helix, beta-sheet, turn) approximations
CF_HELIX = {'A':1.45,'C':0.77,'D':0.98,'E':1.53,'F':1.12,'G':0.53,'H':1.24,'I':1.00,'K':1.07,'L':1.34,'M':1.20,'N':0.73,'P':0.59,'Q':1.17,'R':0.79,'S':0.79,'T':0.82,'V':1.14,'W':1.14,'Y':0.61}
CF_SHEET = {'A':0.97,'C':1.30,'D':0.80,'E':0.26,'F':1.28,'G':0.81,'H':1.00,'I':1.60,'K':0.74,'L':1.22,'M':1.67,'N':0.65,'P':0.62,'Q':1.23,'R':0.90,'S':0.72,'T':1.20,'V':1.65,'W':1.19,'Y':1.29}
CF_TURN  = {'A':0.66,'C':1.19,'D':1.46,'E':0.74,'F':0.60,'G':1.56,'H':0.95,'I':0.47,'K':1.01,'L':0.59,'M':0.60,'N':1.56,'P':1.52,'Q':0.98,'R':0.95,'S':1.43,'T':0.96,'V':0.50,'W':0.96,'Y':1.14}

# Side-chain volumes (empirical, Å^3)
VOL = {'A':67,'C':86,'D':91,'E':109,'F':135,'G':48,'H':118,'I':124,'K':135,'L':124,'M':124,'N':96,'P':90,'Q':114,'R':148,'S':73,'T':93,'V':105,'W':163,'Y':141}

# Relative accessible surface area (empirical max ASA) approximate (in Å^2)
# values are common residue maxima (for exposed residue), used to compute RSA = ASA/maxASA
MAX_ASA = {'A':129,'C':167,'D':193,'E':223,'F':240,'G':104,'H':224,'I':197,'K':236,'L':201,'M':224,'N':195,'P':159,'Q':225,'R':274,'S':155,'T':172,'V':174,'W':285,'Y':263}

# Side-chain polarizability (from literature, arbitrary normalized)
POLAR = {'A':0.046,'C':0.128,'D':0.105,'E':0.151,'F':0.291,'G':0.000,'H':0.230,'I':0.186,'K':0.219,'L':0.186,'M':0.221,'N':0.134,'P':0.131,'Q':0.180,'R':0.291,'S':0.062,'T':0.108,'V':0.140,'W':0.409,'Y':0.298}

# Counts of H-bond donors/acceptors in sidechains (very approximate)
HBD = {'A':0,'C':0,'D':1,'E':1,'F':0,'G':0,'H':1,'I':0,'K':1,'L':0,'M':0,'N':1,'P':0,'Q':1,'R':2,'S':1,'T':1,'V':0,'W':1,'Y':1}
HBA = {'A':0,'C':0,'D':2,'E':2,'F':0,'G':0,'H':1,'I':0,'K':0,'L':0,'M':1,'N':2,'P':0,'Q':2,'R':0,'S':1,'T':1,'V':0,'W':1,'Y':1}

# pKa values for side chains and termini (approximate)
PKA = {
 'Cterm': 3.55, 'Nterm': 8.0,
 'C': 8.5, 'D': 3.9, 'E': 4.1, 'H': 6.0, 'K': 10.5, 'R': 12.5, 'Y': 10.1
}

AA1 = "ACDEFGHIKLMNPQRSTVWYX"
AA_TO_IDX = {a: i for i, a in enumerate(AA1)}
AA_DIM = len(AA1)   # 21

def one_hot_encode(seq):
    L = len(seq)
    oh = np.zeros((L, AA_DIM), dtype=np.float32)

    x_idx = AA_TO_IDX['X']

    for i, a in enumerate(seq):
        oh[i, AA_TO_IDX.get(a, x_idx)] = 1.0

    return oh
    
def add_unknown_residue_defaults():
    dicts = [RES_MASS, KD, HW, CF_HELIX, CF_SHEET, CF_TURN,
             VOL, MAX_ASA, POLAR, HBD, HBA]
    for d in dicts:
        d['X'] = sum(d.values()) / len(d)

add_unknown_residue_defaults()

AROMATIC = set(['F','W','Y'])
BETA_BRANCHED = set(['V','I','T'])
DIPEP_WEIGHTS = defaultdict(lambda: 0.0) 

def clean_seq(s):
    if s is None:
        return ""
    if not isinstance(s, str):
        try:
            s = str(s)
        except:
            return ""

    s2 = ''.join([c.upper() for c in s.strip() if c.isalpha()])
    seq = []
    has_unknown = False

    for c in s2:
        if c in AA_SET:
            seq.append(c)
        else:
            seq.append('X')
            has_unknown = True

    # if has_unknown:
    #     print("Warning: mapped non-standard or ambiguous residues to 'X' with neutral physicochemical values.", 
    #           file=sys.stderr)

    return ''.join(seq)


def composition(seq):
    cnt = Counter(seq)
    L = len(seq)
    freqs = {aa: cnt.get(aa,0) for aa in AA1}
    freqs['X'] = cnt.get('X', 0)

    freqs_pct = {aa: (freqs[aa]/L*100.0 if L>0 else 0.0) for aa in freqs}

    return freqs, freqs_pct

def mw_total(seq):
    return sum(RES_MASS.get(a, RES_MASS['X']) for a in seq)

def gravy(seq):
    return sum(KD.get(a, KD['X']) for a in seq) / len(seq)

def mean_property(seq, prop):
    return sum(prop.get(a, prop['X']) for a in seq) / len(seq)

def helix_sheet_turn_props(seq):
    if not seq: return (0.0,0.0,0.0)
    h = mean_property(seq, CF_HELIX)
    s = mean_property(seq, CF_SHEET)
    t = mean_property(seq, CF_TURN)
    return h,s,t

def aromaticity_fraction(seq):
    if not seq: return 0.0
    return sum(1 for a in seq if a in AROMATIC) / len(seq)

def beta_branched_fraction(seq):
    if not seq: return 0.0
    return sum(1 for a in seq if a in BETA_BRANCHED) / len(seq)

def aliphatic_index(seq):
    # AI = X(Ala) + a * X(Val) + b * (X(Ile) + X(Leu)), where X are percentages
    L = len(seq)
    if L==0: return 0.0
    cnt = Counter(seq)
    X_A = cnt.get('A',0)/L*100
    X_V = cnt.get('V',0)/L*100
    X_I = cnt.get('I',0)/L*100
    X_L = cnt.get('L',0)/L*100
    a = 2.9
    b = 3.9
    return X_A + a*X_V + b*(X_I + X_L)

def instability_index(seq):
    # simplified version: sum of dipeptide weights; requires full DIPEP_WEIGHTS table for real values.
    L = len(seq)
    if L < 2:
        return 0.0
    S = 0.0
    for i in range(L-1):
        di = seq[i:i+2]
        S += DIPEP_WEIGHTS[di]
    # scale (ProtParam scales by (10/L) * sum)
    return (10.0 / L) * S

def hydrophobic_moment(seq, window=11, angle_deg=100.0):
    if len(seq) < window:
        angles = [math.radians(angle_deg * i) for i in range(len(seq))]
        hx = sum(KD.get(seq[i], KD['X']) * math.cos(angles[i]) for i in range(len(seq)))
        hy = sum(KD.get(seq[i], KD['X']) * math.sin(angles[i]) for i in range(len(seq)))
        return math.sqrt(hx*hx + hy*hy) / len(seq)
    moments = []
    for i in range(len(seq)-window+1):
        w = seq[i:i+window]
        hx = hy = 0.0
        for k,a in enumerate(w):
            ang = math.radians(angle_deg * k)
            v = KD.get(a, KD['X'])
            hx += v * math.cos(ang)
            hy += v * math.sin(ang)
        moments.append(math.sqrt(hx*hx + hy*hy) / window)
    return sum(moments)/len(moments) if moments else 0.0


def net_charge_at_pH(seq, pH=7.0):
    """
    Simple Henderson-Hasselbalch sums for side-chains + termini
    """
    # pKa dictionary used above (PKA)
    if not seq: return 0.0
    # counts of titratable side chains
    cnt = Counter(seq)
    # positive groups: N-term (pKa ~ 8.0), K, R, H
    pos = 0.0
    pos += 1.0 / (1.0 + 10**(pH - PKA['Nterm']))
    pos += cnt.get('K',0) * (1.0 / (1.0 + 10**(pH - PKA['K'])))
    pos += cnt.get('R',0) * (1.0 / (1.0 + 10**(pH - PKA['R'])))
    pos += cnt.get('H',0) * (1.0 / (1.0 + 10**(pH - PKA['H'])))
    # negative groups: C-term (pKa ~ 3.55), D, E, C, Y
    neg = 0.0
    neg += 1.0 / (1.0 + 10**(PKA['Cterm'] - pH))
    neg += cnt.get('D',0) * (1.0 / (1.0 + 10**(PKA['D'] - pH)))
    neg += cnt.get('E',0) * (1.0 / (1.0 + 10**(PKA['E'] - pH)))
    neg += cnt.get('C',0) * (1.0 / (1.0 + 10**(PKA['C'] - pH)))
    neg += cnt.get('Y',0) * (1.0 / (1.0 + 10**(PKA['Y'] - pH)))
    return pos - neg

def estimate_pI(seq, pH_low=0.0, pH_high=14.0, tol=0.001):
    # bisection to find pH where net charge ~ 0
    a = pH_low; b = pH_high
    fa = net_charge_at_pH(seq, a)
    fb = net_charge_at_pH(seq, b)
    if fa*fb > 0:
        # can't find root — return None
        return None
    while (b - a) > tol:
        m = 0.5*(a+b)
        fm = net_charge_at_pH(seq, m)
        if fa*fm <= 0:
            b = m; fb = fm
        else:
            a = m; fa = fm
    return 0.5*(a+b)

def sliding_window_values(seq, prop_dict, window=9):
    L = len(seq)
    if L == 0: return []
    res = []
    half = window//2
    for i in range(L):
        start = max(0, i-half)
        end = min(L, i+half+1)
        w = seq[start:end]
        res.append(mean_property(w, prop_dict))
    return res

def compute_all(seq, window=11, compute_dipeptides=False):
    seq = clean_seq(seq)
    L = len(seq)
    out = {}
    if L == 0:
        return out
    cnt, pct = composition(seq)
    out['length'] = L
    out['composition_counts'] = cnt
    out['composition_pct'] = pct
    out['molecular_weight'] = mw_total(seq)
    out['gravy'] = gravy(seq)
    out['mean_KD'] = mean_property(seq, KD)
    out['mean_HW'] = mean_property(seq, HW)
    out['helix_prop_mean'], out['sheet_prop_mean'], out['turn_prop_mean'] = helix_sheet_turn_props(seq)
    out['aromatic_fraction'] = aromaticity_fraction(seq)
    out['beta_branched_fraction'] = beta_branched_fraction(seq)
    out['aliphatic_index'] = aliphatic_index(seq)
    out['instability_index'] = instability_index(seq)
    out['hydrophobic_moment'] = hydrophobic_moment(seq, window=window, angle_deg=100.0)
    out['mean_sidechain_volume'] = mean_property(seq, VOL)
    out['mean_polarizability'] = mean_property(seq, POLAR)
    out['mean_HBD_sidechain'] = mean_property(seq, HBD)
    out['mean_HBA_sidechain'] = mean_property(seq, HBA)
    out['estimated_pI'] = estimate_pI(seq)
    out['net_charge_pH7'] = net_charge_at_pH(seq, 7.0)
    out['counts_positive'] = cnt.get('K',0) + cnt.get('R',0) + cnt.get('H',0)
    out['counts_negative'] = cnt.get('D',0) + cnt.get('E',0)
    out['mean_max_ASA'] = mean_property(seq, MAX_ASA)
    out['estimated_mean_RSA_if_exposed'] = 1.0 
    per = {}
    per['KD'] = [KD.get(a, KD['X']) for a in seq]
    per['HW'] = [HW.get(a, HW['X']) for a in seq]
    per['volume'] = [VOL.get(a, VOL['X']) for a in seq]
    per['max_ASA'] = [MAX_ASA.get(a, MAX_ASA['X']) for a in seq]
    per['CF_helix'] = [CF_HELIX.get(a, CF_HELIX['X']) for a in seq]
    per['CF_sheet'] = [CF_SHEET.get(a, CF_SHEET['X']) for a in seq]
    per['CF_turn']  = [CF_TURN.get(a, CF_TURN['X']) for a in seq]
    per['polarizability'] = [POLAR.get(a, POLAR['X']) for a in seq]
    per['HBD_sidechain']  = [HBD.get(a, HBD['X']) for a in seq]
    per['HBA_sidechain']  = [HBA.get(a, HBA['X']) for a in seq]

    per['is_aromatic'] = [1 if a in AROMATIC else 0 for a in seq]
    per['is_beta_branched'] = [1 if a in BETA_BRANCHED else 0 for a in seq]

    per['local_KD_mean'] = sliding_window_values(seq, KD, window=window)
    per['local_HW_mean'] = sliding_window_values(seq, HW, window=window)
    per['local_CF_helix'] = sliding_window_values(seq, CF_HELIX, window=window)
    per['local_CF_sheet'] = sliding_window_values(seq, CF_SHEET, window=window)
    per['local_CF_turn']  = sliding_window_values(seq, CF_TURN, window=window)

    out['per_residue'] = per

    if compute_dipeptides:
        dip = Counter()
        for i in range(L-1):
            dip[ seq[i:i+2] ] += 1
        out['dipeptide_counts'] = dip
    return out




