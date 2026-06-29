import pandas as pd, numpy as np
np.random.seed(55)
cities=['Delhi','Mumbai','Chennai','Kolkata','Bangalore',
        'Hyderabad','Pune','Ahmedabad','Lucknow','Jaipur']
n = 720
rng = np.random.default_rng(55)
PM25 = np.random.uniform(10, 500, n).round(1).astype(object)
PM10 = np.random.uniform(20, 600, n).round(1).astype(object)
CO   = np.random.uniform(0.1, 10, n).round(2).astype(object)
city = list(np.random.choice(cities, n))
ts   = list(pd.date_range('2024-01-01', periods=n, freq='h'))
# --- NOISE INJECTION (do NOT modify) --
idx = rng.choice(n, size=60, replace=False)
for i in idx[:12]:  PM25[i]  = np.nan
for i in idx[12:22]: PM10[i] = str(PM10[i]) + ' \u00b5g/m\u00b3'  # µg/m³ suffix
for i in idx[22:32]: CO[i]   = -9999                          # sensor fault
for i in idx[32:42]: city[i] = str(city[i]).lower()           # lowercase
for i in idx[42:52]: PM25[i] = np.nan                         # extra missing
for i in idx[52:57]: ts[i]   = pd.NaT                         # missing time
for i in idx[57:60]: PM25[i] = 9999                           # sensor spike
df = pd.DataFrame({'timestamp':ts,'city':city,'PM25':PM25,'PM10':PM10,
    'NO2':np.random.uniform(5,200,n).round(1),
    'SO2':np.random.choice([np.nan]+list(np.random.uniform(2,80,100).round(1)),n),
    'CO':CO,'O3':np.random.uniform(10,180,n).round(1)})
# ─── YOUR ETL CODE STARTS HERE ──────────────────────────────────

# ===================== TASK 1 : ETL =====================

# 1. Drop rows with NaT timestamps
def task1():
    global df
    df = df.dropna(subset=["timestamp"]).copy()

# 2. Clean PM10 (remove µg/m³ and convert to foat)
    df["PM10"] = (
        df["PM10"]
        .astype(str)
        .str.replace(" µg/m³", "", regex=False)
        .astype(float)
    )

# 3. Convert PM25 to numeric
    df["PM25"] = pd.to_numeric(df["PM25"], errors="coerce")

    # 4. Replace CO sensor error (-9999) with NaN
    df["CO"] = pd.to_numeric(df["CO"], errors="coerce")
    df["CO"] = df["CO"].replace(-9999, np.nan)

    # 5. Normalize city names
    df["city"] = df["city"].str.title()

    # 6. Cap PM25 sensor spikes (9999) to 99th percentile
    valid_pm25 = df.loc[df["PM25"] != 9999, "PM25"]
    cap_value = valid_pm25.quantile(0.99)

    df.loc[df["PM25"] == 9999, "PM25"] = cap_value

    # --------------------------------------------------------
    # Fill Missing Values
    # --------------------------------------------------------

    # PM25 -> city-wise mean
    df["PM25"] = df.groupby("city")["PM25"].transform(
        lambda x: x.fillna(x.mean())
    )

    # CO -> city-wise median
    df["CO"] = df.groupby("city")["CO"].transform(
        lambda x: x.fillna(x.median())
    )

    # SO2 -> city-wise median
    df["SO2"] = df.groupby("city")["SO2"].transform(
        lambda x: x.fillna(x.median())
    )

    # NO2 -> city-wise median
    df["NO2"] = pd.to_numeric(df["NO2"], errors="coerce")

    df["NO2"] = df.groupby("city")["NO2"].transform(
        lambda x: x.fillna(x.median())
    )

    # --------------------------------------------------------
    # AQI Calculation
    # --------------------------------------------------------

    df["AQI"] = np.maximum.reduce([
        df["PM25"],
        df["PM10"],
        df["NO2"] / 2,
        df["SO2"],
        df["CO"] * 10,
        df["O3"] / 2
    ])

    # --------------------------------------------------------
    # AQI Category
    # --------------------------------------------------------

    def aqi_category(aqi):
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Satisfactory"
        elif aqi <= 200:
            return "Moderate"
        elif aqi <= 300:
            return "Poor"
        elif aqi <= 400:
            return "Very Poor"
        else:
            return "Severe"

    df["AQI_Category"] = df["AQI"].apply(aqi_category)

    # --------------------------------------------------------
    # Rush Hour Flag
    # --------------------------------------------------------

    df["hour"] = df["timestamp"].dt.hour

    df["Rush_Hour"] = df["hour"].isin([7, 8, 9, 17, 18, 19])

    # --------------------------------------------------------
    # Daily AQI
    # --------------------------------------------------------

    daily_aqi = (
        df.groupby([
            df["timestamp"].dt.date,
            "city"
        ])
        .agg(
            Avg_AQI=("AQI", "mean"),
            Max_AQI=("AQI", "max"),
            Avg_PM25=("PM25", "mean"),
            Avg_PM10=("PM10", "mean")
        )
        .reset_index()
    )

    daily_aqi.rename(columns={"timestamp": "Date"}, inplace=True)

    daily_aqi.to_csv("daily_aqi.csv", index=False)
    
    
    print("\nDaily AQI File Saved Successfully!")
    return df


# ===================== TASK 2 =====================
# Pollution Alert System (Stack + Priority Queue)

# ---------------- Stack ----------------
def task2(df):
    class Stack:
        def __init__(self):
            self.items = []

        def push(self, item):
            self.items.append(item)

        def pop(self):
            if not self.is_empty():
                return self.items.pop()
            return None

        def peek(self):
            if not self.is_empty():
                return self.items[-1]
            return None

        def is_empty(self):
            return len(self.items) == 0


    # ---------------- Priority Queue ----------------
    class PriorityQueue:
        def __init__(self):
            self.items = []

        def enqueue(self, item, priority):
            self.items.append((priority, item))
            self.items.sort(key=lambda x: x[0], reverse=True)

        def dequeue(self):
            if self.items:
                return self.items.pop(0)
            return None

        def is_empty(self):
            return len(self.items) == 0


    # -------------------------------------------------
    # Create Stack
    # -------------------------------------------------

    alert_stack = Stack()

    # Push alerts where AQI > 200
    for _, row in df.iterrows():
        if row["AQI"] > 200:
            alert = {
                "city": row["city"],
                "timestamp": row["timestamp"],
                "AQI": round(row["AQI"], 2)
            }
            alert_stack.push(alert)

    print("Total Alerts Stored in Stack:", len(alert_stack.items))


    # -------------------------------------------------
    # Transfer Alerts to Priority Queue
    # -------------------------------------------------

    priority_queue = PriorityQueue()

    while not alert_stack.is_empty():
        alert = alert_stack.pop()
        priority_queue.enqueue(alert, alert["AQI"])

    print("Alerts Transferred to Priority Queue:", len(priority_queue.items))


    # -------------------------------------------------
    # Top 10 Critical Alerts
    # -------------------------------------------------

    print("\n========== TOP 10 MOST CRITICAL ALERTS ==========\n")

    count = 1
    top_alerts = []

    while (not priority_queue.is_empty()) and count <= 10:

        priority, alert = priority_queue.dequeue()
        top_alerts.append({
            "City": alert["city"],
            "Timestamp": alert["timestamp"],
            "AQI": priority
        })

        print(f"{count}. City      : {alert['city']}")
        print(f"   Time      : {alert['timestamp']}")
        print(f"   AQI       : {priority:.2f}")
        print("-------------------------------------")

        count += 1

    alerts_df = pd.DataFrame(top_alerts)
    

    print("\n========== 3-HOUR CRITICAL WINDOWS ==========\n")

    critical_cities = []

    for city in df["city"].unique():

        city_df = df[df["city"] == city].sort_values("timestamp")

        window_stack = Stack()

        found = False

        for _, row in city_df.iterrows():

            if row["AQI"] > 200:
                window_stack.push(row)

                if len(window_stack.items) == 3:

                    print(f"{city} has a 3-hour critical pollution window.")

                    start = window_stack.items[0]["timestamp"]
                    end = window_stack.items[2]["timestamp"]

                    print("From :", start)
                    print("To   :", end)
                    print("-----------------------------------")

                    critical_cities.append(city)

                    found = True
                    break

            else:
                window_stack = Stack()

        if not found:
            continue


    print("\nCities with Critical Windows:")
    print(list(set(critical_cities)))
    critical_df = pd.DataFrame({
    "City": list(set(critical_cities))
        })

    return alerts_df, critical_df


# ===================== TASK 3 =====================
# Climate Dashboard (Matplotlib)
def task3(df):
    import matplotlib.pyplot as plt

    plt.style.use("seaborn-v0_8-whitegrid")

    fig = plt.figure(figsize=(20, 14))

    # ==========================================================
    # Panel 1 : 24-Hour Average AQI (Time Series)
    # ==========================================================

    ax1 = plt.subplot(2, 2, 1)

    df["date"] = df["timestamp"].dt.date

    daily_city = (
        df.groupby(["date", "city"])["AQI"]
        .mean()
        .reset_index()
    )

    for city in daily_city["city"].unique():
        temp = daily_city[daily_city["city"] == city]
        ax1.plot(temp["date"], temp["AQI"], label=city)

    ax1.axhspan(200, df["AQI"].max(), color="red", alpha=0.2)

    ax1.set_title("24-Hour Average AQI")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("AQI")
    ax1.legend(fontsize=7)

    # ==========================================================
    # Panel 2 : Heatmap
    # ==========================================================

    ax2 = plt.subplot(2, 2, 2)

    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.day_name()

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    heatmap = (
        df.pivot_table(
            values="AQI",
            index="hour",
            columns="day",
            aggfunc="mean"
        )
    )

    heatmap = heatmap.reindex(columns=days)

    img = ax2.imshow(
        heatmap,
        aspect="auto",
        origin="lower"
    )

    ax2.set_title("Average AQI Heatmap")
    ax2.set_xlabel("Day of Week")
    ax2.set_ylabel("Hour")

    ax2.set_xticks(range(len(days)))
    ax2.set_xticklabels(days, rotation=45)

    ax2.set_yticks(range(24))
    ax2.set_yticklabels(range(24))

    plt.colorbar(img, ax=ax2)

    # ==========================================================
    # Panel 3 : Grouped Bar Chart
    # ==========================================================

    ax3 = plt.subplot(2, 2, 3)

    pollutants = ["PM25", "PM10", "NO2", "SO2", "CO", "O3"]

    group = (
        df.groupby("AQI_Category")[pollutants]
        .mean()
    )

    group["CO"] = group["CO"] * 10

    normalized = (
        group - group.min()
    ) / (
        group.max() - group.min()
    )

    normalized.plot(
        kind="bar",
        ax=ax3
    )

    ax3.set_title("Normalized Pollutants by AQI Category")
    ax3.set_ylabel("Normalized Value")
    ax3.legend(fontsize=8)

    # ==========================================================
    # Panel 4 : Pie Charts (2 x 5 Grid)
    # ==========================================================

    cities = sorted(df["city"].unique())

    fig2, axes = plt.subplots(2, 5, figsize=(18, 8))

    for i, city in enumerate(cities):

        r = i // 5
        c = i % 5

        counts = (
            df[df["city"] == city]["AQI_Category"]
            .value_counts()
        )

        axes[r, c].pie(
            counts,
            labels=counts.index,
            autopct="%1.1f%%",
            textprops={"fontsize":7}
        )

        axes[r, c].set_title(city)

    fig2.suptitle("AQI Category Distribution by City")

    plt.tight_layout()

    fig.savefig(
        "climate_dashboard.png",
        dpi=200,
        bbox_inches="tight"
    )

    fig2.savefig(
        "city_piecharts.png",
        dpi=200,
        bbox_inches="tight"
    )

    plt.show()

    print("Climate Dashboard Saved Successfully!")
    return fig

# ===================== TASK 4 =====================
# AQI Risk Map (Folium)
def task4(df):
    import folium
    import numpy as np
    from folium.plugins import HeatMap
    #from Python.display import display

    # ------------------------------------------------
    # City Coordinates
    # -------------------------------------------------

    CITY_COORDS = {
        'Delhi': [28.6139, 77.2090],
        'Mumbai': [19.0760, 72.8777],
        'Chennai': [13.0827, 80.2707],
        'Kolkata': [22.5726, 88.3639],
        'Bangalore': [12.9716, 77.5946],
        'Hyderabad': [17.3850, 78.4867],
        'Pune': [18.5204, 73.8567],
        'Ahmedabad': [23.0225, 72.5714],
        'Lucknow': [26.8467, 80.9462],
        'Jaipur': [26.9124, 75.7873]
    }

    # -------------------------------------------------
    # Create Map
    # -------------------------------------------------

    aqi_map = folium.Map(
        location=[20.5937, 78.9629],
        zoom_start=5,
        tiles="CartoDB dark_matter"
    )

    # -------------------------------------------------
    # Feature Groups
    # -------------------------------------------------

    good_fg = folium.FeatureGroup(name="Good")
    sat_fg = folium.FeatureGroup(name="Satisfactory")
    mod_fg = folium.FeatureGroup(name="Moderate")
    poor_fg = folium.FeatureGroup(name="Poor")
    vp_fg = folium.FeatureGroup(name="Very Poor")
    sev_fg = folium.FeatureGroup(name="Severe")

    # -------------------------------------------------
    # Average AQI Per City
    # -------------------------------------------------

    city_summary = (
        df.groupby("city")
        .agg({
            "AQI": "mean",
            "PM25": "mean",
            "PM10": "mean",
            "NO2": "mean",
            "SO2": "mean",
            "CO": "mean",
            "O3": "mean"
        })
    )
  

    # -------------------------------------------------
    # Prepare HeatMap Data
    # -------------------------------------------------

    heat_data = []

    for _, row in df.iterrows():

        city = row["city"]

        if city in CITY_COORDS:

            lat, lon = CITY_COORDS[city]

            lat += np.random.uniform(-0.05, 0.05)
            lon += np.random.uniform(-0.05, 0.05)

            heat_data.append([
                lat,
                lon,
                row["AQI"]
            ])
    # -------------------------------------------------
    # Add Circle Markers
    # -------------------------------------------------
    q1 = city_summary["AQI"].quantile(0.2)
    q2 = city_summary["AQI"].quantile(0.4)
    q3 = city_summary["AQI"].quantile(0.6)
    q4 = city_summary["AQI"].quantile(0.8)

    for city in city_summary.index:

        avg_aqi = city_summary.loc[city, "AQI"]

        pollutants = {
            "PM25": city_summary.loc[city, "PM25"],
            "PM10": city_summary.loc[city, "PM10"],
            "NO2": city_summary.loc[city, "NO2"] / 2,
            "SO2": city_summary.loc[city, "SO2"],
            "CO ×10": city_summary.loc[city, "CO"] * 10,
            "O3 /2": city_summary.loc[city, "O3"] / 2
        }

        worst_pollutant = max(pollutants, key=pollutants.get)

        rush = df[
            (df["city"] == city) &
            (df["Rush_Hour"] == True)
        ]["AQI"].mean()

        off = df[
            (df["city"] == city) &
            (df["Rush_Hour"] == False)
        ]["AQI"].mean()

        delta = rush - off

        # AQI Category and Marker Color
        if avg_aqi < 50:
            color = "green"
            category = "Good"
            group = good_fg

        elif avg_aqi < 100:
            color = "yellow"
            category = "Satisfactory"
            group = sat_fg

        elif avg_aqi < 200:
            color = "orange"
            category = "Moderate"
            group = mod_fg

        elif avg_aqi < 300:
            color = "red"
            category = "Poor"
            group = poor_fg

        elif avg_aqi < 400:
            color = "darkred"
            category = "Very Poor"
            group = vp_fg

        else:
            color = "maroon"
            category = "Severe"
            group = sev_fg



        popup = folium.Popup(
            f"""
            <b>City:</b> {city}<br>
            <b>Average AQI:</b> {avg_aqi:.2f}<br>
            <b>AQI Category:</b> {category}<br>
            <b>Worst Pollutant:</b> {worst_pollutant}<br>
            <b>Rush Hour AQI:</b> {rush:.2f}<br>
            <b>Off-Peak AQI:</b> {off:.2f}<br>
            <b>Difference:</b> {delta:.2f}
            """,
            max_width=300
        )

        folium.CircleMarker(
            location=CITY_COORDS[city],
            radius=max(8, avg_aqi / 10),   # Required by hackathon
            color="white",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=popup,
            tooltip=city
        ).add_to(group)
    # -------------------------------------------------
    # Add Feature Groups to Map
    # -------------------------------------------------

    good_fg.add_to(aqi_map)
    sat_fg.add_to(aqi_map)
    mod_fg.add_to(aqi_map)
    poor_fg.add_to(aqi_map)
    vp_fg.add_to(aqi_map)
    sev_fg.add_to(aqi_map)

    # -------------------------------------------------
    # Add HeatMap Layer
    # -------------------------------------------------

    HeatMap(
        heat_data,
        radius=10,
        blur=8,
        min_opacity=0.3,
        max_zoom=8,
        name="AQI HeatMap"
    ).add_to(aqi_map)

    # -------------------------------------------------
    # Layer Control
    # -------------------------------------------------

    folium.LayerControl(collapsed=False).add_to(aqi_map)

    # -------------------------------------------------
    # Fit Map to All Cities
    # -------------------------------------------------

    locations = list(CITY_COORDS.values())
    aqi_map.fit_bounds(locations)

    # -------------------------------------------------
    # Save Map
    # -------------------------------------------------

    aqi_map.save("aqi_risk_map.html")

    
    print("=" * 50)
    print("Cities Plotted      :", len(city_summary))
    print("HeatMap Points      :", len(heat_data))
    print("Output File         : aqi_risk_map.html")
    print("=" * 50)

    # -------------------------------------------------
    # Display in Google Colab
    # -------------------------------------------------
    

    

    print("AQI Risk Map Saved Successfully!")

    return aqi_map



    # Uncomment this if you want to download the HTML file
    # from google.colab import files
    # files.download("aqi_risk_map.html")
    return aqi_map

