from PIL import Image

image = Image.open("receipts/bmv.jpg")
print("Original size:", image.size)

image.thumbnail((1500, 1500))
print("New size:", image.size)

image.save("receipts/bmv_small.jpg")