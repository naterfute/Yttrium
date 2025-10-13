


def matchAuthors(album: list):
    known_albums: dict[str, int] = {}

    albumMatch: bool = True

    for item in album:
        if item is not None:
            if known_albums.get(item) is None:
                known_albums[item] =  1
            else:
                known_albums[item] += 1

    if len(known_albums) > 1:
        print("Not all the same")
    else:
        print("are the same")
    print(known_albums)



matchAuthors(["auth1", "auth1", "auth1", "auth1", "auth2", "auth3"])
matchAuthors(["auth1", "auth1", "auth1", "auth1"])

