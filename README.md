<img width="1472" height="722" alt="image" src="https://github.com/user-attachments/assets/b9f8350e-bb94-4f05-94c1-4d797d65369e" />


**ReliaPy** is a Colab-ready and Hugging Face Space-ready Python/Gradio workbench for reliability analysis. It provides an interactive dashboard for four major reliability-engineering tasks:

1. **Life Data Analysis**
2. **Reliability Growth Analysis**
3. **Repairable Systems Analysis**
4. **Accelerated Life Testing**

The repository contains the main notebook, `ReliaPy_3.ipynb`, together with synthetic benchmark CSV datasets for testing, demonstration, reproducibility, and publication-oriented validation.

ReliaPy can be used in two ways:

- **Google Colab / GitHub version:** run the notebook `ReliaPy_3.ipyn4656-a5ac-7506664bedf2" />

**ReliaPy** is a Colab-ready and Hugging Face Space-ready Python/b`.
- **Online Hugging Face Space version:** use the hosted Gradio app directly.

> GitHub Repository: [https://github.com/ParthaPRay/ReliaPy](https://github.com/ParthaPRay/ReliaPy)  
> Live Hugging Face Space: [https://huggingface.co/spaces/csepartha/ReliaPy](https://huggingface.co/spaces/csepartha/ReliaPy)
---

## Developer

**Partha Pratim Ray**  
Sikkim University  
July 2026  
Email: **parthapratimray1986@gmail.com**

---

## Purpose of the Project

ReliaPy is designed as a lightweight, open, and reproducible reliability-analysis tool that can run directly in **Google Colab** using **Gradio**. The goal is to provide an accessible interface for students, researchers, reliability engineers, and tool-paper reviewers to perform common reliability analyses without requiring commercial software.

The app is suitable for:

- reliability-method teaching,
- demonstration of reliability models,
- reproducible experiments,
- synthetic benchmark testing,
- manuscript figure generation,
- tool-paper validation workflows.

---

## Main Notebook

The main application notebook is:

```text
ReliaPy_3.ipynb
```

Open this notebook in Google Colab and run all cells. The notebook installs the required dependencies and launches the Gradio dashboard.

---

## Installation in Google Colab

Run the following command in Colab if dependencies are not already installed:

```python
!pip -q install gradio scipy pandas numpy matplotlib openpyxl
```

Then run the application cell:

```python
demo.launch(share=True, debug=True)
```

The app will generate a public Gradio link for interactive use.

---

## Key Features

### 1. Life Data Analysis

ReliaPy supports life-data modeling for time-to-failure data.

Supported options include:

- Weibull distribution
- Lognormal distribution
- Maximum Likelihood Estimation
- Rank Regression
- Right-censored data handling
- Reliability at mission time
- Probability plots
- Fitted CDF plots
- Likelihood contour plots

Typical input columns:

```text
time, event
```

or

```text
hours, status
```

---

### 2. Reliability Growth Analysis

ReliaPy supports reliability-growth modeling for cumulative event/failure times during test or development programs.

Supported options include:

- Crow-AMSAA / Power Law NHPP
- Piecewise NHPP
- Automatic change-point detection
- Reliability-growth plot
- Duane plot
- Segment-wise interpretation of beta

Typical input column:

```text
event_time
```

or

```text
test_time
```

---

### 3. Repairable Systems Analysis

ReliaPy supports recurrent-event modeling for repairable units, fleets, systems, and assets.

Supported options include:

- Power Law Process
- Log-Linear NHPP
- Piecewise NHPP
- Cumulative event plot
- Event-rate plot
- Mean Cumulative Function

Typical input columns:

```text
event_time, system
```

or

```text
repair_time, unit
```

---

### 4. Accelerated Life Testing

ReliaPy supports accelerated life testing under stress conditions.

Supported options include:

- Weibull ALT
- Lognormal ALT
- Arrhenius life-stress relationship
- Power Law life-stress relationship
- Celsius and Kelvin temperature handling
- Use-stress prediction
- ALT probability plot
- Life-stress plot

Typical input columns:

```text
time, event, temperature
```

or

```text
cycles, failed, voltage
```

---

## Output and Export Options

The Gradio interface provides:

- result tables,
- plots,
- notes and interpretations,
- CSV download for results,
- PNG download for plots.

Generated PNG plots are intended for reports, teaching notes, and manuscript drafting.

---

## Repository Contents

The repository includes the following main files:

```text
ReliaPy_3.ipynb
ReliaPy_combined_dataset_manifesto.csv
ReliaPy_SYNTHETIC_DATASETS_README.md
```

It also includes several synthetic CSV datasets grouped by analysis module.

---

# Synthetic Benchmark Datasets

The datasets are synthetic and are provided for testing the ReliaPy interface and computations. They should not be described as real industrial field data.

Use the manifesto file to identify the correct module, model, time column, event/status column, system column, or stress column:

```text
ReliaPy_combined_dataset_manifesto.csv
```

The manifesto acts as a dataset index or menu. It is **not** meant to be uploaded into the analysis tabs for model fitting.

---

## Dataset Guide

## A. Life Data Analysis Datasets

Use the following files in the **Life Data Analysis** tab.

| Dataset | Scenario | Suggested model |
|---|---|---|
| `quick_demo_life_weibull.csv` | Compact quick demonstration dataset | Weibull MLE or Rank Regression |
| `life_weibull_censored.csv` | Weibull life data with right censoring | Weibull MLE |
| `life_lognormal_censored.csv` | Lognormal life data with right censoring | Lognormal MLE |
| `life_weibull_text_status_robustness.csv` | Text status labels for robustness testing | Weibull MLE |
| `life_weibull_early_failure_heavy_censoring.csv` | Infant-mortality pattern with decreasing hazard | Weibull MLE |
| `life_weibull_wearout_text_status_warranty.csv` | Wear-out failure pattern with warranty censoring | Weibull MLE or Rank Regression |
| `life_lognormal_mixture_supplier_groups.csv` | Mixed supplier populations | Lognormal MLE |

Example settings:

```text
Tab: Life Data Analysis
Dataset: life_weibull_censored.csv
Distribution: Weibull
Method: MLE
Time column: time
Event column: event
```

---

## B. Reliability Growth Datasets

Use the following files in the **Reliability Growth** tab.

| Dataset | Scenario | Suggested model |
|---|---|---|
| `growth_crow_amsaa_improving.csv` | Improving reliability-growth process | Crow-AMSAA |
| `growth_piecewise_changepoint.csv` | Reliability-growth process with change point | Piecewise NHPP or Automatic change-point |
| `growth_crow_amsaa_deteriorating_beta_gt1.csv` | Deteriorating process with increasing failure intensity | Crow-AMSAA |
| `growth_delayed_fix_auto_changepoint.csv` | Delayed corrective action followed by improvement | Automatic change-point |
| `growth_three_phase_manual_breakpoints.csv` | Three engineering phases with manual change points | Piecewise NHPP |

Example settings:

```text
Tab: Reliability Growth
Dataset: growth_three_phase_manual_breakpoints.csv
Model: Piecewise NHPP
Time column: cumulative_time
Manual breakpoints: 350,800
```

---

## C. Repairable Systems Datasets

Use the following files in the **Repairable Systems** tab.

| Dataset | Scenario | Suggested model |
|---|---|---|
| `repairable_multisystem_powerlaw.csv` | Multiple repairable systems with recurrent events | Power Law |
| `repairable_loglinear_improving.csv` | Repair process with decreasing event rate | Log-Linear |
| `repairable_fleet_heterogeneous_assets.csv` | Heterogeneous asset fleet | Power Law |
| `repairable_preventive_maintenance_improving.csv` | Preventive-maintenance improvement scenario | Log-Linear |
| `repairable_overhaul_piecewise_step_change.csv` | Event-rate reduction after overhaul | Piecewise NHPP |

Example settings:

```text
Tab: Repairable Systems
Dataset: repairable_overhaul_piecewise_step_change.csv
Model: Piecewise NHPP
Time column: repair_time
System column: unit
Manual breakpoint: 450
```

---

## D. Accelerated Life Testing Datasets

Use the following files in the **Accelerated Life Testing** tab.

| Dataset | Scenario | Suggested model |
|---|---|---|
| `alt_arrhenius_weibull_temperature.csv` | Temperature ALT with Weibull life model | Weibull + Arrhenius Celsius |
| `alt_powerlaw_lognormal_voltage.csv` | Voltage ALT with Lognormal life model | Lognormal + Power Law |
| `alt_arrhenius_lognormal_temperature_kelvin.csv` | Temperature ALT with Kelvin temperature column | Lognormal + Arrhenius Kelvin |
| `alt_powerlaw_weibull_voltage_stress.csv` | Voltage-stress ALT with Weibull life model | Weibull + Power Law |
| `alt_powerlaw_weibull_humidity_generic_stress.csv` | Humidity as generic stress with text censoring | Weibull + Power Law |

Example settings:

```text
Tab: Accelerated Life Testing
Dataset: alt_powerlaw_weibull_voltage_stress.csv
Life distribution: Weibull
Life-stress relationship: Power law; generic stress
Time column: cycles
Stress column: voltage
Event column: failed
```

---

## Recommended Demonstration Workflow

A useful demonstration sequence is:

1. Upload `quick_demo_life_weibull.csv` in the Life Data Analysis tab.
2. Run Weibull MLE.
3. Upload `life_weibull_censored.csv`.
4. Compare MLE and Rank Regression.
5. Upload `growth_crow_amsaa_improving.csv`.
6. Run Crow-AMSAA reliability-growth analysis.
7. Upload `growth_delayed_fix_auto_changepoint.csv`.
8. Run Automatic change-point analysis.
9. Upload `repairable_fleet_heterogeneous_assets.csv`.
10. Run Power Law repairable-system analysis.
11. Upload `repairable_overhaul_piecewise_step_change.csv`.
12. Run Piecewise NHPP with breakpoint `450`.
13. Upload `alt_arrhenius_weibull_temperature.csv`.
14. Run Weibull + Arrhenius Celsius ALT.
15. Upload `alt_powerlaw_weibull_voltage_stress.csv`.
16. Run Weibull + Power Law ALT.

---

## Suggested Publication Description

The following statement may be used in a paper or technical report:

> ReliaPy is a Python/Gradio reliability-analysis workbench developed for reproducible life data analysis, reliability growth modeling, repairable-system analysis, and accelerated life testing. The tool runs in Google Colab and provides interactive model fitting, visualization, and export of summary tables and plots. Synthetic benchmark datasets were generated to test multiple scenarios, including right censoring, early-life failures, wear-out failures, mixed life populations, reliability improvement, deteriorating growth, change-point behavior, heterogeneous repairable fleets, preventive-maintenance effects, overhaul-based step changes, Arrhenius temperature acceleration, and power-law stress acceleration.

---

## Important Notes on Synthetic Data

The CSV datasets in this repository are designed for software testing and demonstration. They are useful for:

- verifying that the application runs correctly,
- checking whether column auto-detection works,
- testing censored and uncensored data handling,
- testing text-based event/status labels,
- validating plot generation,
- testing export/download features,
- demonstrating reliability concepts.

They should not be treated as real field, warranty, production, or industrial data.

For publication-grade inference, ReliaPy outputs should be validated against real datasets, domain assumptions, and independent reliability software where possible.

---

## Technologies Used

ReliaPy uses:

- Python
- Gradio
- NumPy
- Pandas
- SciPy
- Matplotlib
- OpenPyXL

---

## License

Please specify the license for this repository according to your intended distribution policy. Suggested options include:

```text
MIT License
Apache License 2.0
CC BY 4.0 for documentation and datasets
```

---

## Citation

If you use this tool or the synthetic datasets, please cite the GitHub repository:

```text
Ray, P. P. (2026). ReliaPy: Python/Gradio Reliability Analysis Workbench. 
GitHub repository: https://github.com/ParthaPRay/ReliaPy
```

---

## Run on your localhost

Running on local URL:  http://127.0.0.1:7860

## Contact

For queries, suggestions, and collaboration:

**Partha Pratim Ray**  
Sikkim University  
Email: **parthapratimray1986@gmail.com**
