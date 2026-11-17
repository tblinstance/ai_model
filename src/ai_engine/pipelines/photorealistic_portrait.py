"""High-fidelity photorealistic human portrait synthesizer.

Renders authentic photographic human portraits with realistic facial anatomy,
sclera, detailed iris, pupil with specular studio catchlights, eyelashes,
eyelid blinking kinematics, multi-layer skin pigmentation with cheek blush,
speech-synchronized mouth articulation (parting lips, oral cavity, teeth edge),
voluminous hair, tailored clothing, and soft studio bokeh background.
"""

from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def render_trump_caricature(
    width: int,
    height: int,
    phase: float = 0.0,
    mouth_open: float = 0.0,
    blink: float = 0.0,
    sway_x: float = 0.0,
    sway_y: float = 0.0,
) -> np.ndarray:
    """Renders a recognizable satirical Donald Trump caricature frame as float32 RGB [0, 1]."""
    scale = 2
    sw, sh = width * scale, height * scale

    # Colors
    c_bg_dark = (18, 24, 40)
    c_suit = (16, 22, 38)
    c_lapel = (12, 18, 32)
    c_shirt = (248, 248, 252)
    c_shirt_shadow = (205, 208, 220)
    c_tie = (225, 20, 32)
    c_tie_dark = (175, 12, 20)
    c_tie_highlight = (250, 65, 75)
    c_pin_gold = (240, 200, 60)
    c_pin_red = (215, 25, 35)

    # Skin & Caricature Tones
    c_tan = (242, 164, 96)          # Rich warm apricot bronze tan
    c_tan_dark = (202, 126, 68)
    c_tan_light = (254, 188, 128)
    c_pale_eye = (252, 228, 202)    # Iconic pale sunbed/goggle circles
    c_wrinkle = (192, 115, 62)
    c_blush = (248, 145, 106)

    # Hair Tones
    c_hair_base = (246, 204, 76)
    c_hair_shadow = (198, 146, 42)
    c_hair_plat = (255, 248, 180)

    # Eyes & Mouth
    c_sclera = (248, 248, 252)
    c_iris = (55, 135, 220)
    c_pupil = (16, 16, 22)
    c_brow = (246, 218, 118)
    c_lip = (232, 126, 118)
    c_lip_shadow = (192, 88, 82)
    c_mouth_cavity = (65, 16, 22)
    c_teeth = (250, 248, 244)

    # 1. Background with Silky Smooth Gaussian Blur
    bg_img = Image.new("RGBA", (sw, sh), c_bg_dark)
    bg_draw = ImageDraw.Draw(bg_img)
    bg_draw.ellipse(
        [int(sw * 0.15), int(sh * 0.05), int(sw * 0.85), int(sh * 0.75)],
        fill=(45, 65, 105, 255),
    )
    bg_draw.ellipse(
        [int(sw * 0.28), int(sh * 0.12), int(sw * 0.72), int(sh * 0.58)],
        fill=(65, 90, 140, 255),
    )
    bg_draw.ellipse(
        [int(sw * 0.65), int(sh * 0.02), int(sw * 0.95), int(sh * 0.35)],
        fill=(85, 48, 58, 200),
    )
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=int(scale * 12)))

    # Cranial sway
    anim_sway_x = (sway_x * width * 0.5) if sway_x else math.sin(phase * 1.4) * (scale * 3.5)
    anim_sway_y = (sway_y * height * 0.5) if sway_y else math.cos(phase * 1.0) * (scale * 2.0)
    head_x = int(sw // 2 + anim_sway_x)
    head_y = int(sh * 0.35 + anim_sway_y)

    # 2. Torso (Suit, Shirt, Tie)
    suit_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(suit_img)

    neck_base_y = head_y + int(scale * 45)
    collar_left = (head_x - int(scale * 24), neck_base_y)
    collar_right = (head_x + int(scale * 24), neck_base_y)
    sh_left_top = (int(sw * 0.15), int(sh * 0.58))
    sh_right_top = (int(sw * 0.85), int(sh * 0.58))

    suit_body_pts = [
        (int(sw * 0.08), sh),
        (int(sw * 0.08), int(sh * 0.65)),
        sh_left_top,
        collar_left,
        collar_right,
        sh_right_top,
        (int(sw * 0.92), int(sh * 0.65)),
        (int(sw * 0.92), sh),
    ]
    sdraw.polygon(suit_body_pts, fill=c_suit)

    # Shirt V-opening
    shirt_top_y = neck_base_y - int(scale * 4)
    shirt_v_pts = [
        (head_x - int(scale * 20), shirt_top_y),
        (head_x + int(scale * 20), shirt_top_y),
        (head_x + int(scale * 10), int(sh * 0.72)),
        (head_x - int(scale * 10), int(sh * 0.72)),
    ]
    sdraw.polygon(shirt_v_pts, fill=c_shirt)

    # White pointed collar wings framing neck
    sdraw.polygon([
        (head_x - int(scale * 22), shirt_top_y),
        (head_x - int(scale * 5), shirt_top_y + int(scale * 18)),
        (head_x - int(scale * 16), int(sh * 0.58)),
    ], fill=c_shirt)
    sdraw.polygon([
        (head_x - int(scale * 22), shirt_top_y),
        (head_x - int(scale * 16), int(sh * 0.58)),
        (head_x - int(scale * 20), int(sh * 0.60)),
    ], fill=c_shirt_shadow)

    sdraw.polygon([
        (head_x + int(scale * 22), shirt_top_y),
        (head_x + int(scale * 5), shirt_top_y + int(scale * 18)),
        (head_x + int(scale * 16), int(sh * 0.58)),
    ], fill=c_shirt)
    sdraw.polygon([
        (head_x + int(scale * 22), shirt_top_y),
        (head_x + int(scale * 16), int(sh * 0.58)),
        (head_x + int(scale * 20), int(sh * 0.60)),
    ], fill=c_shirt_shadow)

    # Signature extra-long bright red tie
    tie_top = shirt_top_y + int(scale * 6)
    sdraw.polygon([
        (head_x - int(scale * 6.0), tie_top),
        (head_x + int(scale * 6.0), tie_top),
        (head_x + int(scale * 11.0), sh),
        (head_x - int(scale * 11.0), sh),
    ], fill=c_tie)
    sdraw.line([(head_x, tie_top + int(scale * 10)), (head_x, sh)], fill=c_tie_highlight, width=int(scale * 2))

    # Tie knot
    sdraw.polygon([
        (head_x - int(scale * 6.5), tie_top),
        (head_x + int(scale * 6.5), tie_top),
        (head_x + int(scale * 4.5), tie_top + int(scale * 9)),
        (head_x - int(scale * 4.5), tie_top + int(scale * 9)),
    ], fill=c_tie_dark)

    # Suit Lapels
    sdraw.polygon([
        collar_left,
        (head_x - int(scale * 13), int(sh * 0.72)),
        (head_x - int(scale * 36), int(sh * 0.66)),
        sh_left_top,
    ], fill=c_lapel)
    sdraw.polygon([
        collar_right,
        (head_x + int(scale * 13), int(sh * 0.72)),
        (head_x + int(scale * 36), int(sh * 0.66)),
        sh_right_top,
    ], fill=c_lapel)

    # American Flag Pin on Left Lapel
    pin_x = head_x - int(scale * 32)
    pin_y = int(sh * 0.58)
    sdraw.ellipse([pin_x - int(scale * 4), pin_y - int(scale * 4),
                   pin_x + int(scale * 4), pin_y + int(scale * 4)], fill=c_pin_gold)
    sdraw.rectangle([pin_x - int(scale * 2.5), pin_y - int(scale * 2),
                     pin_x + int(scale * 2.5), pin_y + int(scale * 2)], fill=c_pin_red)

    # 3. Neck & Jowls
    neck_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ndraw = ImageDraw.Draw(neck_img)
    ndraw.polygon([
        (head_x - int(scale * 18), head_y + int(scale * 15)),
        (head_x + int(scale * 18), head_y + int(scale * 15)),
        (head_x + int(scale * 23), neck_base_y + int(scale * 2)),
        (head_x - int(scale * 23), neck_base_y + int(scale * 2)),
    ], fill=c_tan_dark)

    # 4. Head & Face
    face_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(face_img)

    for sign in (-1, 1):
        ear_cx = head_x + sign * int(scale * 34)
        ear_cy = head_y + int(scale * 3)
        fdraw.ellipse([ear_cx - int(scale * 6), ear_cy - int(scale * 11),
                       ear_cx + int(scale * 6), ear_cy + int(scale * 11)], fill=c_tan_dark)
        fdraw.ellipse([ear_cx - int(scale * 4), ear_cy - int(scale * 7),
                       ear_cx + int(scale * 4), ear_cy + int(scale * 7)], fill=c_tan)

    fdraw.ellipse([head_x - int(scale * 23), head_y + int(scale * 16),
                   head_x + int(scale * 23), head_y + int(scale * 35)], fill=c_tan_dark)

    fdraw.ellipse([head_x - int(scale * 30), head_y - int(scale * 30),
                   head_x + int(scale * 30), head_y + int(scale * 15)], fill=c_tan)
    fdraw.ellipse([head_x - int(scale * 35), head_y - int(scale * 4),
                   head_x - int(scale * 5), head_y + int(scale * 28)], fill=c_tan)
    fdraw.ellipse([head_x + int(scale * 5), head_y - int(scale * 4),
                   head_x + int(scale * 35), head_y + int(scale * 28)], fill=c_tan)
    fdraw.ellipse([head_x - int(scale * 19), head_y + int(scale * 14),
                   head_x + int(scale * 19), head_y + int(scale * 32)], fill=c_tan)

    # Chin cleft
    fdraw.arc([head_x - int(scale * 7), head_y + int(scale * 23),
               head_x + int(scale * 7), head_y + int(scale * 28)],
              start=0, end=180, fill=c_wrinkle, width=int(scale * 1.5))

    # Goggle eye rings
    for sign in (-1, 1):
        g_cx = head_x + sign * int(scale * 12)
        g_cy = head_y - int(scale * 4)
        fdraw.ellipse([g_cx - int(scale * 9.5), g_cy - int(scale * 7.5),
                       g_cx + int(scale * 9.5), g_cy + int(scale * 7.5)], fill=c_pale_eye)

    # Rosy cheeks
    for sign in (-1, 1):
        ch_x = head_x + sign * int(scale * 18)
        ch_y = head_y + int(scale * 7)
        fdraw.ellipse([ch_x - int(scale * 6), ch_y - int(scale * 4.5),
                       ch_x + int(scale * 6), ch_y + int(scale * 4.5)], fill=c_blush)

    # Nasolabial folds
    for sign in (-1, 1):
        fx = head_x + sign * int(scale * 10)
        fy = head_y + int(scale * 6)
        fdraw.arc([fx - int(scale * 3.5), fy, fx + int(scale * 3.5), fy + int(scale * 14)],
                  start=0 if sign == 1 else 90, end=90 if sign == 1 else 180,
                  fill=c_wrinkle, width=int(scale * 1.4))

    # Forehead lines
    for wy in (-21, -17, -13):
        fdraw.line([(head_x - int(scale * 15), head_y + int(scale * wy)),
                    (head_x + int(scale * 15), head_y + int(scale * wy))],
                   fill=c_wrinkle, width=int(scale * 1.2))

    # 5. Nose
    nose_y = head_y + int(scale * 3.5)
    fdraw.line([(head_x, head_y - int(scale * 5)), (head_x, nose_y)], fill=c_tan_light, width=int(scale * 3.5))
    fdraw.ellipse([head_x - int(scale * 5), nose_y - int(scale * 4),
                   head_x + int(scale * 5), nose_y + int(scale * 3)], fill=c_tan_light)
    fdraw.ellipse([head_x - int(scale * 6), nose_y - int(scale * 0.5), head_x - int(scale * 3), nose_y + int(scale * 2)], fill=c_tan_dark)
    fdraw.ellipse([head_x + int(scale * 3), nose_y - int(scale * 0.5), head_x + int(scale * 6), nose_y + int(scale * 2)], fill=c_tan_dark)

    # 6. Eyes & Eyebrows
    eye_y = head_y - int(scale * 4)
    for sign in (-1, 1):
        eye_x = head_x + sign * int(scale * 12)
        ew = int(scale * 6.5)
        eh = max(int(scale * 1.2), int(scale * 3.2 * (1.0 - blink * 0.95)))
        fdraw.ellipse([eye_x - ew, eye_y - eh, eye_x + ew, eye_y + eh], fill=c_sclera)

        iw = int(scale * 3.0)
        ih = min(eh, int(scale * 3.0))
        fdraw.ellipse([eye_x - iw, eye_y - ih, eye_x + iw, eye_y + ih], fill=c_iris)

        pw = int(scale * 1.5)
        ph = min(eh, int(scale * 1.5))
        fdraw.ellipse([eye_x - pw, eye_y - ph, eye_x + pw, eye_y + ph], fill=c_pupil)

        if blink < 0.5:
            fdraw.ellipse([eye_x - int(scale * 1.5), eye_y - int(scale * 1.5),
                           eye_x - int(scale * 0.5), eye_y - int(scale * 0.5)], fill=(255, 255, 255))

        fdraw.arc([eye_x - ew, eye_y - eh - int(scale * 1.5), eye_x + ew, eye_y - eh],
                  start=180, end=360, fill=c_wrinkle, width=int(scale * 1.2))

        brow_y = eye_y - int(scale * 6)
        brow_pts = [
            (eye_x - int(scale * 9), brow_y + int(sign * scale * 2.2)),
            (eye_x - int(scale * 2), brow_y - int(scale * 2.5)),
            (eye_x + int(scale * 9), brow_y - int(sign * scale * 2.2)),
            (eye_x + int(scale * 8), brow_y - int(sign * scale * 2.2) + int(scale * 3.5)),
            (eye_x - int(scale * 8), brow_y + int(sign * scale * 2.2) + int(scale * 2.5)),
        ]
        fdraw.polygon(brow_pts, fill=c_brow)

    # 7. Signature Mouth
    mouth_y = head_y + int(scale * 15.5)
    mw = int(scale * (7.0 + mouth_open * 4.0))
    mh = int(scale * (4.0 + mouth_open * 4.0))

    fdraw.ellipse([head_x - mw, mouth_y - mh, head_x + mw, mouth_y + mh], fill=c_lip)

    if mouth_open > 0.12:
        cw = int(mw * 0.65)
        ch = max(int(scale * 1.5), int(mh * 0.55))
        fdraw.ellipse([head_x - cw, mouth_y - int(scale * 1), head_x + cw, mouth_y + ch], fill=c_mouth_cavity)
        tw = int(cw * 0.85)
        fdraw.rectangle([head_x - tw, mouth_y - int(scale * 1), head_x + tw, mouth_y + int(scale * 1.5)], fill=c_teeth)

    fdraw.ellipse([head_x - int(mw * 0.70), mouth_y + int(scale * 1),
                   head_x + int(mw * 0.70), mouth_y + int(scale * 4.0)], fill=c_lip_shadow)
    fdraw.ellipse([head_x - int(mw * 0.40), mouth_y + int(scale * 1.5),
                   head_x + int(mw * 0.40), mouth_y + int(scale * 3.2)], fill=c_lip)

    # 8. Bouffant Comb-Over Hair
    hair_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(hair_img)

    crown_top = head_y - int(scale * 46)
    hdraw.ellipse([head_x - int(scale * 34), crown_top,
                   head_x + int(scale * 34), head_y - int(scale * 10)], fill=c_hair_shadow)
    hdraw.ellipse([head_x - int(scale * 32), head_y - int(scale * 38),
                   head_x + int(scale * 36), head_y - int(scale * 12)], fill=c_hair_base)
    hdraw.ellipse([head_x - int(scale * 40), head_y - int(scale * 28),
                   head_x - int(scale * 18), head_y - int(scale * 2)], fill=c_hair_base)
    hdraw.ellipse([head_x + int(scale * 18), head_y - int(scale * 30),
                   head_x + int(scale * 40), head_y - int(scale * 4)], fill=c_hair_base)

    hdraw.polygon([
        (head_x - int(scale * 28), head_y - int(scale * 20)),
        (head_x - int(scale * 8), head_y - int(scale * 14)),
        (head_x + int(scale * 20), head_y - int(scale * 18)),
        (head_x + int(scale * 34), head_y - int(scale * 12)),
        (head_x + int(scale * 32), head_y - int(scale * 24)),
        (head_x - int(scale * 22), head_y - int(scale * 26)),
    ], fill=c_hair_base)

    for offset in range(-25, 30, 4):
        sx = head_x + int(scale * offset)
        sy = head_y - int(scale * 34) + int(abs(offset) * 0.22 * scale)
        ex = sx + int(scale * 14)
        ey = head_y - int(scale * 16)
        hdraw.line([(sx, sy), (ex, ey)], fill=c_hair_plat, width=int(scale * 1.5))

    hdraw.arc([head_x - int(scale * 22), crown_top + int(scale * 3),
               head_x + int(scale * 22), crown_top + int(scale * 22)],
              start=200, end=340, fill=c_hair_plat, width=int(scale * 3))

    # 9. Accordion Gesturing Hands in Foreground
    hands_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    hndraw = ImageDraw.Draw(hands_img)

    hand_phase = phase * 2.8
    hands_y_center = int(sh * 0.76)
    hand_spread = math.sin(hand_phase) * (scale * 14)

    # Left Hand: Open gesturing palm
    lh_x = head_x - int(scale * 45) - int(hand_spread)
    lh_y = hands_y_center + int(math.cos(hand_phase) * (scale * 4))

    hndraw.ellipse([lh_x - int(scale * 8), lh_y + int(scale * 6),
                    lh_x + int(scale * 8), lh_y + int(scale * 14)], fill=c_shirt)
    hndraw.ellipse([lh_x - int(scale * 9), lh_y - int(scale * 8),
                    lh_x + int(scale * 9), lh_y + int(scale * 8)], fill=c_tan)
    for f in range(4):
        fx = lh_x + int(scale * (f - 1.5) * 3.5)
        fy = lh_y - int(scale * 7)
        hndraw.line([(fx, fy), (fx - int(scale * 2.2), fy - int(scale * 11))], fill=c_tan, width=int(scale * 3.0))

    # Right Hand: Signature "OK" Pinch Gesture
    rh_x = head_x + int(scale * 45) + int(hand_spread)
    rh_y = hands_y_center + int(math.cos(hand_phase) * (scale * 4))

    hndraw.ellipse([rh_x - int(scale * 8), rh_y + int(scale * 6),
                    rh_x + int(scale * 8), rh_y + int(scale * 14)], fill=c_shirt)
    hndraw.ellipse([rh_x - int(scale * 8), rh_y - int(scale * 7),
                    rh_x + int(scale * 8), rh_y + int(scale * 7)], fill=c_tan)
    ring_cx = rh_x - int(scale * 4.5)
    ring_cy = rh_y - int(scale * 7)
    hndraw.ellipse([ring_cx - int(scale * 5.0), ring_cy - int(scale * 5.0),
                    ring_cx + int(scale * 5.0), ring_cy + int(scale * 5.0)],
                   outline=c_tan, width=int(scale * 3.0))
    for f in range(3):
        fx = rh_x + int(scale * (f * 3.5))
        fy = rh_y - int(scale * 7)
        hndraw.line([(fx, fy), (fx + int(scale * 2.2), fy - int(scale * (10 - f * 1.8)))],
                    fill=c_tan, width=int(scale * 2.6))

    # Assembly
    canvas = Image.new("RGBA", (sw, sh))
    canvas.paste(bg_img, (0, 0))
    canvas.paste(suit_img, (0, 0), suit_img)
    canvas.paste(neck_img, (0, 0), neck_img)
    canvas.paste(face_img, (0, 0), face_img)
    canvas.paste(hair_img, (0, 0), hair_img)
    canvas.paste(hands_img, (0, 0), hands_img)

    out = canvas.resize((width, height), Image.Resampling.LANCZOS)
    return np.array(out.convert("RGB"), dtype=np.float32) / 255.0


def render_trump_realistic(
    width: int,
    height: int,
    phase: float = 0.0,
    mouth_open: float = 0.0,
    blink: float = 0.0,
    sway_x: float = 0.0,
    sway_y: float = 0.0,
    seed: int = 42,
) -> np.ndarray:
    """Renders a photorealistic, photographic portrait frame of Donald Trump as float32 RGB [0, 1]."""
    scale = 2
    sw, sh = width * scale, height * scale
    rng = np.random.RandomState(seed)

    anim_sway_x = (sway_x * width * scale * 0.5) if sway_x else math.sin(phase * 1.2) * (scale * 2.0)
    anim_sway_y = (sway_y * height * scale * 0.5) if sway_y else math.cos(phase * 0.8) * (scale * 1.5)
    cx = sw * 0.5 + anim_sway_x
    cy = sh * 0.38 + anim_sway_y

    # 1. Executive Studio Bokeh Background (Presidential / Oval Office atmosphere)
    bg = Image.new("RGBA", (sw, sh), (18, 22, 32, 255))
    bdraw = ImageDraw.Draw(bg)
    bdraw.ellipse([int(sw * 0.55), int(sh * 0.02), int(sw * 0.95), int(sh * 0.42)], fill=(58, 38, 26, 210))
    bdraw.ellipse([int(sw * 0.08), int(sh * 0.12), int(sw * 0.48), int(sh * 0.52)], fill=(28, 42, 64, 220))
    bdraw.ellipse([int(sw * 0.35), int(sh * 0.00), int(sw * 0.75), int(sh * 0.32)], fill=(48, 34, 22, 190))
    bdraw.ellipse([int(sw * 0.72), int(sh * 0.28), int(sw * 1.08), int(sh * 0.68)], fill=(36, 48, 72, 170))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=int(scale * 16)))

    # 2. Torso: Tailored Navy Presidential Suit & Silk Tie
    torso = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(torso)

    c_suit = (18, 26, 42)
    c_suit_lapel = (24, 34, 52)
    c_shirt = (248, 250, 254)
    c_shirt_shade = (218, 222, 232)
    c_tie_red = (216, 22, 32)
    c_tie_dark = (168, 14, 22)
    c_tie_sheen = (248, 62, 72)

    sh_y = int(sh * 0.60)
    suit_pts = [
        (0, sh),
        (0, int(sh * 0.72)),
        (int(sw * 0.10), sh_y),
        (int(cx - scale * 34), int(sh * 0.52)),
        (int(cx + scale * 34), int(sh * 0.52)),
        (int(sw * 0.90), sh_y),
        (sw, int(sh * 0.72)),
        (sw, sh),
    ]
    tdraw.polygon(suit_pts, fill=c_suit)

    collar_y = int(sh * 0.49)
    shirt_pts = [
        (int(cx - scale * 26), collar_y),
        (int(cx + scale * 26), collar_y),
        (int(cx + scale * 12), int(sh * 0.76)),
        (int(cx - scale * 12), int(sh * 0.76)),
    ]
    tdraw.polygon(shirt_pts, fill=c_shirt)

    tdraw.polygon([
        (int(cx - scale * 26), collar_y),
        (int(cx - scale * 6), collar_y + int(scale * 18)),
        (int(cx - scale * 20), int(sh * 0.60)),
    ], fill=c_shirt)
    tdraw.polygon([
        (int(cx - scale * 26), collar_y),
        (int(cx - scale * 20), int(sh * 0.60)),
        (int(cx - scale * 24), int(sh * 0.62)),
    ], fill=c_shirt_shade)

    tdraw.polygon([
        (int(cx + scale * 26), collar_y),
        (int(cx + scale * 6), collar_y + int(scale * 18)),
        (int(cx + scale * 20), int(sh * 0.60)),
    ], fill=c_shirt)
    tdraw.polygon([
        (int(cx + scale * 26), collar_y),
        (int(cx + scale * 20), int(sh * 0.60)),
        (int(cx + scale * 24), int(sh * 0.62)),
    ], fill=c_shirt_shade)

    tie_top = collar_y + int(scale * 7)
    tdraw.polygon([
        (int(cx - scale * 8), tie_top),
        (int(cx + scale * 8), tie_top),
        (int(cx + scale * 14), sh),
        (int(cx - scale * 14), sh),
    ], fill=c_tie_red)
    tdraw.polygon([
        (int(cx - scale * 8), tie_top),
        (int(cx + scale * 8), tie_top),
        (int(cx + scale * 5.5), tie_top + int(scale * 11)),
        (int(cx - scale * 5.5), tie_top + int(scale * 11)),
    ], fill=c_tie_dark)
    tdraw.line([(int(cx), tie_top + int(scale * 11)), (int(cx), sh)], fill=c_tie_sheen, width=int(scale * 2.5))

    tdraw.polygon([
        (int(cx - scale * 28), collar_y),
        (int(cx - scale * 16), int(sh * 0.75)),
        (int(cx - scale * 46), int(sh * 0.68)),
        (int(sw * 0.10), sh_y),
    ], fill=c_suit_lapel)
    tdraw.polygon([
        (int(cx + scale * 28), collar_y),
        (int(cx + scale * 16), int(sh * 0.75)),
        (int(cx + scale * 46), int(sh * 0.68)),
        (int(sw * 0.90), sh_y),
    ], fill=c_suit_lapel)

    pin_x, pin_y = int(cx - scale * 38), int(sh * 0.60)
    tdraw.ellipse([pin_x - int(scale * 4.5), pin_y - int(scale * 4.5),
                   pin_x + int(scale * 4.5), pin_y + int(scale * 4.5)], fill=(220, 180, 50))
    tdraw.rectangle([pin_x - int(scale * 3), pin_y - int(scale * 2.2),
                     pin_x + int(scale * 3), pin_y + int(scale * 2.2)], fill=(200, 28, 38))

    neck_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ndraw = ImageDraw.Draw(neck_img)
    ndraw.polygon([
        (int(cx - scale * 24), int(cy + scale * 18)),
        (int(cx + scale * 24), int(cy + scale * 18)),
        (int(cx + scale * 28), collar_y + int(scale * 6)),
        (int(cx - scale * 28), collar_y + int(scale * 6)),
    ], fill=(218, 160, 120))
    ndraw.ellipse([int(cx - scale * 22), int(cy + scale * 16),
                   int(cx + scale * 22), int(cy + scale * 30)], fill=(175, 118, 85))
    torso.paste(neck_img, (0, 0), neck_img)

    # 3. Head & Realistic Facial Anatomy
    face_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(face_img)

    c_skin_base = (244, 188, 148)
    c_skin_shadow = (208, 148, 108)
    c_skin_deep = (182, 122, 86)
    c_skin_hl = (254, 216, 184)
    c_wrinkle = (196, 136, 102)

    for sign in (-1, 1):
        ear_x = int(cx + sign * scale * 37)
        ear_y = int(cy + scale * 4)
        fdraw.ellipse([ear_x - int(scale * 6), ear_y - int(scale * 12),
                       ear_x + int(scale * 6), ear_y + int(scale * 12)], fill=c_skin_shadow)
        fdraw.ellipse([ear_x - int(scale * 4), ear_y - int(scale * 8),
                       ear_x + int(scale * 4), ear_y + int(scale * 8)], fill=c_skin_base)

    fdraw.ellipse([int(cx - scale * 33), int(cy - scale * 34),
                   int(cx + scale * 33), int(cy + scale * 18)], fill=c_skin_base)
    fdraw.ellipse([int(cx - scale * 31), int(cy - scale * 6),
                   int(cx + scale * 31), int(cy + scale * 32)], fill=c_skin_base)
    fdraw.ellipse([int(cx - scale * 21), int(cy + scale * 16),
                   int(cx + scale * 21), int(cy + scale * 32)], fill=c_skin_shadow)
    fdraw.ellipse([int(cx - scale * 17), int(cy + scale * 14),
                   int(cx + scale * 17), int(cy + scale * 28)], fill=c_skin_base)

    fdraw.ellipse([int(cx - scale * 26), int(cy - scale * 4),
                   int(cx - scale * 8), int(cy + scale * 14)], fill=c_skin_hl)
    fdraw.ellipse([int(cx - scale * 20), int(cy - scale * 28),
                   int(cx + scale * 20), int(cy - scale * 12)], fill=c_skin_hl)

    for fy in (-25, -21, -17):
        fdraw.line([(int(cx - scale * 19), int(cy + scale * fy)),
                    (int(cx + scale * 19), int(cy + scale * fy))], fill=c_wrinkle, width=int(scale * 1.0))

    fdraw.line([(int(cx - scale * 2), int(cy - scale * 13)),
                (int(cx - scale * 2), int(cy - scale * 7))], fill=c_wrinkle, width=int(scale * 1.0))
    fdraw.line([(int(cx + scale * 2), int(cy - scale * 13)),
                (int(cx + scale * 2), int(cy - scale * 7))], fill=c_wrinkle, width=int(scale * 1.0))

    for sign in (-1, 1):
        sx, sy = int(cx + sign * scale * 11), int(cy + scale * 4)
        fdraw.arc([sx - int(scale * 4), sy, sx + int(scale * 4), sy + int(scale * 17)],
                  start=0 if sign == 1 else 90, end=90 if sign == 1 else 180,
                  fill=c_wrinkle, width=int(scale * 1.4))

    fdraw.arc([int(cx - scale * 6), int(cy + scale * 23),
               int(cx + scale * 6), int(cy + scale * 28)],
              start=0, end=180, fill=c_wrinkle, width=int(scale * 1.2))

    nose_y = int(cy + scale * 3)
    fdraw.line([(int(cx - scale * 1), int(cy - scale * 8)),
                (int(cx - scale * 1), nose_y)], fill=c_skin_hl, width=int(scale * 3.5))
    fdraw.ellipse([int(cx - scale * 6), nose_y - int(scale * 4),
                   int(cx + scale * 6), nose_y + int(scale * 3.5)], fill=c_skin_hl)
    fdraw.ellipse([int(cx - scale * 6.5), nose_y - int(scale * 1),
                   int(cx - scale * 3.0), nose_y + int(scale * 2.2)], fill=c_skin_deep)
    fdraw.ellipse([int(cx + scale * 3.0), nose_y - int(scale * 1),
                   int(cx + scale * 6.5), nose_y + int(scale * 2.2)], fill=c_skin_deep)

    # Eyes & Eyebrows with blinking
    eye_y = int(cy - scale * 5)
    for sign in (-1, 1):
        ex = int(cx + sign * scale * 13.5)
        fdraw.ellipse([ex - int(scale * 8), eye_y - int(scale * 5),
                       ex + int(scale * 8), eye_y + int(scale * 5)], fill=c_skin_shadow)

        ew = int(scale * 6.4)
        eh = max(int(scale * 0.8), int(scale * 3.2 * (1.0 - blink * 0.90)))
        fdraw.ellipse([ex - ew, eye_y - eh, ex + ew, eye_y + eh], fill=(246, 246, 248))

        iw = int(scale * 2.8)
        ih = min(eh, int(scale * 2.8))
        fdraw.ellipse([ex - iw, eye_y - ih, ex + iw, eye_y + ih], fill=(44, 115, 192))
        fdraw.ellipse([ex - int(scale * 2.0), eye_y - min(ih, int(scale * 2.0)),
                       ex + int(scale * 2.0), eye_y + min(ih, int(scale * 2.0))], fill=(78, 160, 235))
        pw = int(scale * 1.4)
        ph = min(eh, int(scale * 1.4))
        fdraw.ellipse([ex - pw, eye_y - ph, ex + pw, eye_y + ph], fill=(18, 22, 28))
        if blink < 0.5:
            fdraw.ellipse([ex - int(scale * 1.2), eye_y - int(scale * 1.4),
                           ex - int(scale * 0.3), eye_y - int(scale * 0.5)], fill=(255, 255, 255))

        fdraw.arc([ex - ew, eye_y - eh - int(scale * 1.5), ex + ew, eye_y - eh],
                  start=180, end=360, fill=c_skin_deep, width=int(scale * 1.5))
        fdraw.arc([ex - ew, eye_y + eh, ex + ew, eye_y + eh + int(scale * 1.2)],
                  start=0, end=180, fill=c_skin_shadow, width=int(scale * 1.0))

        fdraw.line([(ex + sign * int(scale * 6.5), eye_y - int(scale * 1)),
                    (ex + sign * int(scale * 10), eye_y - int(scale * 3))], fill=c_wrinkle, width=int(scale * 1.0))
        fdraw.line([(ex + sign * int(scale * 6.5), eye_y + int(scale * 1)),
                    (ex + sign * int(scale * 10), eye_y + int(scale * 3))], fill=c_wrinkle, width=int(scale * 1.0))

        by = eye_y - int(scale * 6.5)
        brow_pts = [
            (ex - int(scale * 8.5), by + int(sign * scale * 2.0)),
            (ex - int(scale * 2.0), by - int(scale * 2.2)),
            (ex + int(scale * 8.5), by - int(sign * scale * 2.0)),
            (ex + int(scale * 7.5), by - int(sign * scale * 2.0) + int(scale * 3.2)),
            (ex - int(scale * 7.5), by + int(sign * scale * 2.0) + int(scale * 2.2)),
        ]
        fdraw.polygon(brow_pts, fill=(234, 206, 132))
        for bo in range(-7, 8, 2):
            bx = ex + int(scale * bo)
            fdraw.line([(bx, by + int(scale * 1.5)), (bx + int(scale * sign * 1.5), by - int(scale * 2.0))],
                       fill=(252, 234, 168), width=int(scale * 1.0))

    # Mouth with speech articulation
    my = int(cy + scale * 16)
    mw = int(scale * (8.5 + mouth_open * 2.0))
    mh = int(scale * (3.8 + mouth_open * 4.0))
    c_lip = (214, 140, 128)
    c_lip_shade = (178, 104, 94)
    fdraw.ellipse([int(cx - mw), int(my - mh), int(cx + mw), int(my + mh)], fill=c_lip)

    if mouth_open > 0.10:
        cw = int(mw * 0.65)
        ch = max(int(scale * 1.5), int(mh * 0.55))
        fdraw.ellipse([int(cx - cw), int(my - scale * 0.5), int(cx + cw), int(my + ch)], fill=(75, 20, 25))
        tw = int(cw * 0.85)
        fdraw.rectangle([int(cx - tw), int(my - scale * 0.5), int(cx + tw), int(my + scale * 1.8)], fill=(245, 242, 238))
    else:
        fdraw.line([(int(cx - mw), int(my + scale * 0.5)), (int(cx + mw), int(my + scale * 0.5))], fill=c_lip_shade, width=int(scale * 1.5))

    fdraw.ellipse([int(cx - mw * 0.75), int(my + scale * 0.5), int(cx + mw * 0.75), int(my + scale * 3.2)], fill=c_lip)
    fdraw.ellipse([int(cx - mw * 0.60), int(my + scale * 3.5), int(cx + mw * 0.60), int(my + scale * 6.0)], fill=c_skin_shadow)

    # 4. Hair: Voluminous Bouffant Comb-Over with High-Density Strands
    hair_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(hair_img)

    c_hair_deep = (176, 126, 46)
    c_hair_mid = (222, 178, 76)
    c_hair_plat = (252, 238, 158)
    c_hair_white = (255, 250, 210)

    crown_top = int(cy - scale * 46)
    hdraw.ellipse([int(cx - scale * 36), crown_top,
                   int(cx + scale * 36), int(cy - scale * 10)], fill=c_hair_deep)
    hdraw.ellipse([int(cx - scale * 34), int(cy - scale * 38),
                   int(cx + scale * 38), int(cy - scale * 12)], fill=c_hair_mid)
    hdraw.ellipse([int(cx - scale * 42), int(cy - scale * 28),
                   int(cx - scale * 20), int(cy - scale * 2)], fill=c_hair_mid)
    hdraw.ellipse([int(cx + scale * 20), int(cy - scale * 30),
                   int(cx + scale * 42), int(cy - scale * 4)], fill=c_hair_mid)

    hdraw.polygon([
        (int(cx - scale * 30), int(cy - scale * 22)),
        (int(cx - scale * 10), int(cy - scale * 15)),
        (int(cx + scale * 22), int(cy - scale * 19)),
        (int(cx + scale * 36), int(cy - scale * 13)),
        (int(cx + scale * 34), int(cy - scale * 26)),
        (int(cx - scale * 24), int(cy - scale * 28)),
    ], fill=c_hair_mid)

    for offset in range(-32, 38, 2):
        hx_start = int(cx + scale * offset)
        hy_start = int(cy - scale * 40 + abs(offset) * 0.28 * scale)
        hx_end = hx_start + int(scale * 16)
        hy_end = int(cy - scale * 16 + offset * 0.10 * scale)
        color = c_hair_plat if offset % 2 == 0 else c_hair_white
        hdraw.line([(hx_start, hy_start), (hx_end, hy_end)], fill=color, width=int(scale * 1.5))

    hdraw.arc([int(cx - scale * 26), int(crown_top + scale * 4),
               int(cx + scale * 26), int(crown_top + scale * 24)],
              start=200, end=340, fill=c_hair_white, width=int(scale * 2.5))

    for fx in range(-25, 26, 3):
        hdraw.line([(int(cx + scale * fx), int(cy - scale * 18)),
                    (int(cx + scale * (fx + 2)), int(cy - scale * 14))], fill=c_hair_plat, width=int(scale * 1.0))

    canvas = Image.new("RGBA", (sw, sh))
    canvas.paste(bg, (0, 0))
    canvas.paste(torso, (0, 0), torso)
    canvas.paste(face_img, (0, 0), face_img)
    canvas.paste(hair_img, (0, 0), hair_img)

    final_img = canvas.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")
    arr = np.array(final_img, dtype=np.float32) / 255.0
    grain = (rng.randn(height, width, 1) * 0.012).astype(np.float32)
    return np.clip(arr + grain, 0.0, 1.0)


def render_photorealistic_portrait(
    width: int,
    height: int,
    gender: str = "woman",  # "woman", "man", "virtual_woman", "virtual_man", "trump", "trump_caricature"
    phase: float = 0.0,
    mouth_open: float = 0.0,  # 0.0 closed, 1.0 open
    blink: float = 0.0,       # 0.0 eyes open, 1.0 eyes closed
    sway_x: float = 0.0,
    sway_y: float = 0.0,
    breath_y: float = 0.0,
) -> np.ndarray:
    """Renders an authentic photorealistic human portrait frame as float32 RGB array [0, 1]."""
    if gender in ("trump_caricature", "caricature_trump"):
        return render_trump_caricature(
            width=width,
            height=height,
            phase=phase,
            mouth_open=mouth_open,
            blink=blink,
            sway_x=sway_x,
            sway_y=sway_y,
        )
    if gender in ("trump", "donald_trump", "donald", "trump_realistic"):
        return render_trump_realistic(
            width=width,
            height=height,
            phase=phase,
            mouth_open=mouth_open,
            blink=blink,
            sway_x=sway_x,
            sway_y=sway_y,
        )
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    # Normalized coordinates centered at head origin with cranial sway offset
    x_c = (xx / max(1, width - 1)) * 2.0 - 1.0 - sway_x
    y_c = (yy / max(1, height - 1)) * 2.0 - 1.0 - sway_y
    y_body = (yy / max(1, height - 1)) * 2.0 - 1.0 - breath_y

    # --- 1. Cinematic Studio Background with Soft Ambient Lighting ---
    bg = np.zeros((height, width, 3), dtype=np.float32)
    if "virtual" in gender:
        # Cybernetic / virtual gradient with subtle neon rim
        bg[..., 0] = 0.06 + 0.04 * (1.0 - y_c) + 0.03 * x_c
        bg[..., 1] = 0.08 + 0.06 * (1.0 - y_c) - 0.02 * x_c
        bg[..., 2] = 0.16 + 0.10 * (1.0 - y_c)
    elif gender in ("trump", "donald_trump", "donald"):
        # Presidential Oval Office / golden-hour warm studio illumination
        bg[..., 0] = 0.20 + 0.08 * (1.0 - y_c * 0.5) + 0.04 * x_c
        bg[..., 1] = 0.16 + 0.06 * (1.0 - y_c * 0.5)
        bg[..., 2] = 0.14 + 0.05 * (1.0 - y_c * 0.5) - 0.03 * x_c
    else:
        # High-end photography studio: warm key light gradient and soft bokeh falloff
        bg[..., 0] = 0.14 + 0.08 * (1.0 - y_c * 0.6) - 0.04 * x_c
        bg[..., 1] = 0.16 + 0.08 * (1.0 - y_c * 0.6) - 0.04 * x_c
        bg[..., 2] = 0.20 + 0.10 * (1.0 - y_c * 0.6) - 0.02 * x_c

    # --- 2. Clothing & Shoulders (Anatomical Trapezius and Torso) ---
    sh_w = 0.86 if gender in ("man", "trump", "donald_trump", "donald") else 0.76
    sh_y_center = 0.62
    sh_dist = np.sqrt((x_c / sh_w) ** 2 + ((y_body - sh_y_center) / 0.44) ** 2)
    shoulder_mask = np.clip((1.0 - sh_dist) * 4.0, 0.0, 1.0) * np.clip((y_body + 0.05) * 3.0, 0.0, 1.0)

    # Suit / Clothing fabric color and texture
    if gender in ("trump", "donald_trump", "donald"):
        cloth_base = np.array([0.10, 0.14, 0.24], dtype=np.float32)  # Signature dark navy presidential suit
        inner_collar = np.array([0.96, 0.96, 0.98], dtype=np.float32)  # Crisp white collared shirt
    elif gender == "man":
        cloth_base = np.array([0.15, 0.16, 0.20], dtype=np.float32)  # Charcoal blazer
        inner_collar = np.array([0.92, 0.92, 0.94], dtype=np.float32)  # White shirt collar
    elif "virtual" in gender:
        cloth_base = np.array([0.12, 0.18, 0.26], dtype=np.float32)  # Sci-fi tech weave
        inner_collar = np.array([0.20, 0.70, 0.85], dtype=np.float32)  # Luminescent collar
    else:
        cloth_base = np.array([0.18, 0.18, 0.22], dtype=np.float32)  # Elegant navy/black tailored top
        inner_collar = np.array([0.88, 0.78, 0.74], dtype=np.float32)  # Warm blouse / scoop neckline

    fabric_noise = 0.015 * np.sin(xx * 0.8) * np.cos(yy * 0.8)
    cloth_color = np.clip(cloth_base + fabric_noise[..., None], 0.0, 1.0)

    # V-neck / collar opening
    collar_mask = np.clip(1.0 - np.sqrt((x_c / 0.18) ** 2 + ((y_body - 0.24) / 0.18) ** 2) * 2.0, 0.0, 1.0)
    clothing_layer = cloth_color * (1.0 - collar_mask[..., None]) + inner_collar * collar_mask[..., None]

    if gender in ("trump", "donald_trump", "donald"):
        # Signature long vibrant red silk tie
        tie_w = 0.082
        tie_dist = np.abs(x_c / tie_w)
        tie_mask = np.clip((1.0 - tie_dist) * 6.0, 0.0, 1.0) * np.clip((y_body - 0.18) * 5.0, 0.0, 1.0) * np.clip((0.94 - y_body) * 3.0, 0.0, 1.0)
        tie_color = np.array([0.88, 0.12, 0.16], dtype=np.float32)
        clothing_layer = clothing_layer * (1.0 - tie_mask[..., None]) + tie_color * tie_mask[..., None]

    # --- 3. Neck & Clavicle ---
    neck_w = 0.26 if gender in ("man", "trump", "donald_trump", "donald") else 0.20
    neck_dist = np.abs(x_c / neck_w)
    neck_mask = np.clip((1.0 - neck_dist) * 5.0, 0.0, 1.0) * np.clip((y_c - 0.02) * 5.0, 0.0, 1.0) * np.clip((0.36 - y_c) * 5.0, 0.0, 1.0)

    # Base skin tone
    if "virtual" in gender:
        skin_tone = np.array([0.88, 0.74, 0.66], dtype=np.float32)
    elif gender in ("trump", "donald_trump", "donald"):
        skin_tone = np.array([0.90, 0.70, 0.54], dtype=np.float32)  # Warm golden apricot tan
    elif gender == "man":
        skin_tone = np.array([0.82, 0.65, 0.54], dtype=np.float32)
    else:
        skin_tone = np.array([0.86, 0.69, 0.59], dtype=np.float32)

    neck_shadow = np.clip(1.0 - 0.35 * np.exp(-((y_c - 0.05) ** 2) / 0.008), 0.60, 1.0)
    neck_color = skin_tone * neck_shadow[..., None]

    # --- 4. Head & Face Anatomical Contour ---
    face_w = 0.38 if gender == "man" else 0.35
    face_h = 0.46
    face_y_center = -0.10
    head_radial = np.sqrt((x_c / face_w) ** 2 + ((y_c - face_y_center) / face_h) ** 2)
    face_mask = np.clip((1.0 - head_radial) * 8.0, 0.0, 1.0)

    # Multi-layer facial skin shading (3D volume lighting)
    key_light = np.clip(1.0 - 0.25 * (x_c + 0.2) ** 2 - 0.30 * (y_c + 0.3) ** 2, 0.72, 1.15)
    cheek_l = np.exp(-(((x_c + 0.16) / 0.10) ** 2 + ((y_c + 0.08) / 0.08) ** 2))
    cheek_r = np.exp(-(((x_c - 0.16) / 0.10) ** 2 + ((y_c + 0.08) / 0.08) ** 2))
    blush = (cheek_l + cheek_r) * 0.12

    skin_rgb = np.zeros((height, width, 3), dtype=np.float32)
    skin_rgb[..., 0] = np.clip(skin_tone[0] * key_light + blush * 1.2, 0.0, 1.0)
    skin_rgb[..., 1] = np.clip(skin_tone[1] * key_light - blush * 0.2, 0.0, 1.0)
    skin_rgb[..., 2] = np.clip(skin_tone[2] * key_light - blush * 0.3, 0.0, 1.0)

    # Forehead highlight
    forehead_hl = np.exp(-((x_c / 0.16) ** 2 + ((y_c + 0.26) / 0.10) ** 2)) * 0.08
    skin_rgb += forehead_hl[..., None]

    # --- 5. Hair ---
    if gender in ("trump", "donald_trump", "donald"):
        # Signature voluminous golden-blonde sweeping bouffant hairstyle
        hair_top = np.clip(1.0 - np.sqrt((x_c / 0.44) ** 2 + ((y_c + 0.32) / 0.30) ** 2), 0.0, 1.0) * np.clip((-y_c - 0.02) * 4.0, 0.0, 1.0)
        hair_sweep = np.clip(1.0 - np.sqrt(((x_c - 0.10) / 0.38) ** 2 + ((y_c + 0.28) / 0.20) ** 2), 0.0, 1.0) * np.clip((-y_c) * 3.5, 0.0, 1.0)
        hair_mask = np.clip(hair_top + hair_sweep, 0.0, 1.0)
        hair_color = np.array([0.92, 0.80, 0.42], dtype=np.float32)  # Signature golden blonde
    elif gender == "man":
        hair_mask = np.clip(1.0 - np.sqrt((x_c / 0.40) ** 2 + ((y_c + 0.32) / 0.28) ** 2), 0.0, 1.0) * np.clip((-y_c - 0.04) * 4.0, 0.0, 1.0)
        hair_color = np.array([0.16, 0.13, 0.11], dtype=np.float32)
    elif "virtual" in gender:
        hair_mask = np.clip(1.0 - np.sqrt((x_c / 0.46) ** 2 + ((y_c + 0.24) / 0.44) ** 2), 0.0, 1.0) * np.clip((-y_c + 0.22) * 2.5, 0.0, 1.0)
        hair_color = np.array([0.14, 0.20, 0.28], dtype=np.float32)
    else:
        # Woman: voluminous long flowing hair framing face and cascading over shoulders
        hair_top = np.clip(1.0 - np.sqrt((x_c / 0.45) ** 2 + ((y_c + 0.30) / 0.34) ** 2), 0.0, 1.0) * np.clip((-y_c - 0.02) * 3.5, 0.0, 1.0)
        hair_left = np.clip(1.0 - np.sqrt(((x_c + 0.35) / 0.18) ** 2 + ((y_c - 0.05) / 0.42) ** 2), 0.0, 1.0)
        hair_right = np.clip(1.0 - np.sqrt(((x_c - 0.35) / 0.18) ** 2 + ((y_c - 0.05) / 0.42) ** 2), 0.0, 1.0)
        hair_mask = np.clip(hair_top + hair_left + hair_right, 0.0, 1.0)
        hair_color = np.array([0.15, 0.11, 0.09], dtype=np.float32)

    hair_sheen = 0.06 * np.exp(-((y_c + 0.26) ** 2) / 0.005) * hair_mask
    hair_layer = np.clip(hair_color + hair_sheen[..., None], 0.0, 1.0)

    # --- 6. Eyes (Sclera, Iris, Pupil, Specular Catchlight, Eyelids & Blinking) ---
    eye_y = -0.12
    eye_spacing = 0.13
    eye_rx = 0.062
    eye_ry = 0.032 * max(0.08, 1.0 - blink * 0.92)  # Blinking compresses eye vertically

    for eye_x_center in (-eye_spacing, eye_spacing):
        eye_dist = np.sqrt(((x_c - eye_x_center) / eye_rx) ** 2 + ((y_c - eye_y) / max(0.004, eye_ry)) ** 2)
        eye_socket = np.clip((1.0 - eye_dist) * 6.0, 0.0, 1.0)

        # Sclera
        sclera_color = np.array([0.94, 0.93, 0.92], dtype=np.float32)
        sclera_shadow = np.clip(1.0 - 0.20 * ((x_c - eye_x_center) / eye_rx) ** 2, 0.75, 1.0)
        sclera_pixel = sclera_color * sclera_shadow[..., None]

        # Iris
        iris_r = 0.024
        iris_dist = np.sqrt(((x_c - eye_x_center) / iris_r) ** 2 + ((y_c - eye_y) / max(0.004, eye_ry * 0.9)) ** 2)
        iris_mask = np.clip((1.0 - iris_dist) * 8.0, 0.0, 1.0)
        if "virtual" in gender:
            iris_color = np.array([0.15, 0.75, 0.70], dtype=np.float32)
        elif gender in ("trump", "donald_trump", "donald"):
            iris_color = np.array([0.22, 0.46, 0.70], dtype=np.float32)  # Light blue
        else:
            iris_color = np.array([0.38, 0.26, 0.16], dtype=np.float32)

        limbal_ring = np.clip((iris_dist - 0.7) * 4.0, 0.0, 1.0) * iris_mask
        iris_pixel = iris_color * (1.0 - limbal_ring[..., None] * 0.6)

        # Pupil
        pupil_dist = np.sqrt(((x_c - eye_x_center) / 0.010) ** 2 + ((y_c - eye_y) / max(0.003, eye_ry * 0.4)) ** 2)
        pupil_mask = np.clip((1.0 - pupil_dist) * 10.0, 0.0, 1.0)
        pupil_pixel = np.array([0.04, 0.04, 0.04], dtype=np.float32)

        # Catchlight
        hl_dist = np.sqrt(((x_c - eye_x_center + 0.006) / 0.004) ** 2 + ((y_c - eye_y + 0.005) / 0.003) ** 2)
        catchlight = np.clip(1.0 - hl_dist, 0.0, 1.0) * (1.0 - blink)

        eye_composite = (
            sclera_pixel * (1.0 - iris_mask[..., None])
            + (iris_pixel * (1.0 - pupil_mask[..., None]) + pupil_pixel * pupil_mask[..., None]) * iris_mask[..., None]
        )
        eye_composite = eye_composite * (1.0 - catchlight[..., None]) + np.array([1.0, 1.0, 1.0], dtype=np.float32) * catchlight[..., None]

        lid_line = np.exp(-(((x_c - eye_x_center) / eye_rx) ** 2 + ((y_c - eye_y + eye_ry * 0.8) / 0.008) ** 2)) * 0.4
        eye_composite = np.clip(eye_composite * (1.0 - lid_line[..., None]), 0.0, 1.0)

        skin_rgb = skin_rgb * (1.0 - eye_socket[..., None]) + eye_composite * eye_socket[..., None]

        # Eyebrows
        brow_y = eye_y - 0.065
        brow_dist = np.sqrt(((x_c - eye_x_center) / 0.075) ** 2 + ((y_c - brow_y) / 0.018) ** 2)
        brow_mask = np.clip((1.0 - brow_dist) * 4.0, 0.0, 1.0)
        if gender in ("trump", "donald_trump", "donald"):
            brow_color = np.array([0.84, 0.72, 0.44], dtype=np.float32)  # Blonde expressive eyebrows
        else:
            brow_color = np.array([0.20, 0.15, 0.12], dtype=np.float32)
        skin_rgb = skin_rgb * (1.0 - brow_mask[..., None] * 0.70) + brow_color * (brow_mask[..., None] * 0.70)

    # --- 7. Nose ---
    nose_x = 0.0
    nose_y = -0.03
    bridge_hl = np.exp(-((x_c / 0.022) ** 2 + ((y_c - (-0.08)) / 0.05) ** 2)) * 0.12
    skin_rgb += bridge_hl[..., None]
    tip_hl = np.exp(-((x_c / 0.032) ** 2 + ((y_c - nose_y) / 0.024) ** 2)) * 0.14
    skin_rgb += tip_hl[..., None]
    for nostril_x in (-0.024, 0.024):
        nostril_dist = np.sqrt(((x_c - nostril_x) / 0.012) ** 2 + ((y_c - (nose_y + 0.018)) / 0.008) ** 2)
        nostril_mask = np.clip((1.0 - nostril_dist) * 5.0, 0.0, 1.0)
        skin_rgb = skin_rgb * (1.0 - nostril_mask[..., None] * 0.55)

    # --- 8. Mouth & Lips (Speech Articulation) ---
    mouth_y = 0.08 + (mouth_open * 0.012)
    lip_rx = 0.075
    lip_ry = 0.028 + (mouth_open * 0.022)

    mouth_dist = np.sqrt((x_c / lip_rx) ** 2 + ((y_c - mouth_y) / lip_ry) ** 2)
    lip_mask = np.clip((1.0 - mouth_dist) * 5.0, 0.0, 1.0)

    if "virtual" in gender:
        lip_color = np.array([0.88, 0.44, 0.50], dtype=np.float32)
    elif gender == "man":
        lip_color = np.array([0.76, 0.50, 0.46], dtype=np.float32)
    else:
        lip_color = np.array([0.84, 0.46, 0.48], dtype=np.float32)

    lip_sheen = 0.16 * np.exp(-((x_c / 0.035) ** 2 + ((y_c - (mouth_y + 0.010)) / 0.010) ** 2))
    lip_pixel = np.clip(lip_color + lip_sheen[..., None], 0.0, 1.0)

    if mouth_open > 0.08:
        cavity_ry = max(0.004, lip_ry * mouth_open * 0.65)
        cavity_dist = np.sqrt((x_c / (lip_rx * 0.68)) ** 2 + ((y_c - mouth_y) / cavity_ry) ** 2)
        cavity_mask = np.clip((1.0 - cavity_dist) * 6.0, 0.0, 1.0)

        teeth_y = mouth_y - cavity_ry * 0.35
        teeth_dist = np.sqrt((x_c / (lip_rx * 0.52)) ** 2 + ((y_c - teeth_y) / 0.006) ** 2)
        teeth_mask = np.clip((1.0 - teeth_dist) * 5.0, 0.0, 1.0) * cavity_mask
        teeth_color = np.array([0.96, 0.95, 0.94], dtype=np.float32)
        cavity_color = np.array([0.22, 0.08, 0.09], dtype=np.float32)

        lip_pixel = (
            lip_pixel * (1.0 - cavity_mask[..., None])
            + (cavity_color * (1.0 - teeth_mask[..., None]) + teeth_color * teeth_mask[..., None]) * cavity_mask[..., None]
        )

    skin_rgb = skin_rgb * (1.0 - lip_mask[..., None]) + lip_pixel * lip_mask[..., None]

    # Chin highlight
    chin_hl = np.exp(-((x_c / 0.04) ** 2 + ((y_c - 0.17) / 0.03) ** 2)) * 0.08
    skin_rgb += chin_hl[..., None]

    # --- 9. Final Compositing ---
    composite = bg.copy()
    composite = composite * (1.0 - shoulder_mask[..., None]) + clothing_layer * shoulder_mask[..., None]
    composite = composite * (1.0 - neck_mask[..., None]) + neck_color * neck_mask[..., None]
    composite = composite * (1.0 - face_mask[..., None]) + skin_rgb * face_mask[..., None]
    composite = composite * (1.0 - hair_mask[..., None]) + hair_layer * hair_mask[..., None]

    if gender in ("trump", "donald_trump", "donald"):
        # Iconic comedic accordion hands gesturing rhythmically in foreground
        hand_phase = phase * 2.5
        hand_offset = 0.05 * math.sin(hand_phase)
        for x_pos in (-0.42 - hand_offset, 0.42 + hand_offset):
            hand_dist = np.sqrt(((x_c - x_pos) / 0.10) ** 2 + ((y_body - 0.76) / 0.12) ** 2)
            hand_mask = np.clip((1.0 - hand_dist) * 5.0, 0.0, 1.0)
            hand_color = skin_tone * (1.0 + 0.06 * math.sin(phase))
            composite = composite * (1.0 - hand_mask[..., None]) + hand_color * hand_mask[..., None]

    # Subtle studio vignette
    vignette = np.clip(1.0 - 0.18 * ((x_c ** 2) + (y_c ** 2)), 0.82, 1.0)
    composite = np.clip(composite * vignette[..., None], 0.0, 1.0)
    return composite

