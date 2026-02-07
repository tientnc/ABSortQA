from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from itertools import combinations

#Check valid smiles
def check_smiles(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    return True

#Count the number of carbons in structure
def count_carbons(smiles):
    mol = Chem.MolFromSmiles(smiles)
    mol.GetAtoms()
    num_carbons = [1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 6]
    return sum(num_carbons)

#Count the number of heavy atoms (all atoms except hydrogen) in structure
def count_heavy_atoms(smiles):
    mol = Chem.MolFromSmiles(smiles)
    return mol.GetNumHeavyAtoms()

#Check if structure is amphoteric (is both an acid and a base - having both a pka and a pkah value)
def check_amphoteric(structure):
    structure['amphoteric'] = False
    if 'pKa1' in structure['pka_type'].values and 'pKaH1' in structure['pka_type'].values:
        structure['amphoteric'] = True
    return structure

#All bases should not have the carboxylic group
def check_CO2H_base(smiles):
    mol = Chem.MolFromSmiles(smiles)
    CO2H = Chem.MolFromSmarts('C(=O)[OH]')
    return not mol.HasSubstructMatch(CO2H)

#Functional group detection (SMARTS list) and primary selection
#Functional groups are prioritized in expected pka/pkah range and uniqueness of the functional group
SMARTS_ACID_GROUPS = [
    (None, '[PX4](=O)(O)(O)'), #Not credible 
    (None, 'S(=O)(=O)[OH]'), #Not credible 
    ('CO2H', 'C(=O)[OH]'),
    ('Ar-SH','c[SH]'),       
    ('Ar-OH', 'c[OH]'),     
    ('SH', '[SH]'),           
    ('1,3-DICARB', 'C(=O)[C;X4;H1,H2]C(=O)'),
    ('N-OH', '[N][OH]'),
    ('N-OH', '[n][OH]'),
    (None, '[B][OH]'),          # Too few substances
    ('Csp3-NO2', '[CX4][N+](=O)[O-]'),
    ('NH', '[nH]'),            
    ('NH', '[*][NH][*]'),
    ('NH', '[*][NH2]'),
    ('OH', '[CX4][OH]'),
    (None, 'C=O'),           # Not alpha carbon acidity 
]

SMARTS_BASE_GROUPS = [
    ('guanidine','N=C(N)N'),
    ('amidine', 'N=CN'),
    ('enamine','C=C-N'),
    ('imine','C=N'),
    ('amine','[NX3;!$(N-*=[O,N,S]);!$(N-c)]'),
    ('Ar-N', '[c]-[N;!$(N(=O)[O])]'),
    ('(Ar)N','[n]'),
    ('amide','[NX3][C](=O)')
]

def detect_functional_groups_acid(smiles):
    mol = Chem.MolFromSmiles(smiles)
    for name, smarts in SMARTS_ACID_GROUPS:
        patt = Chem.MolFromSmarts(smarts)
        if patt is None: 
            continue
        if mol.HasSubstructMatch(patt):
            return name
    
def detect_functional_groups_base(smiles):
    mol = Chem.MolFromSmiles(smiles)
    for name, smarts in SMARTS_BASE_GROUPS:
        patt = Chem.MolFromSmarts(smarts)
        if patt is None: 
            continue
        if mol.HasSubstructMatch(patt):
            #The base strength of Ar-N and Ar(N) are very close, so any structure with both functional group are tagged with both
            if name == 'Ar-N' and mol.HasSubstructMatch(Chem.MolFromSmarts('[n]')):
                return 'Ar-N, (Ar)N'
            return name
        
#Validity function
def check_pair_validity(sub1, sub2):
    #Condition 1: The difference between number of carbon atoms must be less than 3
    c1 = abs(sub1['num_carbons'] - sub2['num_carbons']) <= 3
    
    #Condition 2: The difference between the pka/pkah value must be larger than a certain threshold based on their assessment
    c2 = abs(sub1['pka_value'] - sub2['pka_value']) >= 0.5
    if sub1['assessment'] + sub2['assessment'] == 5:
        c2 = abs(sub1['pka_value'] - sub2['pka_value']) >= 1.25
    elif sub1['assessment'] + sub2['assessment'] == 6:
        c2 = abs(sub1['pka_value'] - sub2['pka_value']) >= 2
    
    moles = [Chem.MolFromSmiles(sub['SMILES']) for sub in [sub1, sub2]]
    fpgen = AllChem.GetRDKitFPGenerator()
    fps = [fpgen.GetFingerprint(m) for m in moles]

    #Condition 3: The two structures must have a certain degree of similarity to be comparable
    c3 = DataStructs.TanimotoSimilarity(fps[0], fps[1]) > 0.2

    return all([c1, c2, c3])

def generate_ordered_pairs(sub_dict):
    result = []
    for group_df in sub_dict.values():
        
        for (idx1, row1), (idx2, row2) in combinations(group_df.iterrows(), 2):

            if check_pair_validity(row1, row2):
                s1 = row1['SMILES']
                s2 = row2['SMILES']
                p1 = row1['pka_value']
                p2 = row2['pka_value']
                a1 = row1['assessment']
                a2 = row2['assessment']

                functional_group = row1['priority_functional_group']

                pair = {'SMILES1': s1, 'pka(h)_value1': p1, 'assessment1': a1,
                        'SMILES2': s2, 'pka(h)_value2': p2, 'assessment2': a2,
                        'functional_group' : functional_group}

                result.append(pair)
                    
    return result