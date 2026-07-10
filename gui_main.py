import logging
import tkinter as tk
from pathlib import Path

from src.uniprot_enzyme_explorer.logger_setup import setup_logging
from src.uniprot_enzyme_explorer.ui import EnzymeExplorerApp


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_FILE = PROJECT_ROOT / "logs" / "app.log"


def main():
    setup_logging(LOG_FILE)
    logging.info("Uruchomiono interfejs graficzny.")

    root = tk.Tk()
    EnzymeExplorerApp(root, PROJECT_ROOT)
    root.mainloop()


if __name__ == "__main__":
    main()
