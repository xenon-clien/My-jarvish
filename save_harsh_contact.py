import sys
sys.path.insert(0, r"c:\Users\shivam\Downloads\chatbot")

from backend.database.repositories import contact_repo

# Save contact Harsh with number 8054840494
contact = contact_repo.save_contact(
    name="Harsh",
    phone="8054840494",
    relationship="friend"
)

print(f"✅ Contact Saved: Name='{contact.name}', Phone='{contact.phone}', ID={contact.id}")

# Verify lookup
found = contact_repo.get_contact("Harsh")
print(f"Lookup check for 'Harsh': {found.name} -> {found.phone}")
found_lower = contact_repo.get_contact("harsh")
print(f"Lookup check for 'harsh': {found_lower.name} -> {found_lower.phone}")
