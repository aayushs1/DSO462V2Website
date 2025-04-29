from pymongo import MongoClient
from pymongo.server_api import ServerApi

# MongoDB Connection
client = MongoClient("mongodb+srv://test:1zrbAbwhLkw360dq@gogoprint.z5cf4yu.mongodb.net/?retryWrites=true&w=majority&appName=GoGoPrint", server_api=ServerApi('1'))
db = client.gogoprint_db  # Database name

# Count and display blog posts
blog_posts_count = db.blog_posts.count_documents({})
print(f"Number of blog posts in database: {blog_posts_count}")

if blog_posts_count > 0:
    print("\nTitles of existing posts:")
    posts = list(db.blog_posts.find({}, {"title": 1}))
    for i, post in enumerate(posts, 1):
        print(f"{i}. {post['title']}")
    
    print("\nTo see all the posts, visit: http://localhost:5001/blog")
    print("If you want to reinitialize the blog posts, first delete the existing ones.")
else:
    print("\nNo blog posts found. Visit http://localhost:5001/admin/initialize_blog_data to create sample posts.") 