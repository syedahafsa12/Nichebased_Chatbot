# --- Required Libraries ---
import os
import streamlit as st
from dotenv import load_dotenv
import requests
from datetime import datetime
import random
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Custom CSS for Modern Chatbot-Like UI ---
def add_custom_css():
    st.markdown(
        """
        <style>
        body {
            background: linear-gradient(to bottom, #232526, #414345);
            color: #FFFFFF;
        }
        h1, h2 {
            text-align: center;
            color: #86AB89;
        }
        p {
            text-align: center !important;
            color: #86AB89;
        }
        .conversation-box {
            max-height: 300px;
            overflow-y: auto;
            padding: 10px;
            border-radius: 5px;
            background-color: #333;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# --- Load API Keys ---
def load_api_keys():
    try:
        spoonacular_key = st.secrets["SPOONACULAR_API_KEY"]
        gemini_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        spoonacular_key = os.getenv("SPOONACULAR_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")

    if not spoonacular_key or not gemini_key:
        st.error("🚨 API keys not found! Add them to Streamlit Secrets or .env file.")
        raise ValueError("🚨 API keys not found! Add them to Streamlit Secrets or .env file.")
    
    return spoonacular_key, gemini_key

# --- Spoonacular API Calls ---
def get_meal_ideas(ingredients, meal_type, api_key):
    """Call the Spoonacular API to get meal ideas."""
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "query": meal_type,
        "includeIngredients": ingredients,
        "number": 5, 
        "apiKey": api_key,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        recipes = response.json().get("results", [])
        return filter_halal_recipes(recipes, api_key)
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Spoonacular API Error: {e}")
        return []

def get_random_meal(api_key):
    """Fetch a random recipe and ensure it is halal."""
    url = f"https://api.spoonacular.com/recipes/random?number=1&apiKey={api_key}"
    try:
        while True:
            response = requests.get(url)
            response.raise_for_status()
            recipe = response.json().get("recipes", [])[0]
            if is_halal(recipe):
                return recipe
    except Exception as e:
        st.error(f"❌ Spoonacular API Error: {e}")
        return None

def filter_halal_recipes(recipes, api_key):
    """Filter recipes to ensure they are 100% halal."""
    forbidden_ingredients = ['pork', 'ham', 'bacon', 'wine', 'rum', 'pecan', 'gelatin', 'beer']
    halal_recipes = []
    for recipe in recipes:
        recipe_id = recipe.get("id")
        details = get_recipe_details(recipe_id, api_key)
        if details and is_halal(details, forbidden_ingredients):
            halal_recipes.append(details)
    return halal_recipes

def is_halal(recipe, forbidden_ingredients=None):
    """Check if a recipe is halal by checking its ingredients."""
    forbidden_ingredients = forbidden_ingredients or ['pork', 'ham', 'bacon', 'wine', 'rum', 'pecan', 'gelatin', 'beer']
    ingredients_list = [i['name'].lower() for i in recipe.get("extendedIngredients", [])]
    for forbidden in forbidden_ingredients:
        if any(forbidden in ingredient for ingredient in ingredients_list):
            return False
    return True

def get_recipe_details(recipe_id, api_key):
    """Fetch detailed recipe information (including ingredients) from Spoonacular."""
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    try:
        response = requests.get(url, params={"apiKey": api_key})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

# --- Chat Memory Management ---
def add_to_memory(user_input, bot_response):
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_input,
        "bot": bot_response,
    })
    if len(st.session_state["history"]) > 10:
        st.session_state["history"].pop(0)

def display_memory():
    st.markdown('<p style="text-align: center; font-size: 24px; font-weight: bold;">💬 Conversation History</p>', unsafe_allow_html=True)
    if "history" in st.session_state:
        for chat in reversed(st.session_state["history"]):
            st.write(f"🕒 {chat['timestamp']}")
            st.write(f"**You:** {chat['user']}")
            st.write(f"**Bot:** {chat['bot']}")
            st.divider()

# --- Streamlit App ---
def create_meal_planner_with_categories():
    add_custom_css()
    st.markdown("<h1>🍽️ ChefMate</h1>", unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 20px; font-weight: bold;">Your Smart Recipe & Chat Assistant</p>', unsafe_allow_html=True)

    try:
        spoonacular_key, gemini_key = load_api_keys()
        genai.configure(api_key=gemini_key)
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=gemini_key)
    except Exception as e:
        return

    ingredients = st.text_input("List your ingredients (e.g., 'chicken, tomato, potato')")
    meal_type = st.selectbox("What type of meal are you planning?", ["Breakfast", "Lunch", "Dinner", "Snack"])

    if st.button("🍲 Get Meal Ideas"):
        with st.spinner("Fetching meal ideas... 🍳"):
            recipes = get_meal_ideas(ingredients, meal_type, spoonacular_key)
            for recipe in recipes:
                st.write(f"**{recipe.get('title')}**")
                st.image(recipe.get("image"), width=200)
                st.write(f"[Full Recipe]({recipe.get('sourceUrl')})")

    if st.button("🎉 Surprise Me!"):
        with st.spinner("Fetching a surprise meal... 🎉"):
            recipe = get_random_meal(spoonacular_key)
            if recipe:
                st.write(f"**{recipe.get('title')}**")
                st.image(recipe.get("image"), width=200)
                st.write(f"[Full Recipe]({recipe.get('sourceUrl')})")

    user_input = st.text_input("You:")
    if user_input:
        response = llm.invoke(user_input)
        st.write(f"🤖 **Bot:** {response.content}")
        add_to_memory(user_input, response.content)

    display_memory()

if __name__ == "__main__":
    create_meal_planner_with_categories()
