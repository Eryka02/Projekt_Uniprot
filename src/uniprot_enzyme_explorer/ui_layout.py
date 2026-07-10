import logging
import tkinter as tk
from tkinter import ttk

from src.uniprot_enzyme_explorer.ui_constants import NUCLEOTIDE_TAG_STYLES


class UiLayoutMixin:
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
            logging.debug("Motyw Tkinter 'clam' nie jest dostępny.")

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

        self.fasta_button = ttk.Menubutton(
            buttons,
            text="Zapisz FASTA",
            state="disabled",
        )
        self.fasta_menu = tk.Menu(self.fasta_button, tearoff=False)
        self.fasta_menu.add_command(
            label="Sekwencje aminokwasowe",
            command=lambda: self.save_fasta("protein"),
        )
        self.fasta_menu.add_command(
            label="Sekwencje nukleotydowe",
            command=lambda: self.save_fasta("nucleotide"),
        )
        self.fasta_button["menu"] = self.fasta_menu
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
        workspace.add(details_panel, minsize=360)

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
            "hydrophobic",
            "cysteines",
            "qc",
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
            "hydrophobic": ("Hydrof.", 86, "e"),
            "cysteines": ("Cys.", 88, "e"),
            "qc": ("Sprawdzenie", 170, "w"),
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

        body_holder = ttk.Frame(parent, style="PanelBody.TFrame")
        body_holder.grid(row=1, column=0, sticky="nsew")
        body_holder.columnconfigure(0, weight=1)
        body_holder.rowconfigure(0, weight=1)

        canvas = tk.Canvas(
            body_holder,
            bg="#ffffff",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            body_holder,
            orient="vertical",
            command=canvas.yview,
        )
        body = ttk.Frame(canvas, style="PanelBody.TFrame", padding=(14, 12))
        body.columnconfigure(0, weight=1)
        canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_body_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        body.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_body_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

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
                ("ec_class", "Rodzaj enzymu"),
                ("reviewed_status", "Status UniProt"),
                ("sequence_length", "Długość sekwencji"),
                ("molecular_weight", "Masa cząsteczkowa"),
            ],
        )
        self._create_detail_section(
            body,
            row=3,
            title="Statystyki sekwencji",
            fields=[
                ("hydrophobic", "Hydrofobowe"),
                ("cysteines", "Cysteiny"),
                ("most_common", "Najczęstszy aminokwas"),
            ],
        )
        self._create_detail_section(
            body,
            row=4,
            title="Informacje z UniProt",
            fields=[
                ("function_description", "Funkcja"),
                ("catalytic_activity", "Reakcja"),
                ("cofactors", "Kofaktory"),
                ("subcellular_location", "Lokalizacja"),
                ("feature_summary", "Cechy sekwencji"),
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
                wraplength=220,
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
        self._configure_sequence_tags()
        self.duplicates_text = self._create_text_tab(
            self.notebook,
            "Duplikaty",
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

    def _set_text(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _configure_sequence_tags(self):
        self.sequence_text.tag_configure(
            "fasta_header",
            foreground="#334155",
            font=("Consolas", 9, "bold"),
        )
        self.sequence_text.tag_configure(
            "sequence_note",
            foreground="#475569",
            font=("Segoe UI", 9),
        )
        self.sequence_text.tag_configure(
            "protein_sequence",
            foreground="#111827",
            font=("Consolas", 9),
        )

        for tag, style in NUCLEOTIDE_TAG_STYLES.items():
            self.sequence_text.tag_configure(
                tag,
                font=("Consolas", 10, "bold"),
                **style,
            )
