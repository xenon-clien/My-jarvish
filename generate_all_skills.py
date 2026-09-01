import sys
sys.path.insert(0, r"c:\Users\shivam\Downloads\chatbot")

from backend.skills.registry import skill_registry
from backend.skills.scanner import capability_scanner
from backend.skills.generator import skill_generator

print("=== GENERATING ALL CORE APPLICATION SKILLS ===")
core_apps = ["youtube", "chrome", "edge", "file_explorer", "vscode", "spotify", "system", "messaging"]

for app in core_apps:
    cap_map = capability_scanner.scan_capabilities(app)
    saved_path = skill_generator.save_skill(cap_map)
    print(f"✅ Generated skill for '{app}': {len(cap_map.capabilities)} capabilities -> {saved_path}")

print("\nAll core application skills generated and saved successfully!")
