

# From: https://stackoverflow.com/questions/37765197/darken-or-lighten-a-color-in-matplotlib
def adjust_lightness(color, amount: float):
    # 1.0 is neutral

    import matplotlib.colors
    import colorsys
    try:
        c = matplotlib.colors.cnames[color]
    except KeyError:
        c = color
    c = colorsys.rgb_to_hls(*matplotlib.colors.to_rgb(c))
    return colorsys.hls_to_rgb(c[0], max(0.0, min(1.0, amount * c[1])), c[2])
