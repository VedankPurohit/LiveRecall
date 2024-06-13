import easyocr

reader = easyocr.Reader(['en']) # specify the language  
result = reader.readtext('image.png')

for (bbox, text, prob) in result:
    print(f'Text: {text}, Probability: {prob}')