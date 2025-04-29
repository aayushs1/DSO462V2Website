from pymongo import MongoClient
from pymongo.server_api import ServerApi

# MongoDB Connection
client = MongoClient("mongodb+srv://test:1zrbAbwhLkw360dq@gogoprint.z5cf4yu.mongodb.net/?retryWrites=true&w=majority&appName=GoGoPrint", server_api=ServerApi('1'))
db = client.gogoprint_db  # Database name

# Count blog posts before deletion
blog_posts_count_before = db.blog_posts.count_documents({})
print(f"Number of blog posts before deletion: {blog_posts_count_before}")

# Delete all blog posts
result = db.blog_posts.delete_many({})
print(f"Deleted {result.deleted_count} blog posts")

# Verify deletion
blog_posts_count_after = db.blog_posts.count_documents({})
print(f"Number of blog posts after deletion: {blog_posts_count_after}")

print("\nNow you can visit http://localhost:5001/admin/initialize_blog_data to add the sample blog posts") 