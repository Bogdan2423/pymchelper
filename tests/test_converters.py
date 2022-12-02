"""
Tests for converters
"""
import logging
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np
import pytest

import pymchelper
from pymchelper import run
from pymchelper.input_output import fromfile

logger = logging.getLogger(__name__)


@pytest.mark.smoke
class TestTrip2Ddd(unittest.TestCase):

    def test_help(self):
        """ Print help text and exit normally.
        """
        try:
            pymchelper.run.main(["tripddd", "--help"])
        except SystemExit as e:
            self.assertEqual(e.code, 0)

    def test_version(self):
        """ Print version and exit normally.
        """
        try:
            pymchelper.run.main(["tripddd", "--version"])
        except SystemExit as e:
            self.assertEqual(e.code, 0)

    def test_noarg(self):
        """ If pymchelper is called without arguments it should fail.
        """
        try:
            pymchelper.run.main(["tripddd"])
        except SystemExit as e:
            self.assertEqual(e.code, 2)


def unpack_sparse_file(filename):
    logger.info("Unpacking sparse file %s", filename)
    npzfile = np.load(filename)
    data = npzfile['data']
    indices = npzfile['indices']
    shape = npzfile['shape']

    result = np.zeros(shape)
    for ind, dat in zip(indices, data):
        result[tuple(ind)] = dat
    return result


class TestSparseConverter(unittest.TestCase):
    """
    Tests if saved sparse matrices, after unpacking are equivalent to original data
    This test is run over collection of large number precalculated BDO files.
    """
    main_dir = os.path.join("tests", "res", "shieldhit", "generated")
    single_dir = os.path.join(main_dir, "single")

    def test_shieldhit_files(self):
        # skip tests on MacOSX, as there is no suitable bdo2txt converter available yet
        if sys.platform.endswith('arwin'):
            return

        # loop over all .bdo files in all subdirectories
        for root, dirs, filenames in os.walk(self.single_dir):
            for input_basename in filenames:
                logger.info("root: %s, file: %s", root, input_basename)

                inputfile_rel_path = os.path.join(root, input_basename)  # choose input file
                self.assertTrue(inputfile_rel_path.endswith(".bdo"))

                working_dir = tempfile.mkdtemp(prefix="sparse_")  # make temp working dir for converter output files
                logger.info("Creating directory %s", working_dir)

                # generate output with pymchelper assuming .ref extension for output file
                pymchelper_output = os.path.join(working_dir, input_basename[:-3] + "npz")
                logger.info("Expecting file %s to be generated by pymchelper converter", pymchelper_output)
                run.main(["sparse", inputfile_rel_path, pymchelper_output])
                self.assertTrue(os.path.exists(pymchelper_output))

                # read the original file into a estimator structure
                estimator_data = fromfile(inputfile_rel_path)
                self.assertTrue(np.any(estimator_data.pages[0].data))

                # unpack saved sparse matrix
                reconstructed_sparse_mtx = unpack_sparse_file(pymchelper_output)

                # check if unpacked shape is correct
                self.assertEqual(reconstructed_sparse_mtx.shape[0], estimator_data.x.n)
                self.assertEqual(reconstructed_sparse_mtx.shape[1], estimator_data.y.n)
                self.assertEqual(reconstructed_sparse_mtx.shape[2], estimator_data.z.n)

                # check if unpacked data is correct
                self.assertTrue(np.array_equal(estimator_data.pages[0].data, reconstructed_sparse_mtx))

                logger.info("Removing directory %s", working_dir)
                shutil.rmtree(working_dir)


if __name__ == '__main__':
    unittest.main()
