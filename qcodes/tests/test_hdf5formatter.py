from unittest import TestCase
import os
import numpy as np
import h5py
from shutil import copy

from qcodes.station import Station
from qcodes.loops import Loop
from qcodes.data.location import FormatLocation
from qcodes.data.hdf5_format import HDF5Format

from qcodes.data.data_array import DataArray
from qcodes.data.data_set import DataSet
from qcodes.utils.helpers import compare_dictionaries
from .data_mocks import DataSet1D, DataSet2D

from qcodes.tests.instrument_mocks import MockParabola


class TestHDF5_Format(TestCase):
    def setUp(self):
        self.io = DataSet.default_io
        self.formatter = HDF5Format()
        # Set up the location provider to always store test data in
        # "qc.tests.unittest_data
        cur_fp = os.path.dirname(__file__)
        base_fp = os.path.abspath(os.path.join(cur_fp, '../unittest_data'))
        self.loc_provider = FormatLocation(
            fmt=base_fp+'/{date}/#{counter}_{name}_{time}')
        DataSet.location_provider = self.loc_provider

    def checkArraysEqual(self, a, b):
        """
        Checks if arrays are equal
        """
        # Modified from GNUplot would be better to have this in some module
        self.checkArrayAttrs(a, b)
        np.testing.assert_array_equal(a, b)
        if len(a.set_arrays) > 1:
            for i, set_arr in enumerate(a.set_arrays):
                np.testing.assert_array_equal(set_arr, b.set_arrays[i])
        else:
            np.testing.assert_array_equal(a.set_arrays, b.set_arrays)

        for sa, sb in zip(a.set_arrays, b.set_arrays):
            self.checkArrayAttrs(sa, sb)

    def checkArrayAttrs(self, a, b):
        self.assertEqual(a.tolist(), b.tolist())
        self.assertEqual(a.label, b.label)
        self.assertEqual(a.array_id, b.array_id)

    def test_full_write_read_1D(self):
        """
        Test writing and reading a file back in
        """
        # location = self.locations[0]
        data = DataSet1D()
        # print('Data location:', os.path.abspath(data.location))
        self.formatter.write(data)
        # Used because the formatter has no nice find file method

        # Test reading the same file through the DataSet.read
        data2 = DataSet(location=data.location, formatter=self.formatter)
        data2.read()
        self.checkArraysEqual(data2.x_set, data.x_set)
        self.checkArraysEqual(data2.y, data.y)
        self.formatter.close_file(data)
        self.formatter.close_file(data2)

    def test_full_write_read_2D(self):
        """
        Test writing and reading a file back in
        """
        data = DataSet2D()
        self.formatter.write(data)
        # Test reading the same file through the DataSet.read
        data2 = DataSet(location=data.location, formatter=self.formatter)
        data2.read()
        self.checkArraysEqual(data2.x_set, data.x_set)
        self.checkArraysEqual(data2.y_set, data.y_set)
        self.checkArraysEqual(data2.z, data.z)

        self.formatter.close_file(data)
        self.formatter.close_file(data2)

    def test_incremental_write(self):
        data = DataSet1D()
        location = data.location
        data_copy = DataSet1D(False)

        # # empty the data and mark it as unmodified
        data.x_set[:] = float('nan')
        data.y[:] = float('nan')
        data.x_set.modified_range = None
        data.y.modified_range = None

        # simulate writing after every value comes in, even within
        # one row (x comes first, it's the setpoint)
        for i, (x, y) in enumerate(zip(data_copy.x_set, data_copy.y)):
            data.x_set[i] = x
            self.formatter.write(data)
            data.y[i] = y
            self.formatter.write(data)
        data2 = DataSet(location=location, formatter=self.formatter)
        data2.read()
        self.checkArraysEqual(data2.arrays['x_set'], data_copy.arrays['x_set'])
        self.checkArraysEqual(data2.arrays['y'], data_copy.arrays['y'])

        self.formatter.close_file(data)
        self.formatter.close_file(data2)

    def test_metadata_write_read(self):
        """
        Test is based on the snapshot of the 1D dataset.
        Having a more complex snapshot in the metadata would be a better test.
        """
        data = DataSet1D()
        data.snapshot()  # gets the snapshot, not added upon init
        self.formatter.write(data)  # write_metadata is included in write
        data2 = DataSet(location=data.location, formatter=self.formatter)
        data2.read()
        self.formatter.close_file(data)
        self.formatter.close_file(data2)
        metadata_equal, err_msg = compare_dictionaries(
            data.metadata, data2.metadata,
            'original_metadata', 'loaded_metadata')
        self.assertTrue(metadata_equal, msg='\n'+err_msg)

    def test_loop_writing(self):
        # pass
        station = Station()
        MockPar = MockParabola(name='Loop_writing_test')
        station.add_component(MockPar)
        # # added to station to test snapshot at a later stage
        loop = Loop(MockPar.x[-100:100:20]).each(MockPar.skewed_parabola)
        data1 = loop.run(name='MockLoop_hdf5_test',
                         formatter=self.formatter,
                         background=False, data_manager=False)
        data2 = DataSet(location=data1.location, formatter=self.formatter)
        data2.read()
        for key in data2.arrays.keys():
            self.checkArraysEqual(data2.arrays[key], data1.arrays[key])

        metadata_equal, err_msg = compare_dictionaries(
            data1.metadata, data2.metadata,
            'original_metadata', 'loaded_metadata')
        self.assertTrue(metadata_equal, msg='\n'+err_msg)
        self.formatter.close_file(data1)
        self.formatter.close_file(data2)

    def test_loop_writing_2D(self):
        # pass
        station = Station()
        MockPar = MockParabola(name='Loop_writing_test_2D')
        station.add_component(MockPar)
        loop = Loop(MockPar.x[-100:100:20]).loop(
            MockPar.y[-50:50:10]).each(MockPar.skewed_parabola)
        data1 = loop.run(name='MockLoop_hdf5_test',
                         formatter=self.formatter,
                         background=False, data_manager=False)
        data2 = DataSet(location=data1.location, formatter=self.formatter)
        data2.read()
        for key in data2.arrays.keys():
            self.checkArraysEqual(data2.arrays[key], data1.arrays[key])

        metadata_equal, err_msg = compare_dictionaries(
            data1.metadata, data2.metadata,
            'original_metadata', 'loaded_metadata')
        self.assertTrue(metadata_equal, msg='\n'+err_msg)
        self.formatter.close_file(data1)
        self.formatter.close_file(data2)

    def test_closed_file(self):
        data = DataSet1D()
        # closing before file is written should not raise error
        self.formatter.close_file(data)
        self.formatter.write(data)
        # Used because the formatter has no nice find file method
        self.formatter.close_file(data)
        # Closing file twice should not raise an error
        self.formatter.close_file(data)

    def test_reading_into_existing_data_array(self):
        data = DataSet1D()
        # closing before file is written should not raise error
        self.formatter.write(data)

        data2 = DataSet(location=data.location, formatter=self.formatter)
        d_array = DataArray(name='dummy', array_id='x_set',  # existing array id in data
                            label='bla', units='a.u.', is_setpoint=False,
                            set_arrays=(), preset_data=np.zeros(5))
        data2.add_array(d_array)
        # test if d_array refers to same as array x_set in dataset
        self.assertTrue(d_array is data2.arrays['x_set'])
        data2.read()
        # test if reading did not overwrite dataarray
        self.assertTrue(d_array is data2.arrays['x_set'])
        # Testing if data was correctly updated into dataset
        self.checkArraysEqual(data2.arrays['x_set'], data.arrays['x_set'])
        self.checkArraysEqual(data2.arrays['y'], data.arrays['y'])
        self.formatter.close_file(data)
        self.formatter.close_file(data2)

    def test_dataset_closing(self):
        data = DataSet1D()
        self.formatter.write(data, flush=False)
        fp = data._h5_base_group.filename
        fp2 = fp[:-5]+'_2.hdf5'
        copy(fp, fp2)
        # Raises an error because the file was open and not flushed
        # This tests if this way of testing works
        with self.assertRaises(OSError):
            F2 = h5py.File(fp2)
        self.formatter.close_file(data)
        fp3 = fp[:-5]+'_3.hdf5'
        copy(fp, fp3)
        # Should now not raise an error because the file was properly closed
        F3 = h5py.File(fp3)

    def test_dataset_flush_after_write(self):
        data = DataSet1D()
        self.formatter.write(data, flush=True)
        fp = data._h5_base_group.filename
        fp2 = fp[:-5]+'_2.hdf5'
        copy(fp, fp2)
        # Opening this copy should not raise an error
        F2 = h5py.File(fp2)

    def test_dataset_finalize_closes_file(self):
        data = DataSet1D()
        # closing before file is written should not raise error
        self.formatter.write(data, flush=False)
        fp = data._h5_base_group.filename
        fp2 = fp[:-5]+'_2.hdf5'
        copy(fp, fp2)
        # Raises an error because the file was still open
        with self.assertRaises(OSError):
            F2 = h5py.File(fp2)
        # Attaching the formatter like this should not be neccesary
        data.formatter = self.formatter
        data.finalize()
        fp3 = fp[:-5]+'_4.hdf5'
        copy(fp, fp3)
        # Should now not raise an error because the file was properly closed
        F3 = h5py.File(fp3)





