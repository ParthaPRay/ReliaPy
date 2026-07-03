# ReliaPy Synthetic Benchmark Datasets

This folder contains synthetic CSV datasets generated for testing the **ReliaPy Workbench** reliability-analysis tool.  
The datasets are meant for demonstration, validation of the Gradio interface, tutorial examples, and reproducible tool-paper experiments.

These files are **synthetic**. They should not be presented as real industrial field data. In publications, describe them as simulated benchmark datasets created to test different reliability-analysis scenarios.

---

## How to use these files

1. Open the ReliaPy Workbench Gradio app.
2. Select the appropriate analysis tab:
   - **Life Data Analysis**
   - **Reliability Growth**
   - **Repairable Systems**
   - **Accelerated Life Testing**
3. Upload the relevant CSV file.
4. Keep column names as **Auto** unless the app does not detect them correctly.
5. Choose the suggested model given below.
6. Run the analysis and inspect the parameter table, plots, and notes.

---

# Dataset Selection Guide

## 1. Life Data Analysis

Use these datasets in the **Life Data Analysis** tab.  
These datasets contain time-to-failure or time-to-censoring records.

| CSV file | Best use case | Suggested model | Column hints |
|---|---|---|---|
| `quick_demo_life_weibull.csv` | Quick first test of the Life Data module | Weibull, MLE | Time: `time`; Event: `event` |
| `life_weibull_censored.csv` | Standard Weibull life data with right censoring | Weibull, MLE | Time: `time`; Event: `event` |
| `life_lognormal_censored.csv` | Lognormal life behavior with censored units | Lognormal, MLE | Time: `time`; Event: `event` |
| `life_weibull_text_status_robustness.csv` | Checks whether the app handles text-based status labels | Weibull, MLE | Time: `time`; Event/status: `status` |
| `life_weibull_early_failure_heavy_censoring.csv` | Infant-mortality / early-failure pattern with decreasing hazard | Weibull, MLE | Time: `time`; Event: `event` |
| `life_weibull_wearout_text_status_warranty.csv` | Wear-out failure pattern with increasing hazard and warranty censoring | Weibull, MLE or Rank Regression | Time: `hours`; Event/status: `status` |
| `life_lognormal_mixture_supplier_groups.csv` | Mixed supplier populations; useful for showing imperfect single-distribution fit | Lognormal, MLE | Time: `failure_time`; Event: `event` |

### Suggested interpretation

- Use `quick_demo_life_weibull.csv` to confirm the tool is running correctly.
- Use `life_weibull_censored.csv` and `life_lognormal_censored.csv` for basic MLE testing.
- Use `life_weibull_text_status_robustness.csv` to test whether text values such as failure/censored are parsed correctly.
- Use `life_weibull_early_failure_heavy_censoring.csv` to demonstrate a decreasing hazard case, where the Weibull shape is expected to be below 1.
- Use `life_weibull_wearout_text_status_warranty.csv` to demonstrate an increasing hazard case, where the Weibull shape is expected to be above 1.
- Use `life_lognormal_mixture_supplier_groups.csv` to show that a single distribution may not fit well when the data are generated from mixed populations.

---

## 2. Reliability Growth

Use these datasets in the **Reliability Growth** tab.  
These datasets contain cumulative failure/event times during a development or test program.

| CSV file | Best use case | Suggested model | Column hints |
|---|---|---|---|
| `growth_crow_amsaa_improving.csv` | Standard reliability growth with improving trend | Crow-AMSAA | Time: `event_time` |
| `growth_piecewise_changepoint.csv` | Growth process with a visible change point | Piecewise NHPP or Automatic change-point | Time: `event_time` |
| `growth_crow_amsaa_deteriorating_beta_gt1.csv` | Deteriorating reliability-growth case with increasing event intensity | Crow-AMSAA | Time: `test_time` |
| `growth_delayed_fix_auto_changepoint.csv` | Delayed corrective action followed by improvement | Automatic change-point | Time: `event_time` |
| `growth_three_phase_manual_breakpoints.csv` | Three engineering phases with multiple changes | Piecewise NHPP | Time: `cumulative_time`; Breakpoints: `350,800` |

### Suggested interpretation

- Use `growth_crow_amsaa_improving.csv` for a clean Crow-AMSAA demonstration.
- Use `growth_crow_amsaa_deteriorating_beta_gt1.csv` to show the opposite case, where failures become more frequent over time.
- Use `growth_piecewise_changepoint.csv` and `growth_delayed_fix_auto_changepoint.csv` to test automatic change-point behavior.
- Use `growth_three_phase_manual_breakpoints.csv` with manual breakpoints `350,800` to demonstrate a three-stage reliability-development process.

---

## 3. Repairable Systems

Use these datasets in the **Repairable Systems** tab.  
These datasets contain recurrent repair/failure events from one or more repairable units.

| CSV file | Best use case | Suggested model | Column hints |
|---|---|---|---|
| `repairable_multisystem_powerlaw.csv` | Multiple repairable systems following a power-law recurrent-event trend | Power Law | Time: `event_time`; System: `system` |
| `repairable_loglinear_improving.csv` | Repair process with improving/decreasing event rate | Log-Linear | Time: `event_time` |
| `repairable_fleet_heterogeneous_assets.csv` | Heterogeneous fleet or asset-level recurrent repairs | Power Law | Time: `event_time`; System: `asset_id` |
| `repairable_preventive_maintenance_improving.csv` | Preventive-maintenance effect with decreasing event intensity | Log-Linear | Time: `event_time`; System: `system` |
| `repairable_overhaul_piecewise_step_change.csv` | Event-rate reduction after overhaul | Piecewise NHPP | Time: `repair_time`; System: `unit`; Breakpoint: `450` |

### Suggested interpretation

- Use `repairable_multisystem_powerlaw.csv` for a standard repairable-system Power Law Process example.
- Use `repairable_loglinear_improving.csv` to test the Log-Linear NHPP model.
- Use `repairable_fleet_heterogeneous_assets.csv` to demonstrate multiple asset IDs and MCF-style visualization.
- Use `repairable_preventive_maintenance_improving.csv` to show how maintenance can reduce recurrent-event intensity.
- Use `repairable_overhaul_piecewise_step_change.csv` with breakpoint `450` to show a clear before/after overhaul effect.

---

## 4. Accelerated Life Testing

Use these datasets in the **Accelerated Life Testing** tab.  
These datasets contain failure/censoring times observed under accelerated stress levels.

| CSV file | Best use case | Suggested model | Column hints |
|---|---|---|---|
| `alt_arrhenius_weibull_temperature.csv` | Temperature ALT with Weibull life model | Weibull + Arrhenius, temperature in Celsius | Time: `time`; Stress: `temperature`; Event: `event` |
| `alt_powerlaw_lognormal_voltage.csv` | Voltage ALT with Lognormal life model | Lognormal + Power Law | Time: `time`; Stress: `voltage`; Event: `event` |
| `alt_arrhenius_lognormal_temperature_kelvin.csv` | Temperature ALT where temperature is already in Kelvin | Lognormal + Arrhenius, temperature in Kelvin | Time: `time`; Stress: `temperature_K`; Event: `event` |
| `alt_powerlaw_weibull_voltage_stress.csv` | Voltage-stress ALT with Weibull life distribution | Weibull + Power Law | Time: `cycles`; Stress: `voltage`; Event: `failed` |
| `alt_powerlaw_weibull_humidity_generic_stress.csv` | Humidity as generic stress; includes text censoring | Weibull + Power Law | Time: `life_hours`; Stress: `humidity_percent`; Event/status: `status` |

### Suggested interpretation

- Use `alt_arrhenius_weibull_temperature.csv` when testing the Arrhenius Celsius option.
- Use `alt_arrhenius_lognormal_temperature_kelvin.csv` when testing the Arrhenius Kelvin option.
- Use `alt_powerlaw_lognormal_voltage.csv` for a Lognormal Power Law ALT example.
- Use `alt_powerlaw_weibull_voltage_stress.csv` for a Weibull Power Law voltage-stress example.
- Use `alt_powerlaw_weibull_humidity_generic_stress.csv` to test a generic stress variable and text censoring.

---

# Manifest files

The folder also contains:

| File | Purpose |
|---|---|
| `dataset_manifest.csv` | Manifest for the first group of generated synthetic datasets |
| `additional_dataset_manifest.csv` | Manifest for the additional synthetic datasets |
| `README.md` | This guide |

---

# Recommended demonstration sequence

For a paper, workshop, or classroom demonstration, the following sequence is recommended:

1. **Life Data quick test**  
   Upload `quick_demo_life_weibull.csv` and run Weibull MLE.

2. **Censoring test**  
   Upload `life_weibull_censored.csv` and compare MLE with Rank Regression.

3. **Text-status robustness test**  
   Upload `life_weibull_text_status_robustness.csv`.

4. **Reliability-growth improvement test**  
   Upload `growth_crow_amsaa_improving.csv` and run Crow-AMSAA.

5. **Change-point test**  
   Upload `growth_delayed_fix_auto_changepoint.csv` and run Automatic change-point.

6. **Repairable-system fleet test**  
   Upload `repairable_fleet_heterogeneous_assets.csv` and run Power Law.

7. **Overhaul step-change test**  
   Upload `repairable_overhaul_piecewise_step_change.csv` and run Piecewise NHPP with breakpoint `450`.

8. **ALT Arrhenius test**  
   Upload `alt_arrhenius_weibull_temperature.csv` and choose Weibull + Arrhenius Celsius.

9. **ALT Power Law test**  
   Upload `alt_powerlaw_weibull_voltage_stress.csv` and choose Weibull + Power Law.

---

# Suggested wording for publication

The following wording may be used in a manuscript:

> To evaluate the usability and computational workflow of the proposed Python/Gradio reliability-analysis workbench, a set of synthetic benchmark datasets was generated for four major reliability tasks: life data analysis, reliability growth analysis, repairable-system modeling, and accelerated life testing. The datasets were designed to represent different reliability scenarios, including right censoring, early-life failures, wear-out failures, mixed populations, reliability improvement, deteriorating growth, change-point behavior, heterogeneous repairable fleets, preventive-maintenance effects, overhaul-based step changes, Arrhenius temperature acceleration, and power-law stress acceleration. These datasets were used only for reproducible tool validation and demonstration, not as real industrial field data.

---

# Important note

These CSV files are designed to test whether the tool behaves correctly across different data structures and modeling scenarios.  
For publication-grade industrial inference, results should also be validated using real benchmark datasets, domain-specific assumptions, and independent reliability software where available.
