from PIL import Image

image = Image.open("receipts/receipt1_small.jpg")

print("Size (width x height):", image.size)
print("Mode:", image.mode)
print("Format:", image.format)

image.show()