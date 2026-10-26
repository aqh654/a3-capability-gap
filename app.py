"""
How far behind are the AI models a Hong Kong bank can actually use?
Individual app for 36104 Assignment 3 Part 1 (view V2: capability gap over time).

Data: Epoch AI, Epoch Capabilities Index (ECI), file eci_scores.csv
https://epoch.ai/data/eci_scores.csv  (Creative Commons Attribution)
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_FILE = Path(__file__).parent / "data" / "eci_scores.csv"
DATA_DATE = "26 October 2026"  # day you downloaded eci_scores.csv: change if different

LEADER_COLOUR = "#1F3A5F"   # closed frontier
ACCESS_COLOUR = "#C8742B"   # accessible group
GREY = "#B8BEC6"

st.set_page_config(page_title="Capability gap over time", page_icon="📉", layout="centered")


# ---------- data ----------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "eci"])
    country = df["Country (of organization)"].fillna("")
    access = df["Model accessibility"].fillna("")
    df["is_china"] = country.str.contains("China")
    df["is_open"] = access.str.startswith("Open weights")
    return df.sort_values("date").reset_index(drop=True)


def running_best(df: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """For each date, the highest-ECI model released on or before that date."""
    rows = []
    for d in dates:
        released = df[df["date"] <= d]
        if released.empty:
            rows.append({"as_of": d})
            continue
        best = released.loc[released["eci"].idxmax()]
        rows.append({
            "as_of": d,
            "model": best["Model"],
            "eci": best["eci"],
            "ci_low": best["eci_ci_low"],
            "ci_high": best["eci_ci_high"],
        })
    return pd.DataFrame(rows)


df = load_data(DATA_FILE)

# ---------- header ----------
st.title("How far behind are the AI models a Hong Kong bank can actually use?")
st.markdown(
    "**Group question.** In regions where leading closed US models are restricted, which "
    "accessible AI model gives an organisation the most measured capability for its cost "
    "and data-control needs?\n\n"
    "**Persona.** A group enterprise architect at an Asia-Pacific bank, building a shortlist "
    "of approved AI models within two weeks. The leading US models are not offered in Hong Kong."
)
st.markdown(
    "This page answers one part of that question: **should the architect wait for the US "
    "models, or is the gap small enough to choose from what is available now?**"
)

# ---------- controls ----------
group = st.radio(
    "Compare the best model overall with the best model that is",
    ["China-based (usually available in Hong Kong)", "Open-weight (can be self-hosted by the bank)"],
    horizontal=False,
)
show_all = st.checkbox("Show every model in the file as grey dots", value=False)

mask = df["is_china"] if group.startswith("China") else df["is_open"]
label = "Best China-based model" if group.startswith("China") else "Best open-weight model"

months = pd.date_range(df["date"].min().normalize(), df["date"].max(), freq="MS")
months = months.append(pd.DatetimeIndex([df["date"].max()]))
lead = running_best(df, months)
acc = running_best(df[mask], months)
gap = lead[["as_of", "eci"]].merge(acc[["as_of", "eci"]], on="as_of", suffixes=("_lead", "_acc"))
gap["gap"] = gap["eci_lead"] - gap["eci_acc"]

latest_lead = lead.iloc[-1]
latest_acc = acc.iloc[-1]
current_gap = latest_lead["eci"] - latest_acc["eci"]

# ---------- headline numbers ----------
c1, c2, c3 = st.columns(3)
c1.metric("Best model overall", f"{latest_lead['eci']:.2f}", help=latest_lead["model"])
c2.metric(label, f"{latest_acc['eci']:.2f}", help=latest_acc["model"])
c3.metric("Gap today (ECI points)", f"{current_gap:.2f}")
st.caption(
    f"Best overall: **{latest_lead['model']}**. {label}: **{latest_acc['model']}**. "
    f"Gap = {latest_lead['eci']:.2f} − {latest_acc['eci']:.2f} = {current_gap:.2f}."
)

# ---------- chart ----------
fig = go.Figure()

if show_all:
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["eci"], mode="markers", name="Every model in the file",
        marker=dict(color=GREY, size=5, opacity=0.6),
        text=df["Model"], hovertemplate="%{text}<br>ECI %{y:.2f}<extra></extra>",
    ))


def add_band_and_line(frame: pd.DataFrame, colour: str, name: str) -> None:
    f = frame.dropna(subset=["eci"])
    fig.add_trace(go.Scatter(
        x=pd.concat([f["as_of"], f["as_of"][::-1]]),
        y=pd.concat([f["ci_high"], f["ci_low"][::-1]]),
        fill="toself", fillcolor=colour, opacity=0.15, line=dict(width=0, shape="hv"),
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=f["as_of"], y=f["eci"], mode="lines", name=name,
        line=dict(color=colour, width=3, shape="hv"),
        text=f["model"], hovertemplate="%{x|%b %Y}<br>%{text}<br>ECI %{y:.2f}<extra></extra>",
    ))


add_band_and_line(lead, LEADER_COLOUR, "Best model overall")
add_band_and_line(acc, ACCESS_COLOUR, label)

fig.update_layout(
    height=460, margin=dict(l=10, r=10, t=30, b=10),
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(color="#1F2933", size=14),
    legend_font=dict(color="#1F2933", size=14),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis_title="Epoch Capabilities Index (higher is better)",
    xaxis_title="Model release date",
    hovermode="closest",
)
fig.update_xaxes(showgrid=False, tickfont=dict(color="#1F2933", size=13),
                 title_font=dict(color="#1F2933", size=14), linecolor="#9AA3AD")
fig.update_yaxes(gridcolor="#E3E6EA", tickfont=dict(color="#1F2933", size=13),
                 title_font=dict(color="#1F2933", size=14))
st.plotly_chart(fig, width="stretch", theme=None)

st.markdown(
    "**How to read it.** Each line steps up when a new best model is released. The shaded band "
    "is Epoch's confidence interval for the leading model: where the two bands overlap, the "
    "two models cannot be told apart with confidence."
)

# ---------- takeaway (computed from the data, not typed in) ----------
recent = (gap[gap["as_of"] >= pd.Timestamp("2024-01-01")].dropna()
          .merge(acc[["as_of", "model"]], on="as_of"))
narrow = recent.loc[recent["gap"].idxmin()]
lead_ci_width = latest_lead["ci_high"] - latest_lead["ci_low"]
reopened = current_gap - narrow["gap"] > 4
st.markdown(
    f"**Takeaway for the architect.** Since January 2024 the gap was narrowest at "
    f"**{narrow['gap']:.1f}** ECI points in {narrow['as_of']:%B %Y}, after "
    f"{narrow['model']} was released. Today it is **{current_gap:.1f}** points. "
    + ("Accessible models catch up in bursts, then the next US release pulls ahead again. "
       if reopened else "")
    + (f"Today's gap is larger than the leading model's own confidence interval "
       f"({lead_ci_width:.1f} points), so choosing an accessible model today means accepting "
       f"about {current_gap:.0f} points less measured capability. The gap has narrowed and "
       "reopened before, so the architect should not assume it will close soon. "
       "Cost and data control should be weighed against this gap."
       if current_gap > lead_ci_width else
       f"Today's gap is within the leading model's own confidence interval "
       f"({lead_ci_width:.1f} points), so waiting for the US models is unlikely to bring a "
       "clear jump in measured capability. Cost and data control should decide the shortlist.")
)

with st.expander("Gap by month (table)"):
    table = gap.copy()
    table["as_of"] = table["as_of"].dt.strftime("%Y-%m")
    table = table.rename(columns={"as_of": "Month", "eci_lead": "Best overall",
                                  "eci_acc": label, "gap": "Gap"})
    st.dataframe(table.round(2), hide_index=True, width="stretch")

# ---------- design decision, verification, AI use ----------
with st.expander("Design decision: why a step line with a confidence band"):
    st.markdown(
        "**Visual task.** Show *change over time* in the gap between two groups, and how "
        "uncertain that gap is (FT Visual Vocabulary: change over time).\n\n"
        "**Form chosen.** Two step lines of the best model so far, each with Epoch's "
        "confidence band. A step line is honest here: the best score only changes on the day "
        "a better model is released, so a smooth line would invent values between releases.\n\n"
        "**Alternative rejected: a bar chart of the monthly gap.** It shows the gap size, but "
        "it hides the uncertainty, so a 9-point gap would look certain even when the two "
        "models' confidence intervals overlap. The architect needs to see that overlap to "
        "decide whether waiting is worth it.\n\n"
        "**Also rejected as the default: a scatter of every model.** With hundreds of dots the "
        "two lines that answer the question get lost. It stays available as the grey-dots option."
    )

with st.expander("Check the gap yourself in the source file"):
    st.markdown(
        f"1. Open `data/eci_scores.csv` (the file downloaded from Epoch AI).\n"
        f"2. Sort by `eci`, largest first. The top row is **{latest_lead['model']}** with "
        f"**{latest_lead['eci']:.2f}**.\n"
        + ("3. Filter `Country (of organization)` to China. "
           if group.startswith("China") else
           "3. Filter `Model accessibility` to values starting with “Open weights”. ")
        + f"The top row is **{latest_acc['model']}** with **{latest_acc['eci']:.2f}**.\n"
        f"4. {latest_lead['eci']:.2f} − {latest_acc['eci']:.2f} = **{current_gap:.2f}**, "
        "the gap shown at the top of this page."
    )

with st.expander("AI use on this page"):
    st.markdown(
        "I used Claude (Anthropic) to draft the Python code for this page and to help word "
        "the explanations. **Checks I applied:** I traced the headline gap back to "
        "`eci_scores.csv` by hand (steps above) and confirmed it matches; I checked that the top "
        "China-based model is the same one our group's notebook `Data/01_epoch_eci_scores` "
        "found (Kimi K3; the scores differ slightly because Epoch re-estimates ECI when it "
        "adds models); and I read the code that marks China-based and "
        "open-weight models to make sure it uses Epoch's own columns."
    )

# ---------- source ----------
st.divider()
st.caption(
    "**Source.** Epoch AI, Epoch Capabilities Index, file `eci_scores.csv` "
    f"(https://epoch.ai/data/eci_scores.csv), downloaded {DATA_DATE}, "
    f"{len(df)} models. Licence: Creative Commons Attribution, credit Epoch AI.  \n"
    "**What I did to it.** Kept rows with a date and ECI score; marked China-based models "
    "where `Country (of organization)` contains “China”, and open-weight models where "
    "`Model accessibility` starts with “Open weights”; for each month, took the highest `eci` "
    "among models released on or before that month.  \n"
    "**Limits.** ECI covers the models Epoch evaluated, not every model on the market. "
    "Country is the developer’s country, not where the model runs. This page gives no legal advice."
)
