#!/usr/bin/env python3
"""
Recipe API - Flask backend for the recipe tool
"""

import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from recipe_tool import RecipeScraper, Recipe, Ingredient

app = Flask(__name__)
CORS(app)  # Allow React frontend to call this

scraper = RecipeScraper()

# Store current recipe in memory (simple for now)
current_recipe = None

# Anthropic API key from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


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


@app.route('/api/extract-image', methods=['POST'])
def extract_from_image():
    """Extract recipe from an uploaded image using Claude."""
    global current_recipe
    
    if not ANTHROPIC_API_KEY:
        return jsonify({'error': 'ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=your-key'}), 500
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    image_file = request.files['image']
    image_data = base64.standard_b64encode(image_file.read()).decode('utf-8')
    
    # Determine media type
    content_type = image_file.content_type or 'image/jpeg'
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": """Extract the recipe from this image. Return ONLY valid JSON in this exact format, no other text:

{
  "name": "Recipe Name",
  "servings": 4,
  "prep_time": "15m",
  "cook_time": "30m",
  "ingredients": [
    {"quantity": 2, "unit": "cups", "item": "flour"},
    {"quantity": 1, "unit": "tsp", "item": "salt"},
    {"quantity": null, "unit": null, "item": "fresh herbs"}
  ],
  "instructions": [
    "First step here.",
    "Second step here."
  ]
}

Rules:
- quantity should be a number or null if not specified
- unit should be a string or null if not specified (e.g., "2 eggs" has no unit)
- Extract ALL ingredients and ALL instructions visible
- Use lowercase units: cups, tbsp, tsp, oz, g, ml, etc.
- Return ONLY the JSON, no markdown code blocks, no explanation"""
                        }
                    ],
                }
            ],
        )
        
        # Parse Claude's response
        response_text = message.content[0].text.strip()
        
        # Try to extract JSON if wrapped in code blocks
        if '```' in response_text:
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)
        
        import json
        recipe_data = json.loads(response_text)
        
        # Convert to Recipe object
        ingredients = []
        for ing in recipe_data.get('ingredients', []):
            ingredients.append(Ingredient(
                quantity=ing.get('quantity'),
                unit=ing.get('unit'),
                item=ing.get('item', ''),
                original_text=''
            ))
        
        current_recipe = Recipe(
            name=recipe_data.get('name', 'Untitled Recipe'),
            servings=recipe_data.get('servings'),
            prep_time=recipe_data.get('prep_time'),
            cook_time=recipe_data.get('cook_time'),
            ingredients=ingredients,
            instructions=recipe_data.get('instructions', []),
            source_url=None
        )
        
        return jsonify(current_recipe.to_dict())
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse recipe from image: {str(e)}'}), 500
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
    if not ANTHROPIC_API_KEY:
        print("⚠️  Warning: ANTHROPIC_API_KEY not set. Image extraction won't work.")
        print("   Run: export ANTHROPIC_API_KEY=your-key")
    print("🍳 Recipe API running at http://localhost:5001")
    app.run(debug=True, port=5001)