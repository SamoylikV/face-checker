import json

def loadFaces():
    try:
        f = open('faces/faces.json')
        data = json.load(f)
        return data, None
    except Exception as e:
        return None, repr(e)

def saveFaces(data):
    try:
        with open('faces/faces.json', 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        return True, None
    except Exception as e:
        return None, repr(e)
