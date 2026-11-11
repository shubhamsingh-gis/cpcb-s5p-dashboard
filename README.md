# 🏭 Multi-Station CPCB CAAQMS & Sentinel-5P (TROPOMI) Calibration Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end analytical dashboard designed to ingest raw continuous ground monitoring datasets (CPCB CAAQMS) across India, calculate annual data completeness based on standard regulatory thresholds, evaluate NAAQS compliance, and calibrate Sentinel-5P (TROPOMI) satellite column densities using dynamic boundary layer meteorology.

---

## 📌 Project Overview

Ground-based Continuous Ambient Air Quality Monitoring Systems (CAAQMS) provide high-frequency local concentration metrics but suffer from spatial coverage gaps and logging downtime. Conversely, Sentinel-5P (TROPOMI) provides daily global satellite coverage but measures vertical column densities ($\text{mol/m}^2$) rather than direct surface concentrations.

This platform bridges point-based ground observations and Earth observation satellite data by:
1. Parsing raw 15-minute CPCB CSV exports across multiple monitoring stations.
2. Enforcing CPCB's **75% completeness rule** (minimum 72 valid 15-minute samples/day) to calculate valid annual data availability in days.
3. Modeling surface pollutant levels ($\text{NO}_2$, $\text{SO}_2$, $\text{CO}$, $\text{Ozone}$) from TROPOMI column densities using a **physical box-model** scaled by ECMWF ERA5 Planetary Boundary Layer Height (PBLH).
4. Computing comparative statistical bias metrics (**MB, NMB, RMSE, $R^2$**) to evaluate satellite-to-ground alignment.

---

## ✨ Key Features

* **Automated Raw Log Ingestion:** Parses multi-station 15-minute CPCB CSV logs, automatically sanit
