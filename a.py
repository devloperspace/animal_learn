import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from gtts import gTTS
import base64
import mysql.connector
import speech_recognition as sr
from groq import Groq
from PIL import Image
import matplotlib.pyplot as plt

# Constants and Paths
DATASET_PATH = "animal_dataset.csv"
DATA_FILE_PATH = "animal_data.csv"
MYSQL_CONFIG = {
    "host": '127.0.0.1',
    "user": 'root',
    "password": '9545883002@Sj',
    "database": 'customer'
}

# Load dataset
animal_data = pd.read_csv(DATASET_PATH)

# Utility Functions
def get_animal_details(category):
    """Fetch animals and details based on category."""
    return animal_data[animal_data["animal_category"].str.lower() == category.lower()]

def fetch_characteristics(animal, number_char):
    """Fetch animal characteristics using Groq API."""
    client = Groq(api_key="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")
    try:
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": f"""You are an expert teacher for children below age 5, to teach them characteristics for animal 
                Please describe {number_char} of {animal} in a numbered list. each characteristics in 5-6 words."""
            }],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content.split("\n")
    except Exception as e:
        st.error(f"Error fetching characteristics: {e}")
        return []

def generate_audio(text):
    """Generate audio from text and return base64 string."""
    try:
        tts = gTTS(text, lang="en")
        audio_file_path = "temp_audio.mp3"
        tts.save(audio_file_path)

        # Read and encode the audio file to base64
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
            b64_audio = base64.b64encode(audio_bytes).decode()

        os.remove(audio_file_path)
        return b64_audio
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

def update_mysql_table(animal_name, is_correct, category):
    """Insert new entry into MySQL table with animal performance data."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS animal_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                animal_name VARCHAR(255),
                category VARCHAR(255),
                attempt INT DEFAULT 0,
                correct INT DEFAULT 0,
                incorrect INT DEFAULT 0,
                timestamps TEXT,
                dates TEXT
            )
        """)

        current_timestamp = datetime.now().timestamp()
        current_date = datetime.now().date()

        # Always insert a new record
        cursor.execute("""
            INSERT INTO animal_data (animal_name, category, attempt, correct, incorrect, timestamps, dates)
            VALUES (%s, %s, 1, %s, %s, %s, %s)
        """, (animal_name, category, 1 if is_correct else 0, 0 if is_correct else 1, current_timestamp, current_date))

        conn.commit()
    except mysql.connector.Error as e:
        st.error(f"Error inserting data into MySQL table: {e}")
    finally:
        cursor.close()
        conn.close()

def recognize_speech():
    """Recognize speech using microphone input."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Please say the animal's name.")
        audio_data = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio_data).lower()
        except (sr.UnknownValueError, sr.RequestError) as e:
            st.error("Could not understand or request failed. Please try again.")
            return None

# Pages
def home_page():
    st.title("Animal Sounds Learning Application")
    st.subheader("Choose a Category:")
    categories = ["Farm Animal", "Sea Creature", "Bird", "Wild Animal", "Jungle Animal"]
    for i, category in enumerate(categories):
        if st.button(category):
            st.session_state.selected_category = category.lower()
            st.session_state.page_index = i + 1
            break

def animal_page(category):
    """Display animal page with selected category."""
    st.title(f"{category} Animals")
    animals = get_animal_details(category)
    if animals.empty:
        st.error(f"No {category.lower()} found in the dataset.")
        return

    animal_names = animals["animal_name"].tolist()
    selected_animal_name = st.selectbox("Select an Animal:", animal_names)
    selected_animal = animals[animals["animal_name"] == selected_animal_name].iloc[0]

    try:
        st.image(selected_animal["url"], caption=selected_animal["animal_name"])
    except Exception:
        st.error(f"Failed to load image for {selected_animal_name}.")

    if st.button("Play Sound"):
        b64_audio = generate_audio(selected_animal_name)
        if b64_audio:
            st.markdown(f'<audio autoplay style="display:none;"><source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3"></audio>', unsafe_allow_html=True)

    if st.button(f"Try Saying Here"):
        recognized_text = recognize_speech()
        if recognized_text:
            is_correct = recognized_text == selected_animal_name.lower()
            st.session_state.test_attempts.append({"animal": selected_animal_name, "recognized_text": recognized_text, "is_correct": is_correct})

            if is_correct:
                st.success(f"Correct! You said '{selected_animal_name}'.")
            else:
                st.error(f"Incorrect. You said '{recognized_text}'. Try again.")

            update_mysql_table(selected_animal_name, is_correct, category)
            
    num_characteristics = st.selectbox("Select number of characteristics to display:", list(range(1, 21)))
    st.session_state.num_characteristics = num_characteristics

    st.subheader(f"{selected_animal_name} Characteristics:")
    characteristics = fetch_characteristics(selected_animal_name, num_characteristics)
    if characteristics:
        for char in characteristics:
            st.write(char)
    else:
        st.error("Failed to fetch characteristics. Please try again.")

def load_data_from_mysql():
    try:
        # Establish the connection
        conn = mysql.connector.connect(
            **MYSQL_CONFIG
        )
        query = "SELECT animal_name, category, attempt, correct, incorrect, timestamps, dates FROM animal_data"
        df = pd.read_sql(query, conn)

        return df

    except mysql.connector.Error as e:
        st.error(f"Error fetching data from MySQL: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

    finally:
        if conn:
            conn.close()
def dashboard_page():
    st.title("Learning Dashboard")

    # Load data from MySQL or mock data
    df = load_data_from_mysql()  # Replace this with your actual loading function
    if df.empty:
        st.warning("No data available.")
        return

    # Sidebar filters for category and animal name
    st.sidebar.header("Filters")
    categories = df['category'].unique()
    selected_category = st.sidebar.selectbox("Select Category", ["All"] + list(categories))
    
    if selected_category != "All":
        df = df[df['category'] == selected_category]

    animal_names = df['animal_name'].unique()
    selected_animal = st.sidebar.selectbox("Select Animal", ["All"] + list(animal_names))
    
    if selected_animal != "All":
        df = df[df['animal_name'] == selected_animal]

    # Overall summary stats
    total_attempts = df['attempt'].sum()
    total_correct = df['correct'].sum()
    total_incorrect = df['incorrect'].sum()

    # Row-wise layout
    col1, col2 = st.columns(2)

    # Bar chart of attempts over animals
    with col1:
        st.subheader("Attempts Over Animal Name")
        bar_chart_data = df.groupby('animal_name')[['attempt', 'correct', 'incorrect']].sum().reset_index()
        fig = px.bar(bar_chart_data, x='animal_name', y=['correct', 'incorrect', 'attempt'], barmode='stack', 
                     labels={'value': 'Count', 'animal_name': 'Animal Name'}, title="Attempts per Animal")
        st.plotly_chart(fig)

    # Pie chart of correct vs incorrect
    with col2:
        st.subheader("Correct Vs Incorrect")
        pie_data = pd.DataFrame({
            "Metric": ["Correct", "Incorrect"],
            "Count": [total_correct, total_incorrect]
        })
        fig = px.pie(pie_data, values="Count", names="Metric", title="Correct vs Incorrect Distribution")
        st.plotly_chart(fig)

    # Line chart for trends over time
    st.subheader("Trends in Attempts Over dates")
    trend_data = df.groupby('dates')[['attempt', 'correct', 'incorrect']].sum().reset_index()
    fig = px.line(trend_data, x='dates', y=['attempt', 'correct', 'incorrect'], 
                  labels={'value': 'Count', 'dates': 'Day'}, title="Daily Trends")
    st.plotly_chart(fig)



    st.title("Learning Dashboard")

    # Load data from MySQL
    df = load_data_from_mysql()  # Assuming this function loads the relevant data

    if df.empty:
        st.warning("No data available.")
        return

    # Split screen into two columns
    col1, col2 = st.columns(2)

    # Left column - Pie chart
    with col1:
        st.header("Animal Distribution")
        # Pie chart of the categories
        category_counts = df['category'].value_counts()
        fig = px.pie(names=category_counts.index, values=category_counts.values, title="Animal Categories")
        st.plotly_chart(fig)

    # Right column - Animal Category selection
    with col2:
        st.header("Select Animal Category")
        # Dropdown to select animal category
        selected_category = st.selectbox("Choose an Animal Category", df['category'].unique())
        
        # Filter the DataFrame based on selected category
        filtered_df = df[df['category'] == selected_category]
        
        st.write(f"Showing animals for category: {selected_category}")
        st.dataframe(filtered_df)

        # Generate and display the statistics (number of attempts, correct, incorrect)
        attempts = filtered_df['attempt'].sum()
        correct = filtered_df['correct'].sum()
        incorrect = filtered_df['incorrect'].sum()

        st.subheader("Category Report")
        st.write(f"Total Attempts: {attempts}")
        st.write(f"Correct: {correct}")
        st.write(f"Incorrect: {incorrect}")
        
        # Optionally, you can show a bar chart to visualize the numbers
        report_data = {'Attempts': attempts, 'Correct': correct, 'Incorrect': incorrect}
        report_df = pd.DataFrame(list(report_data.items()), columns=["Metric", "Value"])
        st.bar_chart(report_df.set_index('Metric'))
# Session State Initialization
if "page_index" not in st.session_state:
    st.session_state.page_index = 0  # Home page
if "test_attempts" not in st.session_state:
    st.session_state.test_attempts = []

# Pages List
pages = [
    home_page,  # Home Page
    lambda: animal_page("Farm Animals"),
    lambda: animal_page("Sea Creatures"),
    lambda: animal_page("Bird"),
    lambda: animal_page("Wild Animal"),
    lambda: animal_page("Jungle Animal"),
    dashboard_page
]

# Display Page
pages[st.session_state.page_index]()

# Navigation
if st.session_state.page_index == 0 and st.button("Go to Dashboard"):
    st.session_state.page_index = 6
elif st.session_state.page_index > 0 and st.button("Back to Home"):
    st.session_state.page_index = 0
