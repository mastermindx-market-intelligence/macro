import unittest,struct
import inspect_wave9_snapshot as m
class DecodeTests(unittest.TestCase):
 def test_rle(self): self.assertEqual(m.hybrid(bytes([10,3]),2,5),[3]*5)
 def test_bit_packed(self): self.assertEqual(m.hybrid(bytes([3,0b11001010]),1,8),[0,1,0,1,0,0,1,1])
 def test_zero_width(self): self.assertEqual(m.hybrid(bytes([8]),0,4),[0]*4)
 def test_plain_text(self): self.assertEqual(m.plain(struct.pack('<I',3)+b'abc',6,1),['abc'])
 def test_plain_double(self): self.assertEqual(m.plain(struct.pack('<d',-1.5),5,1),[-1.5])
 def test_bad_truncation(self):
  with self.assertRaises(ValueError):m.hybrid(bytes([10]),2,5)
if __name__=='__main__':unittest.main()
