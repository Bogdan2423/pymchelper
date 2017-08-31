"""
Reads PLD file in IBA format and convert to sobp.dat
which is readable by FLUKA with source_sampler.f and by SHIELD-HIT12A.
"""
import argparse
import json
import logging
from math import exp, log
import sys

logger = logging.getLogger(__name__)


def dedx_air(energy):
    """
    Calculate the mass stopping power of protons in air following ICRU 49.
    Valid from 1 to 500 MeV only.

    :params energy: Proton energy in MeV
    :returns: mass stopping power in MeV cm2/g
    """
    if energy > 500.0 or energy < 1.0:
        logger.error("Proton energy must be between 1 and 500 MeV.")
        raise ValueError("Energy = {:.2f} out of bounds.".format(energy))

    x = log(energy)
    y = 5.4041 - 0.66877 * x - 0.034441 * (x**2) - 0.0010707 * (x**3) + 0.00082584 * (x**4)
    return exp(y)


class Layer(object):
    """
    Class for handling Layers.
    """
    def __init__(self, spottag, energy, meterset, elsum, repaints, elements):
        self.spottag = float(spottag)     # spot tag number
        self.energy = float(energy)
        self.meterset = float(meterset)   # MU sum of this + all previous layers
        self.elsum = float(elsum)         # sum of elements in this layer
        self.repaints = int(repaints)     # number of repaints
        self.elements = elements          # number of elements
        self.spots = int(len(elements) / 2)  # there are two elements per spot

        self.x = [0.0] * self.spots       # position of spot center at isocenter [mm]
        self.y = [0.0] * self.spots       # position of spot center at isocenter [mm]
        self.w = [0.0] * self.spots       # MU weight
        self.rf = [0.0] * self.spots      # fluence weight

        j = 0
        for element in elements:
            token = element.split(",")
            if token[3] != "0.0":
                self.x[j] = float(token[1].strip())
                self.y[j] = float(token[2].strip())
                self.w[j] = float(token[3].strip())  # meterset weight of this spot
                self.rf[j] = self.w[j]
                j += 1  # only every second token has a element we need.


class PLDRead(object):
    """
    Class for handling PLD files.
    """

    def __init__(self, fpld):
        """ Read the rst file."""

        pldlines = fpld.readlines()
        pldlen = len(pldlines)
        logger.info("Read {} lines of data.".format(pldlen))

        self.layers = []

        # parse first line
        token = pldlines[0].split(",")
        self.beam = token[0].strip()
        self.patient_iD = token[1].strip()
        self.patient_name = token[2].strip()
        self.patient_initals = token[3].strip()
        self.patient_firstname = token[4].strip()
        self.plan_label = token[5].strip()
        self.beam_name = token[6].strip()
        self.mu = float(token[7].strip())
        self.csetweight = float(token[8].strip())
        self.nrlayers = int(token[9].strip())  # number of layers

        for i in range(1, pldlen):  # loop over all lines starting from the second one
            line = pldlines[i]
            if "Layer" in line:
                header = line

                token = header.split(",")
                # extract the subsequent lines with elements
                el_first = i + 1
                el_last = el_first + int(token[4])

                elements = pldlines[el_first:el_last]

                # read number of repaints only if 5th column is present, otherwise set to 0
                repaints_no = 0
                if 5 in token:
                    repaints_no = token[5].strip()

                self.layers.append(Layer(token[1].strip(),  # spot tag
                                         token[2].strip(),  # energy
                                         token[3].strip(),  # cumulative meter set weight including this layer
                                         token[4].strip(),  # number of elements in this layer
                                         repaints_no,  # number of repaints.
                                         elements))  # array holding all elements for this layer


def extract_model(model_dictionary, spottag, energy):
    """
    TODO
    :param model_dictionary:
    :param spottag:
    :param energy:
    :return:
    """

    sigma_to_fwhm = (8.0*log(2.0))**0.5

    spot_fwhm_x_cm = 0.0  # point-like source
    spot_fwhm_y_cm = 0.0  # point-like source
    energy_spread = 0.0

    if model_dictionary:
        compatible_models = [model for model in model_dictionary["model"] if spottag == model["spottag"]]
        if not compatible_models:
            print("no models found for spottag {}".format(spottag))
            return None
        elif len(compatible_models) > 1:
            print("more than one model found for spottag {}, taking first one".format(spottag))
        else:
            compatible_layers = [model_layer for model_layer in compatible_models[0]["layers"] if
                                 model_layer["mean_energy"] == energy]
            if not compatible_layers:
                print("no layers found for {}".format(energy))
                return None
            elif len(compatible_models) > 1:
                print("more than one layer found for {}, taking first one".format(energy))
            else:
                spot_fwhm_x_cm = sigma_to_fwhm * compatible_layers[0]["spot_x"]
                spot_fwhm_y_cm = sigma_to_fwhm * compatible_layers[0].get("spot_y", spot_fwhm_x_cm)
                energy_spread = compatible_layers[0].get("energy_spread", 0.0)
    return spot_fwhm_x_cm, spot_fwhm_y_cm, energy_spread


def main(args=sys.argv[1:]):
    """ Main function of the pld2sobp script.
    """

    import pymchelper

    # _scaling holds the number of particles * dE/dx / MU = some constant
    _scaling = 5e8  # some rough estimation for typical proton center

    parser = argparse.ArgumentParser()
    parser.add_argument('fin', metavar="input_file.pld", type=argparse.FileType('r'),
                        help="path to .pld input file in IBA format.",
                        default=sys.stdin)
    parser.add_argument('fout', nargs='?', metavar="output_file.dat", type=argparse.FileType('w'),
                        help="path to the SHIELD-HIT12A/FLUKA output file, or print to stdout if not given.",
                        default=sys.stdout)
    parser.add_argument('-m', '--model', metavar='beam_model.yml', type=argparse.FileType('r'),
                        help="beam model file",
                        default=None)
    parser.add_argument('-f', '--flip', action='store_true', help="flip XY axis", dest="flip", default=False)
    parser.add_argument('-d', '--diag', action='store_true', help="prints additional diagnostics",
                        dest="diag", default=False)
    parser.add_argument('-s', '--scale', type=float, dest='scale',
                        help="number of particles*dE/dx per MU.", default=_scaling)
    parser.add_argument('-v', '--verbosity', action='count', help="increase output verbosity", default=0)
    parser.add_argument('-V', '--version', action='version', version=pymchelper.__version__)
    args = parser.parse_args(args)

    if args.verbosity == 1:
        logging.basicConfig(level=logging.INFO)
    if args.verbosity > 1:
        logging.basicConfig(level=logging.DEBUG)

    pld_data = PLDRead(args.fin)
    args.fin.close()

    if args.model:
        # TODO add validation of JSON schema
        beam_model = json.load(args.model)

        args.fout.writelines("*ENERGY(GEV) SigmaT0(GEV) X(CM) Y(CM) FWHMx(cm) FWHMy(cm) WEIGHT\n")
        outstr = "{:-10.6f} {:-10.6f} {:-10.2f} {:-10.2f} {:-10.2f} {:-10.2f} {:-16.6E}\n"
    else:
        args.fout.writelines("*ENERGY(GEV) X(CM) Y(CM) FWHM(cm) WEIGHT\n")
        outstr = "{:-10.6f} {:-10.2f} {:-10.2f} {:-10.2f} {:-16.6E}\n"

    meterset_weight_sum = 0.0
    particles_sum = 0.0

    for layer in pld_data.layers:

        model_data = extract_model(beam_model, layer.spottag, layer.energy)

        if model_data:
            spot_fwhm_x_cm, spot_fwhm_y_cm, energy_spread = model_data
        else:
            return

        for spot_x_iso_mm, spot_y_iso_mm, spot_w, spot_rf in zip(layer.x, layer.y, layer.w, layer.rf):

            weight = spot_rf * pld_data.mu / pld_data.csetweight
            # Need to convert to weight by fluence, rather than weight by dose
            # for building the SOBP. Monitor Units (MU) = "meterset", are per dose
            # in the monitoring Ionization chamber, which returns some signal
            # proportional to dose to air. D = phi * S => MU = phi * S(air)
            phi_weight = weight / dedx_air(layer.energy)

            # add number of particles in this spot
            particles_spot = args.scale * phi_weight
            particles_sum += particles_spot

            meterset_weight_sum += spot_w

            spot_x_source_cm = spot_x_iso_mm * 0.1
            spot_y_source_cm = spot_y_iso_mm * 0.1
            layer_xy_source_cm = [spot_x_source_cm, spot_y_source_cm]

            if args.flip:
                layer_xy_source_cm.reverse()

            if args.model:
                args.fout.writelines(outstr.format(layer.energy * 0.001,  # MeV -> GeV
                                                   0.0,  # TODO add energy spread
                                                   layer_xy_source_cm[0],
                                                   layer_xy_source_cm[1],
                                                   spot_fwhm_x_cm,  # FWHMx
                                                   spot_fwhm_y_cm,  # FWHMy
                                                   particles_spot))
            else:
                args.fout.writelines(outstr.format(layer.energy * 0.001,  # MeV -> GeV
                                                   layer_xy_source_cm[0],
                                                   layer_xy_source_cm[1],
                                                   spot_fwhm_x_cm,
                                                   particles_spot))

    logger.info("Data were scaled with a factor of {:e} particles*S/MU.".format(args.scale))
    if args.flip:
        logger.info("Output file was XY flipped.")

    if args.diag:
        energy_list = [layer.energy for layer in pld_data.layers]

        # double loop over all layers and over all spots in a layer
        spot_x_list = [x for layer in pld_data.layers for x in layer.x]
        spot_y_list = [y for layer in pld_data.layers for y in layer.y]
        spot_w_list = [w for layer in pld_data.layers for w in layer.w]

        print("")
        print("Diagnostics:")
        print("------------------------------------------------")
        print("Total MUs              : {:10.4f}".format(pld_data.mu))
        print("Total meterset weigths : {:10.4f}".format(meterset_weight_sum))
        print("Total particles        : {:10.4e} (estimated)".format(particles_sum))
        print("------------------------------------------------")
        for i, energy in enumerate(energy_list):
            print("Energy in layer {:3}    : {:10.4f} MeV".format(i, energy))
        print("------------------------------------------------")
        print("Highest energy         : {:10.4f} MeV".format(max(energy_list)))
        print("Lowest energy          : {:10.4f} MeV".format(min(energy_list)))
        print("------------------------------------------------")
        print("Spot X         min/max : {:10.4f} {:10.4f} mm".format(min(spot_x_list), max(spot_x_list)))
        print("Spot Y         min/max : {:10.4f} {:10.4f} mm".format(min(spot_y_list), max(spot_y_list)))
        print("Spot meterset  min/max : {:10.4f} {:10.4f}   ".format(min(spot_w_list), max(spot_w_list)))
        print("")
    args.fout.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
