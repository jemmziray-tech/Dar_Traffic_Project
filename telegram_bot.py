import os
import joblib
import logging
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# --- Configure Enterprise Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ---------------------------------------------------------
# 1. LOAD THE BRAIN (.pkl via Joblib)
# ---------------------------------------------------------
try:
    logging.info("Loading AI Traffic Model with Joblib...")
    model = joblib.load("traffic_model.pkl")
    logging.info("✅ Brain successfully loaded into memory!")
except Exception as e:
    logging.error(f"❌ Could not load model. Error: {e}")
    model = None


# ---------------------------------------------------------
# 2. LIVE WEATHER ENGINE (Dar es Salaam)
# ---------------------------------------------------------
def get_live_weather_condition():
    """Fetches real-time weather in Dar es Salaam to feed the AI."""
    url = "https://api.open-meteo.com/v1/forecast?latitude=-6.7978&longitude=39.2201&current_weather=true"
    try:
        data = requests.get(url).json()
        code = data["current_weather"]["weathercode"]
        # Convert the raw weather code into the words your AI understands
        condition = "Clear" if code <= 3 else "Rainy" if code >= 51 else "Cloudy"
        return condition
    except Exception as e:
        logging.error(f"Weather API Error: {e}. Defaulting to Clear.")
        return "Clear"  # Fallback if the internet is down


# ---------------------------------------------------------
# 3. THE INTERACTIVE MENU (START COMMAND)
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when a user types /start and shows the buttons"""

    # Define our interactive buttons
    # The Full 22-Route Smart Grid (2 columns per row for mobile optimization)
    keyboard = [
        [
            InlineKeyboardButton("Morogoro Rd (Ubungo)", callback_data="ubungo"),
            InlineKeyboardButton("Bagamoyo Rd (Mwenge)", callback_data="mwenge"),
        ],
        [
            InlineKeyboardButton("Ali Hassan Mwinyi", callback_data="selander"),
            InlineKeyboardButton("Nyerere Rd (Tazara)", callback_data="tazara"),
        ],
        [
            InlineKeyboardButton("Mandela Rd (Port)", callback_data="mandela_buguruni"),
            InlineKeyboardButton("Kilwa Rd (Mbagala)", callback_data="kilwa_mbagala"),
        ],
        [
            InlineKeyboardButton("Old Bagamoyo Rd", callback_data="old_bagamoyo"),
            InlineKeyboardButton("Sam Nujoma Rd", callback_data="sam_nujoma"),
        ],
        [
            InlineKeyboardButton("Uhuru St (Ilala)", callback_data="uhuru_street"),
            InlineKeyboardButton("Posta to Tegeta", callback_data="posta_to_tegeta"),
        ],
        [
            InlineKeyboardButton("Posta to Kimara", callback_data="posta_to_kimara"),
            InlineKeyboardButton(
                "Posta to G. Mboto", callback_data="posta_to_gongolamboto"
            ),
        ],
        [
            InlineKeyboardButton(
                "Tabata (Mandela-Segerea)", callback_data="tabata_dampo"
            ),
            InlineKeyboardButton("Kamata/Gerezani", callback_data="kamata_gerezani"),
        ],
        [
            InlineKeyboardButton("Chang'ombe Rd", callback_data="changombe_road"),
            InlineKeyboardButton(
                "Kawawa (Morocco)", callback_data="morocco_intersection"
            ),
        ],
        [
            InlineKeyboardButton("Kawawa (Kigogo)", callback_data="kigogo_roundabout"),
            InlineKeyboardButton("UN Road (Fire)", callback_data="fire_upanga"),
        ],
        [
            InlineKeyboardButton("Mwai Kibaki Rd", callback_data="mwai_kibaki"),
            InlineKeyboardButton("Sinza Rd (Mori)", callback_data="sinza_mori"),
        ],
        [
            InlineKeyboardButton("Goba Rd (Massana)", callback_data="goba_massana")
            # Notice this last row only has 1 button because 21 is an odd number!
            # You can add a 22nd route here later to balance the grid.
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = (
        "Habari! 🇹🇿 I am the Dar es Salaam Traffic AI.\n\n"
        "Tap a route below, and I will predict your delay instantly:"
    )

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


# ---------------------------------------------------------
# 4. THE BUTTON CLICK HANDLER (AI PREDICTION)
# ---------------------------------------------------------
async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires automatically when a user taps an Inline Button"""

    query = update.callback_query
    await query.answer()  # Acknowledge the tap so the button stops flashing

    if not model:
        await query.edit_message_text(text="Sorry, my AI brain is currently offline.")
        return

    # Extract the exact ID hidden inside the button the user tapped
    selected_road_id = query.data

    try:
        # --- GET LIVE DATA ---
        now = datetime.now()
        # High precision time matching your training data
        current_hour = now.hour + (now.minute / 60.0)

        # 🚨 THE FINAL FIX: Translate the weekday number into the English word!
        days_of_week = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        current_day_name = days_of_week[now.weekday()]

        current_weather = get_live_weather_condition()

        # Feed the perfectly formatted LIVE data into the AI
        prediction_features = pd.DataFrame(
            [
                {
                    "road_id": selected_road_id,
                    "Condition": current_weather,
                    "Hour": current_hour,
                    "Day": current_day_name,
                }
            ]
        )

        # Ask the brain to predict!
        predicted_delay = model.predict(prediction_features)[0]

        # Format a beautiful response
        road_name_display = selected_road_id.replace("_", " ").title()
        reply = (
            f"🧠 **AI Prediction for {road_name_display}**\n"
            f"───────────────────────\n"
            f"🌦️ Current Weather: {current_weather}\n"
            f"🚦 Expected Delay: **{int(predicted_delay)} minutes**\n\n"
            f"*(Type /start to check another route)*"
        )

        # Replace the buttons with the final answer
        await query.edit_message_text(text=reply, parse_mode="Markdown")

    except ValueError as e:
        logging.error(f"Value Error: {e}")
        await query.edit_message_text(
            text="I need a tune-up! My data columns don't match the model."
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await query.edit_message_text(
            text="An unexpected error occurred in my neural network."
        )


# ---------------------------------------------------------
# 5. START THE BOT
# ---------------------------------------------------------
if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logging.error("Missing TELEGRAM_TOKEN in .env file!")
    else:
        logging.info("Starting Interactive Telegram Bot...")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Listen for the /start command
        app.add_handler(CommandHandler("start", start))

        # Listen for ANY button tap
        app.add_handler(CallbackQueryHandler(button_tap))

        app.run_polling()
