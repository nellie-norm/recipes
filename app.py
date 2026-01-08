#!/usr/bin/env python3
"""
Recipe API - Flask backend for the recipe tool
"""

import os
import re
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from recipe_tool import RecipeScraper, Recipe, Ingredient

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Allow React frontend to call this


@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

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
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)
        
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


@app.route('/api/shopping-list', methods=['POST'])
def create_shopping_list():
    """Extract ingredients from multiple images and consolidate into a shopping list."""
    
    if not ANTHROPIC_API_KEY:
        return jsonify({'error': 'ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=your-key'}), 500
    
    images = request.files.getlist('images')
    
    if len(images) < 1:
        return jsonify({'error': 'Please upload at least one image'}), 400
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        all_ingredients = []
        
        # Extract ingredients from each image
        for image_file in images:
            image_data = base64.standard_b64encode(image_file.read()).decode('utf-8')
            content_type = image_file.content_type or 'image/jpeg'
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
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
                                "text": """Extract ONLY the ingredients from this recipe image. Return ONLY valid JSON array, no other text:

[
  {"quantity": 2, "unit": "cups", "item": "flour"},
  {"quantity": 1, "unit": "tsp", "item": "salt"},
  {"quantity": null, "unit": null, "item": "fresh herbs"}
]

Rules:
- quantity should be a number or null if not specified
- unit should be a lowercase string or null (cups, tbsp, tsp, oz, g, ml, etc.)
- item should be the ingredient name, normalized (e.g., "onion" not "onions, diced")
- Return ONLY the JSON array, no markdown, no explanation"""
                            }
                        ],
                    }
                ],
            )
            
            response_text = message.content[0].text.strip()
            
            # Try to extract JSON if wrapped in code blocks
            if '```' in response_text:
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    response_text = json_match.group(1)
            
            ingredients = json.loads(response_text)
            all_ingredients.extend(ingredients)
        
        # Consolidate ingredients
        consolidated = consolidate_ingredients(all_ingredients)
        
        return jsonify({'ingredients': consolidated})
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse ingredients: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def consolidate_ingredients(ingredients):
    """Combine duplicate ingredients, adding quantities where possible."""
    from collections import defaultdict
    
    # Group by normalized item name + unit
    groups = defaultdict(list)
    
    for ing in ingredients:
        item = ing.get('item', '').lower().strip()
        unit = (ing.get('unit') or '').lower().strip()
        
        # Normalize common variations
        item = item.rstrip('s') if item.endswith('s') and not item.endswith('ss') else item
        
        key = (item, unit)
        groups[key].append(ing)
    
    # Combine quantities
    result = []
    for (item, unit), group in groups.items():
        total_qty = None
        has_qty = False
        
        for ing in group:
            qty = ing.get('quantity')
            if qty is not None:
                has_qty = True
                if total_qty is None:
                    total_qty = 0
                total_qty += qty
        
        # Use original case from first occurrence
        original_item = group[0].get('item', item)
        original_unit = group[0].get('unit', unit) if unit else None
        
        result.append({
            'quantity': total_qty if has_qty else None,
            'unit': original_unit,
            'item': original_item
        })
    
    # Sort by item name
    result.sort(key=lambda x: x.get('item', '').lower())
    
    return result


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
    port = int(os.environ.get('PORT', 5001))
    print(f"🍳 Recipe API running at http://localhost:{port}")
    app.run(debug=True, port=port, host='0.0.0.0')