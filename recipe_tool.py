#!/usr/bin/env python3
"""
Recipe Tool - Scrape, scale, and convert recipes
"""

import json
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional
import requests
from bs4 import BeautifulSoup

# Optional: recipe-scrapers for better site coverage
try:
    from recipe_scrapers import scrape_me
    HAS_RECIPE_SCRAPERS = True
except ImportError:
    HAS_RECIPE_SCRAPERS = False

# Unit conversion tables
VOLUME_TO_ML = {
    "ml": 1,
    "milliliter": 1,
    "milliliters": 1,
    "l": 1000,
    "liter": 1000,
    "liters": 1000,
    "tsp": 4.929,
    "teaspoon": 4.929,
    "teaspoons": 4.929,
    "tbsp": 14.787,
    "tablespoon": 14.787,
    "tablespoons": 14.787,
    "cup": 236.588,
    "cups": 236.588,
    "fl oz": 29.574,
    "fluid ounce": 29.574,
    "fluid ounces": 29.574,
    "pint": 473.176,
    "pints": 473.176,
    "quart": 946.353,
    "quarts": 946.353,
    "gallon": 3785.41,
    "gallons": 3785.41,
}

WEIGHT_TO_G = {
    "g": 1,
    "gram": 1,
    "grams": 1,
    "kg": 1000,
    "kilogram": 1000,
    "kilograms": 1000,
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "lb": 453.592,
    "pound": 453.592,
    "pounds": 453.592,
}


@dataclass
class Ingredient:
    """Represents a single ingredient with quantity, unit, and name."""
    quantity: Optional[float]
    unit: Optional[str]
    item: str
    original_text: str = ""
    
    def scale(self, factor: float) -> "Ingredient":
        """Return a new ingredient scaled by the given factor."""
        new_qty = self.quantity * factor if self.quantity else None
        return Ingredient(
            quantity=new_qty,
            unit=self.unit,
            item=self.item,
            original_text=self.original_text
        )
    
    def convert_unit(self, target_unit: str) -> "Ingredient":
        """Convert to a different unit if possible."""
        if not self.quantity or not self.unit:
            return self
        
        source_unit = self.unit.lower()
        target_lower = target_unit.lower()
        
        # Try volume conversion
        if source_unit in VOLUME_TO_ML and target_lower in VOLUME_TO_ML:
            ml = self.quantity * VOLUME_TO_ML[source_unit]
            new_qty = ml / VOLUME_TO_ML[target_lower]
            return Ingredient(
                quantity=round(new_qty, 3),
                unit=target_unit,
                item=self.item,
                original_text=self.original_text
            )
        
        # Try weight conversion
        if source_unit in WEIGHT_TO_G and target_lower in WEIGHT_TO_G:
            grams = self.quantity * WEIGHT_TO_G[source_unit]
            new_qty = grams / WEIGHT_TO_G[target_lower]
            return Ingredient(
                quantity=round(new_qty, 3),
                unit=target_unit,
                item=self.item,
                original_text=self.original_text
            )
        
        # Can't convert
        return self
    
    def __str__(self) -> str:
        if self.quantity is None:
            return self.item
        
        # Format quantity nicely (use fractions for common values)
        qty_str = self._format_quantity(self.quantity)
        
        if self.unit:
            return f"{qty_str} {self.unit} {self.item}"
        return f"{qty_str} {self.item}"
    
    @staticmethod
    def _format_quantity(qty: float) -> str:
        """Format quantity, using fractions when appropriate."""
        if qty == int(qty):
            return str(int(qty))
        
        # Try to represent as a nice fraction
        try:
            frac = Fraction(qty).limit_denominator(8)
            if frac.denominator in [2, 3, 4, 8]:
                if frac.numerator > frac.denominator:
                    whole = frac.numerator // frac.denominator
                    remainder = frac.numerator % frac.denominator
                    if remainder == 0:
                        return str(whole)
                    return f"{whole} {remainder}/{frac.denominator}"
                return f"{frac.numerator}/{frac.denominator}"
        except (ValueError, ZeroDivisionError):
            pass
        
        return f"{qty:.2f}".rstrip('0').rstrip('.')


@dataclass
class Recipe:
    """Represents a complete recipe."""
    name: str
    servings: Optional[int] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    ingredients: list[Ingredient] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    source_url: Optional[str] = None
    
    def scale(self, factor: float) -> "Recipe":
        """Return a new recipe scaled by the given factor."""
        new_servings = int(self.servings * factor) if self.servings else None
        return Recipe(
            name=self.name,
            servings=new_servings,
            prep_time=self.prep_time,
            cook_time=self.cook_time,
            total_time=self.total_time,
            ingredients=[ing.scale(factor) for ing in self.ingredients],
            instructions=self.instructions.copy(),
            source_url=self.source_url
        )
    
    def halve(self) -> "Recipe":
        """Return recipe halved."""
        return self.scale(0.5)
    
    def double(self) -> "Recipe":
        """Return recipe doubled."""
        return self.scale(2.0)
    
    def triple(self) -> "Recipe":
        """Return recipe tripled."""
        return self.scale(3.0)
    
    def convert_to_metric(self) -> "Recipe":
        """Convert all ingredients to metric units where possible."""
        metric_ingredients = []
        for ing in self.ingredients:
            if ing.unit and ing.unit.lower() in VOLUME_TO_ML:
                # Convert volume to ml (or L if large)
                converted = ing.convert_unit("ml")
                if converted.quantity and converted.quantity >= 1000:
                    converted = converted.convert_unit("L")
                metric_ingredients.append(converted)
            elif ing.unit and ing.unit.lower() in WEIGHT_TO_G:
                # Convert weight to grams (or kg if large)
                converted = ing.convert_unit("g")
                if converted.quantity and converted.quantity >= 1000:
                    converted = converted.convert_unit("kg")
                metric_ingredients.append(converted)
            else:
                metric_ingredients.append(ing)
        
        return Recipe(
            name=self.name,
            servings=self.servings,
            prep_time=self.prep_time,
            cook_time=self.cook_time,
            total_time=self.total_time,
            ingredients=metric_ingredients,
            instructions=self.instructions.copy(),
            source_url=self.source_url
        )
    
    def convert_to_imperial(self) -> "Recipe":
        """Convert all ingredients to imperial units where possible."""
        imperial_ingredients = []
        for ing in self.ingredients:
            if ing.unit and ing.unit.lower() in ["ml", "milliliter", "milliliters", "l", "liter", "liters"]:
                converted = ing.convert_unit("cups")
                imperial_ingredients.append(converted)
            elif ing.unit and ing.unit.lower() in ["g", "gram", "grams", "kg", "kilogram", "kilograms"]:
                converted = ing.convert_unit("oz")
                imperial_ingredients.append(converted)
            else:
                imperial_ingredients.append(ing)
        
        return Recipe(
            name=self.name,
            servings=self.servings,
            prep_time=self.prep_time,
            cook_time=self.cook_time,
            total_time=self.total_time,
            ingredients=imperial_ingredients,
            instructions=self.instructions.copy(),
            source_url=self.source_url
        )
    
    def to_dict(self) -> dict:
        """Convert recipe to dictionary."""
        return {
            "name": self.name,
            "servings": self.servings,
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "total_time": self.total_time,
            "ingredients": [
                {"quantity": ing.quantity, "unit": ing.unit, "item": ing.item}
                for ing in self.ingredients
            ],
            "instructions": self.instructions,
            "source_url": self.source_url
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert recipe to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def __str__(self) -> str:
        lines = [f"{'=' * 50}", f"{self.name}", f"{'=' * 50}"]
        
        if self.servings:
            lines.append(f"Servings: {self.servings}")
        if self.prep_time:
            lines.append(f"Prep Time: {self.prep_time}")
        if self.cook_time:
            lines.append(f"Cook Time: {self.cook_time}")
        if self.total_time:
            lines.append(f"Total Time: {self.total_time}")
        
        lines.append(f"\n{'─' * 30}")
        lines.append("INGREDIENTS")
        lines.append(f"{'─' * 30}")
        for ing in self.ingredients:
            lines.append(f"  • {ing}")
        
        lines.append(f"\n{'─' * 30}")
        lines.append("INSTRUCTIONS")
        lines.append(f"{'─' * 30}")
        for i, step in enumerate(self.instructions, 1):
            lines.append(f"  {i}. {step}")
        
        if self.source_url:
            lines.append(f"\nSource: {self.source_url}")
        
        return "\n".join(lines)


class RecipeScraper:
    """Scrapes recipes from URLs."""
    
    # Pattern to parse ingredient strings
    # Note: single-letter units (g, l) use word boundary to avoid matching start of words
    INGREDIENT_PATTERN = re.compile(
        r'^(?P<quantity>[\d\s./½⅓⅔¼¾⅛⅜⅝⅞-]+)?\s*'
        r'(?P<unit>cups?|tbsp|tablespoons?|tsp|teaspoons?|oz|ounces?|'
        r'pounds?|lbs?|grams?|g\b|kg\b|ml\b|liters?|l\b|pints?|quarts?|gallons?|'
        r'fl\s*oz|fluid\s*ounces?|cloves?|cans?|packages?|pkgs?|bunch|'
        r'head|stalk|stalks|sprigs?|slices?|pieces?|pinch|dash)?\s*'
        r'(?:of\s+)?(?P<item>.+)',
        re.IGNORECASE
    )
    
    # Unicode fraction mapping
    UNICODE_FRACTIONS = {
        '½': 0.5, '⅓': 1/3, '⅔': 2/3, '¼': 0.25, '¾': 0.75,
        '⅛': 0.125, '⅜': 0.375, '⅝': 0.625, '⅞': 0.875,
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; RecipeScraper/1.0)'
        })
    
    def scrape(self, url: str) -> Recipe:
        """Scrape a recipe from a URL."""
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try JSON-LD first (most reliable)
        recipe_data = self._extract_json_ld(soup)
        if recipe_data:
            return self._parse_schema_recipe(recipe_data, url)
        
        # Fallback: try recipe-scrapers library
        if HAS_RECIPE_SCRAPERS:
            try:
                recipe = self._parse_recipe_scrapers(url)
                # Validate: if "ingredients" look like instructions, fall through
                if recipe.ingredients and not self._ingredients_look_valid(recipe.ingredients):
                    pass  # Fall through to heuristic
                else:
                    return recipe
            except Exception:
                pass  # Fall through to heuristic
        
        # Last resort: heuristic parsing
        return self._parse_heuristic(soup, url)
    
    def _parse_recipe_scrapers(self, url: str) -> Recipe:
        """Use recipe-scrapers library to extract recipe."""
        scraper = scrape_me(url)
        
        # Parse ingredients
        ingredients = []
        for ing_text in scraper.ingredients():
            parsed = self._parse_ingredient(ing_text)
            if parsed:  # Skip None (filtered headers/notes)
                ingredients.append(parsed)
        
        # Parse instructions
        instructions = []
        inst_text = scraper.instructions()
        if inst_text:
            # Split on newlines or numbered steps
            steps = re.split(r'\n+|\d+\.\s+', inst_text)
            instructions = [s.strip() for s in steps if s.strip()]
        
        # Get servings
        servings = None
        try:
            yields = scraper.yields()
            if yields:
                match = re.search(r'\d+', yields)
                if match:
                    servings = int(match.group())
        except Exception:
            pass
        
        # Get times
        prep_time = None
        cook_time = None
        total_time = None
        try:
            if scraper.prep_time():
                prep_time = f"{scraper.prep_time()}m"
        except Exception:
            pass
        try:
            if scraper.cook_time():
                cook_time = f"{scraper.cook_time()}m"
        except Exception:
            pass
        try:
            if scraper.total_time():
                total_time = f"{scraper.total_time()}m"
        except Exception:
            pass
        
        return Recipe(
            name=scraper.title() or "Untitled Recipe",
            servings=servings,
            prep_time=prep_time,
            cook_time=cook_time,
            total_time=total_time,
            ingredients=ingredients,
            instructions=instructions,
            source_url=url
        )
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract Recipe schema from JSON-LD."""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                recipe = self._find_recipe_in_json(data)
                if recipe:
                    return recipe
            except (json.JSONDecodeError, TypeError):
                continue
        
        return None
    
    def _find_recipe_in_json(self, data) -> Optional[dict]:
        """Recursively find Recipe type in JSON-LD data."""
        if isinstance(data, dict):
            # Check @type for Recipe
            type_val = data.get('@type', [])
            if isinstance(type_val, str):
                type_val = [type_val]
            if 'Recipe' in type_val:
                return data
            
            # Check inside @graph
            if '@graph' in data:
                result = self._find_recipe_in_json(data['@graph'])
                if result:
                    return result
            
            # Check all other values
            for value in data.values():
                result = self._find_recipe_in_json(value)
                if result:
                    return result
                    
        elif isinstance(data, list):
            for item in data:
                result = self._find_recipe_in_json(item)
                if result:
                    return result
        return None
    
    def _parse_schema_recipe(self, data: dict, url: str) -> Recipe:
        """Parse a Schema.org Recipe object."""
        name = data.get('name', 'Untitled Recipe')
        
        # Parse servings
        servings = None
        yield_value = data.get('recipeYield')
        if yield_value:
            if isinstance(yield_value, list):
                yield_value = yield_value[0]
            servings_match = re.search(r'\d+', str(yield_value))
            if servings_match:
                servings = int(servings_match.group())
        
        # Parse ingredients
        ingredients = []
        for ing_text in data.get('recipeIngredient', []):
            parsed = self._parse_ingredient(ing_text)
            if parsed:  # Skip None (filtered headers/notes)
                ingredients.append(parsed)
        
        # Parse instructions
        instructions = []
        inst_data = data.get('recipeInstructions', [])
        if isinstance(inst_data, str):
            instructions = [self._clean_html_text(s) for s in inst_data.split('\n') if s.strip()]
        elif isinstance(inst_data, list):
            for item in inst_data:
                if isinstance(item, str):
                    instructions.append(self._clean_html_text(item))
                elif isinstance(item, dict):
                    # Handle HowToStep
                    if item.get('@type') == 'HowToStep':
                        text = item.get('text', '')
                        if text:
                            instructions.append(self._clean_html_text(text))
                    # Handle HowToSection (has itemListElement with steps)
                    elif item.get('@type') == 'HowToSection':
                        section_steps = item.get('itemListElement', [])
                        for step in section_steps:
                            if isinstance(step, dict):
                                text = step.get('text', '')
                                if text:
                                    instructions.append(self._clean_html_text(text))
                            elif isinstance(step, str):
                                instructions.append(self._clean_html_text(step))
                    # Fallback: just get text field
                    else:
                        text = item.get('text', '')
                        if text:
                            instructions.append(self._clean_html_text(text))
        
        return Recipe(
            name=name,
            servings=servings,
            prep_time=self._parse_duration(data.get('prepTime')),
            cook_time=self._parse_duration(data.get('cookTime')),
            total_time=self._parse_duration(data.get('totalTime')),
            ingredients=ingredients,
            instructions=instructions,
            source_url=url
        )
    
    def _parse_ingredient(self, text: str) -> Ingredient:
        """Parse an ingredient string into structured data."""
        text = text.strip()
        original = text
        
        # Skip lines that are clearly not ingredients
        if self._is_section_header_or_note(text):
            return None
        
        # Clean up common cruft
        text = self._clean_ingredient_text(text)
        
        # After cleaning, check again if it's empty or a header
        if not text or self._is_section_header_or_note(text):
            return None
        
        match = self.INGREDIENT_PATTERN.match(text)
        
        if not match:
            return Ingredient(quantity=None, unit=None, item=text, original_text=original)
        
        quantity_str = match.group('quantity')
        unit = match.group('unit')
        item = match.group('item').strip()
        
        # Clean up the item text too
        item = self._clean_ingredient_text(item)
        
        # Parse quantity
        quantity = None
        if quantity_str:
            quantity = self._parse_quantity(quantity_str.strip())
        
        return Ingredient(
            quantity=quantity,
            unit=unit,
            item=item,
            original_text=original
        )
    
    def _is_section_header_or_note(self, text: str) -> bool:
        """Check if text is a section header or note rather than an ingredient."""
        text = text.strip()
        
        # Empty
        if not text:
            return True
        
        lower = text.lower()
        
        # Starts with common note patterns
        note_starters = [
            'see in post', 'see post', 'see here', 'see note', 'see recipe',
            'option to', 'optional:', 'options:', 'note:', 'notes:',
            'for the ', 'to make ', 'to prepare ', 'you can also',
            'alternatively', 'substitute', 'tip:', 'tips:',
        ]
        if any(lower.startswith(s) for s in note_starters):
            return True
        
        # Starts with open paren and is a note
        if lower.startswith('(see') or lower.startswith('(option') or lower.startswith('(note'):
            return True
        
        # All caps = likely a header like "RASPBERRY COULIS"
        if text.isupper() and len(text.split()) <= 4:
            return True
        
        # Check the part before any parentheses
        main_part = re.split(r'\s*\(', text)[0].strip()
        
        # Title case short phrase with no numbers = likely a sub-recipe header
        # e.g. "Raspberry Coulis", "Lemon Curd", "Whipped Cream"
        words = main_part.split()
        if (len(words) <= 3 and 
            len(main_part) <= 25 and
            not any(c.isdigit() for c in main_part) and
            not any(c in main_part.lower() for c in ['/', ',']) and
            main_part[0].isupper()):
            # Check if it looks like a title (most words capitalized)
            cap_words = sum(1 for w in words if w and w[0].isupper())
            if cap_words >= len(words) * 0.7:
                return True
        
        return False
    
    def _clean_ingredient_text(self, text: str) -> str:
        """Clean up ingredient text by removing notes and fixing formatting."""
        # First decode HTML entities
        text = self._clean_html_text(text)
        
        # Remove (Note X), (Note: ...), (see note X), etc.
        text = re.sub(r'\(Note\s*:?\s*\d*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(see\s+note\s*\d*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bNote\s*\d+\b', '', text, flags=re.IGNORECASE)
        
        # Remove leading slashes (from fractions that got split weird)
        text = re.sub(r'^[/\s]+', '', text)
        
        # Fix "(," or "( ," to just "("
        text = re.sub(r'\(\s*,\s*', '(', text)
        
        # Fix double parens
        text = re.sub(r'\(\(', '(', text)
        text = re.sub(r'\)\)', ')', text)
        
        # Remove empty parentheses
        text = re.sub(r'\(\s*\)', '', text)
        
        # Fix spaces before closing paren
        text = re.sub(r'\s+\)', ')', text)
        
        # Fix double spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove trailing/leading parens with just whitespace
        text = re.sub(r'\(\s*$', '', text)
        text = re.sub(r'^\s*\)', '', text)
        
        # Clean up dangling commas at end
        text = re.sub(r',\s*$', '', text)
        
        # Balance parentheses - remove unmatched ones
        text = self._balance_parens(text)
        
        return text.strip()
    
    def _balance_parens(self, text: str) -> str:
        """Remove unbalanced parentheses from text."""
        # Count opens and closes
        result = []
        depth = 0
        
        for char in text:
            if char == '(':
                depth += 1
                result.append(char)
            elif char == ')':
                if depth > 0:
                    depth -= 1
                    result.append(char)
                # else: skip unmatched closing paren
            else:
                result.append(char)
        
        # Remove any unmatched opening parens from the end
        final = ''.join(result)
        while final.count('(') > final.count(')'):
            # Find last unmatched ( and remove it
            idx = final.rfind('(')
            final = final[:idx] + final[idx+1:]
        
        return final
    
    def _clean_html_text(self, text: str) -> str:
        """Clean HTML entities and normalize text."""
        import html
        text = html.unescape(text)  # Decode &quot; &#39; etc.
        text = text.replace('\u2019', "'")  # Smart quotes
        text = text.replace('\u2018', "'")
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '-')  # Em dash
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        # Remove leading hyphens/dashes from instructions
        text = re.sub(r'^[\-–—]\s*', '', text)
        return text.strip()
    
    def _parse_quantity(self, qty_str: str) -> Optional[float]:
        """Parse a quantity string into a float."""
        if not qty_str:
            return None
        
        total = 0.0
        
        # Handle ranges like "1-2" - take the average
        if '-' in qty_str and not qty_str.startswith('-'):
            range_match = re.match(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', qty_str.strip())
            if range_match:
                low, high = float(range_match.group(1)), float(range_match.group(2))
                return (low + high) / 2
        
        # Replace unicode fractions
        for char, value in self.UNICODE_FRACTIONS.items():
            if char in qty_str:
                total += value
                qty_str = qty_str.replace(char, '')
        
        # Parse remaining number (could be "1 1/2" format)
        qty_str = qty_str.strip()
        if qty_str:
            parts = qty_str.split()
            for part in parts:
                if '/' in part:
                    try:
                        num, denom = part.split('/')
                        total += float(num) / float(denom)
                    except (ValueError, ZeroDivisionError):
                        pass
                else:
                    try:
                        total += float(part)
                    except ValueError:
                        pass
        
        return total if total > 0 else None
    
    def _parse_duration(self, duration: Optional[str]) -> Optional[str]:
        """Parse ISO 8601 duration to human readable."""
        if not duration:
            return None
        
        # Match ISO 8601 duration format PT1H30M
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            hours, minutes, seconds = match.groups()
            parts = []
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if seconds:
                parts.append(f"{seconds}s")
            return ' '.join(parts) if parts else None
        
        return duration
    
    def _parse_heuristic(self, soup: BeautifulSoup, url: str) -> Recipe:
        """Fallback: try to extract recipe using heuristics."""
        # Try to find title
        name = "Untitled Recipe"
        title = soup.find('h1')
        if title:
            name = title.get_text(strip=True)
        
        ingredients = []
        instructions = []
        
        # Method 1: Look for heading-based recipes (Substack, blogs)
        ingredients, instructions = self._extract_from_headings(soup)
        
        # Method 2: Look for tables (Ottolenghi-style)
        if not ingredients:
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        qty_text = cells[0].get_text(strip=True)
                        item_text = cells[1].get_text(strip=True)
                        if item_text and not item_text.isupper():  # Skip headers like "BROTH"
                            combined = f"{qty_text} {item_text}".strip()
                            if combined:
                                parsed = self._parse_ingredient(combined)
                                if parsed:  # Skip None (filtered headers/notes)
                                    ingredients.append(parsed)
        
        # Method 3: Look for ingredient lists (ul/ol)
        if not ingredients:
            for ul in soup.find_all(['ul', 'ol']):
                items = ul.find_all('li')
                if items and self._looks_like_ingredients(items):
                    for li in items:
                        text = li.get_text(strip=True)
                        if text:
                            parsed = self._parse_ingredient(text)
                            if parsed:  # Skip None (filtered headers/notes)
                                ingredients.append(parsed)
                    break
        
        # Look for instructions in ordered lists (if not found from headings)
        if not instructions:
            for ol in soup.find_all('ol'):
                items = ol.find_all('li')
                if items and len(items) >= 2:
                    potential_instructions = []
                    for li in items:
                        text = self._clean_html_text(li.get_text(strip=True))
                        # Instructions are usually longer and don't start with quantities
                        if text and len(text) > 50 and not re.match(r'^\d+\s*g\b', text):
                            potential_instructions.append(text)
                    if potential_instructions:
                        instructions = potential_instructions
                        break
        
        # Extract servings/time from meta info if available
        servings = None
        prep_time = None
        cook_time = None
        
        # Look for common patterns
        page_text = soup.get_text()
        serves_match = re.search(r'Serves?\s*(\d+)', page_text, re.IGNORECASE)
        if serves_match:
            servings = int(serves_match.group(1))
        
        prep_match = re.search(r'Prep\s*:?\s*(\d+)\s*min', page_text, re.IGNORECASE)
        if prep_match:
            prep_time = f"{prep_match.group(1)}m"
            
        cook_match = re.search(r'Cook\s*:?\s*(\d+)\s*min', page_text, re.IGNORECASE)
        if cook_match:
            cook_time = f"{cook_match.group(1)}m"
        
        return Recipe(
            name=name,
            servings=servings,
            prep_time=prep_time,
            cook_time=cook_time,
            ingredients=ingredients,
            instructions=instructions,
            source_url=url
        )
    
    def _looks_like_ingredients(self, items) -> bool:
        """Check if list items look like ingredients."""
        if len(items) < 3:
            return False
        
        # Check for common ingredient patterns
        ingredient_words = ['cup', 'tbsp', 'tsp', 'oz', 'pound', 'gram', 'salt', 'pepper', 'butter', 'oil', 'flour', 'sugar']
        matches = 0
        for item in items[:5]:
            text = item.get_text().lower()
            if any(word in text for word in ingredient_words):
                matches += 1
        
        return matches >= 2
    
    def _extract_from_headings(self, soup: BeautifulSoup):
        """Extract ingredients and instructions from heading-based structure (blogs, Substack)."""
        ingredients = []
        instructions = []
        ingredients_list_elem = None  # Track which list element has ingredients
        
        # Find all potential headings including bold/strong text (common in Substack)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
        
        for heading in headings:
            heading_text = heading.get_text(strip=True).lower()
            
            # Look for ingredients heading
            if 'ingredient' in heading_text and not ingredients:
                # Find the next list after this heading
                next_elem = heading.find_next(['ul', 'ol'])
                if next_elem:
                    ingredients_list_elem = next_elem  # Remember this list
                    for li in next_elem.find_all('li', recursive=False):
                        text = li.get_text(strip=True)
                        if text:
                            parsed = self._parse_ingredient(text)
                            if parsed:
                                ingredients.append(parsed)
            
            # Look for method/instructions heading
            if any(word in heading_text for word in ['method', 'instruction', 'direction', 'preparation', 'steps']) and not instructions:
                # Find the next list after this heading
                next_elem = heading.find_next(['ul', 'ol'])
                # Make sure we don't use the same list as ingredients
                if next_elem and next_elem != ingredients_list_elem:
                    for li in next_elem.find_all('li', recursive=False):
                        text = self._clean_html_text(li.get_text(strip=True))
                        if text:
                            instructions.append(text)
        
        return ingredients, instructions
    
    def _ingredients_look_valid(self, ingredients: list) -> bool:
        """Check if parsed ingredients actually look like ingredients, not instructions."""
        if not ingredients:
            return False
        
        # Real ingredients are typically short (under 100 chars)
        # Instructions are long paragraphs
        long_count = 0
        for ing in ingredients[:5]:
            text = ing.original_text if ing.original_text else str(ing)
            if len(text) > 100:
                long_count += 1
        
        # If most "ingredients" are long paragraphs, they're probably instructions
        return long_count < len(ingredients[:5]) / 2
    
    def _looks_like_instructions(self, items) -> bool:
        """Check if list items look like instructions."""
        if len(items) < 2:
            return False
        
        # Instructions tend to be longer and start with verbs
        instruction_verbs = ['preheat', 'mix', 'stir', 'add', 'combine', 'bake', 'cook', 'heat', 'pour', 'place', 'let', 'remove', 'set', 'whisk']
        matches = 0
        for item in items[:5]:
            text = item.get_text().lower().strip()
            if len(text) > 20 and any(text.startswith(verb) for verb in instruction_verbs):
                matches += 1
        
        return matches >= 1


def demo():
    """Demonstrate the recipe tool capabilities."""
    print("Recipe Tool")
    print("=" * 50)
    print(f"recipe-scrapers library: {'✅ Available' if HAS_RECIPE_SCRAPERS else '❌ Not installed (pip install recipe-scrapers)'}")
    print("=" * 50)
    
    # Example: Create a recipe manually to show scaling/conversion
    recipe = Recipe(
        name="Classic Chocolate Chip Cookies",
        servings=24,
        prep_time="15m",
        cook_time="10m",
        ingredients=[
            Ingredient(2.25, "cups", "all-purpose flour"),
            Ingredient(1, "tsp", "baking soda"),
            Ingredient(1, "tsp", "salt"),
            Ingredient(1, "cup", "butter, softened"),
            Ingredient(0.75, "cup", "granulated sugar"),
            Ingredient(0.75, "cup", "packed brown sugar"),
            Ingredient(2, None, "large eggs"),
            Ingredient(1, "tsp", "vanilla extract"),
            Ingredient(2, "cups", "chocolate chips"),
        ],
        instructions=[
            "Preheat oven to 375°F (190°C).",
            "Mix flour, baking soda, and salt in a bowl.",
            "Beat butter and sugars until creamy.",
            "Add eggs and vanilla to butter mixture.",
            "Gradually blend in flour mixture.",
            "Stir in chocolate chips.",
            "Drop rounded tablespoons onto ungreased baking sheets.",
            "Bake for 9 to 11 minutes or until golden brown.",
        ]
    )
    
    print("ORIGINAL RECIPE:")
    print(recipe)
    
    print("\n\n" + "=" * 50)
    print("HALVED RECIPE:")
    print("=" * 50)
    halved = recipe.halve()
    print(halved)
    
    print("\n\n" + "=" * 50)
    print("CONVERTED TO METRIC:")
    print("=" * 50)
    metric = recipe.convert_to_metric()
    print(metric)
    
    print("\n\n" + "=" * 50)
    print("JSON OUTPUT:")
    print("=" * 50)
    print(recipe.to_json())


if __name__ == "__main__":
    demo()