import asyncio
import aiohttp

async def test_pullpush():
    url = "https://api.pullpush.io/reddit/search/submission/?q=blinkit&size=2"
    print(f"Testing PullPush: {url}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                print(f"PullPush Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    if "data" in data and len(data["data"]) > 0:
                        for post in data["data"]:
                            print(f"- Found post: '{post.get('title', '')[:60]}...' in r/{post.get('subreddit', 'unknown')}")
                    else:
                        print("Success, but no data returned.")
                else:
                    text = await response.text()
                    print(f"Failed: {text[:100]}")
        except Exception as e:
            print(f"Exception: {e}")

async def test_arctic_shift():
    # Searching for general keyword "blinkit" across a known subreddit
    url = "https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=india&title=blinkit&limit=2"
    print(f"\nTesting Arctic Shift: {url}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                print(f"Arctic Shift Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    posts = data.get("data", []) if isinstance(data, dict) else data
                    if len(posts) > 0:
                        for post in posts:
                            print(f"- Found post: '{post.get('title', '')[:60]}...' in r/{post.get('subreddit', 'unknown')}")
                    else:
                        print("Success, but no data returned for this specific sub/query combo.")
                else:
                    text = await response.text()
                    print(f"Failed: {text[:100]}")
        except Exception as e:
            print(f"Exception: {e}")

async def main():
    await test_pullpush()
    await test_arctic_shift()

if __name__ == "__main__":
    asyncio.run(main())
