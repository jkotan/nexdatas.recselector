#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2014 DESY, Jan Kotanski <jkotan@mail.desy.de>
#
#    nexdatas is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    nexdatas is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with nexdatas.  If not, see <http://www.gnu.org/licenses/>.
## \package test nexdatas
## \file UtilsTest.py
# unittests for field Tags running Tango Server
#
import unittest
import os
import sys
import subprocess
import random
import struct
import PyTango
import pickle
import json
from xml.dom import minidom
import binascii

import logging
logger = logging.getLogger()


import TestServerSetUp

from nxsrecconfig.Utils import Utils, TangoUtils, MSUtils, PoolUtils




## if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)

class Datum(object):
    def __init__(self, device, value_string = None):
        self.device = device
        self.value_string = value_string if value_string else []

class DB(object):
    def __init__(self):
        self.classdevices = {
            "NXSDataWriter":['test/nxsdatawriter/01','test/nxsdatawriter/02'],
            "NXSConfigServer":['test/nxsconfigserver/01','test/nxsconfigserver/02'],
            "Door":['test/door/01','test/door/02','test/door/03'],
            "MacroServer":['test/ms/01'],
            "TestServer":['ttestp09/testts/t1r228'],
            }
        pass

    def get_device_exported_for_class(self, class_name, filter= '*'):
        dd = Datum('device')
        if class_name in self.classdevices:
            dd.value_string = self.classdevices[class_name]
        else:
            dd.value_string = []
        return dd
    
class Pool(object):

    def __init__(self):
        self.AcqChannelList = []
        self.MeasurementGroupList = []
        self.ExpChannelList = []
        self.MotorList = []


class Server(object):

    def __init__(self, value=None):
        self.reset(value)

    def reset(self, value=None):
        self.value = value
        self.command = None
        self.exe = False
        self.var = None
        
    def command_inout(self,command, var=None):
        self.command = command
        self.var = var
        self.exe = True
        return self.value

class NoServer(object):

    def __init__(self, value=None):
        self.reset(value)

    def reset(self, value=None):
        self.value = value
        self.command = None
        self.exe = False
        self.var = None
        
    def testcommand(self,  var):
        self.command = 'testcommand'
        self.var = var
        self.exe = True
        return self.value

    def testcommand2(self):
        self.command = 'testcommand2'
        self.var = None
        self.exe = True
        return self.value

        

## test fixture
class UtilsTest(unittest.TestCase):

    ## constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)


        self._tfname = "field"
        self._tfname = "group"
        self._fattrs = {"short_name":"test","units":"m" }


        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"

        self._simps = TestServerSetUp.TestServerSetUp()
        self._simps2 = TestServerSetUp.TestServerSetUp( "ttestp09/testts/t2r228", "S2")
        self._simps3 = TestServerSetUp.TestServerSetUp( "ttestp09/testts/t3r228", "S3") 
        self._simps4 = TestServerSetUp.TestServerSetUp( "ttestp09/testts/t4r228", "S4")

        self.cnt = '{"units": {"0":{"channels":{},' \
            + ' "trigger_type":0, "id":0, "timer":"%s", "monitor":"%s"}}}'
        self.chnl = '{"ndim":0, "index":%s, "name":"%s", "data_type":"%s", "plot_type":%s, "enabled": true, "label": "%s", "instrument":null, "shape": [%s], "_controller_name": "%s", "conditioning": "", "full_name": "%s", "_unit_id": "0", "normalization": 0, "output":true, "plot_axes":[%s], "nexus_path": "", "data_units": "No unit", "source": "%s"}'


        try:
            self.__seed  = long(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            self.__seed  = long(time.time() * 256) 
         
        self.__rnd = random.Random(self.__seed)


        self._counter =  [1,-2,6,-8,9,-11]
        self._bools =  ["TruE","0","1","False","false", "True"]
        self._fcounter =  [1.1,-2.4,6.54,-8.456,9.456,-0.46545]
        self._dcounter =  [0.1,-2342.4,46.54,-854.456,9.243456,-0.423426545]
        self._logical =  [[True,False,True,False], [True,False,False,True], [False,False,True,True]]

        self._logical2 =  [[[True,False,True,False], [True,False,False,True]], 
                           [[False,False,True,True], [False,False,True,False]],
                           [[True,False,True,True], [False,False,True,False]]]

        self._mca1 = [[self.__rnd.randint(-100, 100) for e in range(256)] for i in range(3)]
        self._mca2 = [[self.__rnd.randint(0, 100) for e in range(256)] for i in range(3)]
        self._fmca1 = [[self.__rnd.randint(0, 100)/10. for e in range(256)] for i in range(3)]
#        self._fmca2 = [(float(e)/(100.+e)) for e in range(2048)]

        self._dates = [["1996-07-31T21:15:22.123+0600","2012-11-14T14:05:23.2344-0200",
                        "2014-02-04T04:16:12.43-0100","2012-11-14T14:05:23.2344-0200"],
                       ["1956-05-23T12:12:32.123+0400","1212-12-12T12:25:43.1267-0700",
                        "914-11-04T04:13:13.44-0000","1002-04-03T14:15:03.0012-0300"],                 
                       ["1966-02-21T11:22:02.113+0200","1432-12-11T11:23:13.1223-0300",
                        "1714-11-10T14:03:13.12-0400","1001-01-01T14:11:11.0011-0100"]]

        self._dates2 = [[["1996-07-31T21:15:22.123+0600","2012-11-14T14:05:23.2344-0200",
                          "2014-02-04T04:16:12.43-0100","2012-11-14T14:05:23.2344-0200"],
                         ["1996-07-31T21:15:22.123+0600","2012-11-14T14:05:23.2344-0200",
                          "2014-02-04T04:16:12.43-0100","2012-11-14T14:05:23.2344-0200"]],
                        [["1996-07-31T21:15:22.123+0600","2012-11-14T14:05:23.2344-0200",
                          "2014-02-04T04:16:12.43-0100","2012-11-14T14:05:23.2344-0200"],
                         ["956-05-23T12:12:32.123+0400","1212-12-12T12:25:43.1267-0700",
                          "914-11-04T04:13:13.44-0000","1002-04-03T14:15:03.0012-0300"]],
                        [["956-05-23T12:12:32.123+0400","1212-12-12T12:25:43.1267-0700",
                          "914-11-04T04:13:13.44-0000","1002-04-03T14:15:03.0012-0300"],                 
                         ["956-05-23T12:12:32.123+0400","1212-12-12T12:25:43.1267-0700",
                          "914-11-04T04:13:13.44-0000","1002-04-03T14:15:03.0012-0300"]]]

        self._pco1 = [[[self.__rnd.randint(0, 100) for e1 in range(8)]  for e2 in range(10)] for i in range(3)]
        self._fpco1 = [[[self.__rnd.randint(0, 100)/10. for e1 in range(8)]  for e2 in range(10)] for i in range(3)]

        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"


    ## test starter
    # \brief Common set up
    def setUp(self):       
        print "SEED =", self.__seed 
        self._simps.setUp()
        self._simps2.setUp()
        self._simps3.setUp()
        self._simps4.setUp()

    ## test closer
    # \brief Common tear down
    def tearDown(self):       
        self._simps4.tearDown()
        self._simps3.tearDown()
        self._simps2.tearDown()
        self._simps.tearDown()

    ## Exception tester
    # \param exception expected exception
    # \param method called method      
    # \param args list with method arguments
    # \param kwargs dictionary with method arguments
    def myAssertRaise(self, exception, method, *args, **kwargs):
        err = None
        try:
            error =  False
            method(*args, **kwargs)
        except exception, e:
            error = True
            err = e
        self.assertEqual(error, True)
        return err


    def myAssertDict(self, dct, dct2):
        logger.debug('dict %s' % type(dct))
        logger.debug("\n%s\n%s" % ( dct, dct2))
        self.assertTrue(isinstance(dct, dict))
        self.assertTrue(isinstance(dct2, dict))
        logger.debug("%s %s" %(len(dct.keys()), len(dct2.keys())))
        self.assertEqual(len(dct.keys()), len(dct2.keys()))
        for k,v in dct.items():
            logger.debug("%s  in %s" %(str(k), str(dct2.keys())))
            self.assertTrue(k in dct2.keys())
            if isinstance(v, dict):
                self.myAssertDict(v, dct2[k])
            else:
                logger.debug("%s , %s" %(str(v), str(dct2[k])))
                self.assertEqual(v, dct2[k])

    def checkstu(self, par, shape, dtype, unit):
        self.assertEqual(shape, par[0])
        self.assertEqual(dtype, par[1])
        self.assertEqual(unit if unit else 'No unit', par[2])


    ## constructor test
    # \brief It tests default settings
    def test_constructor(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        el = Utils()

        tTnp = {PyTango.DevLong64: "int64", PyTango.DevLong: "int32",
                PyTango.DevShort: "int16", PyTango.DevUChar: "uint8",
                PyTango.DevULong64: "uint64", PyTango.DevULong: "uint32",
                PyTango.DevUShort: "uint16", PyTango.DevDouble: "float64",
                PyTango.DevFloat: "float32", PyTango.DevString: "string",
                PyTango.DevBoolean: "bool", PyTango.DevEncoded:"encoded"}
        
        self.myAssertDict(tTnp, TangoUtils.tTnp)

    ## openProxy test
    # \brief It tests default settings
    def test_openProxy(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        self.myAssertRaise(PyTango.DevFailed, TangoUtils.openProxy, "sdf/testtestsf/d")

        dp = TangoUtils.openProxy(self._simps.new_device_info_writer.name)
        self.assertTrue(isinstance(dp, PyTango.DeviceProxy))
        self.assertEqual(dp.name(), self._simps.new_device_info_writer.name)
        dp.setState("RUNNING")
        dp = TangoUtils.openProxy(self._simps.new_device_info_writer.name)
        self._simps.stop()
        
        self.myAssertRaise(PyTango.DevFailed, TangoUtils.openProxy, 
                           self._simps.new_device_info_writer.name)

    ## getEnv test   
    def test_getsetEnv(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = {
            "ScanDir": [u'/tmp/',  "/tmp/sardana/" ],
            "ScanFile": [[u'sar4r.nxs'], [u'sar4r.nxs', u'sar5r.nxs']],
            "ScanID": [192, 123],
            "ScanNone": ["", "Something new"],
            "_ViewOptions": [{'ShowDial': True}, {'ShowDial': False}],
            }

        for k, vl in arr.items():
            self.assertEqual(
                vl[0], MSUtils.getEnv(
                    k, self._simps.new_device_info_writer.name))

        for k, vl in arr.items():
            MSUtils.setEnv(k, vl[1], 
                         self._simps.new_device_info_writer.name)
            self.assertEqual(vl[1], MSUtils.getEnv(
                    k, self._simps.new_device_info_writer.name))


    ## getEnv test   
    def test_getEnv(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = {
            "ScanDir": [u'/tmp/',  "/tmp/sardana/" ],
            "ScanFile": [[u'sar4r.nxs'], [u'sar4r.nxs', u'sar5r.nxs']],
            "ScanID": [192, 123],
            "blebleble": ["", "Something new"],
            "_ViewOptions": [{'ShowDial': True}, {'ShowDial': False}],
            }

        
        for k, vl in arr.items():
            self.assertEqual(
                vl[0], MSUtils.getEnv(
                    k, self._simps.new_device_info_writer.name))

        self.assertEqual(self._simps.dp.Environment[0],'pickle')
        en = pickle.loads(self._simps.dp.Environment[1])['new']
        
        for k, vl in arr.items():
            en[k] = vl[1]
            self._simps.dp.Environment =  (
                'pickle',
                pickle.dumps( {'new': en}))
            self.assertEqual(vl[1], MSUtils.getEnv(
                    k, self._simps.new_device_info_writer.name))

            

 

    ## setEnv test   
    def test_setEnv(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = {
            "ScanDir": [u'/tmp/',  "/tmp/sardana/" ],
            "ScanFile": [[u'sar4r.nxs'], [u'sar4r.nxs', u'sar5r.nxs']],
            "ScanID": [192, 123],
            "ScanNone": ["", "Something new"],
            "_ViewOptions": [{'ShowDial': True}, {'ShowDial': False}],
            }

        for k, vl in arr.items():
            self.assertEqual(
                vl[0], MSUtils.getEnv(
                    k, self._simps.new_device_info_writer.name))

        for k, vl in arr.items():
            MSUtils.setEnv(k, vl[1], 
                         self._simps.new_device_info_writer.name)

            self.assertEqual(self._simps.dp.Environment[0],'pickle')
            en = pickle.loads(self._simps.dp.Environment[1])['new']
            self.assertEqual(en[k], MSUtils.getEnv(
                    k, self._simps.new_device_info_writer.name))


    ## getProxies test   
    def test_getProxies(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        self.assertEqual(TangoUtils.getProxies([]), [])
        self.myAssertRaise(PyTango.DevFailed, TangoUtils.getProxies, ["bleble"])
        dpl = TangoUtils.getProxies([self._simps.new_device_info_writer.name])
        self.assertEqual(len(dpl), 1)
        self.assertEqual(type(dpl[0]), PyTango.DeviceProxy)
        self.assertEqual(dpl[0].name(), 
                         self._simps.new_device_info_writer.name)


        dpl = TangoUtils.getProxies([
                self._simps.new_device_info_writer.name,
                self._simps2.new_device_info_writer.name])
        self.assertEqual(len(dpl), 2)
        self.assertEqual(type(dpl[0]), PyTango.DeviceProxy)
        self.assertEqual(type(dpl[1]), PyTango.DeviceProxy)
        self.assertEqual(dpl[0].name(), 
                         self._simps.new_device_info_writer.name)
        self.assertEqual(dpl[1].name(), 
                         self._simps2.new_device_info_writer.name)



    ## getDeviceName test   
    def test_getDeviceName(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = [ "NXSDataWriter" , "" , "NXSConfigServer", "Door", 
                "MacroServer" , "bleble"]

        db = DB()
    
        for ar in arr:
            dd = TangoUtils.getDeviceName(db, ar)
            src = db.get_device_exported_for_class(ar).value_string
            dv = ''
            for server in src:
                try:
                    dp = PyTango.DeviceProxy(server)
                    dp.ping()
                    dv = server
                    break
                except:
                    pass
            self.assertEqual(dd, dv)


    ## getDeviceName test   
    def test_getDeviceName_OK(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = ["TestServer"]

        db = DB()
    
        for ar in arr:
            dd = TangoUtils.getDeviceName(db, ar)
            src = db.get_device_exported_for_class(ar).value_string
            dv = src[0] if len(src) else ''
            self.assertEqual(dd, dv)


    ## getDeviceName test   
    def test_getDeviceName_db(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = [ "NXSDataWriter" , "" , "NXSConfigServer", "Door", 
                "MacroServer" , "bleble"]

        db = PyTango.Database()
    
        for ar in arr:
            dd = TangoUtils.getDeviceName(db, ar)
            src = db.get_device_exported_for_class(ar).value_string
            dv = ''
            for server in src:
                try:
                    dp = PyTango.DeviceProxy(server)
                    dp.ping()
                    dv = server
                    break
                except:
                    pass
            self.assertEqual(dd, dv)
                
            
    ## getDeviceName test   
    def test_getMacroServer(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = [
            [self._simps.new_device_info_writer.name, 'test/door/1'],
            [self._simps.new_device_info_writer.name, 'test/door/2'],
            [self._simps2.new_device_info_writer.name, 'test/door/3'],
            ["", 'test/door/4'],
            ]

        self._simps2.dp.DoorList = [
            'test/door/2','test/door/3'
            ]
        db = DB()
        db.classdevices['MacroServer'] = [ 
            self._simps.new_device_info_writer.name,
            self._simps2.new_device_info_writer.name]

        for ar in arr:
            ms = MSUtils.getMacroServer(db, ar[1])
            self.assertEqual(ms, ar[0])


    ## getDeviceName test   
    def test_getMacroServer_db(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arr = [
            [self._simps.new_device_info_writer.name, 'test/door/1'],
            [self._simps.new_device_info_writer.name, 'test/door/2'],
            [self._simps2.new_device_info_writer.name, 'test/door/3'],
            ["", 'test/door/4'],
            ]

        self._simps2.dp.DoorList = [
            'test/door/2','test/door/3'
            ]
        db = DB()
        servers =  db.get_device_exported_for_class(
            "MacroServer").value_string

        alldoors = set()
        for sr in servers:
            try:
                dp = PyTango.DeviceProxy(sr)
            except:
                dp = None
            if dp:
                doors = dp.DoorList
                sdoors = set(doors) - alldoors
                for dr in sdoors:
                    ms = MSUtils.getMacroServer(db, dr)
                    self.assertEqual(ms, sr)
                alldoors.extends(sdoors)


    ## getDeviceName test   
    def test_getFullDeviceNames_empty(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            {"name":"test/ct/01", "full_name":"counter_01/Value"} ,
            {"name":"test/ct/02", "full_name":"counter_02/att"} ,
            {"name":"test/ct/03", "full_name":"counter_03/value"} ,
            {"name":"test/ct/04", "full_name":"counter_04/13"} ,
            {"name":"null", "full_name":"counter_04"} ,
            ]



        pool = Pool()
        pool.AcqChannelList = [json.dumps(a) for a in arr]
    
        import nxsrecconfig 
        dd = PoolUtils.getFullDeviceNames([])
        self.assertEqual(dd, {})

        dd = PoolUtils.getFullDeviceNames([], [arr[0]["name"]])
        self.assertEqual(dd, {})
        dd = PoolUtils.getFullDeviceNames([pool], [arr[4]["name"]])
        self.assertEqual(dd, {"null":""})
        


    ## getDeviceName test   


    ## getDeviceName test   
    def test_getFullDeviceNames_pool1(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "counter_01", "Value"],
            ["test/ct/02", "counter_02", "att"],
            ["test/ct/03", "counter_03", "value"],
            ["test/ct/04", "counter_04", "13"],
            ["null", "counter_04",""],
            ]

        pool = Pool()
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in arr]
    
        
        for ar in arr:
            dd = PoolUtils.getFullDeviceNames([pool], [ar[0]])
            self.assertEqual(dd, {ar[0]:ar[1]})
        

        dd = PoolUtils.getFullDeviceNames([pool], [ar[0] for ar in arr])
        self.assertEqual(dd, dict((ar[0],ar[1]) for ar in arr))

        dd = PoolUtils.getFullDeviceNames([pool])
        self.assertEqual(dd, dict((ar[0],ar[1]) for ar in arr))
            


    def test_getFullDeviceNames_pool2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "counter_01", "Value"],
            ["test/ct/02", "counter_02", "att"],
            ["test/ct/03", "counter_03", "value"],
            ["test/ct/04", "counter_04", "13"],
            ["null", "counter_04",""],
            ]


        arr2 = [
            ["test/mca/01", "mca_01", "1"],
            ["test/mca/02", "mca_02", "a"],
            ["test/sca/03", "my_sca_03", "1"],
            ["test/sca/04", "mysca_04", "123"],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in arr]
        pool2.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in arr2]
    
        
        for ar in arr:
            dd = PoolUtils.getFullDeviceNames([pool, pool2], [ar[0]])
            self.assertEqual(dd, {ar[0]:ar[1]})

        for ar in arr2:
            dd = PoolUtils.getFullDeviceNames([pool, pool2], [ar[0]])
            self.assertEqual(dd, {ar[0]:ar[1]})
        

        res = dict((ar[0],ar[1]) for ar in arr)
        res.update(dict((ar[0],ar[1]) for ar in arr2))

        lst = [ar[0] for ar in arr]
        lst.extend([ar[0] for ar in arr2])

        dd = PoolUtils.getFullDeviceNames([pool, pool2], lst)
        self.assertEqual(dd, res)

        dd = PoolUtils.getFullDeviceNames([pool, pool2])
        self.assertEqual(dd, res)

        lst.extend(["sfdsdf","sdfsfd"])
        dd = PoolUtils.getFullDeviceNames([pool, pool2], lst)
        self.assertEqual(dd, res)
            



    ## getDeviceName test   
    def test_getAliases_empty(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            {"name":"test/ct/01", "full_name":"counter_01/Value"} ,
            {"name":"test/ct/02", "full_name":"counter_02/att"} ,
            {"name":"test/ct/03", "full_name":"counter_03/value"} ,
            {"name":"test/ct/04", "full_name":"counter_04/13"} ,
            {"name":"conternull", "full_name":"null"} ,
            ]



        pool = Pool()
        pool.AcqChannelList = [json.dumps(a) for a in arr]
    
        import nxsrecconfig 
        dd = PoolUtils.getAliases([])
        self.assertEqual(dd, {})

        dd = PoolUtils.getAliases([], [arr[0]["full_name"]])
        self.assertEqual(dd, {})
        dd = PoolUtils.getAliases([pool], [arr[4]["full_name"]])
        self.assertEqual(dd, {})
        


    ## getDeviceName test   


    ## getDeviceName test   
    def test_getAliases_pool1(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "counter_01", "Value"],
            ["test/ct/02", "counter_02", "att"],
            ["test/ct/03", "counter_03", "value"],
            ["test/ct/04", "counter_04", "13"],
            ["counter_04","null",""],
            ]

        pool = Pool()
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in arr]
    
        
        for ar in arr:
            dd = PoolUtils.getAliases([pool], [ar[1]])
            self.assertEqual(dd, {ar[1]:ar[0]})
        

        dd = PoolUtils.getAliases([pool], [ar[1] for ar in arr])
        self.assertEqual(dd, dict((ar[1],ar[0]) for ar in arr))

        dd = PoolUtils.getAliases([pool])
        self.assertEqual(dd, dict((ar[1],ar[0]) for ar in arr))
            


    def test_getAliases_pool2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "counter_01", "Value"],
            ["test/ct/02", "counter_02", "att"],
            ["test/ct/03", "counter_03", "value"],
            ["test/ct/04", "counter_04", "13"],
            ["counter_04", "null",""],
            ]


        arr2 = [
            ["test/mca/01", "mca_01", "1"],
            ["test/mca/02", "mca_02", "a"],
            ["test/sca/03", "my_sca_03", "1"],
            ["test/sca/04", "mysca_04", "123"],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in arr]
        pool2.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in arr2]
    
        
        for ar in arr:
            dd = PoolUtils.getAliases([pool, pool2], [ar[1]])
            self.assertEqual(dd, {ar[1]:ar[0]})

        for ar in arr2:
            dd = PoolUtils.getAliases([pool, pool2], [ar[1]])
            self.assertEqual(dd, {ar[1]:ar[0]})
        

        res = dict((ar[1],ar[0]) for ar in arr)
        res.update(dict((ar[1],ar[0]) for ar in arr2))

        lst = [ar[1] for ar in arr]
        lst.extend([ar[1] for ar in arr2])

        dd = PoolUtils.getAliases([pool, pool2], lst)
        self.assertEqual(dd, res)

        dd = PoolUtils.getAliases([pool, pool2])
        self.assertEqual(dd, res)

        lst.extend(["sfdsdf","sdfsfd"])
        dd = PoolUtils.getAliases([pool, pool2], lst)
        self.assertEqual(dd, res)
            
        


    ## getDeviceName test   
    def test_getMntGrpName_empty(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            {"name":"test/ct/01", "full_name":"mntgrp_01e"} ,
            {"name":"test/ct/02", "full_name":"mntgrp_02att"} ,
            {"name":"test/ct/03", "full_name":"mntgrp_03value"} ,
            {"name":"test/ct/04", "full_name":"mntgrp_04/13"} ,
            {"name":"null", "full_name":"mntgrp_04"} ,
            ]



        pool = Pool()
        pool.MeasurementGroupList = [json.dumps(a) for a in arr]
    
        import nxsrecconfig 
        dd = PoolUtils.getFullDeviceNames([])
        self.assertEqual(dd, {})

        dd = PoolUtils.getMntGrpName([], arr[0]["name"])
        self.assertEqual(dd, '')
        dd = PoolUtils.getMntGrpName([pool], arr[4]["name"])
        self.assertEqual(dd, arr[4]["full_name"])


    def test_getMntGrpName_pool1(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "mntgrp_01Value"],
            ["test/ct/02", "mntgrp_02att"],
            ["test/ct/03", "mntgrp_03value"],
            ["test/ct/04", "mntgrp_0413"],
            ["null", "mntgrp_04"],
            ]



        pool = Pool()
        pool.MeasurementGroupList = [json.dumps(
                {"name":a[0], "full_name":a[1]}) for a in arr]
    
        
        for ar in arr:
            dd = PoolUtils.getMntGrpName([pool], ar[0])
            self.assertEqual(dd, ar[1])

        

        dd = PoolUtils.getMntGrpName([pool], "adsasd")
        self.assertEqual(dd, '')


    def test_getMntGrpName_pool2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "mntgrp_01Value"],
            ["test/ct/02", "mntgrp_02att"],
            ["test/ct/03", "mntgrp_03value"],
            ["test/ct/04", "mntgrp_0413"],
            ["null", "mntgrp_04"],
            ]


        arr2 = [
            ["test/mca/01", "mgca_011"],
            ["test/mca/02", "mgca_02a"],
            ["test/sca/03", "mgy_sca_031"],
            ["test/sca/04", "mntysca_04123"],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.MeasurementGroupList = [json.dumps(
                {"name":a[0], "full_name":a[1]}) for a in arr]
        pool2.MeasurementGroupList = [json.dumps(
                {"name":a[0], "full_name":a[1]}) for a in arr2]
    
        
        for ar in arr:
            dd = PoolUtils.getMntGrpName([pool, pool2], ar[0])
            self.assertEqual(dd, ar[1])

        for ar in arr2:
            dd = PoolUtils.getMntGrpName([pool, pool2], ar[0])
            self.assertEqual(dd, ar[1])
        

        dd = PoolUtils.getMntGrpName([pool, pool2], "adsasd")
        self.assertEqual(dd, '')
            




    ## getDeviceName test   
    def test_getMntGrps(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            {"name":"test/ct/01", "full_name":"mntgrp_01e"} ,
            {"name":"test/ct/02", "full_name":"mntgrp_02att"} ,
            {"name":"test/ct/03", "full_name":"mntgrp_03value"} ,
            {"name":"test/ct/04", "full_name":"mntgrp_04/13"} ,
            {"name":"null", "full_name":"mntgrp_04"} ,
            ]

        arr2 = [
            {"name":"test/ct/011", "full_name":"mntgrp_01e1"} ,
            {"name":"test/ct/021", "full_name":"mntgrp_02att1"} ,
            {"name":"test/ct/031", "full_name":"mntgrp_03value1"} ,
            {"name":"test/ct/041", "full_name":"mntgrp_04/131"} ,
            {"name":"null", "full_name":"mntgrp_041"} ,
            ]



        pool = Pool()
        pool.MeasurementGroupList = [json.dumps(a) for a in arr]
        pool2 = Pool()
        pool2.MeasurementGroupList = [json.dumps(a) for a in arr2]
        import nxsrecconfig 
        dd = PoolUtils.getFullDeviceNames([])
        self.assertEqual(dd, {})

        self.myAssertRaise(Exception, PoolUtils.getMntGrps, None)
        dd = PoolUtils.getMntGrps([pool])
        self.assertEqual(dd, [a["name"] for a in arr])
        self.myAssertRaise(Exception, PoolUtils.getMntGrps, None)
        dd = PoolUtils.getMntGrps([pool, pool2])
        res = [a["name"] for a in arr] 
        res.extend([a["name"] for a in arr2])
        self.assertEqual(dd, res)






    ## getDeviceControllers test   
    def test_getDeviceControllers_empty(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            {"name":"test/ct/01", "controller":"counter_01/Value"} ,
            {"name":"test/ct/02", "controller":"counter_02/att"} ,
            {"name":"test/ct/03", "controller":"counter_03/value"} ,
            {"name":"test/ct/04", "controller":"counter_04/13"} ,
            {"name":"null", "controller":"counter_04"} ,
            ]



        pool = Pool()
        pool.ExpChannelList = [json.dumps(a) for a in arr]
    
        import nxsrecconfig 
        dd = PoolUtils.getDeviceControllers([], "test/ct/01")
        self.assertEqual(dd, {})

        dd = PoolUtils.getDeviceControllers([], arr[0]["name"])
        self.assertEqual(dd, {})
        dd = PoolUtils.getDeviceControllers([pool], arr[4]["name"])
        self.assertEqual(dd, {arr[4]["name"]:arr[4]["controller"]})
        
        dd = PoolUtils.getDeviceControllers([pool], "sdfds")
        self.assertEqual(dd, {})




    ## getDeviceControllers test   
    def test_getDeviceControllers_pool1(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "counter_01"],
            ["test/ct/02", "counter_02att"],
            ["test/ct/03", "counter_03value"],
            ["test/ct/04", "counter_0413"],
            ["null", "counter_04"],
            ]

        pool = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr]
    
        
        for ar in arr:
            dd = PoolUtils.getDeviceControllers([pool], [ar[0]])
            self.assertEqual(dd, {ar[0]:ar[1]})
        

        dd = PoolUtils.getDeviceControllers([pool], [ar[0] for ar in arr])
        self.assertEqual(dd, dict((ar[0],ar[1]) for ar in arr))

            


    def test_getDeviceControllers_pool2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "counter_01Value"],
            ["test/ct/02", "counter_02att"],
            ["test/ct/03", "counter_03alue"],
            ["test/ct/04", "counter_0413"],
            ["null", "counter_04"],
            ]


        arr2 = [
            ["test/mca/01", "mca_01"],
            ["test/mca/02", "mca_02"],
            ["test/sca/03", "my_sca1"],
            ["test/sca/04", "mysca_123"],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr2]
    
        
        for ar in arr:
            dd = PoolUtils.getDeviceControllers([pool, pool2], [ar[0]])
            self.assertEqual(dd, {ar[0]:ar[1]})

        for ar in arr2:
            dd = PoolUtils.getDeviceControllers([pool, pool2], [ar[0]])
            self.assertEqual(dd, {ar[0]:ar[1]})
        

        res = dict((ar[0],ar[1]) for ar in arr)
        res.update(dict((ar[0],ar[1]) for ar in arr2))

        lst = [ar[0] for ar in arr]
        lst.extend([ar[0] for ar in arr2])

        dd = PoolUtils.getDeviceControllers([pool, pool2], lst)
        self.assertEqual(dd, res)


        lst.extend(["sfdsdf","sdfsfd"])
        dd = PoolUtils.getDeviceControllers([pool, pool2], lst)
        self.assertEqual(dd, res)
            





    ## getExperimentalChannels test   
    def test_getExperimentalChannels_pool1(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            {"name":"test/ct/01", "controller":"counter_01/Value"} ,
            {"name":"test/ct/02", "controller":"counter_02/att"} ,
            {"name":"test/ct/03", "controller":"counter_03/value"} ,
            {"name":"test/ct/04", "controller":"counter_04/13"} ,
            {"name":"null", "controller":"counter_04"} ,
            ]

        arr2 = [
            ["test/mca/01", "mca_01"],
            ["test/mca/02", "mca_02"],
            ["test/sca/03", "my_sca1"],
            ["test/sca/04", "mysca_123"],
            ]


        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(a) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr2]
    
        import nxsrecconfig 
        dd = PoolUtils.getExperimentalChannels([])
        self.assertEqual(dd, [])

        dd = PoolUtils.getExperimentalChannels([])
        self.assertEqual(dd, [])
        dd = PoolUtils.getExperimentalChannels([pool])
        self.assertEqual(dd, [a["name"] for a in arr])

        dd = PoolUtils.getExperimentalChannels([pool, pool2])
        res = [a["name"] for a in arr]
        res.extend([a[0] for a in arr2])
        self.assertEqual(dd, res)


    ## getMotorNames test   
    def test_getMotorNames_pool1(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            {"name":"test/ct/01", "controller":"counter_01/Value"} ,
            {"name":"test/ct/02", "controller":"counter_02/att"} ,
            {"name":"test/ct/03", "controller":"counter_03/value"} ,
            {"name":"test/ct/04", "controller":"counter_04/13"} ,
            {"name":"null", "controller":"counter_04"} ,
            ]

        arr2 = [
            ["test/mca/01", "mca_01"],
            ["test/mca/02", "mca_02"],
            ["test/sca/03", "my_sca1"],
            ["test/sca/04", "mysca_123"],
            ]


        pool = Pool()
        pool2 = Pool()
        pool.MotorList = [json.dumps(a) for a in arr]
        pool2.MotorList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr2]
    
        import nxsrecconfig 
        dd = PoolUtils.getMotorNames([])
        self.assertEqual(dd, [])

        dd = PoolUtils.getMotorNames([])
        self.assertEqual(dd, [])
        dd = PoolUtils.getMotorNames([pool])
        self.assertEqual(dd, [a["name"] for a in arr])

        dd = PoolUtils.getMotorNames([pool, pool2])
        res = [a["name"] for a in arr]
        res.extend([a[0] for a in arr2])
        self.assertEqual(dd, res)


    def test_getTimers(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", ["CTExpChannel"],
             "haso228k:10000/expchan/dgg2_exp_00/1/Value"],
            ["test/ct/02", ["conem", "CTExpChannel"],
                            "haso228k:10000/expchan/dgg2_exp_01/1/Value"],
            ["test/ct/03", ["CTExpChannel", "ZeroDChannel"],
             "haso228k:10000/expchan/dgg2_exp_02/1/Value"],
            ["test/ct/04", ["oneD","CTExpChannel"],
             "haso228k:10000/expchan/dgg2_exp_03/1/Value"],
            ["null", ["counter_04"],
             "haso228k:10000/expchan/dg2_exp_01/1/Value"],
            ]


        arr2 = [
            ["test/mca/01", ["CTExpChannel"],
             "haso228k:10000/expchan/dgg2_exp_01/1/Value"],
            ["test/mca/02", ["CTExpChannel2","CTExpChannel1"],"haso228k:10000/expchan/dg2_exp_01/1/Value"],
            ["test/sca/03", ["CTExpChannel3","CTExpChannel123"],"haso228k:10000/expchan/dg2_exp_01/1/Value"],
            ["test/sca/04", ["CTExpChannel","CTExpChannel2","CTExpChannel3"], 
            "haso228k:10000/expchan/dgg2_exp_01/1/Value"],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "interfaces":a[1],"source":a[2]}) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "interfaces":a[1],"source":a[2]}) for a in arr2]

        dd = PoolUtils.getTimers([])
        self.assertEqual(dd, [])

        lst = [ar[0] for ar in arr if  "CTExpChannel" in ar[1]]

        dd = PoolUtils.getTimers([pool])
        self.assertEqual(dd, lst)

        lst.extend([ar[0] for ar in arr2 if  "CTExpChannel" in ar[1]])
    
        dd = PoolUtils.getTimers([pool, pool2])
        self.assertEqual(dd, lst)
            



    def oldtest_addDevice_empty(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        arr = [
            ["test/ct/01", "counter_01Value"],
            ["test/ct/02", "counter_02att"],
            ["test/ct/03", "counter_03alue"],
            ["test/ct/04", "counter_0413"],
            ["null", "counter_04"],
            ]


        arr2 = [
            ["test/mca/01", "mca_01"],
            ["test/mca/02", "mca_02"],
            ["test/sca/03", "my_sca1"],
            ["test/sca/04", "mysca_123"],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr2]
    


        hsh = {}
        res =  Utils.addDevice("", [],[], hsh,"", 0)
        self.assertEqual(res, 0)
        self.assertEqual(hsh, {})

        hsh = {}
        res =  Utils.addDevice("", [], [pool, pool2], hsh, "", 0 )
        self.assertEqual(res, 0)
        self.assertEqual(hsh, {})

        hsh = {}
        res =  Utils.addDevice("test/ct/012134", [], [pool, pool2], hsh, "", 0)
        self.assertEqual(res, 0)
        self.assertEqual(hsh, {})





    def oldtest_addDevice_controller(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        


        aarr = [
            ["test/ct/01", self._simps.new_device_info_writer.name, "Value"],
            ["test/ct/02", self._simps.new_device_info_writer.name, "att"],
            ["test/ct/03", self._simps2.new_device_info_writer.name, "value"],
            ["test/ct/04", self._simps2.new_device_info_writer.name, "13"],
            ["null", self._simps2.new_device_info_writer.name,""],
            ]


        aarr2 = [
            ["test/mca/01", "mca_01", "1"],
            ["test/mca/02", "mca_02", "a"],
            ["test/sca/03", "my_sca_03", "1"],
            ["test/sca/04", "mysca_04", "123"],
            ]

        arr = [
            ["test/ct/01", "cntl_01Value", ["CTExpChannel"]],
            ["test/ct/02", "cntl_02att", ["conem", "CTExpChannel"]],
            ["test/ct/03", "cntl_03alue", ["CTExpChannel", "ZeroDChannel"]],
            ["test/ct/04", "cntl_0413", ["oneD","CTExpChannel"]],
            ["null", "cntl_04", ["counter_04"]],
            ]


        arr2 = [
            ["test/mca/01", "mca_01", ["CTExpChannel"]],
            ["test/mca/02", "mca_02", ["conem", "CTExpChannel"]],
            ["test/sca/03", "my_sca1", ["CTExpChannel2", "ZeroDChannel"]],
            ["test/sca/04", "mysca_123", ["CTExpChannel","CTExpChannel2","CTExpChannel3"]],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr2]
    



        hsh = {}
        self.myAssertRaise(PyTango.DevFailed, Utils.addDevice,
                           arr[0][0], [], [pool, pool2], hsh, "", 0)
        res = json.loads(self.cnt % ("",""))
        fr = {}
        fr['controllers'] = {}
        fr['controllers'][arr[0][1]]= res
        self.assertEqual(hsh, fr)

        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr]
        pool2.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr2]

        hsh = {}
        res = Utils.addDevice(arr[0][0], [], [pool, pool2], hsh, "", 0)
        self.assertEqual(res, 1)
        jres = json.loads(self.cnt % ("",""))
        fr = {}
        fr['controllers'] = {}
        fr['controllers'][arr[0][1]]= jres
        ch = json.loads(self.chnl % (0,arr[0][0], "float64",
                                     "1",arr[0][0],"",arr[0][1],aarr[0][1],'"<mov>"',
                                "%s/%s" %(aarr[0][1], 'Value')))
        fr['controllers'][arr[0][1]]['units']['0']['channels'][aarr[0][1]] = ch
        self.myAssertDict(hsh, fr)

        ch = json.loads(self.chnl % (0,arr[0][0], "float64","1",
                                     arr[0][0],"",arr[0][1],aarr[0][1],'"<mov>"',
                                "%s/%s" %(aarr[0][1], 'Value')))
        fr['controllers'][arr[0][1]]['units']['0']['channels'][aarr[0][1]] = ch
        self.myAssertDict(hsh, fr)


        hsh = {}
        res = Utils.addDevice(arr[0][0], [], [pool, pool2], hsh, aarr[0][0], 0)
        self.assertEqual(res, 1)

        jres = json.loads(self.cnt % (aarr[0][1],aarr[0][1]))
        fr = {}
        fr['controllers'] = {}
        fr['controllers'][arr[0][1]]= jres
        ch = json.loads(self.chnl % (0, arr[0][0], "float64","1",
                                     arr[0][0],"",arr[0][1],aarr[0][1],'"<mov>"',
                                "%s/%s" %(aarr[0][1], 'Value')))
        fr['controllers'][arr[0][1]]['units']['0']['channels'][aarr[0][1]] = ch
        self.myAssertDict(hsh, fr)



    def oldtest_addDevice_controller_separate_ctrls(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        aarr = [
            ["test/ct/01", self._simps.new_device_info_writer.name, "Value"],
            ["test/ct/02", self._simps.new_device_info_writer.name, "att"],
            ["test/ct/03", self._simps2.new_device_info_writer.name, "value"],
            ["test/ct/04", self._simps2.new_device_info_writer.name, "13"],
            ["null", self._simps2.new_device_info_writer.name,""],
            ]

        arr = [
            ["test/ct/01", "cntl_01Value", ["CTExpChannel"]],
            ["test/ct/02", "cntl_02att", ["conem", "CTExpChannel"]],
            ["test/ct/03", "cntl_03alue", ["CTExpChannel", "ZeroDChannel"]],
            ["test/ct/04", "cntl_01Value413", ["oneD","CTExpChannel"]],
            ["null", "cntl_04", ["counter_04"]],
            ]


        aarr2 = [
            ["test/mca/01", self._simps.new_device_info_writer.name, "1"],
            ["test/mca/02", self._simps.new_device_info_writer.name, "a"],
            ["test/sca/03", self._simps2.new_device_info_writer.name, "1"],
            ["test/sca/04", self._simps2.new_device_info_writer.name, "123"],
            ]

        arr2 = [
            ["test/mca/01", "mca_01", ["CTExpChannel"]],
            ["test/mca/02", "mca_02", ["conem", "CTExpChannel"]],
            ["test/sca/03", "my_sca1", ["CTExpChannel2", "ZeroDChannel"]],
            ["test/sca/04", "mysca_123", ["CTExpChannel","CTExpChannel2","CTExpChannel3"]],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr2]
    
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr]
        pool2.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr2]

        hsh = {}
        iindex = 123
        index = iindex
        for i, a in enumerate(aarr):
            logger.debug("i = %s"% i)
            index = Utils.addDevice(a[0], [], [pool, pool2], hsh, a[0], index)
            self.assertEqual(index, iindex+1+i)
        fr = {}
        fr['controllers'] = {}

        for i, a in enumerate(aarr):
            jres = json.loads(self.cnt % (a[1],a[1]))
            fr['controllers'][arr[i][1]]= jres
            ch = json.loads(self.chnl % (iindex+i, a[0], "float64","1",
                                         a[0],"",arr[i][1],a[1],'"<mov>"',
                                    "%s/%s" %(a[1], 'Value')))
            fr['controllers'][arr[i][1]]['units']['0']['channels'][a[1]] = ch
        self.myAssertDict(hsh, fr)


    def oldtest_addDevice_controller_separate_ctrls_2pools(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        aarr = [
            ["test/ct/01", self._simps.new_device_info_writer.name, "Value"],
            ["test/ct/02", self._simps.new_device_info_writer.name, "att"],
            ["test/ct/03", self._simps2.new_device_info_writer.name, "value"],
            ["test/ct/04", self._simps2.new_device_info_writer.name, "13"],
            ["null", self._simps2.new_device_info_writer.name,""],
            ]

        arr = [
            ["test/ct/01", "cntl_01Value", ["CTExpChannel"]],
            ["test/ct/02", "cntl_02att", ["conem", "CTExpChannel"]],
            ["test/ct/03", "cntl_03alue", ["CTExpChannel", "ZeroDChannel"]],
            ["test/ct/04", "cntl_01Value413", ["oneD","CTExpChannel"]],
            ["null", "cntl_04", ["counter_04"]],
            ]

        aarr2 = [
            ["test/mca/01", self._simps.new_device_info_writer.name, "1"],
            ["test/mca/02", self._simps.new_device_info_writer.name, "a"],
            ["test/sca/03", self._simps2.new_device_info_writer.name, "1"],
            ["test/sca/04", self._simps2.new_device_info_writer.name, "123"],
            ]

        arr2 = [
            ["test/mca/01", "mca_01", ["CTExpChannel"]],
            ["test/mca/02", "mca_02", ["conem", "CTExpChannel"]],
            ["test/sca/03", "my_sca1", ["CTExpChannel2", "ZeroDChannel"]],
            ["test/sca/04", "mysca_123", ["CTExpChannel","CTExpChannel2","CTExpChannel3"]],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr2]
    
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr]
        pool2.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr2]

        hsh = {}
        iindex = 123
        index = iindex
        for i, a in enumerate(aarr):
            logger.debug("i = %s"% i)
            index = Utils.addDevice(a[0], [], [pool, pool2], hsh, a[0], index)
            self.assertEqual(index, iindex+1+i)

        for i, a in enumerate(aarr2):
            logger.debug("i = %s"% i)
            index = Utils.addDevice(a[0], [], [pool, pool2], hsh, a[0], index)
            self.assertEqual(index, iindex+1+i+len(aarr))

        fr = {}
        fr['controllers'] = {}
        for i, a in enumerate(aarr):
            jres = json.loads(self.cnt % (a[1],a[1]))
            fr['controllers'][arr[i][1]]= jres
            ch = json.loads(self.chnl % (iindex+i, a[0], "float64", 
                                         "1",a[0],"",arr[i][1],a[1],'"<mov>"',
                                         "%s/%s" %(a[1], 'Value')))
            fr['controllers'][arr[i][1]]['units']['0']['channels'][a[1]] = ch
        for i, a in enumerate(aarr2):
            jres = json.loads(self.cnt % (a[1],a[1]))
            fr['controllers'][arr2[i][1]]= jres
            ch = json.loads(self.chnl % (iindex+i+len(aarr), a[0], "float64",
                                         "1",a[0],"",arr2[i][1],a[1],'"<mov>"',
                                         "%s/%s" %(a[1], 'Value')))
            fr['controllers'][arr2[i][1]]['units']['0']['channels'][a[1]] = ch
        self.myAssertDict(hsh, fr)
            
            


    def oldtest_addDevice_controller_ctrls(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        
        aarr = [
            ["test/ct/01", self._simps.new_device_info_writer.name, "Value"],
            ["test/ct/02", self._simps2.new_device_info_writer.name, "att"],
            ["test/ct/03", self._simps3.new_device_info_writer.name, "value"],
            ["test/ct/04", self._simps4.new_device_info_writer.name, "13"],
            ]

        arr = [
            ["test/ct/01", "cntl_01", ["CTExpChannel"]],
            ["test/ct/02", "cntl_01", ["conem", "CTExpChannel"]],
            ["test/ct/03", "cntl_01", ["CTExpChannel", "ZeroDChannel"]],
            ["test/ct/04", "cntl_01", ["oneD","CTExpChannel"]],
            ]


        aarr2 = [
            ["test/mca/01", self._simps.new_device_info_writer.name, "1"],
            ["test/mca/02", self._simps.new_device_info_writer.name, "a"],
            ["test/sca/03", self._simps2.new_device_info_writer.name, "1"],
            ["test/sca/04", self._simps2.new_device_info_writer.name, "123"],
            ]

        arr2 = [
            ["test/mca/01", "mca_01", ["CTExpChannel"]],
            ["test/mca/02", "mca_02", ["conem", "CTExpChannel"]],
            ["test/sca/03", "my_sca1", ["CTExpChannel2", "ZeroDChannel"]],
            ["test/sca/04", "mysca_123", ["CTExpChannel","CTExpChannel2","CTExpChannel3"]],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr2]
    
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr]
        pool2.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr2]

        hsh = {}
        iindex = 123
        index = iindex
        for i, a in enumerate(aarr):
            logger.debug("i = %s"% i)
            index = Utils.addDevice(a[0], [], [pool, pool2], hsh, aarr[0][0], index)
            self.assertEqual(index, iindex+1 + i)
        fr = {}
        fr['controllers'] = {}
        jres = json.loads(self.cnt % (aarr[0][1],aarr[0][1]))
        fr['controllers'][arr[0][1]]= jres

        for i, a in enumerate(aarr):
            ch = json.loads(self.chnl % (iindex+i, a[0], "float64",
                                         "1",a[0],"",arr[i][1],a[1],'"<mov>"',
                                         "%s/%s" %(a[1], 'Value')))
            fr['controllers'][arr[i][1]]['units']['0']['channels'][a[1]] = ch
        self.myAssertDict(hsh, fr)


    def oldtest_addDevice_controller_ctrls_2pools(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        
        aarr = [
            ["test/ct/01", self._simps.new_device_info_writer.name, "Value"],
            ["test/ct/02", self._simps2.new_device_info_writer.name, "att"],
            ["test/ct/03", self._simps3.new_device_info_writer.name, "value"],
            ["test/ct/04", self._simps4.new_device_info_writer.name, "13"],
            ]

        arr = [
            ["test/ct/01", "cntl_01", ["CTExpChannel"]],
            ["test/ct/02", "cntl_01", ["conem", "CTExpChannel"]],
            ["test/ct/03", "cntl_01", ["CTExpChannel", "ZeroDChannel"]],
            ["test/ct/04", "cntl_01", ["oneD","CTExpChannel"]],
            ]

        pool = Pool()
        pool2 = Pool()
        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr[:2]]
        pool2.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1], "interfaces":a[2]}) for a in arr[2:]]
    
        pool.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr[:2]]
        pool2.AcqChannelList = [json.dumps(
                {"name":a[0], "full_name":"%s/%s" % (a[1], a[2])}) for a in aarr[2:]]

        hsh = {}
        iindex = 123
        index = iindex
        for i, a in enumerate(aarr):
            logger.debug("i = %s"% i)
            index = Utils.addDevice(a[0], [], [pool, pool2], hsh, aarr[0][0], index)
            self.assertEqual(index, iindex+1 + i)
        fr = {}
        fr['controllers'] = {}
        jres = json.loads(self.cnt % (aarr[0][1],aarr[0][1]))
        fr['controllers'][arr[0][1]]= jres

        for i, a in enumerate(aarr):
            ch = json.loads(self.chnl % (iindex+i, a[0], "float64","1",
                                         a[0],"",arr[i][1],a[1],'"<mov>"',
                                         "%s/%s" %(a[1], 'Value')))
            fr['controllers'][arr[i][1]]['units']['0']['channels'][a[1]] = ch
        self.myAssertDict(hsh, fr)

            
    def test_getRecord(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        dom = minidom.parseString("<tag></tag>")
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), "")

        dom = minidom.parseString("<tag><device/></tag>")
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), "")

        host = 'haso2'*self.__rnd.randint(1, 3)
        dom = minidom.parseString(
            '<tag><device hostname="%s"></device></tag>' % (host))
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), '')

        host = 'haso2'*self.__rnd.randint(1, 3)
        dev = 'defv'*self.__rnd.randint(1, 3)
        dom = minidom.parseString(
            '<tag><device hostname="%s" /><record name="%s" /></tag>' % (host,dev))
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), dev)

        host = 'haso2'*self.__rnd.randint(1, 3)
        rec = 'recfv'*self.__rnd.randint(1, 3)
        dev = 'devfv/'*self.__rnd.randint(1, 3)
        dom = minidom.parseString(
            '<tag><device name="%s" /><record name="%s" /></tag>' % (dev, rec))
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), "%s/%s" % (dev, rec))

        host = 'haso2'*self.__rnd.randint(1, 3)
        rec = 'recfv'*self.__rnd.randint(1, 3)
        dev = 'devfv/'*self.__rnd.randint(1, 3)
        port = 10000
        dom = minidom.parseString(
            '<tag><device name="%s" hostname="%s" /><record name="%s" /></tag>' % (dev, host, rec))
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), "%s:%s/%s/%s" % (host, port, dev, rec))


        host = 'haso2'*self.__rnd.randint(1, 3)
        rec = 'recfv'*self.__rnd.randint(1, 3)
        dev = 'devfv/'*self.__rnd.randint(1, 3)
        port = 10000*self.__rnd.randint(1, 3)
        dom = minidom.parseString(
            '<tag><device name="%s" port="%s" /><record name="%s" /></tag>' % (dev, port, rec))
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), "%s/%s" % (dev, rec))
        

        host = 'haso2'*self.__rnd.randint(1, 3)
        rec = 'recfv'*self.__rnd.randint(1, 3)
        dev = 'devfv/'*self.__rnd.randint(1, 3)
        port = 10000*self.__rnd.randint(1, 3)
        dom = minidom.parseString(
            '<tag><device name="%s" hostname="%s" port="%s"/><record name="%s" /></tag>' % (
                dev, host, port, rec))
        node = dom.getElementsByTagName("tag")
        self.assertEqual(Utils.getRecord(node[0]), "%s:%s/%s/%s" % (host, port, dev, rec))

    def test_stringToDictJson(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        fac = self.__rnd.randint(2, 10)
        fac2 = self.__rnd.randint(2, 10)
        arg = [
            ["", {}],
            ["Not initialised", {}],
            ["some True", {"some":"True"}],
            ["some trUe", {"some":"trUe"}],
            ["some falSe", {"some":"falSe"}],
            ["some False", {"some":"False"}],
            ["some,False;some2:sfd,som.e4 ;gdg", 
             {"some":"False","some2":"sfd","som.e4":"gdg"}],
            ["some,False;some2:sfd,som.e4 gdg:", 
             {"some":"False","some2":"sfd","som.e4":"gdg"}],
            ["some False some2 sfd some4 gdg", 
             {"some":"False","some2":"sfd","some4":"gdg"}],
            ['{"some":"False","some2":"sfd","some4":"gdg"}', 
             {"some":"False","some2":"sfd","some4":"gdg"}],
            ['{"some":false,"some2":true,"some4":"gdg"}', 
             {"some":False,"some2":True,"some4":"gdg"}],
            ['{"some":123,"some2":154.35,"some4":-34.4}', 
             {"some":123,"some2":154.35,"some4":-34.4}],
            ]

        for ar in arg:
            self.myAssertDict(json.loads(Utils.stringToDictJson(ar[0])), ar[1])
            self.myAssertDict(json.loads(Utils.stringToDictJson(ar[0], False)), ar[1])



    def test_stringToDictJson_tobool(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        fac = self.__rnd.randint(2, 10)
        fac2 = self.__rnd.randint(2, 10)
        arg = [
            ["", {}],
            ["Not initialised", {}],
            ["some True", {"some":True}],
            ["some trUe", {"some":True}],
            ["some falSe", {"some":False}],
            ["some False", {"some":False}],
            ["some False some2 sfd some4 gdg", 
             {"some":False,"some2":True,"some4":True}],
            ['{"some":"False","some2":"sfd","some4":"gdg"}', 
             {"some":"False","some2":"sfd","some4":"gdg"}],
            ['{"some":false,"some2":true,"some4":"gdg"}', 
             {"some":False,"some2":True,"some4":"gdg"}],
            ['{"some":123,"some2":154.35,"some4":-34.4}', 
             {"some":123,"some2":154.35,"some4":-34.4}],
            ]

        for ar in arg:
            self.myAssertDict(json.loads(Utils.stringToDictJson(ar[0], True)), ar[1])


    def test_stringToListJson(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arg = [
            ["", []],
            ["Not initialised", []],
            ["some True", ["some","True"]],
            ["some trUe", ["some","trUe"]],
            ["some falSe", ["some","falSe"]],
            ["some False", ["some","False"]],
            ["some False some2 sfd some4 gdg", 
             ["some","False","some2", "sfd","some4","gdg"]],
             ['["some","False","some2", "sfd","some4","gdg"]',
             ["some","False","some2", "sfd","some4","gdg"]
             ],
            ["some:False,some2 ;sfd;som.e4 gdg", 
             ["some","False","some2", "sfd","som.e4","gdg"]],
            ]

        for ar in arg:
            self.assertEqual(json.loads(Utils.stringToListJson(ar[0])), ar[1])


    def test_compareDict(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        arg = [
            [{}, {}, True],
            ["{}", {}, False],
            [{}, [], False],
            [{"some":False,"some2":True,"some4":True}, 
             {"some":False,"some2":True,"some4":True}, True],
            [{"some":12,"some2":True,"some4":True}, 
             {"some":12,"some4":True,"some2":True}, True],
            [{"some":False,"some2":True,"some4":True}, 
             {"some":False,"some4":True,"some2":False}, False],
            [{"some":12,"some2":True,"some4":True}, 
             {"some":12,"some4":True,"som":True}, False],
            [{"sdf":{"some":"sFalse","some2":True,"some4":True}}, 
             {"sdf":{"some":"sFalse","some4":True,"some2":True}}, True],
            [{"sdf":{"some":"sFalse","some2":True,"some4":True}}, 
             {"sdf":{"some1":"sFalse","some4":True,"some2":True}}, False],
            [{"sdf":["some","sFalse","some2",True,"some4",True]}, 
             {"sdf":["some","sFalse","some2",True,"some4",True]}, True],
            ]

        for ar in arg:
            self.assertEqual(Utils.compareDict(ar[0], ar[1]), ar[2])

    def test_toString_string(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        arg = [
            ["", ""],
            ["asd", "asd"],
            ["asdf", u'asdf'],
            ["dffd", u'dffd'],
               ]
        for ar in arg:
            self.assertEqual(Utils.toString(ar[1]), ar[0])
            self.assertTrue(isinstance(Utils.toString(ar[0]), str))

    def test_toString_list(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        arg = [
            [["asd"], ["asd"]],
            [["asdf"], [u'asdf']],
            [["dffd"], [u'dffd']],
            [["asd","asdfd"], ["asd","asdfd"]],
            [["asdf","asdfasdf"], [u'asdf', u'asdfasdf']],
            [["dffd", 'sdfasdf'], [u'dffd', u'sdfasdf']],
               ]
        for ar in arg:
            self.assertEqual(Utils.toString(ar[1]), ar[0])
            for aa in ar[0]:
                self.assertTrue(isinstance(Utils.toString(aa), str))


    def test_toString_dict(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        arg = [
            [{"asd":"asdfd"}, {"asd":"asdfd"}],
            [{"asdf":"asdfasdf"}, {u'asdf': u'asdfasdf'}],
            [{"dffd": 'sdfasdf'}, {u'dffd': u'sdfasdf'}],
            [{"asdf":"asdfasdf","asdf123":"asdfasdf"}, 
             {u'asdf': u'asdfasdf', u'asdf123': u'asdfasdf'}],
               ]
        for ar in arg:
            print ar
            self.assertEqual(Utils.toString(ar[1]), ar[0])
            for ke, vl in ar[0].items():
                self.assertTrue(isinstance(Utils.toString(ke), str))
                self.assertTrue(isinstance(Utils.toString(vl), str))



    def test_toString_listdict(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        arg = [
            [[{"asd":"asdfd"}], [{"asd":"asdfd"}]],
            [[{"asdf":"asdfasdf"}], [{u'asdf': u'asdfasdf'}]],
            [[{"dffd": 'sdfasdf'}], [{u'dffd': u'sdfasdf'}]],
            [[{"asdf":"asdfasdf","asdf123":"asdfasdf"}], 
             [{u'asdf': u'asdfasdf', u'asdf123': u'asdfasdf'}]],
               ]
        for ar in arg:
            print ar
            self.assertEqual(Utils.toString(ar[1]), ar[0])
            for aa in ar[0]:
                for ke, vl in aa.items():
                    self.assertTrue(isinstance(Utils.toString(ke), str))
                    self.assertTrue(isinstance(Utils.toString(vl), str))

    def test_command(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        arg = [
            ["mycommand", None, "return"],
            ["mycommand1", ":asda",None ],
            ["mycommanwrd", {"sdf":"sdfsd"}, 342],
            ["mycommanwrd", None, None],
            ["mycommansdfd", [], "rurn"],
            ["mmmand", None, []],
            ]
        
        for ar in arg:
            server = Server(ar[2])
            self.assertEqual(server.exe, False)
            val = TangoUtils.command(server, ar[0], ar[1])
            self.assertEqual(server.exe, True)
            self.assertEqual(server.command, ar[0])
            self.assertEqual(server.var, ar[1])
            self.assertEqual(val, ar[2])


        for ar in arg:
            server = Server(ar[2])
            self.assertEqual(server.exe, False)
            val = TangoUtils.command(server, ar[0])
            self.assertEqual(server.exe, True)
            self.assertEqual(server.command, ar[0])
            self.assertEqual(server.var, None)
            self.assertEqual(val, ar[2] )
        
    def test_command_noserver(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        arg = [
            [None, "return"],
            [":asda",None ],
            [{"sdf":"sdfsd"}, 342],
            [ None, None],
            [[], "rurn"],
            [ None, []],
            ]
        
        for ar in arg:
            server = NoServer(ar[1])
            self.assertEqual(server.exe, False)
            val = TangoUtils.command(server, "testcommand",  ar[0])
            self.assertEqual(server.exe, True)
            self.assertEqual(server.command, "testcommand")
            self.assertEqual(server.var, ar[0])
            self.assertEqual(val, ar[1])


        for ar in arg:
            server = Server(ar[1])
            self.assertEqual(server.exe, False)
            val = TangoUtils.command(server, "testcommand2")
            self.assertEqual(server.exe, True)
            self.assertEqual(server.command, "testcommand2")
            self.assertEqual(server.var, None)
            self.assertEqual(val, ar[1])
        

    def test_command_getShapeTypeUnit(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        self.myAssertRaise(Exception,
                           TangoUtils.getShapeTypeUnit, 
                           "ttestp09/testts/t1r228/sdfffffffffffffffffffsdfs")
        
    def test_command_getShapeTypeUnit_scalar(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        self._simps.dp.ScalarBoolean = bool(self._bools[0])
        self._simps.dp.ScalarUChar = abs(self._counter[0])
        self._simps.dp.ScalarShort = self._counter[0]
        self._simps.dp.ScalarUShort = abs(self._counter[0])
        self._simps.dp.ScalarLong = self._counter[0]
        self._simps.dp.ScalarULong = abs(self._counter[0])
        self._simps.dp.ScalarLong64 = self._counter[0]
        self._simps.dp.ScalarFloat = self._fcounter[0]
        self._simps.dp.ScalarDouble = self._dcounter[0]
        self._simps.dp.ScalarString = self._bools[0]
        self._simps.dp.ScalarULong64 =long(abs(self._counter[0]))
        
        
        
        arr = {
            'ScalarBoolean':[[], 'bool','No unit'],
            'ScalarUChar':[[], 'uint8','mm'],
            'ScalarShort':[[], 'int16','deg'],
            'ScalarUShort':[[], 'uint16','No unit'],
            'ScalarLong':[[], 'int32','rad'],
            'ScalarULong':[[], 'uint32','um'],
            'ScalarLong64':[[], 'int64','cm'],
            'ScalarFloat':[[], 'float32','eV'],
            'ScalarDouble':[[], 'float64','GeV'],
            'ScalarString':[[], 'string','mm N'],
            'ScalarULong64':[[], 'uint64',''],
            }

        arr2 = {
            'ScalarEncoded':[[], 'encoded','No unit'],
            }

        for k, ar in arr.items():
            ap = PyTango.AttributeProxy("ttestp09/testts/t1r228/%s" % k)
            ac = ap.get_config()
            ac.unit = ar[2]
            ap.set_config(ac)
        
        for k, ar in arr.items():
#            print k, ar
            self.checkstu(TangoUtils.getShapeTypeUnit("ttestp09/testts/t1r228/%s" % k),
                          ar[0], ar[1], ar[2])

        for k, ar in arr2.items():
#            print k, ar
            self.checkstu(TangoUtils.getShapeTypeUnit("ttestp09/testts/t1r228/%s" % k),
                          ar[0], ar[1], ar[2])




    def test_command_getShapeTypeUnit_spectrum(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        
        self._simps.dp.SpectrumBoolean = self._logical[0]
        self._simps.dp.SpectrumUChar = self._mca2[0]
        self._simps.dp.SpectrumShort = self._mca1[0]
        self._simps.dp.SpectrumUShort = self._mca2[0]
        self._simps.dp.SpectrumLong = self._mca1[0]
        self._simps.dp.SpectrumULong = self._mca2[0]
        self._simps.dp.SpectrumLong64 = self._mca1[0]
        self._simps.dp.SpectrumULong64 = self._mca2[0]
        self._simps.dp.SpectrumFloat = self._fmca1[0]
        self._simps.dp.SpectrumDouble = self._fmca1[0]
        self._simps.dp.SpectrumString = self._dates[0]

        
        arr = {
            'SpectrumBoolean':[[len(self._logical[0])], 'bool','No unit'],
            'SpectrumUChar':[[len(self._mca2[0])], 'uint8','mm'],
            'SpectrumShort':[[len(self._mca1[0])], 'int16','deg'],
            'SpectrumUShort':[[len(self._mca2[0])], 'uint16','No unit'],
            'SpectrumLong':[[len(self._mca1[0])], 'int32','rad'],
            'SpectrumULong':[[len(self._mca2[0])], 'uint32','um'],
            'SpectrumLong64':[[len(self._mca1[0])], 'int64','cm'],
            'SpectrumULong64':[[len(self._mca2[0])], 'uint64',''],
            'SpectrumFloat':[[len(self._fmca1[0])], 'float32','eV'],
            'SpectrumDouble':[[len(self._fmca1[0])], 'float64','GeV'],
            'SpectrumString':[[len(self._dates[0])], 'string','mm N'],
            }


        for k, ar in arr.items():
            ap = PyTango.AttributeProxy("ttestp09/testts/t1r228/%s" % k)
            ac = ap.get_config()
            ac.unit = ar[2]
            ap.set_config(ac)
        
        for k, ar in arr.items():
#            print k, ar
            self.checkstu(TangoUtils.getShapeTypeUnit("ttestp09/testts/t1r228/%s" % k),
                          ar[0], ar[1], ar[2])


    def test_command_getShapeTypeUnit_image(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        self._simps.dp.ImageBoolean = self._logical2[0]
        self._simps.dp.ImageUChar = self._pco1[0]
        self._simps.dp.ImageShort = self._pco1[0]
        self._simps.dp.ImageUShort = self._pco1[0]
        self._simps.dp.ImageLong = self._pco1[0]
        self._simps.dp.ImageULong = self._pco1[0]
        self._simps.dp.ImageLong64 = self._pco1[0]
        self._simps.dp.ImageULong64 = self._pco1[0]
        self._simps.dp.ImageFloat = self._fpco1[0]
        self._simps.dp.ImageDouble = self._fpco1[0]
        self._simps.dp.ImageString = self._dates2[0]

        
        
        arr = {
            'ImageBoolean':[[len(self._logical2[0]),len(self._logical2[0][0])], 'bool','No unit'],
            'ImageUChar':[[len(self._pco1[0]),len(self._pco1[0][0])], 'uint8','mm'],
            'ImageShort':[[len(self._pco1[0]),len(self._pco1[0][0])], 'int16','deg'],
            'ImageUShort':[[len(self._pco1[0]),len(self._pco1[0][0])], 'uint16','No unit'],
            'ImageLong':[[len(self._pco1[0]),len(self._pco1[0][0])], 'int32','rad'],
            'ImageULong':[[len(self._pco1[0]),len(self._pco1[0][0])], 'uint32','um'],
            'ImageLong64':[[len(self._pco1[0]),len(self._pco1[0][0])], 'int64','cm'],
            'ImageULong64':[[len(self._pco1[0]),len(self._pco1[0][0])], 'uint64',''],
            'ImageFloat':[[len(self._fpco1[0]),len(self._fpco1[0][0])], 'float32','eV'],
            'ImageDouble':[[len(self._fpco1[0]),len(self._fpco1[0][0])], 'float64','GeV'],
            'ImageString':[[len(self._dates2[0]),len(self._dates2[0][0])], 'string','mm N'],
            }


        for k, ar in arr.items():
            ap = PyTango.AttributeProxy("ttestp09/testts/t1r228/%s" % k)
            ac = ap.get_config()
            ac.unit = ar[2]
            ap.set_config(ac)
        
        for k, ar in arr.items():
            print k, ar
            self.checkstu(TangoUtils.getShapeTypeUnit("ttestp09/testts/t1r228/%s" % k),
                          ar[0], ar[1], ar[2])


    def test_getSource(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        

        self.assertEqual(PoolUtils.getSource("ttestp09/testts/t1r228"),
                         "ttestp09/testts/t1r228/%s" %  'Value')

        arr = ['ScalarBoolean', 'ScalarUChar', 'ScalarShort', 'ScalarUShort', 
               'ScalarLong', 'ScalarULong', 'ScalarLong64', 'ScalarFloat', 
               'ScalarDouble', 'ScalarString', 'ScalarULong64',
               'SpectrumBoolean', 'SpectrumUChar', 'SpectrumShort', 'SpectrumUShort', 
               'SpectrumLong', 'SpectrumULong', 'SpectrumLong64', 'SpectrumULong64', 
               'SpectrumFloat', 'SpectrumDouble', 'SpectrumString',
               'ImageBoolean', 'ImageUChar', 'ImageShort', 'ImageUShort', 'ImageLong', 
               'ImageULong', 'ImageLong64', 'ImageULong64', 'ImageFloat', 'ImageDouble', 
               'ImageString']
        
        self._simps.dp.CreateAttribute("DataSource")
        for ar in arr:
            self._simps.dp.DataSource = "ttestp09/testts/t1r228/%s" % ar
            self.assertEqual(PoolUtils.getSource("ttestp09/testts/t1r228"),
                             "ttestp09/testts/t1r228/%s" %  ar)
            
        self._simps.dp.DataSource = "ttestp09/testts/t1r228/%s" % "sdfsdf"
        self.assertEqual(PoolUtils.getSource("ttestp09/testts/t1r228"),
                         "ttestp09/testts/t1r228/Value")

if __name__ == '__main__':
    unittest.main()

