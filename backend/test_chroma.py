import chromadb
client = chromadb.Client()
collection = client.create_collection("test")
try:
    collection.upsert(ids=["1", "1"], documents=["a", "b"])
    print("Success")
except Exception as e:
    print("Error:", type(e), e)
