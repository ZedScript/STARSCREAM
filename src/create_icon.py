import math
from PIL import Image, ImageDraw, ImageFilter

def create_starscream_icon(size=512):
    # Create canvas with alpha
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center_x = size / 2.0
    center_y = size / 2.0
    radius = size * 0.45
    
    # Outer dark hexagon / shield background with neon red border
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        px = center_x + radius * math.cos(angle)
        py = center_y + radius * math.sin(angle)
        points.append((px, py))
        
    # Dark cyberpunk chassis
    draw.polygon(points, fill=(13, 16, 24, 255), outline=(255, 42, 95, 255), width=int(size * 0.025))
    
    # Inner metallic edge
    inner_points = []
    inner_r = radius * 0.88
    for i in range(6):
        angle = math.radians(60 * i - 30)
        px = center_x + inner_r * math.cos(angle)
        py = center_y + inner_r * math.sin(angle)
        inner_points.append((px, py))
    draw.polygon(inner_points, outline=(40, 52, 75, 255), width=int(size * 0.015))
    
    # Sharp stylized "S" + supersonic Star wings
    # Left wing
    left_wing = [
        (center_x - radius * 0.72, center_y - radius * 0.25),
        (center_x - radius * 0.15, center_y - radius * 0.48),
        (center_x - radius * 0.25, center_y - radius * 0.05),
    ]
    draw.polygon(left_wing, fill=(255, 42, 95, 255))
    
    # Right wing
    right_wing = [
        (center_x + radius * 0.72, center_y + radius * 0.25),
        (center_x + radius * 0.15, center_y + radius * 0.48),
        (center_x + radius * 0.25, center_y + radius * 0.05),
    ]
    draw.polygon(right_wing, fill=(0, 242, 254, 255))
    
    # Core glowing record circle
    rec_r = radius * 0.38
    rec_box = [center_x - rec_r, center_y - rec_r, center_x + rec_r, center_y + rec_r]
    draw.ellipse(rec_box, fill=(18, 22, 33, 255), outline=(255, 42, 95, 255), width=int(size * 0.02))
    
    # Center Red Record Core
    core_r = radius * 0.22
    core_box = [center_x - core_r, center_y - core_r, center_x + core_r, center_y + core_r]
    draw.ellipse(core_box, fill=(255, 10, 70, 255))
    
    # High-intensity center glint
    glint_r = radius * 0.07
    glint_box = [center_x - glint_r - 8, center_y - glint_r - 8, center_x + glint_r - 8, center_y + glint_r - 8]
    draw.ellipse(glint_box, fill=(255, 255, 255, 220))
    
    return img

if __name__ == "__main__":
    icon_512 = create_starscream_icon(512)
    icon_512.save("D:/STARSCREAM/assets/icon.png", "PNG")
    
    # Generate multi-resolution ICO for Windows
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icon_512.save("D:/STARSCREAM/assets/icon.ico", format="ICO", sizes=sizes)
    print("Branded icon.png and icon.ico created successfully!")
