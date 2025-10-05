import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import json
import time
import re # Import the regular expressions module

# Load environment variables
load_dotenv()

# Import your LangChain logic
from backend.chains import (
    get_restaurant_analysis_chain, get_chatbot_response,
    get_dish_recommendation, get_slogan_generation
)

app = Flask(__name__)
# Renaming the app to avoid conflict with the file name
app.name = 'app_backend' 
CORS(app, resources={r"/*": {"origins": "*"}}) # Allow all origins for development

def clean_json_response(text):
    """
    Cleans the raw text output from the LLM to extract a valid JSON string.
    It removes markdown code fences and any leading/trailing whitespace.
    """
    # Use regex to find the content between ```json and ```
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    # Fallback for cases where there are no fences but maybe extra text
    return text.strip()

@app.route('/analyze', methods=['POST'])
def analyze_restaurant():
    """
    API endpoint for initial restaurant analysis.
    """
    try:
        data = request.json
        restaurant_name = data.get('restaurant_name')
        analysis_type = data.get('analysis_type')
        restaurant_location = data.get('restaurant_location')

        if not restaurant_name or not analysis_type:
            return jsonify({"error": "Missing 'restaurant_name' or 'analysis_type'"}), 400

        restaurant_location_context = f"located in {restaurant_location}" if restaurant_location else ""

        analysis_chain = get_restaurant_analysis_chain()

        chain_input = {
            "input": restaurant_name,
            "analysis_type": analysis_type,
            "restaurant_location_context": restaurant_location_context
        }
        
        print(f"[{time.ctime()}] Starting LLM analysis for: {restaurant_name}, type: {analysis_type}, location: {restaurant_location}")
        start_time = time.time()

        response = analysis_chain.invoke(chain_input)
        
        # In LCEL, the output of a chain like (prompt | llm) is the AIMessage content
        response_content = response.content 

        end_time = time.time()
        print(f"[{time.ctime()}] LLM analysis completed in {end_time - start_time:.2f} seconds.")

        # Clean the JSON before parsing
        cleaned_json_string = clean_json_response(response_content)

        try:
            parsed_analysis = json.loads(cleaned_json_string)
        except json.JSONDecodeError as e:
            print(f"Warning: AI did not return valid JSON after cleaning. Error: {e}. Cleaned content: {cleaned_json_string}")
            return jsonify({"error": f"Failed to parse AI response. Raw content: {response_content}"}), 500

        return jsonify(parsed_analysis), 200

    except Exception as e:
        print(f"[{time.ctime()}] Error in /analyze: {e}")
        # Pass a more user-friendly error message for quota issues
        error_message = str(e)
        if "quota" in error_message.lower():
             error_message = "You have exceeded the API quota. This is a limit on the free tier of the Google AI API. Please check your Google Cloud project's billing status or try again later."
        return jsonify({"error": error_message}), 500


@app.route('/chatbot', methods=['POST'])
def chatbot_query():
    """
    API endpoint for chatbot follow-up questions.
    """
    try:
        data = request.json
        analysis_text_raw = data.get('analysis_text_raw')
        user_question = data.get('user_question')

        if not analysis_text_raw or not user_question:
            return jsonify({"error": "Missing 'analysis_text_raw' or 'user_question'"}), 400

        print(f"[{time.ctime()}] Starting chatbot query for user: '{user_question}'")
        start_time = time.time()

        bot_response = get_chatbot_response(analysis_text_raw, user_question)

        end_time = time.time()
        print(f"[{time.ctime()}] Chatbot query completed.")

        return jsonify({"response": bot_response}), 200

    except Exception as e:
        print(f"[{time.ctime()}] Error in /chatbot: {e}")
        error_message = str(e)
        if "quota" in error_message.lower():
             error_message = "You have exceeded the API quota for the chatbot. Please try again later."
        return jsonify({"error": error_message}), 500

# The following endpoints are kept for potential future use but are not active in the current frontend
@app.route('/recommend_dishes', methods=['POST'])
def recommend_dishes():
    try:
        data = request.json
        analysis_text_raw = data.get('analysis_text_raw')
        recommendations = get_dish_recommendation(analysis_text_raw)
        return jsonify({"recommendations": recommendations}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_slogan', methods=['POST'])
def generate_slogan():
    try:
        data = request.json
        analysis_text_raw = data.get('analysis_text_raw')
        slogan = get_slogan_generation(analysis_text_raw)
        return jsonify({"slogan": slogan}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=8888)

