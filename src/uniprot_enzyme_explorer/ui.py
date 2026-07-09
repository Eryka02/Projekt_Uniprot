import logging
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.uniprot_enzyme_explorer.charts import create_charts
from src.uniprot_enzyme_explorer.pipeline import (
    harvest_enzymes,
    load_uniprot_ids,
    load_uniprot_ids_from_files,
    parse_uniprot_ids,
)
from src.uniprot_enzyme_explorer.reports import (
    export_to_csv,
    export_to_xlsx,
)
from src.uniprot_enzyme_explorer.sequence_qc import (
    find_duplicate_ids,
    prepare_non_redundant_set,
)
from src.uniprot_enzyme_explorer.storage import (
    export_all_enzymes_to_fasta,
    export_non_redundant_fasta,
    save_processed_records,
)


class EnzymeExplorerApp:
    def __init__(
        self,
        root: tk.Tk,
        project_root: Path,
        input_file: Path,
    ):
        self.root = root
        self.project_root = project_root
        self.input_file = input_file
        self.enzymes = []
        self.selected_enzyme = None
        self.input_duplicate_count = 0
        self.unique_input_count = 0
        self.saved_files = []
        self.charts_window = None
        self._ignore_tab_change = False
        self._previous_tab = None

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

        self._load_initial_ids()
        self._build_interface()
        self._reset_display()

    def _load_initial_ids(self):
        try:
            initial_ids = load_uniprot_ids(self.input_file)
        except OSError:
            initial_ids = []

        self.ids_text.set(", ".join(initial_ids))

    def _build_interface(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._configure_styles()

        shell = ttk.Frame(self.root, style="App.TFrame", padding=(18, 14, 18, 0))
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=4)
        shell.rowconfigure(2, weight=1)

        self._build_toolbar(shell)
        self._build_workspace(shell)
        self._build_bottom_tabs(shell)
        self._build_status_bar(shell)

    def _configure_styles(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#f8f9fb")
        style.configure("Toolbar.TFrame", background="#f8f9fb")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("PanelBody.TFrame", background="#ffffff")
        style.configure("PanelHeader.TFrame", background="#eef1f5")
        style.configure("Status.TFrame", background="#f3f4f6", relief="solid", borderwidth=1)
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Charts.TFrame", background="#ffffff")

        style.configure(
            "Title.TLabel",
            background="#f8f9fb",
            foreground="#172033",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#f8f9fb",
            foreground="#637083",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Field.TLabel",
            background="#f8f9fb",
            foreground="#374151",
            font=("Segoe UI", 9),
        )
        style.configure(
            "PanelHeader.TLabel",
            background="#eef1f5",
            foreground="#374151",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "PanelMuted.TLabel",
            background="#eef1f5",
            foreground="#6b7280",
            font=("Segoe UI", 9),
        )
        style.configure(
            "DetailTitle.TLabel",
            background="#ffffff",
            foreground="#111827",
            font=("Segoe UI", 15, "bold"),
        )
        style.configure(
            "DetailSubtitle.TLabel",
            background="#ffffff",
            foreground="#4b5563",
            font=("Segoe UI", 9),
        )
        style.configure(
            "DetailName.TLabel",
            background="#ffffff",
            foreground="#6b7280",
            font=("Segoe UI", 8),
        )
        style.configure(
            "DetailValue.TLabel",
            background="#ffffff",
            foreground="#111827",
            font=("Segoe UI", 8, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background="#f3f4f6",
            foreground="#374151",
            font=("Segoe UI", 9),
        )
        style.configure(
            "KpiLabel.TLabel",
            background="#ffffff",
            foreground="#637083",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Primary.TButton",
            background="#2563eb",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=(12, 7),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1d4ed8"), ("disabled", "#b9c6d7")],
            foreground=[("disabled", "#edf2f7")],
        )
        style.configure("TButton", font=("Segoe UI", 9), padding=(10, 7))
        style.configure("TEntry", padding=(8, 6))
        style.configure("TMenubutton", font=("Segoe UI", 9), padding=(10, 7))

        style.configure(
            "Treeview",
            rowheight=27,
            font=("Segoe UI", 8),
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#111827",
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 8, "bold"),
            background="#f8fafc",
            foreground="#4b5563",
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#111827")],
        )

    def _build_toolbar(self, parent: ttk.Frame):
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.columnconfigure(0, weight=1)

        input_area = ttk.Frame(toolbar, style="Toolbar.TFrame")
        input_area.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        input_area.columnconfigure(0, weight=1)

        ttk.Label(
            input_area,
            text="Identyfikatory UniProt",
            style="Field.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.ids_entry = ttk.Entry(
            input_area,
            textvariable=self.ids_text,
            font=("Consolas", 10),
        )
        self.ids_entry.grid(row=1, column=0, sticky="ew")

        buttons = ttk.Frame(toolbar, style="Toolbar.TFrame")
        buttons.grid(row=0, column=1, sticky="sew")
        buttons.rowconfigure(0, weight=1)

        self.files_button = ttk.Button(
            buttons,
            text="Wczytaj...",
            command=self.select_input_files,
        )
        self.files_button.grid(row=1, column=0, padx=(0, 8))

        self.download_button = ttk.Button(
            buttons,
            text="Pobierz i analizuj",
            command=self.start_download,
            style="Primary.TButton",
        )
        self.download_button.grid(row=1, column=1, padx=(0, 8))

        self.report_button = ttk.Menubutton(
            buttons,
            text="Zapisz raport",
            state="disabled",
        )
        self.report_menu = tk.Menu(self.report_button, tearoff=False)
        self.report_menu.add_command(label="CSV", command=self.save_csv)
        self.report_menu.add_command(label="XLSX", command=self.save_xlsx)
        self.report_button["menu"] = self.report_menu
        self.report_button.grid(row=1, column=2, padx=(0, 8))

        self.fasta_button = ttk.Button(
            buttons,
            text="Zapisz FASTA",
            command=self.save_fasta,
            state="disabled",
        )
        self.fasta_button.grid(row=1, column=3)

    def _build_workspace(self, parent: ttk.Frame):
        workspace = tk.PanedWindow(
            parent,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            bg="#d1d7df",
            bd=0,
            relief="flat",
        )
        workspace.grid(row=1, column=0, sticky="nsew")

        table_panel = ttk.Frame(workspace, style="Panel.TFrame")
        details_panel = ttk.Frame(workspace, style="Panel.TFrame")

        workspace.add(table_panel, minsize=670)
        workspace.add(details_panel, minsize=330)

        self._build_table_panel(table_panel)
        self._build_details_panel(details_panel)

    def _build_table_panel(self, parent: ttk.Frame):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        header = ttk.Frame(parent, style="PanelHeader.TFrame", padding=(10, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Tabela enzymów",
            style="PanelHeader.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            textvariable=self.table_count_text,
            style="PanelMuted.TLabel",
        ).grid(row=0, column=1, sticky="e")

        table_frame = ttk.Frame(parent, style="PanelBody.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = (
            "id",
            "name",
            "organism",
            "ec",
            "length",
            "mass",
            "reviewed",
            "qc",
            "hydrophobic",
            "cysteines",
            "decision",
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        settings = {
            "id": ("ID", 82, "w"),
            "name": ("Nazwa białka", 230, "w"),
            "organism": ("Organizm", 145, "w"),
            "ec": ("EC", 90, "w"),
            "length": ("aa", 64, "e"),
            "mass": ("Masa", 86, "e"),
            "reviewed": ("UniProt", 86, "w"),
            "qc": ("QC", 104, "w"),
            "hydrophobic": ("Hydrof.", 86, "e"),
            "cysteines": ("Cys.", 88, "e"),
            "decision": ("Decyzja", 138, "w"),
        }

        for column, (heading, width, anchor) in settings.items():
            self.table.heading(column, text=heading)
            self.table.column(column, width=width, minwidth=58, anchor=anchor)

        self.table.tag_configure("odd", background="#ffffff")
        self.table.tag_configure("even", background="#f8fafc")
        self.table.tag_configure("duplicate", foreground="#92400e")
        self.table.tag_configure("missing", foreground="#991b1b")
        self.table.bind("<<TreeviewSelect>>", self._on_table_select)
        self.table.bind("<Double-1>", self.show_selected_details)

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.table.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.table.xview,
        )

        self.table.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.table.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    def _build_details_panel(self, parent: ttk.Frame):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        header = ttk.Frame(parent, style="PanelHeader.TFrame", padding=(10, 6))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            header,
            text="Szczegóły enzymu",
            style="PanelHeader.TLabel",
        ).grid(row=0, column=0, sticky="w")

        body = ttk.Frame(parent, style="PanelBody.TFrame", padding=(14, 12))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

        ttk.Label(
            body,
            textvariable=self.details_title_text,
            style="DetailTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            body,
            textvariable=self.details_subtitle_text,
            style="DetailSubtitle.TLabel",
            wraplength=330,
        ).grid(row=1, column=0, sticky="ew", pady=(2, 12))

        self._create_detail_section(
            body,
            row=2,
            title="Informacje podstawowe",
            fields=[
                ("organism", "Organizm"),
                ("ec_number", "Numer EC"),
                ("reviewed_status", "Status UniProt"),
                ("sequence_length", "Długość sekwencji"),
                ("molecular_weight", "Masa cząsteczkowa"),
                ("length_category", "Kategoria długości"),
            ],
        )
        self._create_detail_section(
            body,
            row=3,
            title="Kontrola jakości",
            fields=[
                ("decision", "Decyzja programu"),
                ("qc_status", "Status QC"),
                ("duplicate_group", "Grupa duplikatów"),
                ("representative_id", "Reprezentant"),
            ],
        )
        self._create_detail_section(
            body,
            row=4,
            title="Statystyki sekwencji",
            fields=[
                ("hydrophobic", "Hydrofobowe"),
                ("cysteines", "Cysteiny"),
                ("most_common", "Najczęstszy aminokwas"),
            ],
        )

    def _create_detail_section(
        self,
        parent: ttk.Frame,
        row: int,
        title: str,
        fields: list[tuple[str, str]],
    ):
        section = ttk.Frame(parent, style="PanelBody.TFrame")
        section.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        section.columnconfigure(1, weight=1)

        ttk.Separator(section, orient="horizontal").grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 8),
        )
        ttk.Label(
            section,
            text=title,
            style="DetailValue.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))

        for index, (key, label) in enumerate(fields, start=2):
            value = tk.StringVar(value="-")
            self.detail_values[key] = value

            ttk.Label(
                section,
                text=label,
                style="DetailName.TLabel",
            ).grid(row=index, column=0, sticky="w", pady=2, padx=(0, 10))
            ttk.Label(
                section,
                textvariable=value,
                style="DetailValue.TLabel",
                wraplength=190,
            ).grid(row=index, column=1, sticky="w", pady=2)

    def _build_bottom_tabs(self, parent: ttk.Frame):
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

        self.interpretation_text = self._create_text_tab(
            self.notebook,
            "Interpretacja",
        )
        self.sequence_text = self._create_text_tab(
            self.notebook,
            "Sekwencja FASTA",
            font=("Consolas", 9),
        )
        self.duplicates_text = self._create_text_tab(
            self.notebook,
            "Duplikaty",
        )
        self.files_text = self._create_text_tab(
            self.notebook,
            "Pliki wynikowe",
        )
        self._create_charts_tab(self.notebook)
        self._previous_tab = self.notebook.tabs()[0]
        self.notebook.bind("<<NotebookTabChanged>>", self._handle_tab_change)

    def _create_text_tab(
        self,
        notebook: ttk.Notebook,
        title: str,
        font=("Segoe UI", 9),
    ):
        frame = ttk.Frame(notebook, style="PanelBody.TFrame", padding=8)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text = tk.Text(
            frame,
            wrap="word",
            height=5,
            font=font,
            bg="#ffffff",
            fg="#374151",
            relief="flat",
            padx=8,
            pady=6,
        )
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        notebook.add(frame, text=title)
        return text

    def _create_charts_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook, style="Charts.TFrame")
        self.charts_tab = frame
        notebook.add(frame, text="Wykresy")

    def _handle_tab_change(self, _event=None):
        if self._ignore_tab_change:
            return

        selected_tab = self.notebook.select()
        if selected_tab == str(self.charts_tab):
            previous_tab = self._previous_tab or self.notebook.tabs()[0]

            self._ignore_tab_change = True
            self.notebook.select(previous_tab)
            self._ignore_tab_change = False

            self.show_charts_window()
            return

        self._previous_tab = selected_tab

    def _build_status_bar(self, parent: ttk.Frame):
        status_bar = ttk.Frame(parent, style="Status.TFrame", padding=(10, 5))
        status_bar.grid(row=3, column=0, sticky="ew")
        status_bar.columnconfigure(0, weight=1)

        ttk.Label(
            status_bar,
            textvariable=self.status_text,
            style="Status.TLabel",
        ).grid(row=0, column=0, sticky="w")

    def _set_all_result_buttons(self, state: str):
        self.report_button.configure(state=state)
        self.fasta_button.configure(state=state)
        if hasattr(self, "charts_preview_button"):
            self.charts_preview_button.configure(state=state)
        if hasattr(self, "charts_save_button"):
            self.charts_save_button.configure(state=state)

    def _reset_display(self):
        if hasattr(self, "table"):
            for item in self.table.get_children():
                self.table.delete(item)

        self.table_count_text.set("0 rekordów")
        self.selected_enzyme = None
        self.saved_files = []
        self.details_title_text.set("Wybierz rekord z tabeli")
        self.details_subtitle_text.set(
            "Po kliknięciu enzymu pokażą się jego szczegóły."
        )

        for value in self.detail_values.values():
            value.set("-")

        self._set_text(
            self.interpretation_text,
            "Po pobraniu danych kliknij rekord w tabeli, aby zobaczyć interpretację.",
        )
        self._set_text(
            self.sequence_text,
            "Po pobraniu danych kliknij rekord w tabeli, aby zobaczyć sekwencję FASTA.",
        )
        self._set_text(
            self.duplicates_text,
            "Po analizie program pokaże tu powtórzone ID i grupy identycznych sekwencji.",
        )
        self._update_files_tab()
        self._set_all_result_buttons("disabled")

    def _set_text(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _decision_for(self, enzyme) -> str:
        if not enzyme.sequence:
            return "brak sekwencji"
        if not enzyme.is_representative:
            return "duplikat - pominięty"
        return "zostaje w FASTA"

    def _update_summary(self, enzymes, _total: int):
        records_count = len(enzymes)
        self.table_count_text.set(f"{records_count} rekordów")
        self.status_text.set("Analiza zakończona.")

    def select_input_files(self):
        selected_files = filedialog.askopenfilenames(
            parent=self.root,
            title="Wybierz pliki z identyfikatorami",
            filetypes=[
                ("Pliki tekstowe", "*.txt"),
                ("Wszystkie pliki", "*.*"),
            ],
        )

        if not selected_files:
            return

        try:
            file_paths = [
                Path(file_path)
                for file_path in selected_files
            ]

            uniprot_ids = load_uniprot_ids_from_files(file_paths)

            if not uniprot_ids:
                messagebox.showwarning(
                    "Brak identyfikatorów",
                    "Wybrane pliki nie zawierają identyfikatorów.",
                )
                return

            self.ids_text.set(", ".join(uniprot_ids))
            self.status_text.set(
                f"Wczytano {len(uniprot_ids)} identyfikatorów "
                f"z {len(file_paths)} plików."
            )

        except OSError as error:
            logging.exception("Błąd odczytu plików.")
            messagebox.showerror("Błąd pliku", str(error))

    def start_download(self):
        uniprot_ids = parse_uniprot_ids(self.ids_text.get())

        if not uniprot_ids:
            messagebox.showwarning(
                "Brak danych",
                "Wpisz przynajmniej jeden identyfikator UniProt.",
            )
            return

        duplicate_ids = find_duplicate_ids(uniprot_ids)
        self.input_duplicate_count = len(uniprot_ids) - len(set(uniprot_ids))
        self.unique_input_count = len(set(uniprot_ids))
        self.enzymes = []

        self._reset_display()
        self._set_all_result_buttons("disabled")
        self.download_button.configure(state="disabled")
        self.files_button.configure(state="disabled")
        self.ids_entry.configure(state="disabled")
        self.report_button.configure(state="disabled")
        self.fasta_button.configure(state="disabled")

        if duplicate_ids:
            self.status_text.set(
                f"Wykryto {len(duplicate_ids)} powtórzone ID. "
                f"Pobieranie {self.unique_input_count} unikalnych rekordów..."
            )
        else:
            self.status_text.set(
                f"Pobieranie {self.unique_input_count} rekordów..."
            )

        threading.Thread(
            target=self._download_data,
            args=(uniprot_ids,),
            daemon=True,
        ).start()

    def _download_data(self, uniprot_ids):
        try:
            enzymes, errors = harvest_enzymes(uniprot_ids)
            self.root.after(
                0,
                self._display_results,
                enzymes,
                errors,
                len(set(uniprot_ids)),
            )
        except Exception as error:
            logging.exception("Błąd podczas pracy GUI.")
            self.root.after(0, self._show_error, str(error))

    def _display_results(self, enzymes, errors, total):
        self.enzymes = enzymes
        save_processed_records(enzymes)

        for item in self.table.get_children():
            self.table.delete(item)

        for index, enzyme in enumerate(enzymes):
            tag = "even" if index % 2 else "odd"
            if not enzyme.sequence:
                tag = "missing"
            elif not enzyme.is_representative:
                tag = "duplicate"

            self.table.insert(
                "",
                tk.END,
                values=(
                    enzyme.uniprot_id,
                    enzyme.protein_name,
                    enzyme.organism,
                    enzyme.ec_number,
                    enzyme.sequence_length,
                    enzyme.molecular_weight,
                    enzyme.reviewed_status,
                    enzyme.qc_status,
                    f"{enzyme.hydrophobic_percent}%",
                    f"{enzyme.cysteine_count} ({enzyme.cysteine_percent}%)",
                    self._decision_for(enzyme),
                ),
                tags=(tag,),
            )

        self._update_summary(enzymes, total)
        self._update_duplicates_tab()
        self._update_files_tab()

        self.download_button.configure(state="normal")
        self.ids_entry.configure(state="normal")
        self.files_button.configure(state="normal")

        if enzymes:
            self._set_all_result_buttons("normal")
            first_item = self.table.get_children()[0]
            self.table.selection_set(first_item)
            self.table.focus(first_item)
            self._on_table_select()
        else:
            self._set_all_result_buttons("disabled")
            self._reset_details_only()
            self.status_text.set("Nie znaleziono poprawnych rekordów.")

        if errors:
            messagebox.showwarning("Niepełne wyniki", "\n".join(errors))

    def _on_table_select(self, _event=None):
        selected_item = self.table.selection()
        if not selected_item:
            self._reset_details_only()
            return

        row_index = self.table.index(selected_item[0])
        if row_index >= len(self.enzymes):
            self._reset_details_only()
            return

        enzyme = self.enzymes[row_index]
        self.selected_enzyme = enzyme
        self._update_details_panel(enzyme)
        self._update_selected_tabs(enzyme)

    def _reset_details_only(self):
        self.selected_enzyme = None
        self.details_title_text.set("Wybierz rekord z tabeli")
        self.details_subtitle_text.set(
            "Po kliknięciu enzymu pokażą się jego szczegóły."
        )
        for value in self.detail_values.values():
            value.set("-")

    def _update_details_panel(self, enzyme):
        self.details_title_text.set(enzyme.uniprot_id)
        self.details_subtitle_text.set(f"{enzyme.protein_name} | {enzyme.organism}")

        values = {
            "organism": enzyme.organism,
            "ec_number": enzyme.ec_number,
            "reviewed_status": enzyme.reviewed_status,
            "sequence_length": f"{enzyme.sequence_length} aa",
            "molecular_weight": f"{enzyme.molecular_weight} Da",
            "length_category": enzyme.sequence_length_category,
            "decision": self._decision_for(enzyme),
            "qc_status": enzyme.qc_status,
            "duplicate_group": enzyme.duplicate_group or "Brak",
            "representative_id": enzyme.representative_id or enzyme.uniprot_id,
            "hydrophobic": (
                f"{enzyme.hydrophobic_count} / {enzyme.hydrophobic_percent}%"
            ),
            "cysteines": f"{enzyme.cysteine_count} / {enzyme.cysteine_percent}%",
            "most_common": enzyme.most_common_amino_acid,
        }

        for key, value in values.items():
            self.detail_values[key].set(value)

    def _update_selected_tabs(self, enzyme):
        self._set_text(
            self.interpretation_text,
            self._format_interpretation_text(enzyme),
        )
        self._set_text(
            self.sequence_text,
            self._format_fasta_text(enzyme),
        )
        self._update_duplicates_tab(enzyme)
        self._update_files_tab()

    def _format_interpretation_text(self, enzyme) -> str:
        return (
            f"{enzyme.interpretation}\n\n"
            f"Decyzja programu: {self._decision_for(enzyme)}.\n"
            f"Status QC: {enzyme.qc_status}.\n"
            f"Grupa duplikatów: {enzyme.duplicate_group or 'Brak'}.\n"
            f"Reprezentant grupy: {enzyme.representative_id or enzyme.uniprot_id}."
        )

    def _format_fasta_text(self, enzyme) -> str:
        if not enzyme.sequence:
            return "Ten rekord nie ma sekwencji aminokwasowej."

        header = (
            f">{enzyme.uniprot_id} {enzyme.protein_name} | "
            f"{enzyme.organism} | EC: {enzyme.ec_number} | "
            f"{enzyme.reviewed_status}"
        )
        return f"{header}\n{self._wrap_sequence(enzyme.sequence)}"

    def _wrap_sequence(self, sequence: str, line_length: int = 70) -> str:
        return "\n".join(
            sequence[index:index + line_length]
            for index in range(0, len(sequence), line_length)
        )

    def _update_duplicates_tab(self, selected_enzyme=None):
        lines = [
            f"Powtórzone ID w danych wejściowych: {self.input_duplicate_count}",
            f"Unikalne ID pobierane z UniProt: {self.unique_input_count}",
            "",
        ]

        duplicate_groups = {}
        for enzyme in self.enzymes:
            if enzyme.duplicate_group:
                duplicate_groups.setdefault(enzyme.duplicate_group, []).append(enzyme)

        if duplicate_groups:
            lines.append("Grupy identycznych sekwencji:")
            for group_id, records in duplicate_groups.items():
                representative = next(
                    (
                        record
                        for record in records
                        if record.is_representative
                    ),
                    records[0],
                )
                lines.append("")
                lines.append(f"{group_id}")
                lines.append(f"  Reprezentant: {representative.uniprot_id}")
                for record in records:
                    status = "zostaje" if record.is_representative else "duplikat"
                    lines.append(f"  - {record.uniprot_id}: {status}")
        else:
            lines.append("Nie wykryto identycznych sekwencji w pobranych rekordach.")

        if selected_enzyme and selected_enzyme.duplicate_group:
            lines.append("")
            lines.append(
                f"Zaznaczony rekord należy do grupy "
                f"{selected_enzyme.duplicate_group}."
            )

        self._set_text(self.duplicates_text, "\n".join(lines))

    def _update_files_tab(self):
        unique_sequences = len(prepare_non_redundant_set(self.enzymes))
        lines = [
            "Pliki wynikowe:",
            "",
            "1. all_analyzed_enzymes.fasta",
            "   Wszystkie pobrane sekwencje enzymów.",
            "",
            "2. non_redundant_sequences.fasta",
            f"   Czysty zestaw bez duplikatów: {unique_sequences} sekwencji.",
            "",
            "3. enzyme_report.csv / enzyme_report.xlsx",
            "   Tabela z danymi, statystykami sekwencji, QC i interpretacją.",
        ]

        if self.saved_files:
            lines.extend(["", "Ostatnio zapisane pliki:"])
            lines.extend(f"- {path}" for path in self.saved_files)

        self._set_text(self.files_text, "\n".join(lines))

    def _format_full_details(self, enzyme) -> str:
        return (
            f"Identyfikator UniProt: {enzyme.uniprot_id}\n"
            f"Nazwa białka: {enzyme.protein_name}\n"
            f"Organizm: {enzyme.organism}\n"
            f"Numer EC: {enzyme.ec_number}\n"
            f"Masa cząsteczkowa: {enzyme.molecular_weight}\n"
            f"Długość sekwencji: {enzyme.sequence_length}\n"
            f"Status rekordu: {enzyme.reviewed_status}\n"
            f"Status QC: {enzyme.qc_status}\n"
            f"Decyzja programu: {self._decision_for(enzyme)}\n"
            f"Grupa duplikatów: {enzyme.duplicate_group or 'Brak'}\n"
            f"Reprezentant grupy: "
            f"{enzyme.representative_id or enzyme.uniprot_id}\n\n"
            f"Statystyki sekwencji:\n"
            f"- aminokwasy hydrofobowe: {enzyme.hydrophobic_count}\n"
            f"- procent aminokwasów hydrofobowych: "
            f"{enzyme.hydrophobic_percent}%\n"
            f"- liczba cystein: {enzyme.cysteine_count}\n"
            f"- procent cystein: {enzyme.cysteine_percent}%\n"
            f"- najczęstszy aminokwas: {enzyme.most_common_amino_acid}\n"
            f"- kategoria długości: {enzyme.sequence_length_category}\n\n"
            f"Interpretacja:\n{enzyme.interpretation}\n\n"
            f"Sekwencja aminokwasowa:\n{enzyme.sequence}"
        )

    def show_selected_details(self, _event=None):
        selected_item = self.table.selection()

        if not selected_item:
            messagebox.showwarning(
                "Brak wyboru",
                "Najpierw wybierz enzym z tabeli.",
            )
            return

        row_index = self.table.index(selected_item[0])
        enzyme = self.enzymes[row_index]

        details_window = tk.Toplevel(self.root)
        details_window.title(f"Szczegóły enzymu {enzyme.uniprot_id}")
        details_window.geometry("780x560")
        details_window.configure(bg="#f4f7fb")

        text = tk.Text(
            details_window,
            wrap="word",
            font=("Consolas", 10),
            bg="#ffffff",
            fg="#172033",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=10,
        )
        text.pack(fill="both", expand=True, padx=14, pady=14)
        text.insert("1.0", self._format_full_details(enzyme))
        text.configure(state="disabled")

    def _save_report(self, exporter, output_file: Path, report_name: str):
        try:
            exporter(self.enzymes, output_file)
            display_path = str(output_file)
            self.saved_files = [display_path]
            self._update_files_tab()
            self.status_text.set("Raport zapisany.")
            logging.info("Zapisano raport %s: %s", report_name, output_file)
            messagebox.showinfo(
                "Raport zapisany",
                f"Utworzono raport {report_name}:\n{display_path}",
            )
        except OSError as error:
            logging.exception("Błąd zapisu raportu.")
            messagebox.showerror("Błąd zapisu", str(error))

    def save_csv(self):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        selected_file = filedialog.asksaveasfilename(
            parent=self.root,
            title="Zapisz raport CSV",
            defaultextension=".csv",
            initialfile="enzyme_report.csv",
            filetypes=[("Pliki CSV", "*.csv")],
        )

        if not selected_file:
            return

        self._save_report(
            export_to_csv,
            Path(selected_file),
            "CSV",
        )

    def save_xlsx(self):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        selected_file = filedialog.asksaveasfilename(
            parent=self.root,
            title="Zapisz raport XLSX",
            defaultextension=".xlsx",
            initialfile="enzyme_report.xlsx",
            filetypes=[("Pliki Excel", "*.xlsx")],
        )

        if not selected_file:
            return

        self._save_report(
            export_to_xlsx,
            Path(selected_file),
            "XLSX",
        )

    def show_charts_window(self):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        if (
            self.charts_window is not None
            and self.charts_window.winfo_exists()
        ):
            self.charts_window.lift()
            self.charts_window.focus_force()
            return

        charts_window = tk.Toplevel(self.root)
        self.charts_window = charts_window
        charts_window.title("Wykresy")
        charts_window.geometry("1120x820")
        charts_window.minsize(900, 650)
        charts_window.configure(bg="#f4f7fb")
        charts_window.columnconfigure(0, weight=1)
        charts_window.rowconfigure(1, weight=1)

        header = ttk.Frame(charts_window, style="App.TFrame", padding=(16, 12))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Wykresy",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Button(
            header,
            text="Zapisz wykresy",
            command=lambda: self.save_charts(charts_window),
            style="Primary.TButton",
        ).grid(row=0, column=1, sticky="e", padx=(14, 0))

        content = ttk.Frame(charts_window, style="App.TFrame", padding=(16, 0, 16, 16))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        try:
            temp_dir = tempfile.TemporaryDirectory()
            charts_window._chart_temp_dir = temp_dir
            chart_files = list(create_charts(self.enzymes, Path(temp_dir.name)))
            self._show_chart_images(charts_window, content, chart_files)
            self.status_text.set("Wykresy wyświetlone.")
        except OSError as error:
            logging.exception("Błąd tworzenia podglądu wykresów.")
            charts_window.destroy()
            self.charts_window = None
            messagebox.showerror("Błąd wykresów", str(error))

    def _show_chart_images(self, charts_window: tk.Toplevel, parent: ttk.Frame, chart_files):
        canvas = tk.Canvas(
            parent,
            bg="#f4f7fb",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="App.TFrame")

        scroll_frame.columnconfigure(0, weight=1)
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_canvas_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        scroll_frame.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        charts_window._chart_images = []

        visible_charts = 0
        for index, chart_file in enumerate(chart_files):
            chart_path = Path(chart_file)

            card = ttk.Frame(scroll_frame, style="Card.TFrame", padding=12)
            card.grid(row=index, column=0, sticky="ew", pady=(0, 12))
            card.columnconfigure(0, weight=1)

            ttk.Label(
                card,
                text=chart_path.name,
                style="KpiLabel.TLabel",
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))

            try:
                image = tk.PhotoImage(file=str(chart_path))
            except tk.TclError:
                ttk.Label(
                    card,
                    text=(
                        "Tego formatu nie udało się pokazać w oknie. "
                        "Możesz zapisać wykresy przyciskiem u góry."
                    ),
                    style="KpiLabel.TLabel",
                    wraplength=720,
                ).grid(row=1, column=0, sticky="w")
                continue

            max_preview_width = 1080
            scale = max(1, (image.width() + max_preview_width - 1) // max_preview_width)
            if scale > 1:
                image = image.subsample(scale, scale)

            charts_window._chart_images.append(image)
            ttk.Label(
                card,
                image=image,
                background="#ffffff",
            ).grid(row=1, column=0)
            visible_charts += 1

        if not chart_files or visible_charts == 0:
            empty = ttk.Frame(scroll_frame, style="Card.TFrame", padding=18)
            empty.grid(row=len(chart_files), column=0, sticky="ew")
            ttk.Label(
                empty,
                text="Nie znaleziono wykresów do wyświetlenia.",
                style="KpiLabel.TLabel",
            ).grid(row=0, column=0, sticky="w")

        charts_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self._close_charts_window(charts_window),
        )

    def _close_charts_window(self, charts_window: tk.Toplevel):
        temp_dir = getattr(charts_window, "_chart_temp_dir", None)
        charts_window.destroy()
        if self.charts_window is charts_window:
            self.charts_window = None
        if temp_dir is not None:
            temp_dir.cleanup()

    def save_charts(self, parent=None):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        dialog_parent = parent or self.root
        selected_directory = filedialog.askdirectory(
            parent=dialog_parent,
            title="Wybierz folder dla wykresów",
        )

        if not selected_directory:
            return

        try:
            chart_files = create_charts(
                self.enzymes,
                Path(selected_directory),
            )

            self.saved_files = [str(path) for path in chart_files]
            self._update_files_tab()
            self.status_text.set("Wykresy zapisane.")
            logging.info("Utworzono wykresy z poziomu GUI.")

            file_names = "\n".join(
                str(path)
                for path in chart_files
            )

            messagebox.showinfo(
                "Wykresy utworzone",
                f"Zapisano wykresy:\n{file_names}",
            )

        except OSError as error:
            logging.exception("Błąd tworzenia wykresów.")
            messagebox.showerror("Błąd wykresów", str(error))

    def save_fasta(self):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        selected_directory = filedialog.askdirectory(
            parent=self.root,
            title="Wybierz folder dla plików FASTA",
        )

        if not selected_directory:
            return

        try:
            output_dir = Path(selected_directory)

            all_enzymes_file = export_all_enzymes_to_fasta(
                self.enzymes,
                output_dir,
            )
            non_redundant_file = export_non_redundant_fasta(
                self.enzymes,
                output_dir,
            )

            self.saved_files = [
                str(all_enzymes_file),
                str(non_redundant_file),
            ]
            self._update_files_tab()
            self.status_text.set("Eksport zakończony.")
            logging.info("Zapisano pliki FASTA z poziomu GUI.")

            messagebox.showinfo(
                "FASTA zapisane",
                "Utworzono pliki FASTA:\n"
                f"{all_enzymes_file}\n"
                f"{non_redundant_file}",
            )

        except Exception as error:
            logging.exception("Błąd zapisu FASTA.")
            messagebox.showerror("Błąd FASTA", str(error))

    def _show_error(self, message: str):
        self.status_text.set("Nie udało się pobrać danych.")
        self.download_button.configure(state="normal")
        self.ids_entry.configure(state="normal")
        self.files_button.configure(state="normal")
        self._set_all_result_buttons("disabled")
        messagebox.showerror("Błąd", message)
