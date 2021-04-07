# main script for tts-deck-import
# andy wong

import json
import sys
from shutil import copyfile
from functions import *

# step 1: process decklist
# step 2: get collection from scryfall
# step 3: download card images
# step 4: stitch together card images for tts
# step 5: create json for tts

def main(deckName, cardBack = "magic"):
    print("opening decklists/" + deckName + ".txt")
    cardNames, cardFrequency = processDecklist(deckName + ".txt")
    print("gathering card data from scryfall")
    cardData, tokenData = cardCollection(cardNames)
    if cardData is None:
        print("cards missing - end program")
        return
    # elif checkExisting(cardData, cardFrequency):
    #     replaceCardBack(deckName, cardBack)
    #     print("card back changed")
    else:
        print("downloading card images")
        flipCardNums = downloadImages(cardData)
        flipCardNums += downloadImages(tokenData, token=True)
        print("stitching images together")
        stitchImages(deckName, len(cardData), len(tokenData), flipCardNums)
        generateJSON(deckName, cardData, cardFrequency, tokenData, flipCardNums, cardBack)
        print("deck generated - saved to outputs/" + deckName + ".json")

def processDecklist(deckName):

    with open("decklists/" + deckName, "r") as deckFile:
        zippedCards = [tuple(line.rstrip().split(maxsplit=1)) for line in deckFile if line.rstrip()]
        cardFrequencyStr, cardNames = zip(*zippedCards)
        cardFrequency = [int(str) for str in cardFrequencyStr]
    return cardNames, cardFrequency

def cardCollection(cardNames):

    # get card data
    cardData, failures = getbyfield("name", cardNames)

    # show failures, end run of code if any failures
    if len(failures) > 0:
        print("# failures: " + str(len(failures)) + "; " + str(failures))
        return None

    # check for tokens, get token data
    tokenIDs = [
        part["id"]
        for card in cardData if "all_parts" in card
        for part in card["all_parts"] if part["component"] == "token"
    ]
    tokenData, __ = getbyfield("id", tokenIDs)

    return (cardData, tokenData)

def downloadImages(cardData, token=False):

    append = "t" if token else ""
    flipCardNums = []
    for x, cardInfo in enumerate(cardData):
        # if it's a transform card
        if not "image_uris" in cardInfo:
            flipCardNums += [x]
            getpost(
                url = cardInfo["card_faces"][0]["image_uris"]["normal"],
                filename = ".temp/" + append + str(x) + ".jpg"
            )
            # make a flip card copy too
            copyfile(".temp/" + append + str(x) + ".jpg", ".temp/tf" + append + str(x) + ".jpg")
            getpost(
                url = cardInfo["card_faces"][1]["image_uris"]["normal"],
                filename = ".temp/tb" + append + str(x) + ".jpg"
            )
        else:
            getpost(
                url = cardInfo["image_uris"]["normal"],
                filename = ".temp/" + append + str(x) + ".jpg"
            )
    return flipCardNums

def stitchImages(deckName, numCards, numTokens, flipCardNums):

    # stitch card images into a 5x5 grid
    stitcher(deckName, list(range(numCards)))

    # stitch token images
    stitcher(deckName, list(range(numTokens)), "t")

    # stitch transform cards
    if len(flipCardNums):
        stitcher(deckName, flipCardNums, "tf")
        stitcher(deckName, flipCardNums, "tb")

def generateJSON(deckName, cardData, cardFrequency, tokenData, flipCardNums, cardBack = "magenta"):

    # main deck
    cardNames = [cardData[x]["name"] for x in range(len(cardData))]
    cardIDs = [cardIDGen(x) for x in range(len(cardData))]

    chunks = chunkify(cardIDs)
    numChunks = len(chunks)
    chunkLengths = [len(chunk) for chunk in chunks]
    deckImageList = zip(
        [str(x) for x in range(1, numChunks + 1)],
        [imageObject(
            *stitchDimensions(chunkLengths[x]),
            "images/" + deckName + "_" + str(x) + ".jpg",
            "assets/" + cardBack + ".jpg"
        ) for x in range(numChunks)]
    )
    deckImage = dict(deckImageList)

    cardNames = freqMult(cardFrequency, cardNames)
    cardIDs = freqMult(cardFrequency, cardIDs)

    mainDeck = {
        "Transform": transformObject(posY = 1),
        "Name": "DeckCustom",
        "ContainedObjects": [cardObject(name, id) for name, id in zip(cardNames, cardIDs)],
        "DeckIDs": cardIDs,
        "CustomDeck": deckImage
    }

    objectStates = [mainDeck]

    prevDeckNumber = numChunks

    # token deck
    if tokenData:
        tokenNames = [tokenData[x]["name"] for x in range(len(tokenData))]
        tokenIDs = [cardIDGen(x, prevDeckNumber*100) for x in range(len(tokenData))]

        chunks = chunkify(tokenIDs)
        numChunks = len(chunks)
        chunkLengths = [len(chunk) for chunk in chunks]
        tokenImageList = zip(
            [str(x) for x in range(prevDeckNumber + 1, prevDeckNumber + numChunks + 1)],
            [imageObject(
                *stitchDimensions(chunkLengths[x]),
                "images/" + deckName + "_t" + str(x) + ".jpg",
                "assets/" + cardBack + ".jpg"
            ) for x in range(numChunks)]
        )
        tokenImage = dict(tokenImageList)

        if len(tokenNames) == 1:
            tokenNames = tokenNames * 2
            tokenIDs = tokenIDs * 2

        tokenDeck = {
            "Transform": transformObject(posY = 1, posX = -4),
            "Name": "DeckCustom",
            "ContainedObjects": [cardObject(name, id) for name, id in zip(tokenNames, tokenIDs)],
            "DeckIDs": tokenIDs,
            "CustomDeck": tokenImage
        }

        objectStates += [tokenDeck]

        prevDeckNumber += numChunks

    # transform cards deck
    if flipCardNums:
        transformNames = [cardData[x]["name"] for x in flipCardNums]
        transformIDs = [cardIDGen(x, prevDeckNumber*100) for x in range(len(flipCardNums))]

        chunks = chunkify(transformIDs)
        numChunks = len(chunks)
        chunkLengths = [len(chunk) for chunk in chunks]
        frontImageList = zip(
            [str(x) for x in range(prevDeckNumber + 1, prevDeckNumber + numChunks + 1)],
            [imageObject(
                *stitchDimensions(chunkLengths[x]),
                "images/" + deckName + "_tf" + str(x) + ".jpg",
                "assets/" + cardBack + ".jpg"
            ) for x in range(numChunks)]
        )
        transformImageList = zip(
            [str(x) for x in range(prevDeckNumber + 1, prevDeckNumber + numChunks + 1)],
            [imageObject(
                *stitchDimensions(chunkLengths[x]),
                "images/" + deckName + "_tb" + str(x) + ".jpg",
                "images/" + deckName + "_tb" + str(x) + ".jpg",
                uniqueBack = True
            ) for x in range(numChunks)]
        )
        transformImage = dict(transformImageList)

        transformDeck = {
            "Transform": transformObject(posY = 1, posX = -8),
            "Name": "DeckCustom",
            "ContainedObjects": [cardObject(name, id) for name, id in zip(transformNames, transformIDs)],
            "DeckIDs": transformIDs,
            "CustomDeck": transformImage
        }

        objectStates += [transformDeck]

    jsonFile = {"ObjectStates": objectStates}

    with open("outputs/" + deckName + ".json", "w+") as file:
        json.dump(jsonFile, file, indent = 2)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print(str(len(sys.argv)) + " is an invalid number of arguments")
