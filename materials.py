import numpy as np
from scipy import constants
from interpolate_thermal_property import get_potential_aims, get_potential_nist_table, get_potential_sulfur_table
import re

import os  # get correct path for datafiles when called from another directory
materials_directory = os.path.dirname(__file__)
# Append a trailing slash to make coherent directory name - this would select the
#  root directory in the case of no prefix, so we need to check
if materials_directory:
    materials_directory = materials_directory + '/'

# See https://phonopy.github.io/phonopy/setting-tags.html#tprop-tmin-tmax-and-tstep for notes on conversion
eV2Jmol = constants.physical_constants['electron volt-joule relationship'][0] * constants.N_A
    
class material(object):
    """Parent class for materials properties. See docstrings for derived classes solid, ideal_gas"""
    def __init__(self,name,stoichiometry,pbesol_energy_eV=False, hse06_energy_eV=False, N=1):
        self.name = name
        self.stoichiometry = stoichiometry
        self.pbesol_energy_eV = pbesol_energy_eV
        self.hse06_energy_eV = hse06_energy_eV
        self.N = N

    def get_energy(xc='pbesol'):
        """ DFT calculated energy, expressed in eV.

        Keyword argument specifies the functional. 
        It can take one of two values:'pbesol' or 'hse06'.
        If not specified, it defaults to 'pbesol'."""

        if xc == 'pbesol':
            E_dft = self.pbesol_energy_eV
        elif xc == 'hse06':
            E_dft == self.hse06_energy_eV
        else:
            raise RuntimeError('xc functional not found')
        return E_dft


class solid(material):
    """
    Class for solid material data. 

    Sets properties:
    -------------------
    solid.name             (Identifying string)
    solid.stoichiometry    (Dict relating element to number of atoms in a single formula unit)
    solid.pbesol_energy_eV (DFT total energy in eV with PBEsol XC functional)
    solid.hse06_energy_eV  (DFT total energy in eV with HSE06 XC functional)
    solid.fu_cell          (Number of formula units in periodic unit cell)
    solid.volume           (Volume of unit cell in cubic angstroms (m3 * 10^30))
    solid.phonons          (String containing path to phonopy-FHI-aims output data file)
    solid.N                (Number of atoms per formula unit)

    Sets methods:
    -------------------
    solid.U_eV(T), solid.U_J(T), solid.U_kJ(T) : Internal energy 
    solid.H_eV(T,P), solid.H_J(T,P), solid.H_kJ(T,P) : Enthalpy H = U + PV
    solid.mu_eV(T,P), solid.mu_J(T,P), solid.mu_kJ(T,P) : Chemical potential mu = U + PV - TS

    The material is assumed to be incompressible and without thermal expansion
    """
    def __init__(self, name, stoichiometry, pbesol_energy_eV, fu_cell, volume, phonons=False, N=1):
        material.__init__(self,name,stoichiometry,pbesol_energy_eV,N)

        self.fu_cell = fu_cell
        self.volume = volume
        self.phonons = materials_directory + phonons

    def U_eV(self,T,xc='pbesol'):
        """Internal energy of one formula unit of solid, expressed in eV.
        U = solid.U_eV(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.
        Returns a matrix with the same dimensions as T
        """
        U_func = get_potential_aims(self.phonons,'U') 
        E_dft = self.get_energy(xc=xc)
        return (E_dft + U_func(T))/self.fu_cell

    def U_J(self,T,xc='pbesol'):
        """Internal energy of one gram-mole of solid, expressed in J/mol
        U = solid.U_J(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.
        Returns a matrix with the same dimensions as T
        """
        return self.U_eV(T,xc=xc) * constants.physical_constants['electron volt-joule relationship'][0] * constants.N_A

    def U_kJ(self,T,xc='pbesol'):
        """Internal energy of one gram-mole of solid, expressed in kJ/mol
        U = solid.U_kJ(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.
        Returns a matrix with the same dimensions as T
        """
        return self.U_J(T,xc=xc)/1000.

    def H_eV(self,T,P,xc='pbesol'):
        """
        Enthalpy of one formula unit of solid, expressed in eV
        H = solid.H_eV(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.
 
        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        U_func = get_potential_aims(self.phonons,'U')
        PV = P * self.volume * 1E-30 * constants.physical_constants['joule-electron volt relationship'][0] / constants.N_A
        E_dft = self.get_energy(xc=xc)
        return ((E_dft+ U_func(T)) + PV)/self.fu_cell

    def H_J(self,T,P,xc='pbesol'):
        """Enthalpy of one gram-mole of solid, expressed in J/mol
        H = solid.H_J(T,P)

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        return self.H_eV(T,P,xc=xc) * constants.physical_constants['electron volt-joule relationship'][0] * constants.N_A
    
    def H_kJ(self,T,P,xc='pbesol'):
        """Enthalpy of one gram-mole of solid, expressed in kJ/mol
        H = solid.H_kJ(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        return self.H_J(T,P,xc=xc) * 0.001

    def mu_eV(self,T,P,xc='pbesol'):
        """
        Free energy of one formula unit of solid, expressed in eV
        mu = solid.mu_eV(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        TS_func = get_potential_aims(self.phonons,'TS')
        H = self.H_eV(T,P,xc=xc)
        return H - TS_func(T)/self.fu_cell

    def mu_J(self,T,P,xc='pbesol'):
        """
        Free energy of one mol of solid, expressed in J/mol
        mu = solid.mu_J(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        return self.mu_eV(T,P,xc=xc) * constants.physical_constants['electron volt-joule relationship'][0] * constants.N_A

    def mu_kJ(self,T,P,xc='pbesol'):
        """
        Free energy of one mol of solid, expressed in kJ/mol
        mu = solid.mu_kJ(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        return self.mu_J(T,P,xc=xc) * 0.001

    def Cv_kB(self,T):
        """
        Constant-volume heat capacity of one formula unit of solid, expressed in units
        of the Boltzmann constant kB:
        Cv = solid.Cv_kB(T)
        T may be an array, in which case Cv will be an array of the same dimensions.
        """
        Cv_func = get_potential_aims(self.phonons,'Cv')
        return Cv_func(T)/self.fu_cell

    def Cv_eV(self,T):
        """
        Constant-volume heat capacity of one formula unit of solid, expressed in units
        of the Boltzmann constant kB:
        Cv = solid.Cv_eV(T)
        T may be an array, in which case Cv will be an array of the same dimensions.
        """
        return self.Cv_kB(T) * constants.physical_constants['Boltzmann constant in eV/K'][0]
    
    def Cv_J(self,T):
        """
        Constant-volume heat capacity of solid, expressed in J/molK.
        Cv = solid.Cv_J(T)
        T may be an array, in which case Cv will be an array of the same dimensions.
        """
        return (self.Cv_kB(T)  * constants.physical_constants['Boltzmann constant'][0] * constants.N_A)

    def Cv_kJ(self,T):
       """
        Constant-volume heat capacity of solid, expressed in kJ/molK.
        Cv = solid.Cv_kJ(T)
        T may be an array, in which case Cv will be an array of the same dimensions.
        """
       return self.Cv_J(T) * 0.001


   
class ideal_gas(material):
    """
    Class for ideal gas properties. 

    Sets properties:
    -------------------
    ideal_gas.name             (string)
    ideal_gas.stoichiometry    (Dict relating element to number of atoms in a single formula unit)
    ideal_gas.pbesol_energy_eV (DFT total energy in eV with PBEsol XC functional)
    ideal_gas.thermo_data      (String containing path to aims.vibrations output data file)
    ideal_gas.N                (Number of atoms per formula unit)

    Sets methods:
    -------------------
    ideal_gas.U_eV(T), ideal_gas.U_J(T), ideal_gas.U_kJ(T) : Internal energy 
    ideal_gas.H_eV(T), ideal_gas.H_J(T), ideal_gas.H_kJ(T) : Enthalpy H = U + PV
    ideal_gas.mu_eV(T,P), ideal_gas.mu_J(T,P), ideal_gas.mu_kJ(T,P) : Chemical potential mu = U + PV - TS

    Ideal gas law PV=nRT is applied: specifically (dH/dP) at const. T = 0 and int(mu)^P2_P1 dP = kTln(P2/P1)
    Enthalpy has no P dependence as volume is not restricted / expansion step is defined as isothermal
    """

    def __init__(self,name,stoichiometry,pbesol_energy_eV,hse06_energy_eV,thermo_file,zpe_pbesol=0,zpe_hse06=0,zpe_lit=0,N=1):
        material.__init__(self, name, stoichiometry, pbesol_energy_eV,hse06_energy_eV,N)
        self.thermo_file = materials_directory + thermo_file
        # Initialise ZPE to HSE06 value if provided. 
        # This looks redundant at the moment: the intent is to implement
        # some kind of switch or heirarchy of methods further down the line.
        if zpe_hse06 > 0:
            self.zpe = zpe_pbesol
        elif zpe_pbesol > 0:
            self.zpe = zpe_pbesol
        elif zpe_lit > 0:
            self.zpe = zpe_lit
        else:
            self.zpe = 0

    def U_eV(self,T,xc='pbesol'):
        """Internal energy of one formula unit of ideal gas, expressed in eV.
        U = ideal_gas.U_eV(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        Returns a matrix with the same dimensions as T
        """
        U_func = get_potential_nist_table(self.thermo_file,'U')
        E_dft = self.get_energy(xc=xc)
        return (E_dft + self.zpe +
                U_func(T)*constants.physical_constants['joule-electron volt relationship'][0]/constants.N_A
                )

    def U_J(self,T,xc='pbesol'):
        """Internal energy of one gram-mole of ideal gas, expressed in J/mol
        U = ideal_gas.U_J(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        Returns a matrix with the same dimensions as T
        """
        return self.U_eV(T,xc=xc) * constants.physical_constants['electron volt-joule relationship'][0] * constants.N_A

    def U_kJ(self,T,xc='pbesol'):
        """Internal energy of one gram-mole of ideal gas, expressed in kJ/mol
        U = ideal_gas.U_kJ(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        Returns a matrix with the same dimensions as T
        """
        return self.U_J(T,xc=xc) * 0.001

    def H_eV(self,T,*P,xc='pbesol'):
        """Enthalpy of one formula unit of ideal gas, expressed in eV
        H = ideal_gas.H_eV(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        Returns an array with the same dimensions as T

        Accepts ideal_gas.H_eV(T,P): P is unused
        """
        H_func = get_potential_nist_table(self.thermo_file,'H')
        E_dft = self.get_energy(xc=xc)
        return (self.pbesol_energy_eV + self.zpe +
                H_func(T,xc=xc)*constants.physical_constants['joule-electron volt relationship'][0]/constants.N_A
                )

    def H_J(self,T,*P,xc='pbesol'):
        """Enthalpy of one gram-mole of ideal gas, expressed in J/mol
        H = ideal_gas.H_J(T)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        Returns an array with the same dimensions as T

        Accepts ideal_gas.H_eV(T,P): P is unused
        """
        return self.H_eV(T,xc=xc) * constants.physical_constants['electron volt-joule relationship'][0] * constants.N_A
    
    def H_kJ(self,T,*P,xc='pbesol'):
        """Enthalpy of one gram-mole of ideal gas, expressed in kJ/mol
        H = ideal_gas.H_kJ(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        Returns an array with the same dimensions as T

        Accepts ideal_gas.H_eV(T,P): P is unused
        """
        return self.H_J(T,xc=xc) * 0.001

    def mu_eV(self,T,P,xc='pbesol'):
        """
        Free energy of one formula unit of ideal gas, expressed in eV
        mu = ideal_gas.mu_eV(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        S_func = get_potential_nist_table(self.thermo_file,'S')
        S = S_func(T) * constants.physical_constants['joule-electron volt relationship'][0]/constants.N_A
        H = self.H_eV(T,xc=xc)
        return H - T*S + constants.physical_constants['Boltzmann constant in eV/K'][0] * T * np.log(P/1E5)

    def mu_J(self,T,P,xc='pbesol'):
        """
        Free energy of one mol of ideal gas, expressed in J/mol
        mu = ideal_gas.mu_J(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        return self.mu_eV(T,P,xc=xc) * constants.physical_constants['electron volt-joule relationship'][0] * constants.N_A

    def mu_kJ(self,T,P,xc='pbesol'):
        """
        Free energy of one mol of ideal gas, expressed in kJ/mol
        mu = ideal_gas.mu_kJ(T,P)

        The xc keyword specifies the DFT XC functional used to calculate the ground state energy.
        If not specified, it defaults to `pbesol`.

        T, P may be orthogonal 2D arrays of length m and n, populated in one row/column:
        in this case H is an m x n matrix.

        T, P may instead be equal-length non-orthogonal 1D arrays, in which case H is a vector
        of H values corresponding to T,P pairs.

        Other T, P arrays may result in undefined behaviour.
        """
        return self.mu_J(T,P,xc=xc) * 0.001


class sulfur_model(object):
    """
    Class for calculated sulfur equilibria.

    Sets properties:
    -------------------
    sulfur_model.name             (string)
    sulfur_model.pbesol_energy_eV (DFT total energy in eV with PBEsol XC functional for D4d S8 cluster)
    sulfur_model.thermo_data      (String containing path to T/P effects data file)
    sulfur_model.N                (Number of atoms per formula unit)
    sulfur_model.N_ref            (Number of atoms per formula unit of reference state)

    Sets methods:
    -------------------
    sulfur_model.mu_eV(T,P), sulfur_model.mu_J(T,P), sulfur_model.mu_kJ(T,P) : Chemical potential mu = U + PV - TS

    Ideal gas law PV=nRT is applied: specifically (dH/dP) at const. T = 0 and int(mu)^P2_P1 dP = kTln(P2/P1)
    Methods not yet implemented:
    ----------------------------
    sulfur_model.U_eV(T), sulfur_model.U_J(T), sulfur_model.U_kJ(T) : Internal energy 
    sulfur_model.H_eV(T), sulfur_model.H_J(T), sulfur_model.H_kJ(T) : Enthalpy H = U + PV

    Thermo data file format:
    ------------------------

    CSV file containing header line:
    # T/K, mu (x1 Pa) / J mol-1,mu (x2 Pa) / J mol-1...

    followed by comma-separated data rows

    t1,mu11,mu12 ...
    t2,mu21,mu22 ...
    ...

    DEV NOTE:
    ---------
    Not currently a derived class of "material" due to substantially different operation.

    """
    def __init__(self,name,pbesol_energy_eV,mu_file,N=1,N_ref=8):
        self.name = name
        self.stoichiometry = {'S':1}
        self.pbesol_energy_eV = pbesol_energy_eV
        self.mu_file = materials_directory + mu_file
        self.N = 1
        self.N_ref = N_ref

        self._mu_tab = get_potential_sulfur_table(self.mu_file)

    def mu_J(self,T,P):
        if type(T) == np.ndarray:
            T = T.flatten()
        if type(P) == np.ndarray:
            P = P.flatten()

        E0 = self.pbesol_energy_eV * eV2Jmol
        return self._mu_tab(T,P) + E0/self.N_ref

    def mu_kJ(self,T,P):
        return self.mu_J(T,P) * 1e-3

    def mu_eV(self,T,P):
        return self.mu_J(T,P) / eV2Jmol


################ Ternary compounds ###############

BaZrS3_perovskite=solid(name='Perovskite BaZrS3',
                     stoichiometry={'Ba':1,'Zr':1,'S':3},
                     pbesol_energy_eV= None,
                     hse06_energy_eV = None,
                     fu_cell=4,
                     volume=None,
                     phonons=None,
                     N=None
                     )

BaZrS3 = BaZrS3_perovskite

Ba2ZrS4_RP=solid(name='Ruddlesden-Popper Ba2ZrS4',
                     stoichiometry={'Ba':2,'Zr':1,'S':4},
                     pbesol_energy_eV= None,
                     hse06_energy_eV = None,
                     fu_cell=1,
                     volume=None,
                     phonons=None,
                     N=None
                     )

Ba2ZrS4 = Ba2ZrS4_RP

Ba3Zr2S7_RP=solid(name='Ruddlesden-Popper Ba3Zr2S7',
                     stoichiometry={'Ba':3,'Zr':2,'S':7},
                     pbesol_energy_eV= None,
                     hse06_energy_eV = None,
                     fu_cell=None,
                     volume=None,
                     phonons=None,
                     N=None
                     )


Ba3Zr2S7_Needle=solid(name='Needle-like Ba3Zr2S7',
                     stoichiometry={'Ba':3,'Zr':2,'S':7},
                     pbesol_energy_eV= None,
                     hse06_energy_eV = None,
                     fu_cell=None,
                     volume=None,
                     phonons=None,
                     N=None
                     )

############### Elements ###############

Ba = solid(name='Ba',
           stoichiometry={'Ba':1},
           pbesol_energy_eV=None,
           hse06_energy_eV = None,
           fu_cell=None,
           volume=None,
           phonons=None
)

Zr = solid(name='Zr',
                stoichiometry={'Zr':1},
                pbesol_energy_eV=None,
                hse06_energy_eV = None,
                fu_cell=None,
                volume=None,
                phonons=None
)

S = solid(name='S',
                 stoichiometry={'S':1},
                 pbesol_energy_eV=None,
                 hse06_energy_eV = None,
                 fu_cell=None,
                 volume=None,
                 phonons=None
)


############### Binary sulfides ###############

BaS = solid(name='BaS',
    stoichiometry={'Ba':1,'S':1},
    pbesol_energy_eV=None,
    fu_cell=1,
    volume=None,
    phonons=None,
    N=None,
)

BaS2 = solid(name='BaS2',
    stoichiometry={'Ba':1,'S':2},
    pbesol_energy_eV=None,
    fu_cell=2,
    volume=None,
    phonons=None,
    N=None,
)

BaS3 = solid(name='BaS3',
    stoichiometry={'Ba':1,'S':3},
    pbesol_energy_eV=None,
    fu_cell=2,
    volume=None,
    phonons=None,
    N=None,
)

ZrS_P4_nmm = solid(name='A ZrS',        # NOTE: needs adjusting with xtal type
    stoichiometry={'Zr':1,'S':1},
    pbesol_energy_eV=None,
    fu_cell=2,
    volume=None,
    phonons=None,
    N=None,
)

ZrS_Fm_3m = solid(name='B ZrS',        # NOTE: needs adjusting with xtal type
    stoichiometry={'Zr':1,'S':1},
    pbesol_energy_eV=None,
    fu_cell=1,
    volume=None,
    phonons=None,
    N=None,
)

ZrS = None # NOTE: Needs to be set to most stable isomer


ZrS2_P_31m = solid(name='ZrS2',        
    stoichiometry={'Zr':1,'S':2},
    pbesol_energy_eV=None,
    fu_cell=1,
    volume=None,
    phonons=None,
    N=None,
)

ZrS3 = solid(name='ZrS3',        
    stoichiometry={'Zr':1,'S':3},
    pbesol_energy_eV=None,
    fu_cell=2,
    volume=None,
    phonons=None,
    N=None,
)


############### Gases ###############


S8=ideal_gas(
    name='S8',
    stoichiometry={'S':8},
    pbesol_energy_eV=None,
    hse06_energy_eV=None,
    thermo_file='nist_janaf/S8.dat',
    zpe_pbesol=None
    N=8
)

S2=ideal_gas(
    name='S2',
    stoichiometry={'S':2},
    pbesol_energy_eV=None,
    hse06_energy_eV=None,
    thermo_file='nist_janaf/S2.dat',
    zpe_pbesol=None,
    N=2
)


S_model_S8ref = sulfur_model('S vapours',S8.pbesol_energy_eV, S8.hse06_energy_eV,'sulfur/mu_pbe0_scaled_S8ref.csv')

S_model = sulfur_model('S vapours',S2.pbesol_energy_eV, S2.hse06_energy_eV,'sulfur/mu_pbe0_scaled_S2ref.csv',N_ref=2)

S = S_model

def volume_calc(filename):
    """Calculate unit cell volume in cubic angstroms from FHI-aims geometry.in file"""
    import numpy as np
    lattice_vectors = []
    with open(filename, 'r') as f:
        for line in f:
            if line.split()[0] == 'lattice_vector':
                lattice_vectors.append(line.split()[1:4])

    lattice_vectors = np.array(lattice_vectors).astype(float)
    volume = np.dot(lattice_vectors[0],np.cross(lattice_vectors[1],lattice_vectors[2]))

    return abs(volume)
