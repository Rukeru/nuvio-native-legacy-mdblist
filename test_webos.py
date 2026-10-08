import unittest
from webos import package_version, needed

class WebOSRules(unittest.TestCase):
    def test_version_order(self):
        self.assertEqual(package_version('v2.0.2',1),'2.0.200001')
        a=tuple(map(int,package_version('v2.0.2',99999).split('.')))
        b=tuple(map(int,package_version('v2.0.3',1).split('.')))
        self.assertLess(a,b)
        with self.assertRaises(ValueError): package_version('v2.0.2',100000)
    def test_independent_channel(self):
        u={'id':42}
        t={'tag_name':'v2.0.2.3','draft':False,'prerelease':False,'body':'<!-- upstream-release: 42 -->'}
        self.assertTrue(needed(u,[t]))
        w={'tag_name':'webos-v2.0.200001','draft':False,'prerelease':False,'body':'<!-- webos-upstream-release: 42 -->'}
        self.assertFalse(needed(u,[t,w]))
        self.assertTrue(needed(u,[t,w],True))
        self.assertTrue(needed({'id':43},[t,w]))
        w['draft']=True
        self.assertTrue(needed(u,[t,w]))
