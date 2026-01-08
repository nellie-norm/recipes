# Recipe Tool 🍳

A Python tool to scrape recipes from URLs, extract the actual recipe (skipping the life story), and manipulate quantities.

## Features

- **URL Scraping** - Extracts recipes from Schema.org JSON-LD markup (works with most major recipe sites)
- **Smart Parsing** - Handles fractions (½, ¾), mixed numbers (1 1/2), and various unit formats
- **Scaling** - Halve, double, triple, or use any custom multiplier
- **Unit Conversion** - Convert between metric and imperial units
- **Clean Output** - Display as formatted text or export to JSON

## Installation

```bash
pip install requests beautifulsoup4
```

## Quick Start

### As a Library

```python
from recipe_tool import RecipeScraper

# Scrape a recipe
scraper = RecipeScraper()
recipe = scraper.scrape("https://www.allrecipes.com/recipe/...")

# Display it
print(recipe)

# Scale it
half = recipe.halve()
doubled = recipe.double()
custom = recipe.scale(1.5)  # 1.5x

# Convert units
metric = recipe.convert_to_metric()
imperial = recipe.convert_to_imperial()

# Export
json_str = recipe.to_json()
recipe_dict = recipe.to_dict()
```

### Interactive CLI

```bash
python recipe_cli.py
```

Then paste a recipe URL and use the menu to manipulate the recipe.

## Supported Sites

Works with any site using Schema.org Recipe markup, including:
- AllRecipes
- BBC Good Food
- Food Network
- Serious Eats
- Bon Appétit
- NY Times Cooking
- And many more...

## Example Output

```
==================================================
Classic Chocolate Chip Cookies
==================================================
Servings: 24
Prep Time: 15m
Cook Time: 10m

──────────────────────────────
INGREDIENTS
──────────────────────────────
  • 2 1/4 cups all-purpose flour
  • 1 tsp baking soda
  • 1 cup butter, softened
  • 3/4 cup sugar
  • 2 large eggs
  • 2 cups chocolate chips

──────────────────────────────
INSTRUCTIONS
──────────────────────────────
  1. Preheat oven to 375°F.
  2. Mix flour and baking soda.
  ...
```

## API Reference

### `Recipe` class

| Method | Description |
|--------|-------------|
| `scale(factor)` | Scale by any multiplier |
| `halve()` | Divide by 2 |
| `double()` | Multiply by 2 |
| `triple()` | Multiply by 3 |
| `convert_to_metric()` | Convert to ml/g |
| `convert_to_imperial()` | Convert to cups/oz |
| `to_json()` | Export as JSON string |
| `to_dict()` | Export as dictionary |

### `Ingredient` class

| Method | Description |
|--------|-------------|
| `scale(factor)` | Scale quantity |
| `convert_unit(target)` | Convert to specific unit |

## Next Steps

Ideas for extending this tool:
1. **Add photo support** - Use Claude's Vision API to extract recipes from images
2. **Browser extension** - One-click extraction on any recipe page
3. **Recipe database** - Save and organize scraped recipes
4. **Shopping list** - Combine ingredients from multiple recipes
5. **Nutrition info** - Calculate calories and macros