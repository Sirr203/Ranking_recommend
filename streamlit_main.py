import streamlit as st
import openpyxl
import pandas as pd
import numpy as np
import math

# Configuration for Pandas display options
pd.set_option('display.width', 1000)
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)

@st.cache_data
def load_data(excel_file):
    """Loads data from the Excel file and caches it."""
    excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
    df = pd.concat(excel_data.values(), ignore_index=True)
    return df

def recommend_food(df, calories_prompt_per100=None, ingredient_prompt=None, user_type_prompt=None, taste_prompt=None, 
                  negative_prompt=None, top_n=5, desired_calories=None,
                  prioritize_ingredient=False, prioritize_user_type=False, prioritize_taste=False):
    """
    Recommends food from a DataFrame, sorted by score, randomized within the highest score group, and calculates serving size.
    Now with prioritization feature that can increase the score for certain criteria.
    """
    df['Ranking Score'] = 0

    if calories_prompt_per100 is not None:
        calories_first_digit_prompt = str(int(calories_prompt_per100)).split('.')[0][0]
        df['Calories/Serving_str_first_digit'] = df['Calories/Serving'].astype(str).str[0]
        df = df[df['Calories/Serving_str_first_digit'] == calories_first_digit_prompt]
        df = df.drop(columns=['Calories/Serving_str_first_digit'])

    # For each preference, add either 1 or 2 points based on prioritization
    if ingredient_prompt:
        ingredients = [ing.strip().lower() for ing in ingredient_prompt.split(',')]
        score_increment = 2 if prioritize_ingredient else 1
        for ingredient in ingredients:
            df.loc[df['Ingredients'].str.lower().str.contains(ingredient, na=False), 'Ranking Score'] += score_increment

    if user_type_prompt:
        user_types = [ut.strip().lower() for ut in user_type_prompt.split(',')]
        score_increment = 2 if prioritize_user_type else 1
        for user_type in user_types:
            df.loc[df['User type'].str.lower().str.contains(user_type, na=False), 'Ranking Score'] += score_increment

    if taste_prompt:
        tastes = [t.strip().lower() for t in taste_prompt.split(',')]
        score_increment = 2 if prioritize_taste else 1
        for taste in tastes:
            df.loc[df['Taste'].str.lower().str.contains(taste, na=False), 'Ranking Score'] += score_increment
    else:
        tastes = []

    if negative_prompt:
        if 'Ingredient' in negative_prompt and negative_prompt['Ingredient']:
            neg_ingredients = [ing.strip().lower() for ing in negative_prompt['Ingredient'].split(',')]
            for neg_ingredient in neg_ingredients:
                df = df[~df['Ingredients'].str.lower().str.contains(neg_ingredient, na=False)]
        if 'User Type' in negative_prompt and negative_prompt['User Type']:
            neg_user_types = [ut.strip().lower() for ut in negative_prompt['User Type'].split(',')]
            for neg_user_type in neg_user_types:
                df = df[~df['User type'].str.lower().str.contains(neg_user_type, na=False)]
        if 'Taste' in negative_prompt and negative_prompt['Taste']:
            neg_tastes = [t.strip().lower() for t in negative_prompt['Taste'].split(',')]
            for neg_taste in neg_tastes:
                df = df[~df['Taste'].str.lower().str.contains(neg_taste, na=False)]

    ranked_df = df.sort_values(by='Ranking Score', ascending=False).reset_index(drop=True)
    columns_to_drop = ['No'] + ['Serving'] + ['Calories']
    ranked_df = ranked_df.drop(columns=columns_to_drop, errors='ignore')

    max_score = ranked_df['Ranking Score'].max()
    max_score_group = ranked_df[ranked_df['Ranking Score'] == max_score]
    remaining_df = ranked_df[ranked_df['Ranking Score'] != max_score]

    shuffled_max_score_group = max_score_group.sample(frac=1)

    ranked_df = pd.concat([shuffled_max_score_group, remaining_df]).reset_index(drop=True)

    ranked_df = ranked_df.head(top_n)

    if desired_calories is not None:
        ranked_df['Serving Size (grams)'] = (desired_calories / ranked_df['Calories/Serving']).apply(math.ceil).astype(str) + " gram"

    return ranked_df

# File path for the Excel data
excel_file_path = 'food.xlsx'

# Load data
df = load_data(excel_file_path)

# Streamlit UI
st.title("Food Recommendation App")

# Preferences section
st.header("Preferences")
col1, col2, col3 = st.columns([3, 1, 3])

with col1:
    st.subheader("Include")
    
    # Row for ingredients with star
    ing_col1, ing_col2 = st.columns([4, 1])
    with ing_col1:
        user_ingredient_prompt = st.text_input("Preferred ingredients (e.g., beef, cheese) ")
    with ing_col2:
        prioritize_ingredient = st.checkbox("", key="ing_star", help="Prioritize these ingredients")
    
    # Row for user type with star
    type_col1, type_col2 = st.columns([4, 1])
    with type_col1:
        user_user_type_prompt = st.text_input("Your type (e.g., gain, normal, athlete) ")
    with type_col2:
        prioritize_user_type = st.checkbox("", key="type_star", help="Prioritize this type")
    
    # Row for taste with star
    taste_col1, taste_col2 = st.columns([4, 1])
    with taste_col1:
        user_taste_prompt = st.text_input("Preferred tastes (e.g., rich, sweet) ")
    with taste_col2:
        prioritize_taste = st.checkbox("", key="taste_star", help="Prioritize these tastes")

with col3:
    st.subheader("Exclude (optional)")
    negative_ingredient = st.text_input("Ingredients to avoid (e.g., pork, egg) ")
    negative_user_type = st.text_input("Types to avoid (e.g., losing) ")
    negative_taste = st.text_input("Tastes to avoid (e.g., tender, sweet) ")

# Build negative_prompt dictionary with all three categories
user_negative_prompt = {}
if negative_ingredient:
    user_negative_prompt['Ingredient'] = negative_ingredient
if negative_user_type:
    user_negative_prompt['User Type'] = negative_user_type
if negative_taste:
    user_negative_prompt['Taste'] = negative_taste

# Set to None if empty
if not user_negative_prompt:
    user_negative_prompt = None

# Additional options
st.header("Additional Options")
user_desired_calories = st.number_input("Desired calories per serving ", value=None, min_value=0, format="%d")

if st.button("Recommend food"):
    recommended_foods = recommend_food(
        df=df,
        ingredient_prompt=user_ingredient_prompt,
        user_type_prompt=user_user_type_prompt,
        taste_prompt=user_taste_prompt,
        negative_prompt=user_negative_prompt,
        top_n=5,
        desired_calories=user_desired_calories,
        prioritize_ingredient=prioritize_ingredient,
        prioritize_user_type=prioritize_user_type,
        prioritize_taste=prioritize_taste
    )

    # st.write("Recommended Foods:")
    st.dataframe(recommended_foods)
