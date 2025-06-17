import requests
import time
import json

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
EMAIL_OR_USERNAME = "23f2002133@ds.study.iitm.ac.in"
PASSWORD = "214O@B230471cs"

def login_discourse(base, login_val, password):
    sess = requests.Session()
    sess.headers.update({'X-Requested-With': 'XMLHttpRequest'})
    r = sess.get(f"{base}/session/csrf")
    r.raise_for_status()
    csrf = r.json().get("csrf")
    if not csrf:
        raise Exception("❌ No CSRF token obtained")
    sess.headers.update({
        "X-CSRF-Token": csrf,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    payload = {
        "login": login_val,
        "password": password,
    }
    r2 = sess.post(f"{base}/session", data=payload)
    r2.raise_for_status()
    data = r2.json()
    if not data.get("user"):
        raise Exception("❌ Login failed")
    return sess

def scrape_posts(base, sess, category, start, end):
    posts = []
    page = 0
    while True:
        q = f"after:{start} before:{end} category:{category}"
        resp = sess.get(f"{base}/search.json", params={"q": q, "page": page})
        resp.raise_for_status()
        js = resp.json()
        results = js.get("posts") or js.get("topics") or []
        if not results:
            break
        posts.extend(results)
        print(f"🗂 Page {page} → got {len(results)} items")
        page += 1
        time.sleep(1)
    return posts

def fetch_full_topic(base, sess, topic_id):
    # First get the topic metadata to get the stream of post IDs
    url = f"{base}/t/{topic_id}.json"
    resp = sess.get(url)
    resp.raise_for_status()
    topic_data = resp.json()
    slug = topic_data.get("slug", "")
    title = topic_data.get("title", "")
    stream = topic_data.get("post_stream", {}).get("stream", [])
    
    if not stream:
        print(f"⚠️ No stream found for topic {topic_id}")
        return {
            "topic_id": topic_id,
            "title": title,
            "slug": slug,
            "posts": []
        }
    
    print(f"Topic {topic_id}: Found {len(stream)} posts in stream")
    
    # Fetch posts in batches of 20
    all_posts = []
    for i in range(0, len(stream), 20):
        batch_ids = stream[i:i+20]
        batch_params = [("post_ids[]", str(id)) for id in batch_ids]
        
        try:
            resp = sess.get(f"{base}/t/{topic_id}/posts.json", params=batch_params)
            if resp.status_code == 200:
                batch_data = resp.json()
                posts_batch = batch_data.get("post_stream", {}).get("posts", [])
                print(f"🔍 Fetched batch {i//20+1} → {len(posts_batch)} posts")
                all_posts.extend(posts_batch)
            else:
                print(f"⚠️ Batch fetch failed: status {resp.status_code}")
        except Exception as e:
            print(f"⚠️ Error: {e}")
        time.sleep(0.5)
    
    # Build final posts data
    posts_data = []
    for p in all_posts:
        post_number = p.get("post_number")
        cooked = p.get("cooked", "")
        username = p.get("username", "unknown")
        post_url = f"{base}/t/{slug}/{topic_id}/{post_number}"
        posts_data.append({
            "username": username,
            "post_number": post_number,
            "url": post_url,
            "html": cooked
        })

    return {
        "topic_id": topic_id,
        "title": title,
        "slug": slug,
        "posts": posts_data
    }

def main():
    sess = login_discourse(BASE_URL, EMAIL_OR_USERNAME, PASSWORD)
    posts = scrape_posts(BASE_URL, sess, "tds-kb", "2025-01-01", "2025-04-14")
    seen = set()
    filtered_topics = []

    for post in posts:
        topic_id = post.get("topic_id")
        if topic_id and topic_id not in seen:
            seen.add(topic_id)
            try:
                print(f"\n📭 Processing topic {topic_id}")
                topic = fetch_full_topic(BASE_URL, sess, topic_id)
                filtered_topics.append(topic)
                print(f"✅ Topic {topic_id} → {len(topic['posts'])} posts")
            except Exception as e:
                print(f"❌ Error processing topic {topic_id}: {e}")
            time.sleep(1)

    with open("tds_kb_full_posts.json", "w", encoding="utf-8") as f:
        json.dump(filtered_topics, f, ensure_ascii=False, indent=2)

    print("\n✅ All topics saved to `tds_kb_full_posts.json`")

main()