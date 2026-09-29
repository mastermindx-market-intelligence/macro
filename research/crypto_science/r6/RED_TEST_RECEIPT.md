# Observed R6 RED receipt

This is a summary of the actual Studio Direct process return, not a reconstructed raw stdout log.

Before research/crypto_science/r6_probability_study.py existed, process22429 ran:
`python3 -m pytest tests/test_btc_impulse_falsifier.py -k r6 -q --tb=short`.

Observed exit1: seven R6tests failed,34deselected,21warnings. Each failure was ModuleNotFoundError for the absent research module:
- features prefix/zero versus unknown volume;
- price gaps/warmup/chronology;
- mature embargoed training membership;
- fixed likelihood/scaler/probability reproducibility;
- future outcome non-influence and insufficient fit support;
- training class-payoff shrinkage;
- proper probability-score arithmetic.

Implementation then ran process27703: five passed/two failed because the synthetic training fixture declared its y column bool, and pandas3 disallowed later NaN/float assignments. The fixture became explicit float; no market data, fitting parameter or target definition changed. Process33376 subsequently returned seven core passes and41existing research-file passes. Those actual GREEN outputs are retained in green_core.txt and green_research.txt.

The frozen study was first executed after implementation commit7b63e8ab2608a4c280e410d5dfaab7df04042127. No model-performance result was used to correct the tests or choose parameters.
