
# ReliaPy-Workbench: Python/Gradio Reliability Analysis Tool for Colab
# Copy this entire cell after installing gradio.

import io
import math
import warnings
import tempfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import optimize, stats
import gradio as gr

warnings.filterwarnings("ignore")

EPS = 1e-12

def _path(file_obj):
    if file_obj is None:
        return None
    if isinstance(file_obj, str):
        return file_obj
    return getattr(file_obj, "name", None) or getattr(file_obj, "path", None)

def read_table(file_obj):
    path = _path(file_obj)
    if path is None:
        raise ValueError("Please upload a CSV file.")
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path)

def _clean_name(s):
    return str(s).strip()

def infer_col(df, requested, candidates, fallback_index=0):
    if requested and requested != "Auto":
        if requested not in df.columns:
            raise ValueError(f"Column '{requested}' not found. Available columns: {list(df.columns)}")
        return requested
    lower = {str(c).lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    # fuzzy contains
    for c in df.columns:
        lc = str(c).lower()
        if any(k in lc for k in candidates):
            return c
    if len(df.columns) > fallback_index:
        return df.columns[fallback_index]
    raise ValueError("Could not infer a required column.")

def as_event(series):
    s = series.copy()
    if s.dtype == bool:
        return s.astype(int).values
    if pd.api.types.is_numeric_dtype(s):
        return (pd.to_numeric(s, errors="coerce").fillna(0) > 0).astype(int).values
    ss = s.astype(str).str.lower().str.strip()
    return ss.isin(["1", "true", "t", "yes", "y", "event", "failed", "failure", "fail"]).astype(int).values

def benard_ranks(n):
    i = np.arange(1, n + 1)
    return (i - 0.3) / (n + 0.4)

def life_rank_regression(times, dist="Weibull"):
    t = np.asarray(times, dtype=float)
    t = np.sort(t[t > 0])
    n = len(t)
    if n < 2:
        raise ValueError("Rank regression needs at least two uncensored failure times.")
    F = benard_ranks(n)
    x = np.log(t)
    if dist == "Weibull":
        y = np.log(-np.log(1 - F))
        slope, intercept, r, p, se = stats.linregress(x, y)
        beta = max(slope, EPS)
        eta = float(np.exp(-intercept / beta))
        ll = weibull_loglik(t, np.ones_like(t), beta, eta)
        return {"dist": dist, "method": "Rank regression", "beta_shape": beta, "eta_scale": eta,
                "loglik_uncensored": ll, "rr_r2": r*r}
    else:
        y = stats.norm.ppf(F)
        slope, intercept, r, p, se = stats.linregress(x, y)
        sigma = max(1.0 / slope, EPS)
        mu = -intercept / slope
        ll = lognormal_loglik(t, np.ones_like(t), mu, sigma)
        return {"dist": dist, "method": "Rank regression", "mu_log": mu, "sigma_log": sigma,
                "median_life": float(np.exp(mu)), "loglik_uncensored": ll, "rr_r2": r*r}

def weibull_loglik(t, event, beta, eta):
    t = np.asarray(t, dtype=float)
    e = np.asarray(event, dtype=int)
    z = (t / eta) ** beta
    logpdf = np.log(beta) - beta * np.log(eta) + (beta - 1) * np.log(t) - z
    logsf = -z
    return float(np.sum(e * logpdf + (1 - e) * logsf))

def lognormal_loglik(t, event, mu, sigma):
    t = np.asarray(t, dtype=float)
    e = np.asarray(event, dtype=int)
    z = (np.log(t) - mu) / sigma
    logpdf = -np.log(t) - np.log(sigma) - 0.5*np.log(2*np.pi) - 0.5*z*z
    logsf = stats.norm.logsf(z)
    return float(np.sum(e * logpdf + (1 - e) * logsf))

def life_mle(times, event, dist="Weibull"):
    t = np.asarray(times, dtype=float)
    e = np.asarray(event, dtype=int)
    if len(t) < 2 or e.sum() < 1:
        raise ValueError("MLE needs at least two observations and at least one failure event.")
    fail = t[e == 1]
    rr = life_rank_regression(fail, dist) if len(fail) >= 2 else None
    if dist == "Weibull":
        if rr:
            init = [np.log(rr["beta_shape"]), np.log(rr["eta_scale"])]
        else:
            init = [0.0, np.log(np.median(t))]
        def nll(x):
            beta, eta = np.exp(x[0]), np.exp(x[1])
            return -weibull_loglik(t, e, beta, eta)
        res = optimize.minimize(nll, init, method="Nelder-Mead", options={"maxiter": 20000})
        beta, eta = np.exp(res.x[0]), np.exp(res.x[1])
        ll = -res.fun
        return {"dist": dist, "method": "MLE", "beta_shape": beta, "eta_scale": eta,
                "mean_life": float(eta * math.gamma(1 + 1/beta)),
                "median_life": float(eta * (np.log(2)) ** (1/beta)),
                "loglik": ll, "AIC": 2*2 - 2*ll, "BIC": 2*np.log(len(t)) - 2*ll,
                "events": int(e.sum()), "observations": len(t)}
    else:
        if rr:
            init = [rr["mu_log"], np.log(rr["sigma_log"])]
        else:
            init = [np.log(np.median(fail)), 0.0]
        def nll(x):
            mu, sigma = x[0], np.exp(x[1])
            return -lognormal_loglik(t, e, mu, sigma)
        res = optimize.minimize(nll, init, method="Nelder-Mead", options={"maxiter": 20000})
        mu, sigma = res.x[0], np.exp(res.x[1])
        ll = -res.fun
        return {"dist": dist, "method": "MLE", "mu_log": mu, "sigma_log": sigma,
                "median_life": float(np.exp(mu)), "mean_life": float(np.exp(mu + 0.5*sigma*sigma)),
                "loglik": ll, "AIC": 2*2 - 2*ll, "BIC": 2*np.log(len(t)) - 2*ll,
                "events": int(e.sum()), "observations": len(t)}

def reliability_at_time(params, mission_time):
    if mission_time is None or mission_time <= 0:
        return np.nan
    if params["dist"] == "Weibull":
        beta, eta = params["beta_shape"], params["eta_scale"]
        return float(np.exp(- (mission_time / eta) ** beta))
    else:
        mu, sigma = params["mu_log"], params["sigma_log"]
        return float(stats.norm.sf((np.log(mission_time) - mu) / sigma))

def life_probability_plot(t, e, params):
    fig, ax = plt.subplots(figsize=(7, 5))
    fail = np.sort(np.asarray(t)[np.asarray(e) == 1])
    if len(fail) < 2:
        ax.text(0.05, 0.5, "At least two failures are needed for a probability plot.", transform=ax.transAxes)
        return fig
    F = benard_ranks(len(fail))
    x = np.log(fail)
    if params["dist"] == "Weibull":
        y = np.log(-np.log(1 - F))
        ax.scatter(x, y, label="Median-rank failures")
        xx = np.linspace(x.min()*0.95, x.max()*1.05, 100)
        beta, eta = params["beta_shape"], params["eta_scale"]
        yy = beta * (xx - np.log(eta))
        ax.plot(xx, yy, label="Fitted Weibull line")
        ax.set_ylabel("ln[-ln(1-F)]")
        ax.set_title("Weibull Probability Plot")
    else:
        y = stats.norm.ppf(F)
        ax.scatter(x, y, label="Median-rank failures")
        xx = np.linspace(x.min()*0.95, x.max()*1.05, 100)
        mu, sigma = params["mu_log"], params["sigma_log"]
        yy = (xx - mu) / sigma
        ax.plot(xx, yy, label="Fitted Lognormal line")
        ax.set_ylabel("Normal quantile")
        ax.set_title("Lognormal Probability Plot")
    ax.set_xlabel("ln(time)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return fig

def life_cdf_plot(t, e, params):
    fig, ax = plt.subplots(figsize=(7, 5))
    fail = np.sort(np.asarray(t)[np.asarray(e) == 1])
    F = benard_ranks(len(fail)) if len(fail) else np.array([])
    if len(fail):
        ax.scatter(fail, F, label="Median-rank empirical CDF")
    x = np.linspace(max(min(np.asarray(t)) * 0.1, EPS), max(np.asarray(t)) * 1.15, 200)
    if params["dist"] == "Weibull":
        beta, eta = params["beta_shape"], params["eta_scale"]
        cdf = 1 - np.exp(-(x/eta)**beta)
    else:
        mu, sigma = params["mu_log"], params["sigma_log"]
        cdf = stats.norm.cdf((np.log(x) - mu)/sigma)
    ax.plot(x, cdf, label="Fitted CDF")
    ax.set_xlabel("Time")
    ax.set_ylabel("F(t)")
    ax.set_title("Fitted Life Distribution")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return fig

def life_contour_plot(t, e, params):
    fig, ax = plt.subplots(figsize=(7, 5))
    try:
        if params["dist"] == "Weibull":
            beta0, eta0 = params["beta_shape"], params["eta_scale"]
            beta_grid = np.linspace(max(beta0*0.35, EPS), beta0*2.5, 70)
            eta_grid = np.linspace(max(eta0*0.35, EPS), eta0*2.5, 70)
            B, E = np.meshgrid(beta_grid, eta_grid)
            LL = np.zeros_like(B)
            for i in range(B.shape[0]):
                for j in range(B.shape[1]):
                    LL[i, j] = weibull_loglik(t, e, B[i, j], E[i, j])
            D = -2*(LL - np.max(LL))
            cs = ax.contour(B, E, D, levels=[2.30, 6.18, 11.83])
            ax.clabel(cs, inline=True, fontsize=8)
            ax.scatter([beta0], [eta0], marker="x", s=80, label="Estimate")
            ax.set_xlabel("Shape beta")
            ax.set_ylabel("Scale eta")
            ax.set_title("Weibull Likelihood Contours")
        else:
            mu0, sigma0 = params["mu_log"], params["sigma_log"]
            mu_grid = np.linspace(mu0 - 2.0*sigma0, mu0 + 2.0*sigma0, 70)
            sig_grid = np.linspace(max(sigma0*0.35, EPS), sigma0*2.5, 70)
            M, S = np.meshgrid(mu_grid, sig_grid)
            LL = np.zeros_like(M)
            for i in range(M.shape[0]):
                for j in range(M.shape[1]):
                    LL[i, j] = lognormal_loglik(t, e, M[i, j], S[i, j])
            D = -2*(LL - np.max(LL))
            cs = ax.contour(M, S, D, levels=[2.30, 6.18, 11.83])
            ax.clabel(cs, inline=True, fontsize=8)
            ax.scatter([mu0], [sigma0], marker="x", s=80, label="Estimate")
            ax.set_xlabel("mu")
            ax.set_ylabel("sigma")
            ax.set_title("Lognormal Likelihood Contours")
        ax.grid(True, alpha=0.3)
        ax.legend()
    except Exception as exc:
        ax.text(0.05, 0.5, f"Contour plot could not be computed:\n{exc}", transform=ax.transAxes)
    fig.tight_layout()
    return fig

def fit_life_data(file_obj, dist, method, time_col, event_col, mission_time):
    try:
        df = read_table(file_obj)
        tc = infer_col(df, time_col, ["time", "ttf", "failure_time", "life", "hours", "cycles"], 0)
        raw_t = pd.to_numeric(df[tc], errors="coerce")
        if event_col and event_col != "Auto" and event_col != "None":
            ec = infer_col(df, event_col, ["event", "status", "failed", "failure", "censor", "censored"], 1)
            event = as_event(df[ec])
        else:
            # Auto uses event/status column if present; otherwise all failures
            possible = [c for c in df.columns if str(c).lower().strip() in ["event", "status", "failed", "failure"]]
            event = as_event(df[possible[0]]) if possible else np.ones(len(df), dtype=int)
        mask = np.isfinite(raw_t) & (raw_t > 0) & np.isfinite(event)
        t = raw_t[mask].values.astype(float)
        e = np.asarray(event)[mask].astype(int)
        if method == "Rank Regression":
            params = life_rank_regression(t[e == 1], dist)
            params["observations"] = len(t)
            params["events_used"] = int(e.sum())
            params["note"] = "Rank regression uses uncensored failures; right-censored rows are not used in the line fit."
        else:
            params = life_mle(t, e, dist)
        params[f"Reliability_at_t={mission_time}"] = reliability_at_time(params, mission_time)
        summary = pd.DataFrame({"Metric": list(params.keys()), "Value": [params[k] for k in params.keys()]})
        fig1 = life_probability_plot(t, e, params)
        fig2 = life_contour_plot(t, e, params)
        fig3 = life_cdf_plot(t, e, params)
        return summary, fig1, fig2, fig3, f"Used time column: {tc}. Observations after cleaning: {len(t)}."
    except Exception as exc:
        return pd.DataFrame({"Error": [str(exc)]}), None, None, None, "Analysis failed."

def plp_fit(times, T=None):
    t = np.asarray(times, dtype=float)
    t = t[np.isfinite(t) & (t > 0)]
    if T is None:
        T = np.max(t)
    T = float(T)
    if len(t) < 2 or T <= 0:
        raise ValueError("PLP/Crow-AMSAA needs at least two positive event times.")
    denom = np.sum(np.log(T / np.clip(t, EPS, None)))
    beta = len(t) / max(denom, EPS)
    lam = len(t) / (T ** beta)
    ll = float(np.sum(np.log(lam*beta) + (beta - 1)*np.log(np.clip(t, EPS, None))) - lam*(T**beta))
    return {"lambda": float(lam), "beta": float(beta), "T": T, "n_events": len(t), "loglik": ll, "AIC": 2*2 - 2*ll}

def loglinear_nhpp_fit(times, T=None, n_systems=1):
    t = np.asarray(times, dtype=float)
    t = t[np.isfinite(t) & (t >= 0)]
    if T is None:
        T = np.max(t)
    T = float(T)
    n_systems = max(int(n_systems), 1)
    if len(t) < 2:
        raise ValueError("Log-linear NHPP needs at least two event times.")
    init_rate = len(t) / max(n_systems*T, EPS)
    init = [np.log(max(init_rate, EPS)), 0.0]
    def cum_int(a, b):
        if abs(b) < 1e-8:
            return n_systems * np.exp(a) * T
        return n_systems * np.exp(a) * (np.exp(b*T) - 1.0) / b
    def nll(x):
        a, b = x
        val = np.sum(a + b*t) - cum_int(a, b)
        if not np.isfinite(val):
            return 1e100
        return -val
    res = optimize.minimize(nll, init, method="Nelder-Mead", options={"maxiter": 20000})
    a, b = res.x
    ll = -res.fun
    return {"a_log_rate": float(a), "b_time_slope": float(b), "T": T, "n_events": len(t),
            "loglik": float(ll), "AIC": 2*2 - 2*ll}

def parse_breakpoints(text):
    if not text or str(text).strip() == "":
        return []
    vals = []
    for x in str(text).replace(";", ",").split(","):
        x = x.strip()
        if x:
            vals.append(float(x))
    return sorted(vals)

def segment_plp(times, breakpoints=None, auto=False):
    t = np.sort(np.asarray(times, dtype=float))
    t = t[np.isfinite(t) & (t > 0)]
    T = float(np.max(t))
    if auto:
        candidates = np.unique(t)
        candidates = candidates[(candidates > np.quantile(t, 0.2)) & (candidates < np.quantile(t, 0.8))]
        best = None
        for bp in candidates:
            left = t[t <= bp]
            right = t[t > bp] - bp
            try:
                if len(left) < 3 or len(right) < 3:
                    continue
                f1 = plp_fit(left, T=bp)
                f2 = plp_fit(right, T=T-bp)
                aic = f1["AIC"] + f2["AIC"]
                if best is None or aic < best[0]:
                    best = (aic, bp, f1, f2)
            except Exception:
                pass
        if best is not None:
            breakpoints = [best[1]]
        else:
            breakpoints = []
    if breakpoints is None:
        breakpoints = []
    cuts = [0.0] + [bp for bp in breakpoints if 0 < bp < T] + [T]
    rows = []
    for i in range(len(cuts)-1):
        start, end = cuts[i], cuts[i+1]
        seg_abs = t[(t > start) & (t <= end)]
        local = seg_abs - start
        if len(local) >= 2:
            fit = plp_fit(np.clip(local, EPS, None), T=end-start)
            rows.append({"segment": i+1, "start": start, "end": end, **fit})
        else:
            rows.append({"segment": i+1, "start": start, "end": end, "n_events": len(local),
                         "lambda": np.nan, "beta": np.nan, "loglik": np.nan, "AIC": np.nan})
    return pd.DataFrame(rows), cuts

def growth_plots(times, summary_segments, cuts):
    t = np.sort(np.asarray(times, dtype=float))
    n = np.arange(1, len(t)+1)
    T = max(t)

    fig1, ax = plt.subplots(figsize=(7, 5))
    ax.step(t, n, where="post", label="Observed cumulative failures")
    xx_full = []
    yy_full = []
    cum_prev = 0.0
    for _, row in summary_segments.iterrows():
        start, end = row["start"], row["end"]
        if np.isfinite(row.get("lambda", np.nan)) and np.isfinite(row.get("beta", np.nan)):
            xs = np.linspace(start, end, 80)
            local = np.clip(xs - start, 0, None)
            ys = cum_prev + row["lambda"] * (local ** row["beta"])
            xx_full.extend(xs.tolist())
            yy_full.extend(ys.tolist())
        cum_prev += row.get("n_events", 0)
    if xx_full:
        ax.plot(xx_full, yy_full, label="Fitted NHPP mean")
    for bp in cuts[1:-1]:
        ax.axvline(bp, linestyle="--", alpha=0.6)
    ax.set_xlabel("Cumulative test time")
    ax.set_ylabel("Cumulative failures")
    ax.set_title("Reliability Growth / NHPP Plot")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig1.tight_layout()

    fig2, ax = plt.subplots(figsize=(7, 5))
    cum_mtbf = t / n
    ax.plot(t, cum_mtbf, marker="o", linewidth=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Cumulative test time")
    ax.set_ylabel("Cumulative MTBF = time / failures")
    ax.set_title("Duane Plot")
    ax.grid(True, alpha=0.3, which="both")
    fig2.tight_layout()
    return fig1, fig2

def fit_growth(file_obj, model_type, time_col, breakpoints_text):
    try:
        df = read_table(file_obj)
        tc = infer_col(df, time_col, ["time", "event_time", "failure_time", "test_time", "hours", "cycles"], 0)
        t = pd.to_numeric(df[tc], errors="coerce").dropna().values.astype(float)
        t = np.sort(t[t > 0])
        if len(t) < 2:
            raise ValueError("At least two positive cumulative event times are required.")
        if model_type == "Crow-AMSAA":
            seg_df, cuts = segment_plp(t, breakpoints=[])
        elif model_type == "Piecewise NHPP":
            seg_df, cuts = segment_plp(t, breakpoints=parse_breakpoints(breakpoints_text), auto=False)
        else:
            seg_df, cuts = segment_plp(t, auto=True)
        fig1, fig2 = growth_plots(t, seg_df, cuts)
        interpretation = []
        for _, r in seg_df.iterrows():
            beta = r.get("beta", np.nan)
            if np.isfinite(beta):
                trend = "improving/decreasing event intensity" if beta < 1 else "deteriorating/increasing event intensity" if beta > 1 else "approximately constant intensity"
                interpretation.append(f"Segment {int(r['segment'])}: beta={beta:.4g}, indicating {trend}.")
        return seg_df, fig1, fig2, "\n".join(interpretation) + f"\nUsed time column: {tc}."
    except Exception as exc:
        return pd.DataFrame({"Error": [str(exc)]}), None, None, "Analysis failed."

def repair_plots(t, model_params, model_name, n_systems=1, sys_ids=None):
    t = np.sort(np.asarray(t, dtype=float))
    T = max(t)
    fig1, ax = plt.subplots(figsize=(7, 5))
    ax.step(t, np.arange(1, len(t)+1), where="post", label="Observed cumulative events")
    xx = np.linspace(max(T*0.001, EPS), T, 200)
    if model_name == "Power Law":
        lam, beta = model_params["lambda"], model_params["beta"]
        yy = n_systems * lam * (xx ** beta)
    elif model_name == "Log-Linear":
        a, b = model_params["a_log_rate"], model_params["b_time_slope"]
        if abs(b) < 1e-8:
            yy = n_systems * np.exp(a) * xx
        else:
            yy = n_systems * np.exp(a) * (np.exp(b*xx) - 1) / b
    else:
        yy = None
    if yy is not None:
        ax.plot(xx, yy, label="Fitted cumulative mean")
    ax.set_xlabel("Time")
    ax.set_ylabel("Cumulative events")
    ax.set_title("Repairable-System Cumulative Events")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig1.tight_layout()

    fig2, ax = plt.subplots(figsize=(7, 5))
    if model_name == "Power Law":
        lam, beta = model_params["lambda"], model_params["beta"]
        rate = lam * beta * (xx ** (beta - 1))
    elif model_name == "Log-Linear":
        a, b = model_params["a_log_rate"], model_params["b_time_slope"]
        rate = np.exp(a + b*xx)
    else:
        # crude smoothed empirical rate for piecewise
        bins = np.linspace(0, T, 12)
        counts, edges = np.histogram(t, bins=bins)
        centers = 0.5*(edges[1:]+edges[:-1])
        widths = np.diff(edges)
        ax.plot(centers, counts / np.maximum(widths*n_systems, EPS), marker="o")
        rate = None
    if rate is not None:
        ax.plot(xx, rate)
    ax.set_xlabel("Time")
    ax.set_ylabel("Event rate per system")
    ax.set_title("Estimated Event Rate")
    ax.grid(True, alpha=0.3)
    fig2.tight_layout()

    fig3, ax = plt.subplots(figsize=(7, 5))
    if sys_ids is None:
        # one system MCF equals cumulative events
        ax.step(t, np.arange(1, len(t)+1), where="post")
    else:
        tmp = pd.DataFrame({"time": t, "system": sys_ids}).sort_values("time")
        counts = tmp.groupby("time").size().sort_index()
        mcf = counts.cumsum() / max(n_systems, 1)
        ax.step(mcf.index.values, mcf.values, where="post")
    ax.set_xlabel("Time")
    ax.set_ylabel("Mean cumulative function")
    ax.set_title("Mean Cumulative Function (MCF)")
    ax.grid(True, alpha=0.3)
    fig3.tight_layout()
    return fig1, fig2, fig3

def fit_repairable(file_obj, model_type, time_col, system_col, breakpoints_text):
    try:
        df = read_table(file_obj)
        tc = infer_col(df, time_col, ["time", "event_time", "repair_time", "failure_time", "hours", "cycles"], 0)
        time = pd.to_numeric(df[tc], errors="coerce")
        mask = np.isfinite(time) & (time > 0)
        t = time[mask].values.astype(float)
        sys_ids = None
        if system_col and system_col != "Auto" and system_col != "None":
            sc = infer_col(df, system_col, ["system", "unit", "asset", "id"], 1)
            sys_ids = df.loc[mask, sc].astype(str).values
            n_systems = len(pd.unique(sys_ids))
        else:
            possible = [c for c in df.columns if any(k in str(c).lower() for k in ["system", "unit", "asset"])]
            if possible:
                sys_ids = df.loc[mask, possible[0]].astype(str).values
                n_systems = len(pd.unique(sys_ids))
            else:
                n_systems = 1
        if len(t) < 2:
            raise ValueError("At least two repair/failure event times are required.")
        if model_type == "Power Law":
            fit = plp_fit(t, T=max(t))
            summary = pd.DataFrame({"Metric": list(fit.keys()) + ["assumed_number_of_systems"],
                                    "Value": list(fit.values()) + [n_systems]})
            fig1, fig2, fig3 = repair_plots(t, fit, "Power Law", n_systems, sys_ids)
        elif model_type == "Log-Linear":
            fit = loglinear_nhpp_fit(t, T=max(t), n_systems=n_systems)
            summary = pd.DataFrame({"Metric": list(fit.keys()) + ["assumed_number_of_systems"],
                                    "Value": list(fit.values()) + [n_systems]})
            fig1, fig2, fig3 = repair_plots(t, fit, "Log-Linear", n_systems, sys_ids)
        else:
            seg_df, cuts = segment_plp(t, parse_breakpoints(breakpoints_text), auto=False)
            summary = seg_df
            # plot observed plus piecewise fitted using growth plot
            fig1, _ = growth_plots(t, seg_df, cuts)
            # empirical rate and MCF
            fig2, _, fig3 = repair_plots(t, {}, "Piecewise", n_systems, sys_ids)
        note = f"Used time column: {tc}. Number of systems inferred: {n_systems}. If systems have different observation windows, add exposure handling before publication-grade inference."
        return summary, fig1, fig2, fig3, note
    except Exception as exc:
        return pd.DataFrame({"Error": [str(exc)]}), None, None, None, "Analysis failed."

def alt_transform(stress, relationship):
    s = np.asarray(stress, dtype=float)
    if relationship == "Arrhenius; temperature in Celsius":
        return 1.0 / (s + 273.15), "1 / absolute temperature (K^-1)"
    if relationship == "Arrhenius; temperature in Kelvin":
        return 1.0 / s, "1 / absolute temperature (K^-1)"
    return np.log(s), "ln(stress)"

def alt_weibull_loglik(t, event, x, a, b, beta):
    eta = np.exp(a + b*x)
    z = (t / eta) ** beta
    logpdf = np.log(beta) - beta*np.log(eta) + (beta-1)*np.log(t) - z
    logsf = -z
    return float(np.sum(event*logpdf + (1-event)*logsf))

def alt_lognormal_loglik(t, event, x, a, b, sigma):
    mu = a + b*x
    z = (np.log(t) - mu) / sigma
    logpdf = -np.log(t) - np.log(sigma) - 0.5*np.log(2*np.pi) - 0.5*z*z
    logsf = stats.norm.logsf(z)
    return float(np.sum(event*logpdf + (1-event)*logsf))

def fit_alt_model(t, event, stress, dist, relationship):
    x, xlab = alt_transform(stress, relationship)
    # initialize by regression on log failure time
    fail = event == 1
    if fail.sum() >= 2 and len(np.unique(x[fail])) >= 2:
        slope, intercept, *_ = stats.linregress(x[fail], np.log(t[fail]))
        a0, b0 = intercept, slope
    else:
        a0, b0 = np.log(np.median(t)), 0.0
    if dist == "Weibull":
        init = [a0, b0, 0.0]  # log beta
        def nll(par):
            a, b, logbeta = par
            return -alt_weibull_loglik(t, event, x, a, b, np.exp(logbeta))
        res = optimize.minimize(nll, init, method="Nelder-Mead", options={"maxiter": 30000})
        a, b, logbeta = res.x
        beta = np.exp(logbeta)
        ll = -res.fun
        out = {"distribution": "Weibull", "relationship": relationship, "a_intercept_log_eta": a,
               "b_stress_slope": b, "beta_shape_common": beta,
               "loglik": ll, "AIC": 2*3 - 2*ll, "BIC": 3*np.log(len(t)) - 2*ll}
    else:
        init = [a0, b0, 0.0]  # log sigma
        def nll(par):
            a, b, logsig = par
            return -alt_lognormal_loglik(t, event, x, a, b, np.exp(logsig))
        res = optimize.minimize(nll, init, method="Nelder-Mead", options={"maxiter": 30000})
        a, b, logsig = res.x
        sigma = np.exp(logsig)
        ll = -res.fun
        out = {"distribution": "Lognormal", "relationship": relationship, "a_intercept_mu": a,
               "b_stress_slope": b, "sigma_common": sigma,
               "loglik": ll, "AIC": 2*3 - 2*ll, "BIC": 3*np.log(len(t)) - 2*ll}
    return out, x, xlab

def alt_plots(t, event, stress, params, x, xlab):
    fig1, ax = plt.subplots(figsize=(7, 5))
    for s in sorted(pd.unique(stress)):
        mask = (stress == s) & (event == 1)
        tf = np.sort(t[mask])
        if len(tf) >= 2:
            F = benard_ranks(len(tf))
            if params["distribution"] == "Weibull":
                y = np.log(-np.log(1-F))
                ax.scatter(np.log(tf), y, label=f"stress={s}")
            else:
                y = stats.norm.ppf(F)
                ax.scatter(np.log(tf), y, label=f"stress={s}")
    ax.set_xlabel("ln(time)")
    ax.set_ylabel("Weibull/lognormal probability scale")
    ax.set_title("ALT Probability Plot by Stress Level")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig1.tight_layout()

    fig2, ax = plt.subplots(figsize=(7, 5))
    raw_s_grid = np.linspace(np.min(stress), np.max(stress), 200)
    xg, _ = alt_transform(raw_s_grid, params["relationship"])
    if params["distribution"] == "Weibull":
        life = np.exp(params["a_intercept_log_eta"] + params["b_stress_slope"]*xg)
        ylab = "Characteristic life eta"
    else:
        life = np.exp(params["a_intercept_mu"] + params["b_stress_slope"]*xg)
        ylab = "Median life"
    # Observed stress-wise median failure times
    med = pd.DataFrame({"time": t[event == 1], "stress": stress[event == 1]}).groupby("stress")["time"].median()
    if len(med):
        ax.scatter(med.index.values, med.values, label="Observed median failure time")
    ax.plot(raw_s_grid, life, label="Fitted life-stress curve")
    ax.set_xlabel("Stress")
    ax.set_ylabel(ylab)
    ax.set_yscale("log")
    ax.set_title("Life-Stress Relationship")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig2.tight_layout()
    return fig1, fig2

def fit_alt(file_obj, dist, relationship, time_col, stress_col, event_col, use_stress):
    try:
        df = read_table(file_obj)
        tc = infer_col(df, time_col, ["time", "ttf", "failure_time", "life", "hours", "cycles"], 0)
        sc = infer_col(df, stress_col, ["stress", "temperature", "temp", "voltage", "load"], 1)
        t = pd.to_numeric(df[tc], errors="coerce").values
        stress = pd.to_numeric(df[sc], errors="coerce").values
        if event_col and event_col != "Auto" and event_col != "None":
            ec = infer_col(df, event_col, ["event", "status", "failed", "failure"], 2)
            event = as_event(df[ec])
        else:
            possible = [c for c in df.columns if str(c).lower().strip() in ["event", "status", "failed", "failure"]]
            event = as_event(df[possible[0]]) if possible else np.ones(len(df), dtype=int)
        mask = np.isfinite(t) & np.isfinite(stress) & (t > 0) & (stress > 0) & np.isfinite(event)
        t, stress, event = t[mask].astype(float), stress[mask].astype(float), np.asarray(event)[mask].astype(int)
        if len(t) < 3 or event.sum() < 2:
            raise ValueError("ALT fitting needs at least three rows and at least two failures.")
        params, x, xlab = fit_alt_model(t, event, stress, dist, relationship)
        if use_stress is not None and np.isfinite(use_stress) and use_stress > 0:
            xu, _ = alt_transform(np.array([use_stress]), relationship)
            if dist == "Weibull":
                eta_use = float(np.exp(params["a_intercept_log_eta"] + params["b_stress_slope"]*xu[0]))
                params[f"eta_at_use_stress_{use_stress}"] = eta_use
            else:
                med_use = float(np.exp(params["a_intercept_mu"] + params["b_stress_slope"]*xu[0]))
                params[f"median_life_at_use_stress_{use_stress}"] = med_use
        params["stress_transform"] = xlab
        params["observations"] = len(t)
        params["events"] = int(event.sum())
        summary = pd.DataFrame({"Metric": list(params.keys()), "Value": [params[k] for k in params.keys()]})
        fig1, fig2 = alt_plots(t, event, stress, params, x, xlab)
        note = f"Used time column: {tc}; stress column: {sc}. Relationship transform: {xlab}."
        return summary, fig1, fig2, note
    except Exception as exc:
        return pd.DataFrame({"Error": [str(exc)]}), None, None, "Analysis failed."

def sample_life_csv():
    rng = np.random.default_rng(7)
    beta, eta = 1.8, 500
    t = eta * rng.weibull(beta, 80)
    censor = rng.uniform(350, 900, 80)
    obs = np.minimum(t, censor)
    event = (t <= censor).astype(int)
    return pd.DataFrame({"time": np.round(obs, 2), "event": event})

def sample_growth_csv():
    rng = np.random.default_rng(9)
    # NHPP with mean lambda*t^beta
    beta, lam = 0.72, 0.45
    n = 50
    u = np.sort(rng.uniform(0, 1, n))
    T = (n/lam)**(1/beta)
    times = T * (u ** (1/beta))
    return pd.DataFrame({"event_time": np.round(times, 2)})

def sample_repair_csv():
    rng = np.random.default_rng(3)
    rows = []
    for sys in range(1, 6):
        gaps = rng.exponential(80, size=10)
        times = np.cumsum(gaps)
        for tm in times[times < 600]:
            rows.append({"system": f"S{sys}", "event_time": round(float(tm), 2)})
    return pd.DataFrame(rows)

def sample_alt_csv():
    rng = np.random.default_rng(5)
    rows = []
    for temp in [85, 105, 125]:
        x = 1/(temp+273.15)
        eta = np.exp(2.0 + 3800*x)  # longer life at lower temperature
        beta = 1.7
        for i in range(30):
            true_t = eta * rng.weibull(beta)
            censor = rng.uniform(1000, 5000)
            rows.append({"time": round(float(min(true_t, censor)), 2),
                         "event": int(true_t <= censor),
                         "temperature": temp})
    return pd.DataFrame(rows)

# -----------------------------------------------------------------------------
# Presentation and export layer
# The analytical functions above are intentionally unchanged. The wrapper
# functions below only call the existing computations and save returned tables
# and figures as downloadable artifacts for the Gradio interface.
# -----------------------------------------------------------------------------
import os
import time
import uuid

# Gradio can only serve returned files safely from the current working directory,
# system temp directory, upload directory, or explicit allowed_paths.
EXPORT_DIR = os.path.join(tempfile.gettempdir(), "reliapy_exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


def _export_token(prefix):
    return f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def _save_summary_csv(df, token):
    path = os.path.join(EXPORT_DIR, f"{token}_summary.csv")
    try:
        if isinstance(df, pd.DataFrame):
            df.to_csv(path, index=False)
            return path
    except Exception:
        pass
    return None


def _save_figure_png(fig, token, suffix):
    if fig is None:
        return None
    path = os.path.join(EXPORT_DIR, f"{token}_{suffix}.png")
    try:
        fig.savefig(path, dpi=300, bbox_inches="tight")
        return path
    except Exception:
        return None


def run_life_with_downloads(file_obj, dist, method, time_col, event_col, mission_time):
    summary, fig1, fig2, fig3, note = fit_life_data(file_obj, dist, method, time_col, event_col, mission_time)
    token = _export_token("life_data")
    csv_path = _save_summary_csv(summary, token)
    p1 = _save_figure_png(fig1, token, "probability_plot")
    p2 = _save_figure_png(fig2, token, "likelihood_contour")
    p3 = _save_figure_png(fig3, token, "fitted_cdf")
    return summary, fig1, fig2, fig3, note, csv_path, p1, p2, p3


def run_growth_with_downloads(file_obj, model_type, time_col, breakpoints_text):
    summary, fig1, fig2, note = fit_growth(file_obj, model_type, time_col, breakpoints_text)
    token = _export_token("reliability_growth")
    csv_path = _save_summary_csv(summary, token)
    p1 = _save_figure_png(fig1, token, "growth_plot")
    p2 = _save_figure_png(fig2, token, "duane_plot")
    return summary, fig1, fig2, note, csv_path, p1, p2


def run_repairable_with_downloads(file_obj, model_type, time_col, system_col, breakpoints_text):
    summary, fig1, fig2, fig3, note = fit_repairable(file_obj, model_type, time_col, system_col, breakpoints_text)
    token = _export_token("repairable_system")
    csv_path = _save_summary_csv(summary, token)
    p1 = _save_figure_png(fig1, token, "cumulative_events")
    p2 = _save_figure_png(fig2, token, "event_rate")
    p3 = _save_figure_png(fig3, token, "mcf")
    return summary, fig1, fig2, fig3, note, csv_path, p1, p2, p3


def run_alt_with_downloads(file_obj, dist, relationship, time_col, stress_col, event_col, use_stress):
    summary, fig1, fig2, note = fit_alt(file_obj, dist, relationship, time_col, stress_col, event_col, use_stress)
    token = _export_token("accelerated_life_testing")
    csv_path = _save_summary_csv(summary, token)
    p1 = _save_figure_png(fig1, token, "alt_probability_plot")
    p2 = _save_figure_png(fig2, token, "life_stress_plot")
    return summary, fig1, fig2, note, csv_path, p1, p2


APP_CSS = """
:root {
    --rp-red: #d71920;
    --rp-red-dark: #991b1b;
    --rp-red-soft: rgba(215, 25, 32, .10);
    --rp-ink: #0f172a;
    --rp-slate: #334155;
    --rp-muted: #64748b;
    --rp-line: rgba(15, 23, 42, .10);
    --rp-card: rgba(255, 255, 255, .92);
    --rp-bg: #f5f7fb;
}

.gradio-container {
    max-width: 1480px !important;
    margin: 0 auto !important;
    color: var(--rp-ink) !important;
    background:
        radial-gradient(circle at 8% 4%, rgba(215, 25, 32, .14), transparent 28%),
        radial-gradient(circle at 92% 0%, rgba(2, 132, 199, .09), transparent 26%),
        linear-gradient(180deg, #ffffff 0%, var(--rp-bg) 100%) !important;
}

#title-banner {
    position: relative;
    overflow: hidden;
    padding: 34px 38px;
    border-radius: 28px;
    background:
        linear-gradient(135deg, rgba(153, 27, 27, .98), rgba(215, 25, 32, .94) 45%, rgba(15, 23, 42, .96));
    color: white;
    margin: 14px 0 20px 0;
    border: 1px solid rgba(255, 255, 255, .24);
    box-shadow: 0 24px 70px rgba(15, 23, 42, .22);
}
#title-banner:before {
    content: "";
    position: absolute;
    right: -95px;
    top: -95px;
    width: 340px;
    height: 340px;
    border-radius: 999px;
    background: rgba(255, 255, 255, .11);
}
#title-banner:after {
    content: "";
    position: absolute;
    right: 98px;
    bottom: -120px;
    width: 270px;
    height: 270px;
    border-radius: 999px;
    border: 42px solid rgba(255, 255, 255, .07);
}
#title-banner h1 {
    position: relative;
    font-size: 2.8rem;
    letter-spacing: -.05em;
    margin: 0 0 9px 0;
    line-height: 1.02;
}
#title-banner p {
    position: relative;
    max-width: 920px;
    margin: 0;
    font-size: 1.07rem;
    color: rgba(255, 255, 255, .89);
    line-height: 1.55;
}
#hero-kicker {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 7px 13px;
    border-radius: 999px;
    background: rgba(255,255,255,.16);
    color: rgba(255,255,255,.96);
    font-size: .78rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .09em;
    margin-bottom: 14px;
}

.metric-card {
    padding: 20px 20px;
    min-height: 128px;
    border: 1px solid var(--rp-line);
    border-radius: 22px;
    background: var(--rp-card);
    box-shadow: 0 14px 38px rgba(15, 23, 42, .075);
    transition: transform .18s ease, box-shadow .18s ease;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 20px 48px rgba(15, 23, 42, .10); }
.metric-card .icon {
    display: inline-flex;
    width: 38px;
    height: 38px;
    align-items: center;
    justify-content: center;
    border-radius: 13px;
    color: #fff;
    background: linear-gradient(135deg, var(--rp-red), #ef4444);
    margin-bottom: 10px;
    font-size: 1.1rem;
}
.metric-card h3 { margin: 0 0 7px 0; font-size: 1.02rem; color: var(--rp-ink); }
.metric-card p { margin: 0; color: var(--rp-muted); font-size: .91rem; line-height: 1.45; }

.module-intro {
    padding: 18px 20px;
    border: 1px solid var(--rp-line);
    border-left: 7px solid var(--rp-red);
    border-radius: 20px;
    background: rgba(255, 255, 255, .88);
    box-shadow: 0 10px 30px rgba(15,23,42,.055);
    margin: 10px 0 13px 0;
}
.module-intro h2 { margin: 0 0 6px 0; font-size: 1.35rem; letter-spacing: -.02em; }
.module-intro p { margin: 0; color: var(--rp-muted); line-height: 1.5; }

.control-panel, .output-panel, .download-panel {
    border: 1px solid var(--rp-line) !important;
    border-radius: 22px !important;
    background: rgba(255, 255, 255, .90) !important;
    box-shadow: 0 12px 34px rgba(15, 23, 42, .06) !important;
    padding: 14px !important;
}
.plot-card {
    border: 1px solid var(--rp-line) !important;
    border-radius: 20px !important;
    background: rgba(255, 255, 255, .92) !important;
    box-shadow: 0 10px 28px rgba(15, 23, 42, .055) !important;
    padding: 9px !important;
}
.download-card {
    border: 1px dashed rgba(215, 25, 32, .32) !important;
    border-radius: 18px !important;
    background: linear-gradient(180deg, rgba(255,255,255,.92), rgba(254,242,242,.55)) !important;
    padding: 10px !important;
}
.footer-note {
    margin-top: 16px;
    padding: 17px 19px;
    border-radius: 19px;
    background: #fff7ed;
    border: 1px solid rgba(249,115,22,.22);
    color: #7c2d12;
    line-height: 1.48;
}

.gr-button-primary {
    border-radius: 13px !important;
    font-weight: 800 !important;
    box-shadow: 0 10px 24px rgba(215, 25, 32, .22) !important;
}
.gr-button-secondary, button { border-radius: 13px !important; }
.tabitem { padding-top: 14px !important; }
.block label, .gradio-container label { font-weight: 700 !important; color: #334155 !important; }
textarea, input, select { border-radius: 13px !important; }
.table-wrap, .dataframe { border-radius: 15px !important; }
.file-preview, .upload-container { border-radius: 15px !important; }
code { background: rgba(15,23,42,.06); padding: 2px 5px; border-radius: 6px; }
"""

INTRO_HTML = """
<div id="title-banner">
  <div id="hero-kicker">Reliability analysis · Python · Gradio · Colab-ready</div>
  <h1>ReliaPy Workbench</h1>
  <p>Publication-oriented reliability analysis dashboard for life data, reliability growth, repairable systems, and accelerated life testing. The calculation layer is preserved; this version enriches the interface and adds downloadable CSV/PNG exports.</p>
  <p style="margin-top:12px;font-size:0.95rem;color:rgba(255,255,255,.86);"><strong>Developer:</strong> Partha Pratim Ray, Sikkim University · July 2026 · <strong>Email:</strong> parthapratimray1986@gmail.com</p>
</div>
"""

CSV_NOTE = """
<div class="module-intro">
<h2>Input convention and export support</h2>
<p>Upload CSV or Excel files with positive numeric times. Optional event/status columns accept <code>1/true/failure</code> as failure and <code>0/false</code> as right-censored. After every run, the result table can be downloaded as CSV and each plot can be downloaded as a 300-dpi PNG image.</p>
</div>
"""


def download_area(csv_component, plot_components):
    gr.Markdown("### ⬇️ Downloads")
    with gr.Row():
        csv_component.render()
    with gr.Row():
        for comp in plot_components:
            comp.render()


with gr.Blocks(
    css=APP_CSS,
    theme=gr.themes.Soft(primary_hue="red", secondary_hue="slate", neutral_hue="slate"),
    title="ReliaPy Workbench"
) as demo:
    gr.Markdown(INTRO_HTML)
    with gr.Row(equal_height=True):
        gr.Markdown("""<div class="metric-card"><div class="icon">⏳</div><h3>Life Data Analysis</h3><p>Weibull and Lognormal models using MLE or Rank Regression with probability, CDF, and likelihood-contour plots.</p></div>""")
        gr.Markdown("""<div class="metric-card"><div class="icon">↗</div><h3>Reliability Growth</h3><p>Crow-AMSAA, piecewise NHPP, and automatic change-point analysis with growth and Duane visualizations.</p></div>""")
        gr.Markdown("""<div class="metric-card"><div class="icon">🔧</div><h3>Repairable Systems</h3><p>Power Law, Log-Linear, and Piecewise NHPP models with cumulative events, event rate, and MCF outputs.</p></div>""")
        gr.Markdown("""<div class="metric-card"><div class="icon">⚡</div><h3>Accelerated Life Testing</h3><p>Weibull or Lognormal ALT with Arrhenius or Power Law stress relationships and use-condition prediction.</p></div>""")
    gr.Markdown(CSV_NOTE)

    with gr.Tabs():
        with gr.Tab("Life Data Analysis"):
            gr.Markdown("""<div class="module-intro"><h2>Life Data Analysis</h2><p>Fit Weibull or Lognormal life distributions using MLE or median-rank regression. Outputs include parameter estimates, reliability at mission time, probability plot, likelihood contour, fitted CDF, and downloadable artifacts.</p></div>""")
            with gr.Row():
                with gr.Column(scale=1, elem_classes="control-panel"):
                    gr.Markdown("### Inputs")
                    life_file = gr.File(label="Upload life-data CSV/XLSX", file_types=[".csv", ".xlsx", ".xls"])
                    with gr.Row():
                        life_dist = gr.Dropdown(["Weibull", "Lognormal"], value="Weibull", label="Distribution")
                        life_method = gr.Dropdown(["MLE", "Rank Regression"], value="MLE", label="Fitting method")
                    life_time_col = gr.Textbox(value="Auto", label="Time column name")
                    life_event_col = gr.Textbox(value="Auto", label="Event/status column name; use None if all failures")
                    life_mission = gr.Number(value=500, label="Mission time for reliability R(t)")
                    with gr.Row():
                        life_btn = gr.Button("Run analysis", variant="primary")
                        life_sample = gr.Button("Load sample table")
                with gr.Column(scale=2, elem_classes="output-panel"):
                    gr.Markdown("### Results")
                    life_out = gr.Dataframe(label="Parameter summary", wrap=True, interactive=False)
                    life_note = gr.Textbox(label="Notes", lines=3)
                    with gr.Accordion("⬇️ Download result table and plots", open=True):
                        with gr.Row():
                            life_csv = gr.File(label="⬇️ Download results CSV", elem_classes="download-card")
                        with gr.Row():
                            life_png1 = gr.File(label="⬇️ Probability plot PNG", elem_classes="download-card")
                            life_png2 = gr.File(label="⬇️ Likelihood contour PNG", elem_classes="download-card")
                            life_png3 = gr.File(label="⬇️ Fitted CDF PNG", elem_classes="download-card")
            with gr.Row():
                with gr.Column(elem_classes="plot-card"):
                    life_plot1 = gr.Plot(label="Probability plot")
                with gr.Column(elem_classes="plot-card"):
                    life_plot2 = gr.Plot(label="Likelihood contour")
                with gr.Column(elem_classes="plot-card"):
                    life_plot3 = gr.Plot(label="Fitted CDF")
            life_sample.click(sample_life_csv, outputs=life_out)
            life_btn.click(run_life_with_downloads,
                           inputs=[life_file, life_dist, life_method, life_time_col, life_event_col, life_mission],
                           outputs=[life_out, life_plot1, life_plot2, life_plot3, life_note, life_csv, life_png1, life_png2, life_png3])

        with gr.Tab("Reliability Growth"):
            gr.Markdown("""<div class="module-intro"><h2>Reliability Growth Analysis</h2><p>Model cumulative test failures using Crow-AMSAA/Power Law NHPP, manual piecewise NHPP, or automatic one-change-point detection.</p></div>""")
            with gr.Row():
                with gr.Column(scale=1, elem_classes="control-panel"):
                    gr.Markdown("### Inputs")
                    growth_file = gr.File(label="Upload reliability-growth CSV/XLSX", file_types=[".csv", ".xlsx", ".xls"])
                    growth_model = gr.Dropdown(["Crow-AMSAA", "Piecewise NHPP", "Automatic change-point"], value="Crow-AMSAA", label="Model")
                    growth_time_col = gr.Textbox(value="Auto", label="Cumulative event-time column")
                    growth_bps = gr.Textbox(value="", label="Manual breakpoints, comma-separated; used for Piecewise NHPP")
                    with gr.Row():
                        growth_btn = gr.Button("Run growth analysis", variant="primary")
                        growth_sample = gr.Button("Load sample table")
                with gr.Column(scale=2, elem_classes="output-panel"):
                    gr.Markdown("### Results")
                    growth_out = gr.Dataframe(label="Growth/NHPP summary", wrap=True, interactive=False)
                    growth_note = gr.Textbox(label="Interpretation", lines=6)
                    with gr.Accordion("⬇️ Download result table and plots", open=True):
                        with gr.Row():
                            growth_csv = gr.File(label="⬇️ Download results CSV", elem_classes="download-card")
                        with gr.Row():
                            growth_png1 = gr.File(label="⬇️ Reliability growth plot PNG", elem_classes="download-card")
                            growth_png2 = gr.File(label="⬇️ Duane plot PNG", elem_classes="download-card")
            with gr.Row():
                with gr.Column(elem_classes="plot-card"):
                    growth_plot1 = gr.Plot(label="Reliability growth plot")
                with gr.Column(elem_classes="plot-card"):
                    growth_plot2 = gr.Plot(label="Duane plot")
            growth_sample.click(sample_growth_csv, outputs=growth_out)
            growth_btn.click(run_growth_with_downloads,
                             inputs=[growth_file, growth_model, growth_time_col, growth_bps],
                             outputs=[growth_out, growth_plot1, growth_plot2, growth_note, growth_csv, growth_png1, growth_png2])

        with gr.Tab("Repairable Systems"):
            gr.Markdown("""<div class="module-intro"><h2>Repairable Systems</h2><p>Analyze recurrent repair/failure events with Power Law, Log-Linear, or Piecewise NHPP models. Includes cumulative events, event rate, Mean Cumulative Function, and downloadable exports.</p></div>""")
            with gr.Row():
                with gr.Column(scale=1, elem_classes="control-panel"):
                    gr.Markdown("### Inputs")
                    rep_file = gr.File(label="Upload repairable-system CSV/XLSX", file_types=[".csv", ".xlsx", ".xls"])
                    rep_model = gr.Dropdown(["Power Law", "Log-Linear", "Piecewise NHPP"], value="Power Law", label="Model")
                    rep_time_col = gr.Textbox(value="Auto", label="Event-time column")
                    rep_system_col = gr.Textbox(value="Auto", label="System/unit ID column; use None for one system")
                    rep_bps = gr.Textbox(value="", label="Manual breakpoints for Piecewise NHPP")
                    with gr.Row():
                        rep_btn = gr.Button("Run repairable analysis", variant="primary")
                        rep_sample = gr.Button("Load sample table")
                with gr.Column(scale=2, elem_classes="output-panel"):
                    gr.Markdown("### Results")
                    rep_out = gr.Dataframe(label="Repairable-system summary", wrap=True, interactive=False)
                    rep_note = gr.Textbox(label="Notes", lines=4)
                    with gr.Accordion("⬇️ Download result table and plots", open=True):
                        with gr.Row():
                            rep_csv = gr.File(label="⬇️ Download results CSV", elem_classes="download-card")
                        with gr.Row():
                            rep_png1 = gr.File(label="⬇️ Cumulative events PNG", elem_classes="download-card")
                            rep_png2 = gr.File(label="⬇️ Event rate PNG", elem_classes="download-card")
                            rep_png3 = gr.File(label="⬇️ MCF PNG", elem_classes="download-card")
            with gr.Row():
                with gr.Column(elem_classes="plot-card"):
                    rep_plot1 = gr.Plot(label="Cumulative events")
                with gr.Column(elem_classes="plot-card"):
                    rep_plot2 = gr.Plot(label="Event rate")
                with gr.Column(elem_classes="plot-card"):
                    rep_plot3 = gr.Plot(label="MCF")
            rep_sample.click(sample_repair_csv, outputs=rep_out)
            rep_btn.click(run_repairable_with_downloads,
                          inputs=[rep_file, rep_model, rep_time_col, rep_system_col, rep_bps],
                          outputs=[rep_out, rep_plot1, rep_plot2, rep_plot3, rep_note, rep_csv, rep_png1, rep_png2, rep_png3])

        with gr.Tab("Accelerated Life Testing"):
            gr.Markdown("""<div class="module-intro"><h2>Accelerated Life Testing</h2><p>Fit accelerated life models under Arrhenius or Power Law stress relationships with common Weibull shape or common Lognormal sigma.</p></div>""")
            with gr.Row():
                with gr.Column(scale=1, elem_classes="control-panel"):
                    gr.Markdown("### Inputs")
                    alt_file = gr.File(label="Upload ALT CSV/XLSX", file_types=[".csv", ".xlsx", ".xls"])
                    alt_dist = gr.Dropdown(["Weibull", "Lognormal"], value="Weibull", label="Life distribution")
                    alt_rel = gr.Dropdown(["Arrhenius; temperature in Celsius", "Arrhenius; temperature in Kelvin", "Power law; generic stress"],
                                          value="Arrhenius; temperature in Celsius", label="Life-stress relationship")
                    alt_time_col = gr.Textbox(value="Auto", label="Time column")
                    alt_stress_col = gr.Textbox(value="Auto", label="Stress column")
                    alt_event_col = gr.Textbox(value="Auto", label="Event/status column; use None if all failures")
                    alt_use_stress = gr.Number(value=55, label="Use stress for predicted life")
                    with gr.Row():
                        alt_btn = gr.Button("Run ALT analysis", variant="primary")
                        alt_sample = gr.Button("Load sample table")
                with gr.Column(scale=2, elem_classes="output-panel"):
                    gr.Markdown("### Results")
                    alt_out = gr.Dataframe(label="ALT summary", wrap=True, interactive=False)
                    alt_note = gr.Textbox(label="Notes", lines=4)
                    with gr.Accordion("⬇️ Download result table and plots", open=True):
                        with gr.Row():
                            alt_csv = gr.File(label="⬇️ Download results CSV", elem_classes="download-card")
                        with gr.Row():
                            alt_png1 = gr.File(label="⬇️ ALT probability plot PNG", elem_classes="download-card")
                            alt_png2 = gr.File(label="⬇️ Life-stress plot PNG", elem_classes="download-card")
            with gr.Row():
                with gr.Column(elem_classes="plot-card"):
                    alt_plot1 = gr.Plot(label="ALT probability plot")
                with gr.Column(elem_classes="plot-card"):
                    alt_plot2 = gr.Plot(label="Life-stress plot")
            alt_sample.click(sample_alt_csv, outputs=alt_out)
            alt_btn.click(run_alt_with_downloads,
                          inputs=[alt_file, alt_dist, alt_rel, alt_time_col, alt_stress_col, alt_event_col, alt_use_stress],
                          outputs=[alt_out, alt_plot1, alt_plot2, alt_note, alt_csv, alt_png1, alt_png2])

    gr.Markdown("""
    <div class="footer-note"><strong>Developer:</strong> Partha Pratim Ray, Sikkim University · July 2026 · <strong>Email:</strong> parthapratimray1986@gmail.com<br><br><strong>Publication note.</strong> For an IEEE Reliability Magazine tool paper, validate this workbench against known datasets and report numerical agreement, limitations, censoring assumptions, and reproducible Colab/GitHub availability. Downloaded PNGs are saved at 300 dpi for manuscript drafting and reports.</div>
    """)

demo.queue()
demo.launch(allowed_paths=[tempfile.gettempdir(), EXPORT_DIR])

