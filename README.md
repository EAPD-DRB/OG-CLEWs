# CLEWS-OG
Integration of the CLEWS and OG-CORE models

## Workshop (January 14-15, 2026 in Manila, Philippines):
* 2 days, ~12-13 hours of presentations
* Tentative Schedule:
  * Background on CLEWS
    * Theory (1 hour)
    * Calibration / data requirements (1.5 hours)
    * Example applications (0.5-1 hour)
  * Background on OG-Core
    * Theory (1 hour)
    * Calibration / data requirements (1.5 hours)
    * Example applications (0.5-1 hour)
  * Describe illustrative example setup (1 hour)
  * Describe how models link (1.5 hours)
  * Describe results of illustrative example (1 hour)
  * Brainstorming session of possible applications (1 hour)

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