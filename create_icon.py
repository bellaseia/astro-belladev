"""Genera el icono de Astro BellaDev: estrella de 4 puntas."""
import struct
import math
import zlib

def create_ico():
    """Crea un .ico con estrella de 4 puntas azul BellaDev."""
    size = 256
    pixels = []

    cx, cy = size // 2, size // 2

    for y in range(size):
        row = []
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)

            # Fondo circular oscuro con gradiente
            if dist > 120:
                row.append((0, 0, 0, 0))
                continue

            bg_alpha = max(0, int(255 * (1 - dist / 120)))
            r_bg = int(12 * (1 - dist / 140))
            g_bg = int(16 * (1 - dist / 140))
            b_bg = int(32 * (1 - dist / 140))

            # Estrella de 4 puntas
            angle = math.atan2(dy, dx)

            # 4 puntas con coseno
            spike = abs(math.cos(2 * angle))
            spike = spike ** 3  # hacer puntas mas finas

            # Brillo de la estrella
            star_radius = 8 + spike * 100
            if dist < star_radius:
                t = 1 - dist / star_radius
                t = t ** 0.5

                # Color BellaDev azul
                r = int(74 + 180 * t)
                g = int(127 + 128 * t)
                b = int(181 + 74 * t)

                # Halo central blanco
                if dist < 12:
                    core_t = 1 - dist / 12
                    r = int(r + (255 - r) * core_t ** 2)
                    g = int(g + (255 - g) * core_t ** 2)
                    b = int(b + (255 - b) * core_t ** 2)

                alpha = int(255 * t)
                alpha = max(alpha, bg_alpha)
                r = min(255, max(0, r))
                g = min(255, max(0, g))
                b = min(255, max(0, b))
                row.append((r, g, b, alpha))
            else:
                # Halo difuso
                halo_dist = dist - star_radius
                if halo_dist < 20 and spike > 0.3:
                    halo_t = 1 - halo_dist / 20
                    r = int(74 * halo_t * 0.3)
                    g = int(127 * halo_t * 0.3)
                    b = int(181 * halo_t * 0.3)
                    alpha = int(100 * halo_t)
                    alpha = max(alpha, bg_alpha)
                    row.append((r, g, b, alpha))
                else:
                    row.append((r_bg, g_bg, b_bg, bg_alpha))

        pixels.append(row)

    # Crear PNG
    def make_png(pixels, w, h):
        raw = b""
        for row in pixels:
            raw += b"\x00"
            for r, g, b, a in row:
                raw += struct.pack("BBBB", r, g, b, a)

        def chunk(ctype, data):
            c = ctype + data
            crc = zlib.crc32(c) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

        png = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
        png += chunk(b"IHDR", ihdr)
        compressed = zlib.compress(raw)
        png += chunk(b"IDAT", compressed)
        png += chunk(b"IEND", b"")
        return png

    png_data = make_png(pixels, size, size)

    # ICO format
    ico = struct.pack("<HHH", 0, 1, 1)  # header
    ico += struct.pack("<BBBBHHII",
        0, 0,  # 256x256
        0, 0,  # colors, reserved
        1, 32,  # planes, bpp
        len(png_data),  # size
        22,  # offset
    )
    ico += png_data

    with open("astro_belladev.ico", "wb") as f:
        f.write(ico)

    # Also save PNG
    with open("astro_belladev.png", "wb") as f:
        f.write(png_data)

    print(f"Icon: astro_belladev.ico ({len(ico)} bytes)")
    print(f"PNG: astro_belladev.png ({len(png_data)} bytes)")

if __name__ == "__main__":
    create_ico()
