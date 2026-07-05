class Panel:
    def __init__(self, left: float, top: float, right: float, bottom: float):
        self.left = float(left)
        self.top = float(top)
        self.right = float(right)
        self.bottom = float(bottom)

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def centerX(self) -> float:
        return (self.left + self.right) / 2.0

    @property
    def centerY(self) -> float:
        return (self.top + self.bottom) / 2.0

    def to_dict(self) -> dict:
        return {"left": self.left, "top": self.top, "right": self.right, "bottom": self.bottom}
