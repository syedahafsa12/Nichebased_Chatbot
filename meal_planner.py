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
    """Fetch API keys for Spoonacular and Gemini."""
    spoonacular_key = None
    gemini_key = None

    try:
        spoonacular_key = st.secrets["SPOONACULAR_API_KEY"]
        gemini_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    if not spoonacular_key or not gemini_key:
        st.error("🚨 API keys not found! Add them to Streamlit Secrets or .env file.")
        raise ValueError("🚨 API keys not found! Add them to Streamlit Secrets or .env file.")
    
    return spoonacular_key, gemini_key

# --- Spoonacular API Call ---
def get_meal_ideas(ingredients, meal_type, api_key):
    """Call the Spoonacular API to get halal meal ideas."""
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "query": meal_type,
        "includeIngredients": ingredients,
        "number": 10, 
        "apiKey": api_key,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        recipes = response.json().get("results", [])
        
        # Filter recipes to ensure they are halal (example logic can be improved)
        halal_keywords = ['chicken', 'beef', 'fish', 'vegetarian', 'vegan', 'egg', 'lentil', 'chickpea', 'bean', 'seafood']
        detailed_recipes = []
        for recipe in recipes:
            recipe_id = recipe.get("id")
            details = get_recipe_details(recipe_id, api_key)
            ingredients_list = [i['name'].lower() for i in details.get("extendedIngredients", [])]
            
            # Check if the ingredients are in the list of halal-friendly items
            if any(halal_item in ingredients_list for halal_item in halal_keywords):
                detailed_recipes.append(details)

        return detailed_recipes
    except Exception as e:
        return {"error": str(e)}

def get_recipe_details(recipe_id, api_key):
    """Fetch detailed recipe information (including ingredients) from Spoonacular."""
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {"apiKey": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

# --- Chat Memory Management ---
def add_to_memory(user_input, bot_response):
    """Add a conversation to memory (limit to 10)."""
    if "history" not in st.session_state:
        st.session_state["history"] = []
    
    st.session_state["history"].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_input,
        "bot": bot_response,
    })

    if len(st.session_state["history"]) > 10:
        st.session_state["history"].pop(0)  # Keep only the last 10 interactions

def display_memory():
    """Display the last 10 chats."""
    st.markdown('<p style="text-align: center; font-size: 24px; font-weight: bold; color: #86AB89;">💬 Conversation History</p>', unsafe_allow_html=True)
    if "history" in st.session_state:
        for chat in reversed(st.session_state["history"]):  # Show latest first
            st.write(f"🕒 {chat['timestamp']}")
            st.write(f"**You:** {chat['user']}")
            st.write(f"**Bot:** {chat['bot']}")
            st.divider()

# --- Streamlit App ---
def create_meal_planner_with_categories():
    """Main Meal Planner with Meal Categories and Seamless Chat."""
    add_custom_css()

    # Title and Header
    st.markdown("<h1>🍽️ ChefMate</h1>", unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 20px; font-weight: bold; color: #86AB89;">Your Smart Recipe & Chat Assistant</p>', unsafe_allow_html=True)

    # Load API Keys
    try:
        spoonacular_key, gemini_key = load_api_keys()
        genai.configure(api_key=gemini_key)
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=gemini_key)
    except Exception as e:
        st.error(f"Error loading API keys: {e}")
        return

    # Ingredient Input
    st.markdown('<p style="text-align: center; font-size: 20px; font-weight: bold; color: #86AB89;">🍅 What is in your fridge?</p>', unsafe_allow_html=True)
    ingredients = st.text_input("List your ingredients (e.g., 'chicken, tomato, potato')", placeholder="Type your ingredients...")
    meal_type = st.selectbox("What type of meal are you planning?", ["Breakfast", "Lunch", "Dinner", "Snack", "Drink"])

    if st.button("🍲 Get Meal Ideas"):
        with st.spinner("Fetching meal ideas... 🍳"):
            spoonacular_recipes = get_meal_ideas(ingredients, meal_type, spoonacular_key)

        if isinstance(spoonacular_recipes, dict) and "error" in spoonacular_recipes:
            st.error(f"Spoonacular Error: {spoonacular_recipes['error']}")
        elif not spoonacular_recipes:
            st.warning(f"No {meal_type.lower()} meal ideas found! Try adding more ingredients.")
        else:
            st.markdown(f"## 🍽️ {meal_type} Meal Suggestions")
            for recipe in spoonacular_recipes:
                st.write(f"**{recipe.get('title', 'No title')}**")
                st.image(recipe.get("image", ""), width=200)
                st.write(f"Ingredients: {', '.join([i['name'] for i in recipe.get('extendedIngredients', [])])}")
                st.write(f"[Full Recipe]({recipe.get('sourceUrl', '#')})")

    if st.button("🎉 Surprise Me!"):
        with st.spinner("Fetching a surprise meal... 🍳"):
            surprise_recipes = get_meal_ideas('', 'any', spoonacular_key)
            if surprise_recipes:
                random_recipe = random.choice(surprise_recipes)
                st.markdown(f"## 🎉 Surprise Meal")
                st.write(f"**{random_recipe.get('title', 'No title')}**")
                st.image(random_recipe.get("image", ""), width=200)
                st.write(f"Ingredients: {', '.join([i['name'] for i in random_recipe.get('extendedIngredients', [])])}")
                st.write(f"[Full Recipe]({random_recipe.get('sourceUrl', '#')})")

    display_memory()

# --- Main Execution ---
if __name__ == "__main__":
    create_meal_planner_with_categories()
