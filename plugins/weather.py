# plugins/weather.py
from plugins.base import Plugin
from ddgs import DDGS

class WeatherPlugin(Plugin):
    name = "WEATHER"
    description = "Get current weather for any city"
    triggers = ["weather", "temperature", "forecast", "rain", "sunny"]
    
    def execute(self, value: str) -> tuple:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"weather in {value} today",
                    max_results=3
                ))
            if results:
                info = "\n".join([r['body'] for r in results[:2]])
                return f"🌤️ *Weather in {value}*\n\n{info[:1000]}", None
            return f"❌ Could not get weather for {value}", None
        except Exception as e:
            return f"❌ Weather error: {str(e)}", None
