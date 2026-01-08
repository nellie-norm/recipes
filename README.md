# what are you cooking up? 🍳

A recipe tool that extracts the actual recipe from URLs (skipping the life story), with scaling and unit conversion.

## Features

- **URL scraping** — extracts recipes from 400+ sites via JSON-LD schema and [recipe-scrapers](https://github.com/hhursev/recipe-scrapers)
- **Smart parsing** — handles fractions (½, ¾), ranges (1-2 cups), and cleans up note cruft
- **Scaling** — halve, double, triple, or use any multiplier (always from original, no compounding errors)
- **Unit conversion** — switch between metric and imperial, with a reset to original
- **Clean output** — filters out section headers and notes, keeps the useful stuff

## Quick start

```bash
# Clone
git clone https://github.com/nellie-norm/recipes.git
cd recipes

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the API
python app.py

# In another terminal, serve the frontend
python -m http.server 8080
```

Open http://localhost:8080, paste a recipe URL, done.

## Usage

### Web UI

1. Paste a recipe URL
2. Click **Extract**
3. Use buttons to scale (½×, 2×, 3×) or convert units (Metric/Imperial)
4. **1× (reset)** returns to original quantities

### CLI

```bash
python recipe_cli.py
```

### As a library

```python
from recipe_tool import RecipeScraper

scraper = RecipeScraper()
recipe = scraper.scrape("https://www.recipetineats.com/pavlova-bombs/")

print(recipe)
print(recipe.halve())
print(recipe.convert_to_metric())
print(recipe.to_json())
```

## Files

| File | Description |
|------|-------------|
| `recipe_tool.py` | Core scraper, parser, and Recipe/Ingredient classes |
| `app.py` | Flask API backend |
| `index.html` | React frontend |
| `recipe_cli.py` | Interactive command-line interface |
| `requirements.txt` | Python dependencies |

## Supported sites

Works with any site using Schema.org Recipe markup, including:

- AllRecipes
- BBC Good Food  
- RecipeTin Eats
- Serious Eats
- Bon Appétit
- Ottolenghi
- NY Times Cooking
- And [many more](https://github.com/hhursev/recipe-scrapers#scrapers-available-for)...

## Known limitations

- **Instructions aren't scaled** — quantities mentioned in instruction text (e.g., "makes 5 domes") stay as-is. A note appears when scaling.
- **Some sites are weird** — if a site has non-standard markup, parsing may be incomplete

## License

MIT