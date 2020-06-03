import logging
import os

import numpy as np

from pymchelper.estimator import MeshAxis
from pymchelper.readers.common import Reader
from pymchelper.shieldhit.detector.detector_type import SHDetType
from pymchelper.shieldhit.detector.estimator_type import SHGeoType

logger = logging.getLogger(__name__)


class SHReader(Reader):
    """
    Reads binary output files generated by SHIELD-HIT12A code.
    """

    def read_data(self, estimator, nscale=1):
        """
        TODO
        :param estimator:
        :param nscale:
        :return:
        """
        _postprocess(estimator, nscale)
        return True

    @property
    def corename(self):
        """
        TODO
        :return:
        """
        core_name = None

        if self.filename.endswith(('.bdo', '.bdox')):  # TODO add more sophisticated check for file being SH12A output
            basename = os.path.basename(self.filename)
            # we expect the basename to follow one of two conventions:
            #  - corenameABCD.bdo (where ABCD is 4-digit integer)
            #  - corename.bdo
            core_name = basename[:-4]  # assume no number in the basename
            if basename[-8:-4].isdigit() and len(basename[-8:-4]) == 4:  # check if number present
                core_name = basename[:-8]

        return core_name


def _get_mesh_units(estimator, axis):
    """ Set units depending on detector type.
    """

    _geotyp_units = {
        SHGeoType.msh: ("cm", "cm", "cm"),
        SHGeoType.dmsh: ("cm", "cm", "cm"),
        SHGeoType.cyl: ("cm", "radians", "cm"),
        SHGeoType.dcyl: ("cm", "radians", "cm"),
        SHGeoType.zone: ("zone number", "(nil)", "(nil)"),
        SHGeoType.voxscore: ("cm", "cm", "cm"),
        SHGeoType.geomap: ("cm", "cm", "cm"),
        SHGeoType.plane: ("cm", "cm", "cm"),
        SHGeoType.dplane: ("cm", "cm", "cm")
    }
    _default_units = ("(nil)", "(nil)", "(nil)")

    unit = _geotyp_units.get(estimator.geotyp, _default_units)[axis]

    if estimator.geotyp in {SHGeoType.msh, SHGeoType.dmsh, SHGeoType.voxscore, SHGeoType.geomap,
                            SHGeoType.plane, SHGeoType.dplane}:
        name = ("Position (X)", "Position (Y)", "Position (Z)")[axis]
    elif estimator.geotyp in {SHGeoType.cyl, SHGeoType.dcyl}:
        name = ("Radius (R)", "Angle (PHI)", "Position (Z)")[axis]
    else:
        name = ""

    # dirty hack to change the units for differential scorers
    if hasattr(estimator, 'dif_axis') and hasattr(estimator, 'dif_type') and axis == estimator.dif_axis:
        if estimator.dif_type == 1:
            unit, name = _get_detector_unit(SHDetType.energy, estimator.geotyp)
        elif estimator.dif_type == 2:
            unit, name = _get_detector_unit(SHDetType.let_bdo2016, estimator.geotyp)
        elif estimator.dif_type == 3:
            unit, name = _get_detector_unit(SHDetType.angle_bdo2016, estimator.geotyp)
        else:
            unit, name = _get_detector_unit(estimator.dif_type, estimator.geotyp)

    return unit, name


def _bintyp(n):
    """
    Calculates type of binning based on number of bins.

    We follow the convention that positive number of bins means linear binning,
    while the negative - logarithmic.

    :param n: number of bins
    :return: MeshAxis.BinningType.linear or MeshAxis.BinningType.logarithmic
    """
    return MeshAxis.BinningType.linear if n > 0 else MeshAxis.BinningType.logarithmic


def _get_detector_unit(detector_type, geotyp):
    """
    TODO
    :param detector_type:
    :param geotyp:
    :return:
    """
    if geotyp == SHGeoType.zone:
        dose_units = ("MeV/primary", "Dose*volume")
        dose_gy_units = ("J", "Dose*volume")
        alanine_units = ("MeV/primary", "Alanine RE*Dose*volume")
        alanine_gy_units = ("J", "Alanine RE*Dose*volume")
    else:
        dose_units = (" MeV/g/primary", "Dose")
        dose_gy_units = ("Gy", "Dose")
        alanine_units = ("MeV/g/primary", "Alanine RE*Dose")
        alanine_gy_units = ("Gy", "Alanine RE*Dose")

    # TODO add more units, move to shieldhit/detector package
    _detector_units = {
        SHDetType.none: ("(nil)", "None"),
        SHDetType.energy: ("MeV/primary", "Energy"),
        SHDetType.fluence: ("cm^-2/primary", "Fluence"),
        SHDetType.crossflu: ("cm^-2/primary", "Planar fluence"),
        SHDetType.letflu: ("MeV/cm", "LET fluence"),
        SHDetType.dose: dose_units,
        SHDetType.dose_gy_bdo2016: dose_gy_units,
        SHDetType.dlet: ("keV/um", "dose-averaged LET"),
        SHDetType.tlet: ("keV/um", "track-averaged LET"),
        SHDetType.avg_energy: ("MeV/nucleon", "Average kinetic energy"),
        SHDetType.avg_beta: ("(dimensionless)", "Average beta"),
        SHDetType.material: ("(nil)", "Material number"),
        SHDetType.alanine: alanine_units,
        SHDetType.alanine_gy_bdo2016: alanine_gy_units,
        SHDetType.counter: ("/primary", "Particle counter"),
        SHDetType.pet: ("/primary", "PET isotopes"),
        SHDetType.dletg: ("keV/um", "dose-averaged LET"),
        SHDetType.tletg: ("keV/um", "track-averaged LET"),
        SHDetType.q: ("(nil)", "beam quality Q"),
        SHDetType.flu_char: ("cm^-2/primary", "Charged particle fluence"),
        SHDetType.flu_neut: ("cm^-2/primary", "Neutral particle fluence"),
        SHDetType.flu_neqv: ("cm^-2/primary", "1 MeV eqv. neutron fluence"),
        SHDetType.let_bdo2016: ("keV/um", "LET"),
        SHDetType.angle_bdo2016: ("radians", "Angle"),
        SHDetType.zone: ("(dimensionless)", "Zone#"),
        SHDetType.medium: ("(dimensionless)", "Medium#"),
        SHDetType.rho: ("g/cm^3", "Density"),
        SHDetType.kinetic_energy: ("MeV", "Kinetic energy"),
    }
    return _detector_units.get(detector_type, ("(nil)", "(nil)"))


def read_next_token(f):
    """
    returns a tuple with 4 elements:
    0: payload id
    1: payload dtype string
    2: payload number of elements
    3: payload itself
    f is an open and readable file pointer.
    returns None if no token was found / EOF
    """

    tag = np.dtype([('pl_id', '<u8'),
                    ('pl_type', 'S8'),
                    ('pl_len', '<u8')])

    x1 = np.fromfile(f, dtype=tag, count=1)  # read the data into numpy

    if not x1:
        return None
    else:
        pl_id = x1['pl_id'][0]
        pl_type = x1['pl_type'][0]
        pl_len = x1['pl_len'][0]
        try:
            pl = np.fromfile(f,
                             dtype=pl_type,
                             count=pl_len)  # read the data into numpy
            return pl_id, pl_type, pl_len, pl
        except TypeError:
            return None


def _postprocess(estimator, nscale):
    """normalize result if we need that."""
    for page in estimator.pages:
        if page.dettyp not in (SHDetType.dlet, SHDetType.tlet, SHDetType.letflu, SHDetType.dletg, SHDetType.tletg,
                               SHDetType.avg_energy, SHDetType.avg_beta, SHDetType.material, SHDetType.q):
            if estimator.number_of_primaries != 0:  # geotyp = GEOMAP will have 0 projectiles simulated
                page.data_raw /= np.float64(estimator.number_of_primaries)
                page.error_raw /= np.float64(estimator.number_of_primaries)

    if nscale != 1:
        # scale with number of particles given by user
        for page in estimator.pages:
            page.data_raw *= np.float64(nscale)
            page.error_raw *= np.float64(nscale)

        # rescaling with particle number means also unit change for some estimators
        # from per particle to Grey - this is why we override detector type
        for page in estimator.pages:
            page.data_raw *= np.float64(nscale)
            page.error_raw *= np.float64(nscale)

            if page.dettyp == SHDetType.dose:
                page.dettyp = SHDetType.dose_gy_bdo2016
            if page.dettyp == SHDetType.alanine:
                page.dettyp = SHDetType.alanine_gy_bdo2016
            # for the same reason as above we change units
            if page.dettyp in (SHDetType.dose_gy_bdo2016, SHDetType.alanine_gy_bdo2016):
                # 1 megaelectron volt / gram = 1.60217662 x 10-10 Gy
                MeV_g = np.float64(1.60217662e-10)
                page.data_raw *= MeV_g
                page.error_raw *= MeV_g
                page.unit, page.name = _get_detector_unit(page.dettyp, estimator.geotyp)
