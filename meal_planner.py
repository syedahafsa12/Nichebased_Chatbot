# --- Required Libraries ---
import os
import streamlit as st
from dotenv import load_dotenv
import requests
from datetime import datetime
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Custom CSS for Modern Chatbot-Like UI ---
def add_custom_css():
    st.markdown(
        """
        <style>
        body {
            background: linear-gradient(to bottom, #232526, #414345);
            # font-family: "Arial", sans-serif;
            color: #FFFFFF;
        }
        h1, h2 {
            text-align: center;
            color: #86AB89;
        },
        p{
         text-align: center !important;
        },
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
        # st.success("✅ Using Streamlit Secrets API keys.")
    except Exception:
        pass

    # if not spoonacular_key or not gemini_key:
    #     load_dotenv()
    #     spoonacular_key = os.getenv("SPOONACULAR_API_KEY")
    #     gemini_key = os.getenv("GEMINI_API_KEY")
    #     if spoonacular_key and gemini_key:
    #         st.success("✅ Using .env API keys.")

    if not spoonacular_key or not gemini_key:
        st.error("🚨 API keys not found! Add them to Streamlit Secrets or .env file.")
        raise ValueError("🚨 API keys not found! Add them to Streamlit Secrets or .env file.")
    
    return spoonacular_key, gemini_key

# --- Spoonacular API Call ---
def get_meal_ideas(ingredients, meal_type, api_key):
    """Call the Spoonacular API to get meal ideas."""
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "query": meal_type,
        "includeIngredients": ingredients,
        "number": 10,  # Fetch up to 10 recipes
        "apiKey": api_key,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        recipes = response.json().get("results", [])

        # Fetch recipe details to confirm ingredient match
        detailed_recipes = []
        for recipe in recipes:
            recipe_id = recipe.get("id")
            details = get_recipe_details(recipe_id, api_key)
            if details and ingredients.lower() in str(details.get("extendedIngredients", "")).lower():
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
    st.markdown(<p>"##### 💬 Conversation History"</p>)
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
    st.markdown(<p>"##### Your Smart Recipe & Chat Assistant"</p>)

    # Load API Keys
    try:
        spoonacular_key, gemini_key = load_api_keys()
        genai.configure(api_key=gemini_key)
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=gemini_key)
    except Exception as e:
        st.error(f"Error loading API keys: {e}")
        return

    # Ingredient Input
    st.write(<p>"#####🍅 What is in your fridge?"</p>)
    ingredients = st.text_input("List your ingredients (e.g., 'chicken, tomato, potato')", placeholder="Type your ingredients...")
    meal_type = st.selectbox("What type of meal are you planning?", ["Breakfast", "Lunch", "Dinner", "Snack"])

    if st.button("🍲 Get Meal Ideas"):
        with st.spinner("Fetching meal ideas... 🍳"):
            spoonacular_recipes = get_meal_ideas(ingredients, meal_type, spoonacular_key)

        # Display Meal Results
        if isinstance(spoonacular_recipes, dict) and "error" in spoonacular_recipes:
            st.error(f"Spoonacular Error: {spoonacular_recipes['error']}")
            bot_response = "Sorry, I couldn't fetch meal ideas right now. Try again later!"
        elif not spoonacular_recipes:
            st.warning(f"No {meal_type.lower()} meal ideas found! Try adding more ingredients.")
            bot_response = f"I couldn't find any {meal_type.lower()} meal ideas based on those ingredients."
        else:
            st.markdown(f"## 🍽️ {meal_type} Meal Suggestions")
            bot_response = f"Here are some {meal_type.lower()} meal ideas based on your ingredients:"
            for recipe in spoonacular_recipes:
                st.write(f"**{recipe.get('title', 'No title')}**")
                st.image(recipe.get("image", ""), width=200)
                st.write(f"Ingredients: {', '.join([i['name'] for i in recipe.get('extendedIngredients', [])])}")
                st.write(f"[Full Recipe]({recipe.get('sourceUrl', '#')})")

        add_to_memory(f"Ingredients: {ingredients}, Meal Type: {meal_type}", bot_response)

    # Chat Box
    st.markdown(<p>"##### 💬 Ask me anything!"</p>)
    user_input = st.text_input("You:", placeholder="Ask me about meals, ingredients, or anything else...")
    if user_input:
        # Use Chat Memory Context
        context = "\n".join(
            [f"You: {chat['user']}\nBot: {chat['bot']}" for chat in st.session_state.get("history", [])]
        )
        full_input = f"{context}\nYou: {user_input}\nBot:"
        response = llm.invoke(full_input)
        bot_response = response.content

        st.write(f"🤖 **Bot:** {bot_response}")
        add_to_memory(user_input, bot_response)

    # Display Conversation History
    display_memory()

# --- Main Execution ---
if __name__ == "__main__":
    create_meal_planner_with_categories()
