#!/usr/bin/env python3
"""
Recipe API - Flask backend for the recipe tool
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from recipe_tool import RecipeScraper, Recipe, Ingredient

app = Flask(__name__)
CORS(app)  # Allow React frontend to call this

scraper = RecipeScraper()

# Store current recipe in memory (simple for now)
current_recipe = None


@app.route('/api/scrape', methods=['POST'])
def scrape_recipe():
    """Scrape a recipe from a URL."""
    global current_recipe
    
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        current_recipe = scraper.scrape(url)
        return jsonify(current_recipe.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scale', methods=['POST'])
def scale_recipe():
    """Scale the current recipe."""
    global current_recipe
    
    if not current_recipe:
        return jsonify({'error': 'No recipe loaded'}), 400
    
    data = request.json
    factor = data.get('factor', 1)
    
    try:
        factor = float(factor)
        current_recipe = current_recipe.scale(factor)
        return jsonify(current_recipe.to_dict())
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid scale factor'}), 400


@app.route('/api/convert', methods=['POST'])
def convert_recipe():
    """Convert recipe units."""
    global current_recipe
    
    if not current_recipe:
        return jsonify({'error': 'No recipe loaded'}), 400
    
    data = request.json
    system = data.get('system', 'metric')
    
    if system == 'metric':
        current_recipe = current_recipe.convert_to_metric()
    else:
        current_recipe = current_recipe.convert_to_imperial()
    
    return jsonify(current_recipe.to_dict())


@app.route('/api/recipe', methods=['GET'])
def get_recipe():
    """Get the current recipe."""
    if not current_recipe:
        return jsonify({'error': 'No recipe loaded'}), 404
    return jsonify(current_recipe.to_dict())


if __name__ == '__main__':
    print("🍳 Recipe API running at http://localhost:5001")
    app.run(debug=True, port=5001)