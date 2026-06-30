"""
Punto de entrada de AI Grocery Planner.
"""
from ui.dashboard import Dashboard


def main():
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
