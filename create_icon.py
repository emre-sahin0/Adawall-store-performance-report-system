from PIL import Image, ImageDraw

img = Image.new('RGBA', (256, 256), color=(0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse((0, 0, 256, 256), fill=(99, 186, 245))
draw.ellipse((50, 50, 206, 206), fill=(255, 255, 255))
img.save('static/favicon.ico')

print("Favicon oluşturuldu: static/favicon.ico") 