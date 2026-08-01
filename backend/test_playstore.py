from google_play_scraper import reviews, Sort

try:
    result, next_token = reviews(
        "com.grofers.customerapp",
        lang='en',
        country='in',
        sort=Sort.NEWEST,
        count=10,
        continuation_token="CtEBIsgBAa2vNjHB63roSRRyOLEicRHqn1Iq0sHYV1JPkWCS8c_AFca6Ufepv0H7XZXo9oLk5sfGQBmjm1GlpwkvXJfGmshJs6Ta8TPHwzAmvdOE2Z-ajvlXy9gGD0R4SrCq48f5q1Q3h3i4IU_QHvc3MUf4BHTLycC6lUr2Q0EAP07XqsXentvOWEfchZt-kSv3oyRuqMEfRIHlg9ExDvm2rvCQ6WH0U5JZJFigBhbOfjBcyxgvJyRbBM_xr0wjqIEGfrMXJo8c43GBhtMoiqiH0wY"
    )
    print("Success")
except Exception as e:
    print("Error:", type(e), e)
