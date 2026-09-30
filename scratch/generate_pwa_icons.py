"""
Generates crisp, branded PWA icons in static/icons/
"""
import os
from PIL import Image, ImageDraw, ImageFont

icons_dir = "static/icons"
os.makedirs(icons_dir, exist_ok=True)

def create_car_icon(size):
    # Blue gradient / rounded rect background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle badge
    margin = int(size * 0.05)
    radius = int(size * 0.22)
    bg_color = (13, 110, 253, 255) # Bootstrap Primary
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=bg_color
    )

    # Inner decorative border
    inner_margin = margin + int(size * 0.03)
    inner_radius = int(radius * 0.85)
    draw.rounded_rectangle(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        radius=inner_radius,
        outline=(255, 255, 255, 60),
        width=max(1, int(size * 0.02))
    )

    # Stylized Car body
    cx, cy = size // 2, size // 2
    car_w = int(size * 0.58)
    car_h = int(size * 0.32)

    x1 = cx - car_w // 2
    x2 = cx + car_w // 2
    y1 = cy - car_h // 4
    y2 = cy + car_h // 2

    # Lower body
    draw.rounded_rectangle(
        [x1, y1 + int(car_h * 0.25), x2, y2],
        radius=int(size * 0.06),
        fill=(255, 255, 255, 255)
    )

    # Cabin (upper roof)
    cabin_w = int(car_w * 0.65)
    cx1 = cx - cabin_w // 2
    cx2 = cx + cabin_w // 2
    cy1 = y1 - int(car_h * 0.2)
    cy2 = y1 + int(car_h * 0.35)
    draw.rounded_rectangle(
        [cx1, cy1, cx2, cy2],
        radius=int(size * 0.06),
        fill=(255, 255, 255, 255)
    )

    # Wheels
    wheel_r = int(size * 0.08)
    w_y = y2
    w1_x = x1 + int(car_w * 0.22)
    w2_x = x2 - int(car_w * 0.22)
    # Wheel 1
    draw.ellipse([w1_x - wheel_r, w_y - wheel_r, w1_x + wheel_r, w_y + wheel_r], fill=(15, 23, 42, 255))
    draw.ellipse([w1_x - wheel_r//2, w_y - wheel_r//2, w1_x + wheel_r//2, w_y + wheel_r//2], fill=(255, 255, 255, 255))
    # Wheel 2
    draw.ellipse([w2_x - wheel_r, w_y - wheel_r, w2_x + wheel_r, w_y + wheel_r], fill=(15, 23, 42, 255))
    draw.ellipse([w2_x - wheel_r//2, w_y - wheel_r//2, w2_x + wheel_r//2, w_y + wheel_r//2], fill=(255, 255, 255, 255))

    return img

icon192 = create_car_icon(192)
icon192.save(os.path.join(icons_dir, "icon-192.png"))

icon512 = create_car_icon(512)
icon512.save(os.path.join(icons_dir, "icon-512.png"))

apple_icon = create_car_icon(180)
apple_icon.save(os.path.join(icons_dir, "apple-touch-icon.png"))

print("PWA icons generated successfully in", icons_dir)

