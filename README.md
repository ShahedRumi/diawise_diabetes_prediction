# DiaWise — Local Diabetes & Food Research Web Application

**Complete offline-hosted demonstration of your three thesis model workstreams.** Built with **Python, FastAPI, Uvicorn, HTML, CSS and vanilla JavaScript**. It runs on your computer; no cloud inference or database is used.

> **Medical caution:** This is a machine-learning research prototype, **not a diagnosis, clinical screening device or individualized food prescription**. It cannot confirm or rule out diabetes. The food labels originate from an author-curated dataset with some estimated nutrient values.

## 1. How to run on Windows (the easiest way)

1. Install **64-bit Python 3.11, 3.12, or 3.13** from [python.org](https://www.python.org/downloads/). During installation, select **Add Python to PATH**.
2. Extract the entire ZIP to a normal Windows folder, e.g., `D:\DiaWise` (do not launch files directly from inside ZIP).
3. Double-click **`run_windows.bat`**.
4. On the first run, the script creates a `.venv` environment and installs dependencies. This initial installation needs an internet connection; **running predictions afterwards does not need internet**.
5. The launcher validates the environment, loads all three models, and opens **http://127.0.0.1:8000** only after the application reports ready.
6. Keep the black terminal window running. To stop the website, press `Ctrl+C` in that terminal.

**The `.pkl` files are already included and trained.** You do **not** need to rerun training to start the website. All computations and data remain local to your machine.

### Windows manual commands

Open Command Prompt inside the project folder:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If Python 3.12 is not installed, substitute `py -3.11` or `py -3.13`. You can choose another free port by replacing `8000` with `8080` in the last command and browser URL.

### Mac / Linux

```bash
bash run_linux_mac.sh
# Then open http://127.0.0.1:8000
```

## 2. Website: two main tabs

### Tab A — Prediction Studio

Choose one of three models:

- **Model 1: PIMA Diabetes** — Enter its original 8 numeric variables (pregnancies, glucose, blood pressure, skin thickness, insulin, BMI, diabetes pedigree function, age). The saved pipeline handles zero-as-missing entries for appropriate fields, feature engineering **8 → 22**, median imputation, and Random Forest classification. The source data is the **Kaggle PIMA dataset**. The decision threshold is **0.48**.
- **Model 2: General Diabetes** — Choose **Full (8 inputs)** with HbA1c and blood glucose or **Non-Lab (6 inputs)** without them. Both trained LightGBM estimators use the experiment's **SMOTENC**-balanced training set. The original **Kaggle Diabetes Prediction dataset** has 100,000 rows; 96,146 remain after duplicate removal. Categorical encodings are identical to the supplied notebook. Non-lab results have **low positive precision** and must not be used to replace lab testing.
- **Model 3: Food Suitability** — Either search an existing food by name, or enter an unfamiliar food's serving size, total carbohydrate, sugar, fiber, fat and glycemic index. For unknown foods, mass-based values are normalized to **100 g**; the glycemic index **is not scaled**. The model is a **sigmoid-calibrated XGBoost classifier** trained from your **primarily author-created and curated** 718-item workbook. Known foods are returned by direct catalog lookup (not by ML inference). A probability **≤25%** returns “not recommended,” **≥75%** returns “recommended,” and otherwise the website says **uncertain**. These are notebook-defined thresholds, not clinically established recommendations.

All prediction inputs are handled **only in computer memory**. No user accounts or remote transmission are implemented. The web server binds to **127.0.0.1** by default, so it is only accessible from your PC.

### Tab B — About the Models

Contains explanations, the three data sources, research methodology diagrams, feature-ablation/SHAP discussion and limitations. The diagrams are sourced from your thesis work and project files.

## 3. Serialized artifacts — exactly three `.pkl` files

| File | Contents |
|---|---|
| `models/pima_model.pkl` | Custom PIMA feature builder + median imputer + tuned Random Forest pipeline. |
| `models/general_diabetes_model.pkl` | Dictionary containing **two trained LightGBM models** (`full`, `nonlab`) and their feature/encoding mappings. Both variants belong to **Model 2**. |
| `models/food_model.pkl` | Imputer + calibrated XGBoost pipeline. |

Models were serialized using `joblib` with a `.pkl` extension. **Unpickling arbitrary files is unsafe**: load only artifacts you personally generated or trust. The `.pkl` files depend on `app/ml/transforms.py` and its import path, so keep the `app` directory in the project.

`models/metrics.json` records actual held-out test results from the included retraining script. The training sets and feature engineering follow the provided notebooks. Re-training with a different Python/library version may yield slightly different results.

## 4. Re-training from scratch (optional)

If you ever modify any source dataset or need to reproduce the artifacts, after installing the requirements run:

```bat
python tools_export_food.py
python train_models.py
```

The first command uses a **standard-library ZIP/XML reader** for extracting the `ML Ready 100g` sheet from your original Excel file; it does not require Excel, extra packages, or a cloud connection. It is **optional if `data/food_100g.csv` is unchanged**. It reads stored cell values rather than recalculating formulas. The second command always works from the already-included CSV files and replaces the three `.pkl` files. To retrain on Windows, you can also double-click `train_models_windows.bat`.

### Retraining metrics on the included datasets

| Workstream | Held-out test records | Accuracy | Positive-class recall | Positive-class precision |
|---|---:|---:|---:|---:|
| Model 1: PIMA Random Forest | 154 | 87.01% | 85.19% | 79.31% |
| Model 2: Full LightGBM | 19,230 | 96.93% | 72.11% | 91.27% |
| Model 2: Non-lab LightGBM | 19,230 | 78.49% | 66.57% | 24.03% |
| Model 3: Calibrated XGBoost | 144 | 91.67% | 93.46% | 95.24% |

These metrics were **recomputed when creating the included artifacts** (see `models/metrics.json`). The Model 2 metrics may be slightly different from notebook outputs recorded in the thesis due to library versions or replay conditions. No claims of fresh external or clinical validation are made.

## 5. Files and folders

```text
DiaWise/
├── run_windows.bat                  # Double-click to launch (Windows)
├── run_windows.ps1                  # Validates/repairs the environment and supervises startup
├── train_models_windows.bat         # Optional retraining
├── run_linux_mac.sh
├── train_models.py                   # Reproduce three .pkl files
├── tools_export_food.py             # Optional Excel-to-CSV export
├── requirements.txt
├── README.md
├── app/
│   ├── main.py                      # FastAPI endpoints, validation and inference
│   ├── launcher.py                  # Server supervision, readiness wait and browser launch
│   └── ml/
│       ├── transforms.py            # PIMA feature engineering (pickle import path)
│       └── constants.py             # Feature lists and categorical maps
├── templates/
│   └── index.html                   # Two-tab UI
├── static/
│   ├── css/style.css                # Responsive premium UI
│   ├── js/main.js                   # Form flow, fetch, result rendering
│   └── images/                     # Original thesis figures and branding
├── models/
│   ├── pima_model.pkl
│   ├── general_diabetes_model.pkl
│   ├── food_model.pkl
│   └── metrics.json
├── data/
│   ├── pima_original.csv
│   ├── general_diabetes_original.csv
│   ├── food_dataset_original.xlsx
│   └── food_100g.csv
└── tests/
    └── test_api.py
```

## 6. API endpoints

- `GET /` — frontend
- `GET /api/health` — readiness and number of catalog foods
- `GET /api/models` — dataset provenance, actual local model metrics
- `POST /api/predict/pima` — PIMA prediction
- `POST /api/predict/general` — full or non-lab diabetes prediction
- `GET /api/foods?query=mango` — food-name autocomplete
- `POST /api/predict/food` — known-food lookup or unfamiliar-food nutrition inference
- `GET /api/docs` — automatically generated Swagger interface

Example requests from `curl`:

```bash
curl -X POST http://127.0.0.1:8000/api/predict/general -H "Content-Type: application/json" -d '{"mode":"nonlab","gender":"Female","age":47,"hypertension":0,"heart_disease":0,"smoking_history":"never","bmi":29.7}'
```

Model 3 custom example (`200 g` serving; GI is not normalized):

```json
{
  "food_name": "Homemade Snack",
  "serving_size_g": 200,
  "carbohydrate_g": 60,
  "sugar_g": 12,
  "fiber_g": 8,
  "fat_g": 6,
  "glycemic_index": 55
}
```

This becomes per 100g carbohydrate 30g, sugar 6g, fiber 4g, fat 3g, and GI 55.

## 7. Research restrictions and limitations

1. **Model 1:** The original PIMA data reflect a limited study population. No diagnosis can be established from the web form. The notebook's saved SHAP outputs may not fully match its current engineered-feature names; therefore, the application does not claim to provide personally tailored SHAP explanations.
2. **Model 2:** Class-imbalance handling was chosen by F1 score; a model optimized for recall alone may produce more false positives. Removing laboratory features significantly reduces precision. The binary target is recorded diabetes status rather than prospectively verified diabetes incidence.
3. **Model 3:** The labels were created/curated for this research, not validated against clinical meal outcomes. The workbook includes 104 estimated nutrient values flagged as unverified in its audit. The model does not consider patient medication, allergies, history or meal plans.
4. The user interface is a **local demonstration**, not a deployed hospital or production system. If the application is exposed to other computers or the public internet, additional privacy, security and regulatory work would be required.

## 8. Troubleshooting

- **`python` is not recognized**: install 64-bit Python and enable “Add Python to PATH,” then reopen Command Prompt.
- **`No module named fastapi`**: activate `.venv` and run `python -m pip install -r requirements.txt`.
- **`ModuleNotFoundError: app.ml.transforms`**: start Python from the project root; do not move a `.pkl` to a different directory by itself.
- **`Address already in use`**: close the other program using port 8000 or use `--port 8080`.
- **Model loading fails**: use Python 3.11–3.13 and the versions in `requirements.txt`; if necessary, retrain on your PC.
- **Browser shows connection refused**: make sure the terminal is still running, wait for `Uvicorn running on...`, then reload `http://127.0.0.1:8000`.
- **Check the Windows setup without starting the server**: run `run_windows.bat -Check` in Command Prompt.
- **Need to use a different PC on the LAN?** This project intentionally binds to localhost only; it does not expose patient inputs across the factory or internet.

---
**Research scope:** A reproducible educational demonstration of the notebook pipelines you supplied, not a replacement for a clinician, dietitian, or validated clinical software.
