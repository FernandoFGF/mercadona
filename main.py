"""
Punto de entrada de AI Grocery Planner.
"""
from core.logging_setup import setup_logging
from ui.dashboard import Dashboard


def main():
    setup_logging()
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
