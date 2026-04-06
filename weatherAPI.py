import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

OPENWEATHER_API_KEY = "39a81eaad8f4d90734462eed7dfc5413"

def set_dynamic_background(weather_condition, is_daytime):
    if is_daytime:
        if "Clear" in weather_condition:
            background_style = "linear-gradient(to bottom, #4facfe, #00f2fe)"
        elif "Rain" in weather_condition or "Thunderstorm" in weather_condition:
            background_style = "linear-gradient(to bottom, #203a43, #2c5364)"
        else:
            background_style = "linear-gradient(to bottom, #757f9a, #d7dde8)"
    else:
        background_style = "linear-gradient(to bottom, #0f2027, #203a43, #2c5364)"

    #text color, so we can read
    text_color = "white" if not is_daytime or "Rain" in weather_condition or "Thunderstorm" in weather_condition else "black"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {background_style};
            background-attachment: fixed;
        }}
        h1, h2, h3, p, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
            color: {text_color} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def fetch_data_from_api(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            if attempt == max_retries - 1: 
                return None
    return None

def get_complete_weather_report(location_query):
    # Coor
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location_query}&limit=1&appid={OPENWEATHER_API_KEY}"
    geo_results = fetch_data_from_api(geo_url)
    if not geo_results: return None
    latitude = geo_results[0]["lat"]
    longitude = geo_results[0]["lon"]
    city_name = geo_results[0]["name"]
    country_code = geo_results[0].get("country", "PH")

    #Get Current Weather
    current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={OPENWEATHER_API_KEY}&units=metric"
    current_weather = fetch_data_from_api(current_url)

    #Get Air Quality
    air_quality_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={OPENWEATHER_API_KEY}"
    air_quality = fetch_data_from_api(air_quality_url)

    #Get 5-Day Forecast
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={OPENWEATHER_API_KEY}&units=metric"
    forecast_data = fetch_data_from_api(forecast_url)

    return {
        "city": city_name, "country": country_code, "lat": latitude, "lon": longitude,
        "current": current_weather, "air": air_quality, "forecast": forecast_data
    }

def calculate_heat_index(celsius_temp, humidity_percentage):
    fahrenheit_temp = (celsius_temp * 9/5) + 32
    if fahrenheit_temp < 80:
        heat_index_f = fahrenheit_temp - (0.55 - 0.0055 * humidity_percentage) * (fahrenheit_temp - 58)
    else:
        heat_index_f = (-42.379 + 2.04901523 * fahrenheit_temp + 10.14333127 * humidity_percentage -
                        0.22475541 * fahrenheit_temp * humidity_percentage - 0.00683783 * fahrenheit_temp**2 -
                        0.05481717 * humidity_percentage**2 + 0.00122874 * fahrenheit_temp**2 * humidity_percentage +
                        0.00085282 * fahrenheit_temp * humidity_percentage**2 - 0.00000199 * fahrenheit_temp**2 * humidity_percentage**2)
    
    heat_index_celsius = (heat_index_f - 32) * 5/9
    return heat_index_celsius

def get_heat_safety_category(heat_index_celsius):
    if heat_index_celsius >= 54: 
        return "EXTREME DANGER", "CRITICAL", "EMERGENCY: Suspend all activities."
    if heat_index_celsius >= 41: 
        return "DANGER", "HIGH RISK", "Stay indoors • High chance of class suspension."
    if heat_index_celsius >= 35: 
        return "EXTREME CAUTION", "MODERATE RISK", "Limit outdoor activities."
    if heat_index_celsius >= 32: 
        return "CAUTION", "LOW RISK", "Stay hydrated • Take shade breaks."
    
    return "NORMAL", "CLEAR", "Safe conditions."

def get_precipitation_volume(current_weather_data):
    """Extracts rain or snow volume in mm."""
    rain_volume = current_weather_data.get('rain', {}).get('1h', 0) or current_weather_data.get('rain', {}).get('3h', 0)
    return rain_volume

def get_flood_risk_level(rainfall_mm):
    if rainfall_mm > 15:
        return "Red Rainfall Warning", "Torrential rain. Flash flooding highly likely."
    elif rainfall_mm > 7.5:
        return "Orange Rainfall Warning", "Heavy rain detected. Potential for localized flooding."
    elif rainfall_mm > 2.5:
        return "Yellow Rainfall Warning", "Steady rain. Stay cautious on the roads."
    return None, None

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="WeatherTracker", layout="wide")

st.title("WeatherTracker")
st.markdown("Real-time Weather, Heat Index & Flood Monitor")

# Sidebar for User Input
with st.sidebar:
    st.header("Search Settings")
    user_location_input = st.text_input("Enter City Name", value="Guinhawa, PH")
    is_search_clicked = st.button("Check Weather")

if user_location_input or is_search_clicked:
    with st.spinner(f"Analyzing weather for {user_location_input}..."):
        all_weather_data = get_complete_weather_report(user_location_input)

    if all_weather_data:
        #Extract current data
        current_data = all_weather_data['current']
        current_temp = current_data['main']['temp']
        current_humidity = current_data['main']['humidity']
        current_weather_main = current_data['weather'][0]['main']
        
        #Background Logic
        current_time_unix = datetime.now().timestamp()
        is_daytime = current_data['sys']['sunrise'] <= current_time_unix <= current_data['sys']['sunset']
        set_dynamic_background(current_weather_main, is_daytime)

        #Hazard and Safety Calculations
        calculated_hi = calculate_heat_index(current_temp, current_humidity)
        hi_label, hi_emoji, hi_advice = get_heat_safety_category(calculated_hi)
        
        rain_amount, snow_amount = get_precipitation_volume(current_data)
        flood_title, flood_description = get_flood_risk_level(rain_amount)
        
        #Display Location Header
        st.header(f"{all_weather_data['city']}, {all_weather_data['country']}")
        
        #Dashboard Metrics
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        metric_col1.metric("Temperature", f"{current_temp}°C")
        metric_col2.metric("Humidity", f"{current_humidity}%")
        metric_col3.metric("Heat Index", f"{round(calculated_hi, 1)}°C")
        metric_col4.metric("Precipitation", f"{max(rain_amount, snow_amount)} mm")
        metric_col5.metric("Wind Speed", f"{round(current_data['wind']['speed']*3.6, 1)} km/h")

        #Safety Alerts
        alert_box_1, alert_box_2 = st.columns(2)
        with alert_box_1:
            st.info(f"**{hi_emoji} {hi_label}**: {hi_advice}")
        with alert_box_2:
            if flood_title:
                st.warning(f"**{flood_title}**: {flood_description}")
            else:
                st.success("**NO FLOOD RISK**: No significant rainfall detected.")

        # Forecast Chart
        st.subheader("5-Day Forecast Analysis")
        formatted_forecast_list = []
        for entry in all_weather_data['forecast']['list']:
            entry_temp = entry['main']['temp']
            entry_humidity = entry['main']['humidity']
            formatted_forecast_list.append({
                "Time": datetime.fromtimestamp(entry['dt']),
                "Temp (°C)": entry_temp,
                "Heat Index (°C)": round(calculate_heat_index(entry_temp, entry_humidity), 1),
                "Condition": entry['weather'][0]['main']
            })
        
        forecast_dataframe = pd.DataFrame(formatted_forecast_list)
        forecast_chart = px.line(
            forecast_dataframe, 
            x="Time", 
            y=["Temp (°C)", "Heat Index (°C)"], 
            color_discrete_map={"Temp (°C)": "#4facfe", "Heat Index (°C)": "#ffa500"}
        )
        st.plotly_chart(forecast_chart, use_container_width=True)

        #Environment Details
        st.divider()
        footer_col1, footer_col2 = st.columns(2)
        with footer_col1:
            st.write("Air Quality Index")
            aqi_score = all_weather_data['air']['list'][0]['main']['aqi']
            aqi_label = {1:"Good", 2:"Fair", 3:"Moderate", 4:"Poor", 5:"Very Poor"}.get(aqi_score)
            st.write(f"**Current Status:** {aqi_label}")     
        
        with footer_col2:
            st.write("Solar & Visibility")
            sunrise_time = datetime.fromtimestamp(current_data['sys']['sunrise']).strftime('%H:%M')
            sunset_time = datetime.fromtimestamp(current_data['sys']['sunset']).strftime('%H:%M')
            visibility_km = current_data.get('visibility', 0) / 1000
            st.write(f"**Sunrise:** {sunrise_time} | **Sunset:** {sunset_time}")
            st.write(f"**Visibility Range:** {visibility_km} km")

    else:
        st.error("Location not found. Please check your spelling and try again.")
else:
    st.info("Enter a city in the sidebar to begin tracking weather hazards.")
