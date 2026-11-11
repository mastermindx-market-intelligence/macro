import unittest
import numpy as np
import pandas as pd
from inputs import parse_french_text,known_monthly
from engine import simulate,causal_exposure_target
from inference import holm,maxdd,bootstrap_means

class Integrity(unittest.TestCase):
    def test_cutoff_before_numeric_parse(self):
        text=',Mkt-RF,RF\n19260701,1,0\n20191231,2,0\n20200102,NOT_A_NUMBER,NEVER_PARSE\n'
        x=parse_french_text(text)[0][1]
        self.assertEqual(len(x),2);self.assertEqual(x.iloc[-1,0],.02)
    def test_missing_never_zero(self):
        x=parse_french_text(',A,B\n19260701,-99.99,-999\n')[0][1]
        self.assertTrue(x.isna().all().all())
    def test_next_close_trade(self):
        idx=pd.date_range('1975-01-01',periods=4)
        r=pd.DataFrame({'M':[0.,.1,.2,.3],'RF':[0.,0.,0.,0.]},index=idx)
        t=pd.DataFrame({'M':[1.,0.,0.,0.],'RF':[0.,1.,1.,1.]},index=idx)
        out=simulate(t,r)
        self.assertTrue(np.isnan(out['return'].iloc[0]))
        self.assertAlmostEqual(out['return'].iloc[1],-.0005)
        self.assertAlmostEqual(out['return'].iloc[2],1.2*(1-.0005)-1)
        self.assertAlmostEqual(out['return'].iloc[3],0.)
    def test_cost_eras_and_sleeve_switch(self):
        idx=pd.to_datetime(['1974-12-30','1974-12-31','1975-01-02'])
        r=pd.DataFrame(0.,index=idx,columns=['A','B','M','RF'])
        t=pd.DataFrame([[1,0,0,0],[0,1,0,0],[0,1,0,0]],index=idx,columns=r.columns)
        out=simulate(t,r)
        self.assertAlmostEqual(out.cost.iloc[1],.0025)
        self.assertAlmostEqual(out.cost.iloc[2],.001)
        self.assertAlmostEqual(out.turnover.iloc[2],2)
    def test_weights_drift_before_trade(self):
        idx=pd.date_range('1980-01-01',periods=3)
        r=pd.DataFrame({'A':[0,0,.1],'B':[0,0,0.],'M':[0,0,0.],'RF':[0,0,0.]},index=idx)
        t=pd.DataFrame([[.5,.5,0,0]]*3,index=idx,columns=r.columns)
        out=simulate(t,r)
        self.assertAlmostEqual(out.turnover.iloc[2],2*(.55/1.05-.5))
    def test_causal_average(self):
        t=pd.DataFrame({'M':[1.,0.,1.],'RF':[0.,1.,0.]})
        q=causal_exposure_target(t)
        np.testing.assert_allclose(q.M,[1,.5,2/3])
        changed=t.copy();changed.loc[2]=[0,1]
        np.testing.assert_allclose(causal_exposure_target(changed).M.iloc[:2],q.M.iloc[:2])
    def test_monthly_known_dates_and_gaps(self):
        s=pd.Series([5.,np.nan],index=pd.to_datetime(['1950-01-01','1950-02-01']))
        idx=pd.to_datetime(['1950-02-28','1950-03-01','1950-04-01'])
        out=known_monthly(s,idx,2)
        self.assertTrue(np.isnan(out.iloc[0]));self.assertEqual(out.iloc[1],5.);self.assertTrue(np.isnan(out.iloc[2]))
    def test_held_missing_fails(self):
        idx=pd.date_range('1980-01-01',periods=3)
        r=pd.DataFrame({'M':[0,0,np.nan],'RF':[0,0,0.]},index=idx)
        t=pd.DataFrame({'M':[1,1,1.],'RF':[0,0,0.]},index=idx)
        with self.assertRaises(ValueError):simulate(t,r)
    def test_holm_and_starting_drawdown(self):
        np.testing.assert_allclose(holm([.01,.03,.2]),[.03,.06,.2])
        self.assertAlmostEqual(maxdd([-.2,.1]),-.2)
    def test_bootstrap_constant_and_paired(self):
        a=np.ones((755,2))*.001
        x=bootstrap_means(a)
        np.testing.assert_allclose(x,.001,atol=1e-14)
        np.testing.assert_allclose(x[:,0]-x[:,1],0.,atol=1e-14)

if __name__=='__main__':unittest.main()
