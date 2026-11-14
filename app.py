# ==============================================================
# HOW'S EARTH?  -  Hey Earth, let's check your temperature!
# NASA Space Apps Challenge 2026 - "Be An Earth System Trend Detective!"
#
# What this app does:
#   1. Asks NASA's POWER service for monthly temperature (T2M)
#      at a city's latitude and longitude.
#   2. Turns the 12 monthly values of each year into one yearly average.
#   3. Draws a graph and fits a straight "trend line" through the years.
#   4. Explains the result in plain English.
#
# Run it with:   streamlit run app.py
# ==============================================================

import streamlit as st                  # builds the website
import requests                         # talks to NASA's web service
import pandas as pd                     # holds data in tables
import matplotlib.pyplot as plt         # draws graphs
from scipy.stats import linregress      # finds the straight-line trend


# --------------------------------------------------------------
# PAGE SETUP
# --------------------------------------------------------------
st.set_page_config(page_title="HOW'S EARTH?", page_icon="🌍")

# Colours used in the graphs (hex colour codes)
CREAM = "#FFF8E7"
BLUE = "#2A7FBA"
GREEN = "#3E8E5A"
ORANGE = "#E07A3F"

# A little bit of CSS (the language that styles web pages)
# so the page is cream, with green headings and blue buttons.
st.markdown(
    """
    <style>
    .stApp { background-color: #FFF8E7; }
    .stApp h1, .stApp h2, .stApp h3 { color: #2E6F57; }
    .stApp p, .stApp li, .stApp label { color: #2B3A33; }
    .stButton > button {
        background-color: #2A7FBA;
        color: white;
        border-radius: 12px;
        border: none;
        padding: 0.6em 1.2em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------
# SETTINGS AND CITY INFORMATION
# --------------------------------------------------------------
API_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
FIRST_YEAR = 2001
LAST_YEAR = 2025
MISSING_VALUE = -999     # NASA POWER uses -999 when a value is missing

# A dictionary stores pairs:  name -> value
# Example: city_latitude["Delhi, India"] gives 28.6139
city_latitude = {
    "Kochi, India": 9.9312,
    "Delhi, India": 28.6139,
    "Mumbai, India": 19.0760,
    "Chennai, India": 13.0827,
}

city_longitude = {
    "Kochi, India": 76.2673,
    "Delhi, India": 77.2090,
    "Mumbai, India": 72.8777,
    "Chennai, India": 80.2707,
}

city_names = list(city_latitude.keys())

DATA_SOURCE_TEXT = (
    "NASA POWER (Prediction Of Worldwide Energy Resources), Monthly API, "
    "parameter T2M = Temperature at 2 Meters. "
    "NASA POWER's temperature values come from NASA's MERRA-2 model, which "
    "blends satellite and ground measurements into a grid of map squares. "
    "So each value describes a square around the city, not one thermometer."
)


# --------------------------------------------------------------
# FUNCTION 1: get yearly temperatures from NASA
# --------------------------------------------------------------
# A function is a named block of code we can use again and again.
# This one takes a city name and gives back a dictionary
# (a "box with labels") holding everything we found.
def get_nasa_data(city_name):

    # This box starts empty. We fill it in as we go.
    result = {
        "error": None,           # stays None if everything works
        "years": [],             # years that have all 12 months
        "temps": [],             # yearly average temperature for each year
        "skipped_years": [],     # years left out because months were missing
        "monthly_table": None,   # table of all monthly values
    }

    latitude = city_latitude[city_name]
    longitude = city_longitude[city_name]

    # These are the questions we ask NASA
    settings = {
        "parameters": "T2M",
        "community": "RE",
        "latitude": latitude,
        "longitude": longitude,
        "start": FIRST_YEAR,
        "end": LAST_YEAR,
        "format": "JSON",
    }

    # "try / except" means: try this, and if it fails (for example no
    # internet), do the "except" part instead of crashing.
    try:
        response = requests.get(API_URL, params=settings, timeout=60)
    except requests.exceptions.RequestException:
        result["error"] = (
            "Oops! I could not reach NASA's data service. "
            "Please check your internet connection and try again."
        )
        return result

    # Status code 200 means "everything is fine"
    if response.status_code != 200:
        result["error"] = (
            "NASA's data service answered with a problem (code "
            + str(response.status_code)
            + "). Please try again in a few minutes."
        )
        return result

    # Turn the answer into a Python dictionary
    try:
        data = response.json()
    except ValueError:
        result["error"] = "NASA's answer was not in the format I expected."
        return result

    # Find the temperature values inside the answer.
    # NASA's JSON looks like: data -> properties -> parameter -> T2M
    # and T2M holds keys like "200101" (year 2001, month 01).
    try:
        t2m = data["properties"]["parameter"]["T2M"]
    except KeyError:
        result["error"] = "I could not find temperature values in NASA's answer."
        return result

    # Lists to build the monthly table
    table_years = []
    table_months = []
    table_temps = []

    # Go through every year, then every month of that year
    for year in range(FIRST_YEAR, LAST_YEAR + 1):

        good_values = []     # valid monthly temperatures for this year

        for month in range(1, 13):

            # Build the key, for example year 2001, month 1 -> "200101"
            if month < 10:
                key = str(year) + "0" + str(month)
            else:
                key = str(year) + str(month)

            # Only use the value if it exists and is not "missing"
            if key in t2m:
                value = t2m[key]
                if value is not None and value != MISSING_VALUE:
                    good_values.append(value)
                    table_years.append(year)
                    table_months.append(month)
                    table_temps.append(round(value, 2))

        # Only trust a year if all 12 months are available.
        # (A year with missing winter months would look unfairly warm.)
        if len(good_values) == 12:
            yearly_average = sum(good_values) / 12
            result["years"].append(year)
            result["temps"].append(yearly_average)
        else:
            result["skipped_years"].append(year)

    result["monthly_table"] = pd.DataFrame(
        {
            "Year": table_years,
            "Month": table_months,
            "Temperature (°C)": table_temps,
        }
    )

    # A straight-line trend needs enough points to mean anything
    if len(result["years"]) < 5:
        result["error"] = (
            "NASA returned fewer than 5 complete years of data "
            "for this city, so I cannot study a trend."
        )

    return result


# --------------------------------------------------------------
# FUNCTION 2: find the trend (linear regression)
# --------------------------------------------------------------
# Linear regression draws the best straight line through the points.
#   slope   = how many °C the line goes up (or down) each year
#   p-value = how likely we'd see a trend this strong by pure chance
#             if there were really no trend (small = less likely chance)
def analyse_trend(years, temps):

    fit = linregress(years, temps)

    slope = fit.slope
    intercept = fit.intercept
    p_value = fit.pvalue

    # Total change along the trend line, first year to last year
    total_change = slope * (years[-1] - years[0])

    # Points of the trend line, one for each year
    trend_line = []
    for year in years:
        trend_line.append(intercept + slope * year)

    # Direction of the trend
    if slope > 0:
        direction = "increasing"
    elif slope < 0:
        direction = "decreasing"
    else:
        direction = "flat"

    # Statistical significance. 0.05 is the usual cut-off in science.
    if p_value < 0.05:
        significance = "statistically significant (p < 0.05)"
        is_significant = True
    else:
        significance = "NOT statistically significant (p >= 0.05)"
        is_significant = False

    # Average temperature over all years
    average_temp = sum(temps) / len(temps)

    analysis = {
        "slope": slope,
        "total_change": total_change,
        "p_value": p_value,
        "trend_line": trend_line,
        "direction": direction,
        "significance": significance,
        "is_significant": is_significant,
        "average_temp": average_temp,
    }
    return analysis


# --------------------------------------------------------------
# FUNCTION 3: write the friendly "SO, HOW'S EARTH?" message
# --------------------------------------------------------------
def make_story(city_name, analysis):

    slope = analysis["slope"]
    total = analysis["total_change"]

    if analysis["is_significant"] and slope > 0:
        story = (
            "Around **" + city_name + "**, the yearly average temperature "
            "has been **rising** by about " + f"{slope:.3f}" + " °C per year. "
            "Over the whole period that adds up to roughly "
            + f"{total:.2f}" + " °C. "
            "The statistical test says this is unlikely to be just random "
            "ups and downs."
        )
    elif analysis["is_significant"] and slope < 0:
        story = (
            "Around **" + city_name + "**, the yearly average temperature "
            "has been **falling** by about " + f"{abs(slope):.3f}" + " °C per year. "
            "Over the whole period that is roughly "
            + f"{abs(total):.2f}" + " °C cooler. "
            "The statistical test says this is unlikely to be just random "
            "ups and downs."
        )
    else:
        story = (
            "Around **" + city_name + "**, the straight line tilts by about "
            + f"{slope:.3f}" + " °C per year, but this is **not strong enough "
            "to be called a real trend**. Year-to-year changes "
            "(like monsoon years or El Niño) are big compared with this "
            "tiny tilt, so I can't say Earth's temperature here is "
            "clearly going up or down in this period."
        )

    return story


# --------------------------------------------------------------
# FUNCTION 4: show the p-value nicely
# --------------------------------------------------------------
def format_p_value(p_value):
    if p_value < 0.0001:
        return "less than 0.0001"
    else:
        return f"{p_value:.4f}"


# --------------------------------------------------------------
# FUNCTION 5: coloured message boxes that are always easy to read
# --------------------------------------------------------------
# Streamlit's built-in boxes change colour with the computer's dark mode,
# which made the text hard to read. These boxes use fixed colours instead.
def show_box(message, background, border):
    html = (
        '<div style="background-color:' + background
        + '; border-left: 6px solid ' + border
        + '; color:#1F2D26; padding:14px; border-radius:10px;'
        + ' margin:10px 0;">'
        + message
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def show_error(message):
    show_box(message, "#FDE8E4", "#C0392B")      # light red box


def show_warning(message):
    show_box(message, "#FFF3CD", "#E0A800")      # light yellow box


def show_note(message):
    show_box(message, "#E3F1EA", "#3E8E5A")      # light green box


# The note we show with every result
CAUTION_TEXT = (
    "<b>Please remember:</b> this is only one city over about 25 years. "
    "A trend for one city can't, on its own, prove what is causing "
    "climate change. Scientists combine many places, many datasets and "
    "many decades to study that."
)


# ==============================================================
# THE WEBSITE STARTS HERE
# ==============================================================
st.title("HOW'S EARTH? 🌍")
st.subheader("Hey Earth, let's check your temperature!")

st.write("Hey Earth! How have you been feeling lately?")
st.write(
    "Let's take a little look at your temperature history and "
    "discover how our planet has been changing."
)

st.write("---")

mode = st.radio(
    "What would you like to do?",
    ["Check one city", "Compare two cities"],
)


# ==============================================================
# MODE 1: ONE CITY
# ==============================================================
if mode == "Check one city":

    city = st.selectbox("Choose a city:", city_names)
    st.write("📍 Selected location: **" + city + "**")

    if st.button("Check Earth's Temperature 🌡️"):

        with st.spinner("Asking NASA for the temperature history..."):
            data = get_nasa_data(city)

        if data["error"] is not None:
            show_error(data["error"])
        else:
            years = data["years"]
            temps = data["temps"]
            analysis = analyse_trend(years, temps)

            # ---------- Graph ----------
            st.subheader("📈 Yearly average temperature")

            fig, ax = plt.subplots(figsize=(8, 4.5))
            fig.patch.set_facecolor(CREAM)
            ax.set_facecolor("#FFFDF5")

            ax.plot(years, temps, color=BLUE, marker="o",
                    label="Yearly average (NASA POWER)")
            ax.plot(years, analysis["trend_line"], color=GREEN,
                    linestyle="--", linewidth=2, label="Trend line")

            ax.set_title("Temperature at 2 m - " + city)
            ax.set_xlabel("Year")
            ax.set_ylabel("Temperature (°C)")
            ax.grid(True, alpha=0.3)
            ax.legend()

            st.pyplot(fig)

            # ---------- Data tables ----------
            st.subheader("🗂️ Yearly averages")
            yearly_table = pd.DataFrame(
                {
                    "Year": years,
                    "Average temperature (°C)": [round(t, 2) for t in temps],
                }
            )
            st.dataframe(yearly_table, hide_index=True)

            with st.expander("See all the monthly values from NASA"):
                st.dataframe(data["monthly_table"], hide_index=True)

            if len(data["skipped_years"]) > 0:
                show_warning(
                    "These years were left out because some months were "
                    "missing: " + str(data["skipped_years"])
                )

            # ---------- Report ----------
            st.subheader("🌡️ Earth's Temperature Report")

            st.write("**Selected location:** " + city)
            st.write("**Data source:** " + DATA_SOURCE_TEXT)
            st.write(
                "**Observation period:** " + str(years[0]) + " to "
                + str(years[-1]) + " (" + str(len(years)) + " complete years)"
            )
            st.write(
                "**Average temperature:** "
                + f"{analysis['average_temp']:.2f}" + " °C"
            )
            st.write("**Temperature trend:** " + analysis["direction"])
            st.write(
                "**Rate of change:** " + f"{analysis['slope']:.3f}"
                + " °C per year (" + f"{analysis['slope'] * 10:.2f}"
                + " °C per decade)"
            )
            st.write(
                "**Estimated change over the period:** "
                + f"{analysis['total_change']:.2f}" + " °C"
            )
            st.write("**P-value:** " + format_p_value(analysis["p_value"]))
            st.write("**Statistical significance:** " + analysis["significance"])

            # ---------- Friendly summary ----------
            st.subheader("SO, HOW'S EARTH?")
            st.write(make_story(city, analysis))
            show_note(CAUTION_TEXT)


# ==============================================================
# MODE 2: COMPARE TWO CITIES
# ==============================================================
if mode == "Compare two cities":

    city_a = st.selectbox("First city:", city_names, index=0)
    city_b = st.selectbox("Second city:", city_names, index=1)

    st.write("📍 Comparing **" + city_a + "** and **" + city_b + "**")

    if st.button("Compare Earth's Temperature 🌡️"):

        if city_a == city_b:
            show_warning("Please choose two different cities to compare.")
        else:
            with st.spinner("Asking NASA for both cities..."):
                data_a = get_nasa_data(city_a)
                data_b = get_nasa_data(city_b)

            if data_a["error"] is not None:
                show_error(city_a + ": " + data_a["error"])
            elif data_b["error"] is not None:
                show_error(city_b + ": " + data_b["error"])
            else:
                analysis_a = analyse_trend(data_a["years"], data_a["temps"])
                analysis_b = analyse_trend(data_b["years"], data_b["temps"])

                # ---------- Graph with both cities ----------
                st.subheader("📈 Yearly average temperature")

                fig, ax = plt.subplots(figsize=(8, 4.5))
                fig.patch.set_facecolor(CREAM)
                ax.set_facecolor("#FFFDF5")

                ax.plot(data_a["years"], data_a["temps"], color=BLUE,
                        marker="o", label=city_a)
                ax.plot(data_a["years"], analysis_a["trend_line"], color=BLUE,
                        linestyle="--", alpha=0.6, label=city_a + " trend")

                ax.plot(data_b["years"], data_b["temps"], color=ORANGE,
                        marker="s", label=city_b)
                ax.plot(data_b["years"], analysis_b["trend_line"], color=ORANGE,
                        linestyle="--", alpha=0.6, label=city_b + " trend")

                ax.set_title("Temperature at 2 m: " + city_a + " vs " + city_b)
                ax.set_xlabel("Year")
                ax.set_ylabel("Temperature (°C)")
                ax.grid(True, alpha=0.3)
                ax.legend()

                st.pyplot(fig)

                # ---------- Comparison table ----------
                st.subheader("🌡️ Side-by-side report")
                st.write("**Data source:** " + DATA_SOURCE_TEXT)

                comparison = pd.DataFrame(
                    {
                        "": [
                            "Average temperature (°C)",
                            "Trend",
                            "Rate of change (°C per year)",
                            "Estimated change (°C)",
                            "P-value",
                            "Statistically significant?",
                        ],
                        city_a: [
                            f"{analysis_a['average_temp']:.2f}",
                            analysis_a["direction"],
                            f"{analysis_a['slope']:.3f}",
                            f"{analysis_a['total_change']:.2f}",
                            format_p_value(analysis_a["p_value"]),
                            "Yes" if analysis_a["is_significant"] else "No",
                        ],
                        city_b: [
                            f"{analysis_b['average_temp']:.2f}",
                            analysis_b["direction"],
                            f"{analysis_b['slope']:.3f}",
                            f"{analysis_b['total_change']:.2f}",
                            format_p_value(analysis_b["p_value"]),
                            "Yes" if analysis_b["is_significant"] else "No",
                        ],
                    }
                )
                st.dataframe(comparison, hide_index=True)

                # ---------- Friendly comparison ----------
                st.subheader("SO, HOW'S EARTH?")

                st.write(make_story(city_a, analysis_a))
                st.write(make_story(city_b, analysis_b))

                # Which city is warmer on average?
                if analysis_a["average_temp"] > analysis_b["average_temp"]:
                    warmer = city_a
                    cooler = city_b
                else:
                    warmer = city_b
                    cooler = city_a
                gap = abs(analysis_a["average_temp"] - analysis_b["average_temp"])
                st.write(
                    "On average, **" + warmer + "** is warmer than **" + cooler
                    + "** by about " + f"{gap:.2f}" + " °C."
                )

                # Which city's line tilts more? (0.01 °C/year is a rough
                # cut-off I chose: below it, the two tilts are very similar)
                slope_gap = abs(analysis_a["slope"] - analysis_b["slope"])
                if slope_gap < 0.01:
                    st.write(
                        "The two cities have **very similar** rates of change."
                    )
                else:
                    if analysis_a["slope"] > analysis_b["slope"]:
                        faster = city_a
                    else:
                        faster = city_b
                    st.write(
                        "**" + faster + "** has the larger upward tilt in "
                        "this period. But with only about 25 yearly points, "
                        "small differences between cities may just be "
                        "natural variation."
                    )

                show_note(CAUTION_TEXT)


# ==============================================================
# FOOTER
# ==============================================================
st.write("---")
st.caption(
    "Data: NASA POWER Project (https://power.larc.nasa.gov/). "
    "This is a student project and is not affiliated with or endorsed by NASA."
)
