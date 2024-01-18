from pathlib import Path

import matplotlib.pyplot as plt

from util import PathOrStr


class ChartContainer:
    figure: plt.Figure


    def save(self, path: PathOrStr, make_parent: bool = False):
        if make_parent:
            Path(path).parent.mkdir(exist_ok=True)
        self.figure.savefig(str(path))
