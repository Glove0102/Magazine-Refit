
import hashlib

# Replace this with your desired admin password
password = "***AJAX119"  # Change this to your actual password

# Generate the hash
hash_value = hashlib.sha256(password.encode()).hexdigest()

print("=" * 50)
print("ADMIN PASSWORD HASH GENERATOR")
print("=" * 50)
print(f"Password: {password}")
print(f"SHA256 Hash: {hash_value}")
print()
print("Copy the hash above and add it to your Replit Secrets:")
print("1. Go to Secrets tab in Replit")
print("2. Add a new secret:")
print("   Key: ADMIN_PASSWORD_HASH")
print(f"   Value: {hash_value}")
print("3. Restart your Flask app")
print("=" * 50)
