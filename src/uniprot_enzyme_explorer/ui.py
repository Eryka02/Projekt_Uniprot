import tkinter as tk
from pathlib import Path

from src.uniprot_enzyme_explorer.ui_actions import UiActionsMixin
from src.uniprot_enzyme_explorer.ui_layout import UiLayoutMixin


class EnzymeExplorerApp(UiLayoutMixin, UiActionsMixin):
    def __init__(
        self,
        root: tk.Tk,
        project_root: Path,
    ):
        self.root = root
        self.project_root = project_root
        self.enzymes = []
        self.selected_enzyme = None
        self.input_duplicate_count = 0
        self.input_duplicate_ids = {}
        self.unique_input_count = 0
        self.charts_window = None
        self._ignore_tab_change = False
        self._previous_tab = None
        self.initial_input_ids = []
        self.loaded_input_files_count = 0

        self.ids_text = tk.StringVar()
        self.status_text = tk.StringVar(value="Gotowe.")
        self.table_count_text = tk.StringVar(value="0 rekordów")
        self.details_title_text = tk.StringVar(value="Wybierz rekord z tabeli")
        self.details_subtitle_text = tk.StringVar(
            value="Po kliknięciu enzymu pokażą się jego szczegóły."
        )
        self.detail_values = {}

        self.root.title("UniProt Enzyme Explorer")
        self.root.geometry("1220x760")
        self.root.minsize(1100, 650)
        self.root.configure(bg="#eceff3")

        self._build_interface()
        self._reset_display()
