# functions for tts-deck-import
# andy wong

import requests
import time
import json
import os
from math import ceil
from PIL import Image

# collection defines
collectionAllowable = 75
collectionURL = "https://api.scryfall.com/cards/collection"
collectionHeaders = {"Content-Type": "application/JSON"}

# stitched image stats
xDim = 5
yDim = 5
maxCards = xDim * yDim - 1

def getpost(url, data = None, headers = None, filename = None):

    if data is None:
        response = requests.get(url)
    else:
        response = requests.post(url, data = data, headers = headers)
    time.sleep(0.1)
    if filename is None:
        return response
    else:
        with open(filename, "wb") as file:
            file.write(response.content)

def chunkify(arr, size = maxCards):

    return [arr[x:x + size] for x in range(0, len(arr), size)]

def getbyfield(field, identifiers):

    chunks = chunkify(identifiers, collectionAllowable)
    cardData = []
    failures = []

    # for each chunk, get data on the collection of each chunk's cards
    # concat onto cardData, failures
    for chunk in chunks:
        identifiers = [{field: x} for x in chunk]

        collectionData = json.dumps({"pretty": False,
            "identifiers": identifiers
        })
        collection = getpost(
                url = collectionURL,
                data = collectionData,
                headers = collectionHeaders
        ).json()

        cardData += collection["data"]
        failures += collection["not_found"]

    return (cardData, failures)

def stitcher(deckName, ids, prefix = ""):

    imageNames = [".temp/" + prefix + str(num) + ".jpg" for num in ids]
    chunks = chunkify(imageNames, maxCards)
    for i, chunk in enumerate(chunks):
        images = [Image.open(imageName) for imageName in chunk]
        width, height = images[0].size
        cols, rows = stitchDimensions(len(images))
        stitchedImage = Image.new("RGB", (cols*width, rows*height))
        for j, image in enumerate(images):
            stitchedImage.paste(image, (j%cols*width, int(j/cols)*(height)))
        stitchedImage.save("images/" + deckName + "_" + prefix + str(i) + ".jpg")

# calculate size of stitcher sheet given number of cards (<=limX*limxY-1)
def stitchDimensions(num, limX=xDim, limY=yDim):

    columns = num + 1 if num + 1 < limX else limX
    rows = ceil((num + 1)/limX)
    if rows > limY: raise Exception("too many cards to fit on sheet")
    return (columns, rows)

def transformObject(posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0,
    rotZ = 180, scaleX = 1, scaleY = 1, scaleZ = 1):

    return {
        "posX": posX,
        "posY": posY,
        "posZ": posZ,
        "rotX": rotX,
        "rotY": rotY,
        "rotZ": rotZ,
        "scaleX": scaleX,
        "scaleY": scaleY,
        "scaleZ": scaleZ
    }

def cardObject(nickname, cardID, name = "Card", transform = transformObject()):

    return {
        "Name": name,
        "Nickname": nickname,
        "Transform": transform,
        "CardID": cardID
    }

def imageObject(numWidth, numHeight, faceURL, backURL, uniqueBack = None):

    if uniqueBack is None:
        return {
            "NumWidth": numWidth,
            "NumHeight": numHeight,
            "FaceURL": "https://www.brickbolt.com/tts-deck-import/" + faceURL,
            "BackURL": "https://www.brickbolt.com/tts-deck-import/" + backURL
        }
    else:
        return {
            "NumWidth": numWidth,
            "NumHeight": numHeight,
            "FaceURL": "https://www.brickbolt.com/tts-deck-import/" + faceURL,
            "BackURL": "https://www.brickbolt.com/tts-deck-import/" + backURL,
            "UniqueBack": uniqueBack
        }

def cardIDGen(num, start = 0):

    return start + 100 * (1 + int(num/24)) + (num%24)

def freqMult(frequency, value):
    out = []
    for freq, val in zip(frequency, value):
        out += freq * [val]
    return out

def checkCardBack(color):

    return color + ".jpg" in os.listdir("assets")

# hashing not working?
#
# def hashDeck(cardData, cardFrequency):
#     cardNames = [cardData[x]["name"] for x in range(len(cardData))]
#     cards = sorted(freqMult(cardFrequency, cardNames))
#     return hash(tuple(cards))
#
# def checkExisting(cardData, cardFrequency):
#     newHash = hashDeck(cardData, cardFrequency)
#     jsonData = None
#     hashes = None
#     with open("decklists/.deckhashes", "r") as file:
#         jsonData = json.load(file)
#         hashes = jsonData["hashes"]
#     inHash = newHash in hashes
#     if not inHash:
#         with open("decklists/.deckhashes", "w+") as file:
#             jsonData["hashes"] += [newHash]
#             json.dump(jsonData, file, indent = 2)
#     return inHash
#
# def replaceCardBack(deckName, cardBack):
#     with open("outputs/" + deckName + ".json", "r") as file:
#         jsonData = json.load(file)
#     for x in range(len(jsonData["ObjectStates"])):
#         for key in jsonData["ObjectStates"][x]["CustomDeck"].keys():
#             if not "UniqueBack" in jsonData["ObjectStates"][x]["CustomDeck"][key].keys():
#                 jsonData["ObjectStates"][x]["CustomDeck"][key]["BackURL"] = "https://www.brickbolt.com/tts-deck-import/assets/" + cardBack + ".jpg"
#     with open("outputs/" + deckName + ".json", "w+") as file:
#         json.dump(jsonData, file, indent = 2)
