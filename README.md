# CLEWS-OG
Integration of the CLEWS and OG-CORE models

## Workshop (January 14-15, 2026 in Manila, Philippines):
* 2 days, ~12-13 hours of presentations
* Tentative Schedule:
  * Day 1 (can switch oder of CLEWS/OG)
    * Introduction to workshop (~ 30 minutes)
    * Background on OG-Core (~ 3 hours total)
      * Theory
      * Calibration / data requirements
      * Example applications
    * Lunch
    * Background on CLEWS (~ 3 hours total)
      * Theory
      * Calibration / data requirements
      * Example applications
  * Day 2:
    * Describe policy experiment from "[Philippine Energy Plan 2023 - 2050, Volume 1](https://legacy.doe.gov.ph/sites/default/files/pdf/pep/PEP%202023-2050%20Vol.%20I.pdf)" (10 min)
    * Describe overview of this particular run sequence: (1) CLEWS, (2) OG-PHL, (3) CLEWS, (4) Describe the output we have in the end (10 min)
    * Highlight the ways in which we should update the calibrations, but show that these are pretty well calibrated (15 min)
    * Describe setup and initial run of CLEWS and output (30 min)
    * Describe passage of data from CLEWS to OG-PHL and initial OG-PHL run (30 min)
    * Describe passage of demand data back to CLEWS and final output (30 min)
    * Lunch
    * Review final output, how models link, and alternative workflows (30 min)
    * Brainstorming session of possible applications (1 hour)
    * Wrap of brainstorming session, next steps, further resources (1 hour)

## Illustrative example:
* [Philippine Energy Plan](https://legacy.doe.gov.ph/pep) for 2023 to 2050 (2023)
  * Renewable energy adoption in an economy
  * Also coal phaseout?
* Effects we can model:
  * Changes in energy cost in CLEWS -> TFP of energy sector in OG-Core
  * Changes in TFP -> prices -> demand in OG-Core -> energy demand in CLEWS
  * Changes in interest rates in OG-Core -> discount rates in CLEWS
  * Changes in emissions in CLEWS -> change in mortality, productivity (off-model) -> demographics in OG-Core -> demands -> CLEWS
  * Macro effects in OG-Core
  * Iterate between models?


## Resources:
* [Simple OSeMOSYS model to simulate](https://github.com/OSeMOSYS/simplicity)
* [CLEWS-PHL overview](https://docs.google.com/document/d/1gRZgntgdvT-fieKeXVIwFMPKKMCvIsFhhVNscSpYTHY/edit?usp=sharing) (Google Doc)
* OG-Core: [docs](https://pslmodels.github.io/OG-Core/), [repo](https://github.com/PSLmodels/OG-Core)
* OG-PHL: [docs](https://eapd-drb.github.io/OG-PHL/), [repo](https://github.com/EAPD-DRB/OG-PHL/)
