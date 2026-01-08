#!/usr/bin/env python3
"""
Recipe Tool CLI - Interactive command-line interface
"""

import sys
from recipe_tool import RecipeScraper, Recipe


def print_menu():
    """Print the main menu."""
    print("\n" + "─" * 40)
    print("RECIPE TOOL - OPTIONS")
    print("─" * 40)
    print("  1. Scale recipe (custom multiplier)")
    print("  2. Halve recipe (÷2)")
    print("  3. Double recipe (×2)")
    print("  4. Triple recipe (×3)")
    print("  5. Convert to metric")
    print("  6. Convert to imperial")
    print("  7. Export to JSON")
    print("  8. Show current recipe")
    print("  9. Load new URL")
    print("  0. Exit")
    print("─" * 40)


def main():
    scraper = RecipeScraper()
    current_recipe = None
    
    print("=" * 50)
    print("🍳 RECIPE TOOL")
    print("=" * 50)
    print("\nPaste a recipe URL to extract and manipulate recipes.")
    print("Tip: Works best with sites that use Schema.org markup")
    print("     (most major recipe sites like AllRecipes, BBC Food, etc.)")
    
    while True:
        if current_recipe is None:
            url = input("\nEnter recipe URL (or 'quit' to exit): ").strip()
            if url.lower() in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break
            
            if not url.startswith('http'):
                print("Please enter a valid URL starting with http:// or https://")
                continue
            
            print(f"\nFetching recipe from: {url}")
            try:
                current_recipe = scraper.scrape(url)
                print("\n✅ Recipe extracted successfully!\n")
                print(current_recipe)
            except Exception as e:
                print(f"\n❌ Error scraping recipe: {e}")
                continue
        
        print_menu()
        choice = input("Choose option: ").strip()
        
        if choice == '0':
            print("Goodbye!")
            break
        elif choice == '1':
            try:
                factor = float(input("Enter scale factor (e.g., 0.5, 1.5, 2): "))
                current_recipe = current_recipe.scale(factor)
                print(f"\n✅ Recipe scaled by {factor}x\n")
                print(current_recipe)
            except ValueError:
                print("Invalid number. Please enter a decimal like 0.5 or 2")
        elif choice == '2':
            current_recipe = current_recipe.halve()
            print("\n✅ Recipe halved\n")
            print(current_recipe)
        elif choice == '3':
            current_recipe = current_recipe.double()
            print("\n✅ Recipe doubled\n")
            print(current_recipe)
        elif choice == '4':
            current_recipe = current_recipe.triple()
            print("\n✅ Recipe tripled\n")
            print(current_recipe)
        elif choice == '5':
            current_recipe = current_recipe.convert_to_metric()
            print("\n✅ Converted to metric\n")
            print(current_recipe)
        elif choice == '6':
            current_recipe = current_recipe.convert_to_imperial()
            print("\n✅ Converted to imperial\n")
            print(current_recipe)
        elif choice == '7':
            filename = input("Enter filename (default: recipe.json): ").strip()
            if not filename:
                filename = "recipe.json"
            if not filename.endswith('.json'):
                filename += '.json'
            with open(filename, 'w') as f:
                f.write(current_recipe.to_json())
            print(f"\n✅ Saved to {filename}")
        elif choice == '8':
            print("\n" + str(current_recipe))
        elif choice == '9':
            current_recipe = None
        else:
            print("Invalid option. Please choose 0-9.")


if __name__ == "__main__":
    main()