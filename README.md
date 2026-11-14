# HOW'S EARTH? 🌍

Hey Earth, let's check your temperature!

I'm a B.Tech Computer Science student, and this is my project for the NASA Space Apps Challenge 2026 ("Be An Earth System Trend Detective!").

The idea is simple: treat Earth like a friend and check its temperature. You pick a city (Kochi, Delhi, Mumbai or Chennai), and the app shows how the temperature there has changed from 2001 to 2025.

## What it does
- Gets monthly temperature data from NASA POWER (the T2M value, temperature at 2 metres)
- Turns the monthly numbers into one average for each year
- Draws a graph with a trend line
- Tells you if the temperature is going up or down, and how fast
- Checks if the trend is strong enough to count (p-value), or could just be luck
- Lets you compare two cities on one graph

## Where the data comes from
NASA POWER Monthly API: https://power.larc.nasa.gov/docs/

One thing I learned: these temperatures come from a NASA computer model (MERRA-2) that covers map squares. So the number is for the area around the city, not a thermometer in the city.

## Things to keep in mind
- It's only 25 years and four cities.
- One city's trend can't prove what is causing climate change. This app is just for exploring.

## How to run it
1. Install Python
2. pip install streamlit requests pandas matplotlib scipy
3. python -m streamlit run app.py

## Built with
Python, Streamlit, Pandas, Matplotlib, Requests, SciPy

## About the AI help
I'm still learning Python, so I used an AI assistant (Claude) to help write and fix the code. I ran it on my own laptop, tested it, and went through the code so I can explain it.

NASA doesn't endorse this. It's just a student project.
