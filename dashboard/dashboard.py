import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard Kualitas Udara Beijing", page_icon="🌫️", layout="wide")

BASE = os.path.dirname(os.path.abspath(__file__))
BAKU_MUTU = 75  # µg/m3, rata-rata 24 jam (GB 3095-2012 Kelas II)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
WD_ORDER = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
COORDS = {  # koordinat perkiraan (lat, lon); tidak tersedia di dataset asli
    "Aotizhongxin": (39.982, 116.397), "Changping": (40.217, 116.230), "Dingling": (40.292, 116.220),
    "Dongsi": (39.929, 116.417), "Guanyuan": (39.929, 116.339), "Gucheng": (39.914, 116.184),
    "Huairou": (40.328, 116.628), "Nongzhanguan": (39.937, 116.461), "Shunyi": (40.127, 116.655),
    "Tiantan": (39.886, 116.407), "Wanliu": (39.987, 116.287), "Wanshouxigong": (39.878, 116.352),
}
CAT_BINS = [0, 35, 75, 115, 150, 250, np.inf]
CAT_LABELS = ["Baik", "Sedang", "Tidak sehat (sensitif)", "Tidak sehat", "Sangat tidak sehat", "Berbahaya"]
CAT_COLORS = ["#2a9d8f", "#e9c46a", "#f4a261", "#e76f51", "#9d0208", "#370617"]


@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(BASE, "main_data.csv"), parse_dates=["datetime"])
    df["date"] = df["datetime"].dt.normalize()
    df["month"] = df["datetime"].dt.month
    df["hour"] = df["datetime"].dt.hour
    return df


df = load_data()

# ---------------- Sidebar ----------------
st.sidebar.title("🌫️ Filter")
all_stations = sorted(df["station"].unique())
stations = st.sidebar.multiselect("Stasiun", all_stations, default=all_stations)
min_d, max_d = df["date"].min().date(), df["date"].max().date()
date_range = st.sidebar.date_input("Rentang tanggal", (min_d, max_d), min_value=min_d, max_value=max_d)
st.sidebar.caption("Sumber: Beijing Multi-Site Air Quality (Mar 2013 – Feb 2017). Baku mutu acuan PM2.5: 75 µg/m³ (rata-rata 24 jam).")

if not stations:
    st.warning("Pilih minimal satu stasiun.")
    st.stop()
if not (isinstance(date_range, tuple) and len(date_range) == 2):
    st.info("Pilih tanggal akhir pada rentang tanggal.")
    st.stop()

start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
f = df[df["station"].isin(stations) & (df["date"] >= start) & (df["date"] <= end)]
if f["PM2.5"].dropna().empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

daily = f.groupby(["station", "date"], as_index=False)["PM2.5"].mean().dropna()
daily["lewat"] = daily["PM2.5"] > BAKU_MUTU

# ---------------- Header & KPI ----------------
st.title("Dashboard Kualitas Udara Beijing (PM2.5)")
st.caption("Menjawab 3 pertanyaan bisnis: pola waktu, perbandingan stasiun, dan pengaruh cuaca.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rata-rata PM2.5", f"{f['PM2.5'].mean():.1f} µg/m³")
c2.metric("% Hari > 75 µg/m³", f"{daily['lewat'].mean() * 100:.1f}%")
c3.metric("PM2.5 maksimum (per jam)", f"{f['PM2.5'].max():.0f} µg/m³")
c4.metric("Jumlah stasiun", len(stations))

tab1, tab2, tab3, tab4 = st.tabs(["⏱️ Pola Waktu (P1)", "📍 Stasiun & Tren (P2)", "🌬️ Cuaca (P3)", "🗺️ Peta & Kategori"])

# ---------------- Tab 1 ----------------
with tab1:
    st.subheader("Kapan PM2.5 paling tinggi dan berapa % hari melampaui baku mutu?")
    monthly = f.groupby("month", as_index=False)["PM2.5"].mean()
    monthly["bulan"] = monthly["month"].map(lambda m: MONTHS[m - 1])
    monthly["puncak"] = np.where(monthly["PM2.5"] == monthly["PM2.5"].max(), "Tertinggi", "Lainnya")
    a, b = st.columns(2)
    fig = px.bar(monthly, x="bulan", y="PM2.5", color="puncak", category_orders={"bulan": MONTHS},
                 color_discrete_map={"Tertinggi": "#d62828", "Lainnya": "#8ecae6"},
                 labels={"PM2.5": "PM2.5 (µg/m³)", "bulan": "Bulan"}, title="Rata-rata PM2.5 per Bulan")
    fig.add_hline(y=BAKU_MUTU, line_dash="dash", annotation_text="Baku mutu 75")
    fig.update_layout(showlegend=False)
    a.plotly_chart(fig, width="stretch")

    hourly = f.groupby("hour", as_index=False)["PM2.5"].mean()
    fig = px.line(hourly, x="hour", y="PM2.5", markers=True, labels={"hour": "Jam", "PM2.5": "PM2.5 (µg/m³)"},
                  title="Rata-rata PM2.5 per Jam")
    b.plotly_chart(fig, width="stretch")

    heat = f.pivot_table(index="month", columns="hour", values="PM2.5", aggfunc="mean")
    heat.index = [MONTHS[m - 1] for m in heat.index]
    fig = px.imshow(heat, color_continuous_scale="YlOrRd", aspect="auto",
                    labels=dict(x="Jam", y="Bulan", color="µg/m³"), title="Heatmap Bulan × Jam")
    st.plotly_chart(fig, width="stretch")

    def season(m):
        return ("Dingin (Des-Feb)" if m in (12, 1, 2) else "Semi (Mar-Mei)" if m in (3, 4, 5)
                else "Panas (Jun-Agu)" if m in (6, 7, 8) else "Gugur (Sep-Nov)")
    daily["musim"] = daily["date"].dt.month.map(season)
    sea = daily.groupby("musim", as_index=False).agg(pct=("lewat", "mean"), rata2=("PM2.5", "mean"))
    sea["pct"] = sea["pct"] * 100
    sea = sea.sort_values("pct", ascending=False)
    fig = px.bar(sea, x="pct", y="musim", orientation="h", text=sea["pct"].round(1).astype(str) + "%",
                 labels={"pct": "% hari melampaui 75 µg/m³", "musim": ""}, title="% Hari Melampaui Baku Mutu per Musim",
                 color_discrete_sequence=["#e76f51"])
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")
    st.info("**Kesimpulan:** PM2.5 tertinggi pada Desember dan musim dingin (≈45% hari melampaui 75 µg/m³ pada seluruh data). "
            "Variasi antar bulan jauh lebih besar daripada variasi antar jam.")

# ---------------- Tab 2 ----------------
with tab2:
    st.subheader("Stasiun mana yang paling berpolusi dan bagaimana tren antar periode?")
    st_stat = daily.groupby("station", as_index=False).agg(rata2=("PM2.5", "mean"), pct=("lewat", "mean"))
    st_stat["pct"] = st_stat["pct"] * 100
    st_stat = st_stat.sort_values("rata2")
    fig = px.bar(st_stat, x="rata2", y="station", orientation="h", color="rata2", color_continuous_scale="YlOrRd",
                 text=[f"{r:.1f} ({p:.0f}% hari > 75)" for r, p in zip(st_stat["rata2"], st_stat["pct"])],
                 labels={"rata2": "Rata-rata PM2.5 (µg/m³)", "station": ""}, title="Rata-rata PM2.5 per Stasiun")
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")

    daily["periode_start"] = np.where(daily["date"].dt.month >= 3, daily["date"].dt.year, daily["date"].dt.year - 1)
    daily["periode"] = daily["periode_start"].astype(str) + "/" + (daily["periode_start"] + 1).astype(str).str[-2:]
    per = daily.groupby(["periode", "station"], as_index=False)["PM2.5"].mean()
    per_all = daily.groupby("periode", as_index=False)["PM2.5"].mean()
    fig = px.line(per, x="periode", y="PM2.5", color="station", labels={"PM2.5": "PM2.5 (µg/m³)", "periode": "Periode (Mar–Feb)"},
                  title="Tren PM2.5 per Periode (periode parsial muncul jika rentang tanggal dipersempit)")
    fig.update_traces(opacity=0.35, line=dict(width=1))
    fig.add_scatter(x=per_all["periode"], y=per_all["PM2.5"], mode="lines+markers+text", name="Rata-rata terpilih",
                    text=per_all["PM2.5"].round(1), textposition="top center", line=dict(color="#d62828", width=4))
    st.plotly_chart(fig, width="stretch")
    st.info("**Kesimpulan:** Dongsi tertinggi (≈86 µg/m³) dan Dingling terendah (≈67 µg/m³) pada seluruh data. "
            "Rata-rata 12 stasiun turun 10,3% dari 2013/14 ke 2016/17, namun naik 7,1% pada 2016/17.")

# ---------------- Tab 3 ----------------
with tab3:
    st.subheader("Seberapa kuat pengaruh cuaca dan arah angin mana yang paling berpolusi?")
    met = ["WSPM", "TEMP", "PRES", "DEWP", "RAIN"]
    names = {"WSPM": "Kecepatan angin", "TEMP": "Suhu", "PRES": "Tekanan", "DEWP": "Titik embun", "RAIN": "Curah hujan"}
    sample = f[["PM2.5"] + met].dropna()
    if len(sample) > 150_000:
        sample = sample.sample(150_000, random_state=42)
    corr = sample.corr(method="spearman")["PM2.5"].drop("PM2.5").rename(index=names).sort_values().reset_index()
    corr.columns = ["variabel", "korelasi"]
    a, b = st.columns(2)
    fig = px.bar(corr, x="korelasi", y="variabel", orientation="h", text=corr["korelasi"].round(2),
                 color=corr["korelasi"] > 0, color_discrete_map={True: "#e76f51", False: "#2a9d8f"},
                 range_x=[-0.5, 0.5], title="Korelasi Spearman dengan PM2.5")
    fig.update_layout(showlegend=False)
    a.plotly_chart(fig, width="stretch")

    w = f.copy()
    w["kelas_angin"] = pd.cut(w["WSPM"], bins=[-0.01, 0.5, 1, 2, 3, 20],
                              labels=["Tenang (≤0.5)", "Lemah (0.5-1)", "Sedang (1-2)", "Cukup kuat (2-3)", "Kuat (>3)"])
    ws = w.groupby("kelas_angin", observed=True, as_index=False)["PM2.5"].mean()
    fig = px.bar(ws, x="kelas_angin", y="PM2.5", text=ws["PM2.5"].round(0), color_discrete_sequence=["#8ecae6"],
                 labels={"kelas_angin": "Kecepatan angin (m/s)", "PM2.5": "PM2.5 (µg/m³)"}, title="PM2.5 per Kelas Kecepatan Angin")
    b.plotly_chart(fig, width="stretch")

    wd = f.dropna(subset=["wd"]).groupby("wd", as_index=False)["PM2.5"].mean()
    fig = px.bar_polar(wd, r="PM2.5", theta="wd", color="PM2.5", color_continuous_scale="YlOrRd",
                       category_orders={"wd": WD_ORDER}, title="Rata-rata PM2.5 per Arah Angin (asal angin)")
    fig.update_polars(angularaxis=dict(direction="clockwise", rotation=90))
    st.plotly_chart(fig, width="stretch")
    st.info("**Kesimpulan:** Kecepatan angin adalah faktor terkuat (Spearman ≈ −0,33). Angin dari timur–tenggara membawa PM2.5 tertinggi, "
            "angin barat laut paling bersih. Korelasi ini tidak membuktikan hubungan sebab-akibat.")

# ---------------- Tab 4 ----------------
with tab4:
    st.subheader("Analisis lanjutan: geospasial & pengelompokan kategori")
    geo = f.groupby("station", as_index=False)["PM2.5"].mean()
    geo["lat"] = geo["station"].map(lambda s: COORDS[s][0])
    geo["lon"] = geo["station"].map(lambda s: COORDS[s][1])
    geo["ukuran"] = (geo["PM2.5"] - geo["PM2.5"].min() + 5)
    fig = px.scatter_map(geo, lat="lat", lon="lon", size="ukuran", color="PM2.5", hover_name="station",
                         hover_data={"PM2.5": ":.1f", "lat": False, "lon": False, "ukuran": False},
                         color_continuous_scale="YlOrRd", zoom=8.5, size_max=28, map_style="carto-positron",
                         title="Rata-rata PM2.5 per Stasiun (koordinat perkiraan)")
    st.plotly_chart(fig, width="stretch")

    cat = f.dropna(subset=["PM2.5"]).copy()
    cat["kategori"] = pd.cut(cat["PM2.5"], bins=CAT_BINS, labels=CAT_LABELS, include_lowest=True)
    ct = cat.groupby("station")["kategori"].value_counts(normalize=True).unstack().mul(100).reindex(columns=CAT_LABELS)
    ct = ct.sort_values("Baik").reset_index().melt(id_vars="station", var_name="kategori", value_name="persen")
    fig = px.bar(ct, x="persen", y="station", color="kategori", orientation="h",
                 color_discrete_sequence=CAT_COLORS, category_orders={"kategori": CAT_LABELS},
                 labels={"persen": "% jam", "station": ""}, title="Sebaran Kategori PM2.5 per Stasiun")
    st.plotly_chart(fig, width="stretch")
    st.caption("Kategori mengacu pada breakpoint AQI China (HJ 633-2012) yang diterapkan pada data per jam (aproksimasi). "
               "Koordinat stasiun ditambahkan manual dan hanya perkiraan.")

st.markdown("---")
with st.expander("💡 Rekomendasi action item"):
    st.markdown("""
1. Fokuskan pembatasan emisi pada **Oktober–Maret**, terutama Desember.
2. Prioritaskan intervensi di pusat kota (**Dongsi, Nongzhanguan, Wanshouxigong, Gucheng**).
3. Buat peringatan dini saat prakiraan **angin ≤ 1 m/s** dan/atau angin dari sektor **E–SE**.
4. Selidiki kenaikan PM2.5 periode 2016/17 dan replikasi praktik Wanliu (penurunan terbesar).
""")
