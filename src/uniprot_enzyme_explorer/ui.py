# -*- coding: utf-8 -*-
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
from src.uniprot_enzyme_explorer.storage import (
    export_all_enzymes_to_fasta,
    export_best_candidate_to_fasta,
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

        self.root.title("UniProt Enzyme Explorer")
        self.root.geometry("1220x680")
        self.root.minsize(1000, 560)
        self.root.configure(bg="#f4f7fb")

        self._build_interface()

    def _build_interface(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._configure_styles()

        shell = ttk.Frame(self.root, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        self._build_sidebar(shell)
        self._build_main_panel(shell)

    def _configure_styles(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Shell.TFrame", background="#f4f7fb")
        style.configure("Main.TFrame", background="#f4f7fb")
        style.configure("Sidebar.TFrame", background="#223044")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Candidate.TFrame", background="#eefaf5", relief="solid", borderwidth=1)
        style.configure("TableFrame.TFrame", background="#ffffff", relief="solid", borderwidth=1)

        style.configure(
            "Title.TLabel",
            background="#f4f7fb",
            foreground="#172033",
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#f4f7fb",
            foreground="#637083",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Label.TLabel",
            background="#f4f7fb",
            foreground="#526174",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "SidebarTitle.TLabel",
            background="#223044",
            foreground="#ffffff",
            font=("Segoe UI", 15, "bold"),
        )
        style.configure(
            "SidebarMuted.TLabel",
            background="#223044",
            foreground="#b8c5d7",
            font=("Segoe UI", 9),
        )
        style.configure(
            "SidebarSection.TLabel",
            background="#223044",
            foreground="#8ea0b6",
            font=("Segoe UI", 8, "bold"),
        )
        style.configure(
            "KpiValue.TLabel",
            background="#ffffff",
            foreground="#172033",
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "KpiLabel.TLabel",
            background="#ffffff",
            foreground="#637083",
            font=("Segoe UI", 9),
        )
        style.configure(
            "CandidateTitle.TLabel",
            background="#eefaf5",
            foreground="#176c57",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "CandidateText.TLabel",
            background="#eefaf5",
            foreground="#426052",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Status.TLabel",
            background="#f4f7fb",
            foreground="#526174",
            font=("Segoe UI", 9),
        )

        style.configure(
            "Primary.TButton",
            background="#2869b8",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=(14, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#225fa9"), ("disabled", "#b9c6d7")],
            foreground=[("disabled", "#edf2f7")],
        )
        style.configure(
            "Sidebar.TButton",
            background="#31435d",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padding=(12, 8),
            anchor="w",
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", "#3b506d"), ("disabled", "#2a394f")],
            foreground=[("disabled", "#7f8fa3")],
        )
        style.configure("TButton", font=("Segoe UI", 9), padding=(12, 8))
        style.configure("TEntry", padding=(8, 8))

        style.configure(
            "Treeview",
            rowheight=28,
            font=("Segoe UI", 9),
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#263244",
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 8, "bold"),
            background="#f7f9fc",
            foreground="#5a687a",
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#172033")],
        )

    def _build_sidebar(self, shell: ttk.Frame):
        sidebar = ttk.Frame(shell, style="Sidebar.TFrame", width=230, padding=(18, 20))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(10, weight=1)

        ttk.Label(
            sidebar,
            text="UniProt\nEnzyme Explorer",
            style="SidebarTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        ttk.Label(
            sidebar,
            text="Panel analizy enzymów",
            style="SidebarMuted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 24))

        ttk.Label(
            sidebar,
            text="AKCJE",
            style="SidebarSection.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        self.details_button = ttk.Button(
            sidebar,
            text="Szczegóły",
            command=self.show_selected_details,
            state="disabled",
            style="Sidebar.TButton",
        )
        self.details_button.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self.csv_button = ttk.Button(
            sidebar,
            text="Zapisz CSV",
            command=self.save_csv,
            state="disabled",
            style="Sidebar.TButton",
        )
        self.csv_button.grid(row=4, column=0, sticky="ew", pady=(0, 8))

        self.xlsx_button = ttk.Button(
            sidebar,
            text="Zapisz XLSX",
            command=self.save_xlsx,
            state="disabled",
            style="Sidebar.TButton",
        )
        self.xlsx_button.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        self.charts_button = ttk.Button(
            sidebar,
            text="Wykresy",
            command=self.show_charts_window,
            state="disabled",
            style="Sidebar.TButton",
        )
        self.charts_button.grid(row=6, column=0, sticky="ew", pady=(0, 8))

        self.fasta_button = ttk.Button(
            sidebar,
            text="Zapisz FASTA",
            command=self.save_fasta,
            state="disabled",
            style="Sidebar.TButton",
        )
        self.fasta_button.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(
            sidebar,
            text="Najpierw pobierz dane, potem wybierz rekord z tabeli.",
            style="SidebarMuted.TLabel",
            wraplength=175,
        ).grid(row=11, column=0, sticky="sw", pady=(20, 0))

    def _build_main_panel(self, shell: ttk.Frame):
        main_frame = ttk.Frame(shell, style="Main.TFrame", padding=18)
        main_frame.grid(row=0, column=1, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)

        header = ttk.Frame(main_frame, style="Main.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="UniProt Enzyme Explorer",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            header,
            text="Pobieranie rekordów, ocena jakości i eksport wyników.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        try:
            initial_ids = load_uniprot_ids(self.input_file)
        except OSError:
            initial_ids = []

        self.ids_text = tk.StringVar(value=", ".join(initial_ids))
        self._build_input_area(main_frame)
        self._build_summary_cards(main_frame)
        self._build_candidate_card(main_frame)
        self._build_table(main_frame)

        self.status_text = tk.StringVar(value="Gotowe do pobrania danych.")
        ttk.Label(
            main_frame,
            textvariable=self.status_text,
            style="Status.TLabel",
        ).grid(row=5, column=0, sticky="w", pady=(12, 0))

    def _build_input_area(self, main_frame: ttk.Frame):
        input_frame = ttk.Frame(main_frame, style="Main.TFrame")
        input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        input_frame.columnconfigure(0, weight=1)

        input_box = ttk.Frame(input_frame, style="Main.TFrame")
        input_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        input_box.columnconfigure(0, weight=1)

        ttk.Label(
            input_box,
            text="IDENTYFIKATORY UNIPROT",
            style="Label.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.ids_entry = ttk.Entry(
            input_box,
            textvariable=self.ids_text,
            font=("Segoe UI", 10),
        )
        self.ids_entry.grid(row=1, column=0, sticky="ew")

        buttons = ttk.Frame(input_frame, style="Main.TFrame")
        buttons.grid(row=0, column=1, sticky="sew")
        buttons.rowconfigure(0, weight=1)

        self.files_button = ttk.Button(
            buttons,
            text="Wczytaj pliki",
            command=self.select_input_files,
        )
        self.files_button.grid(row=1, column=0, padx=(0, 8))

        self.download_button = ttk.Button(
            buttons,
            text="Pobierz dane",
            command=self.start_download,
            style="Primary.TButton",
        )
        self.download_button.grid(row=1, column=1)

    def _build_summary_cards(self, main_frame: ttk.Frame):
        self.records_count_text = tk.StringVar(value="0")
        self.reviewed_count_text = tk.StringVar(value="0")
        self.average_score_text = tk.StringVar(value="-")
        self.missing_count_text = tk.StringVar(value="0")

        cards_frame = ttk.Frame(main_frame, style="Main.TFrame")
        cards_frame.grid(row=2, column=0, sticky="ew", pady=(0, 14))

        for column in range(4):
            cards_frame.columnconfigure(column, weight=1)

        self._create_kpi_card(
            cards_frame,
            column=0,
            value=self.records_count_text,
            label="rekordy znalezione",
        )
        self._create_kpi_card(
            cards_frame,
            column=1,
            value=self.reviewed_count_text,
            label="rekordy reviewed",
        )
        self._create_kpi_card(
            cards_frame,
            column=2,
            value=self.average_score_text,
            label="średnia ocena",
        )
        self._create_kpi_card(
            cards_frame,
            column=3,
            value=self.missing_count_text,
            label="niepobrane",
        )

    def _create_kpi_card(
        self,
        parent: ttk.Frame,
        column: int,
        value: tk.StringVar,
        label: str,
    ):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(14, 12))
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        card.columnconfigure(0, weight=1)

        ttk.Label(
            card,
            textvariable=value,
            style="KpiValue.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            card,
            text=label,
            style="KpiLabel.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _build_candidate_card(self, main_frame: ttk.Frame):
        candidate = ttk.Frame(main_frame, style="Candidate.TFrame", padding=(14, 12))
        candidate.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        candidate.columnconfigure(0, weight=1)

        self.best_candidate_title = tk.StringVar(value="Najlepszy kandydat: brak danych")
        self.best_candidate_text = tk.StringVar(
            value="Po pobraniu danych tutaj pojawi się najwyżej oceniony rekord."
        )

        ttk.Label(
            candidate,
            textvariable=self.best_candidate_title,
            style="CandidateTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            candidate,
            textvariable=self.best_candidate_text,
            style="CandidateText.TLabel",
            wraplength=820,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _build_table(self, main_frame: ttk.Frame):
        table_frame = ttk.Frame(main_frame, style="TableFrame.TFrame")
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = (
            "id",
            "name",
            "organism",
            "ec",
            "length",
            "mass",
            "status",
            "score",
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )

        settings = {
            "id": ("UniProt ID", 95),
            "name": ("Nazwa białka", 250),
            "organism": ("Organizm", 155),
            "ec": ("EC", 90),
            "length": ("Długość", 85),
            "mass": ("Masa [Da]", 100),
            "status": ("Status", 95),
            "score": ("Quality", 80),
        }

        for column, (heading, width) in settings.items():
            self.table.heading(column, text=heading)
            self.table.column(column, width=width, minwidth=80)

        self.table.tag_configure("odd", background="#ffffff")
        self.table.tag_configure("even", background="#f8fafc")

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

    def _set_report_buttons(self, state: str):
        self.csv_button.configure(state=state)
        self.xlsx_button.configure(state=state)
        self.charts_button.configure(state=state)

    def _set_all_result_buttons(self, state: str):
        self.details_button.configure(state=state)
        self.csv_button.configure(state=state)
        self.xlsx_button.configure(state=state)
        self.charts_button.configure(state=state)
        self.fasta_button.configure(state=state)

    def _reset_summary(self):
        self.records_count_text.set("0")
        self.reviewed_count_text.set("0")
        self.average_score_text.set("-")
        self.missing_count_text.set("0")
        self.best_candidate_title.set("Najlepszy kandydat: brak danych")
        self.best_candidate_text.set(
            "Po pobraniu danych tutaj pojawi się najwyżej oceniony rekord."
        )

    def _update_summary(self, enzymes, total: int):
        records_count = len(enzymes)
        reviewed_count = sum(
            1
            for enzyme in enzymes
            if str(enzyme.reviewed_status).strip().lower() == "reviewed"
        )
        missing_count = max(total - records_count, 0)

        scores = []
        for enzyme in enzymes:
            try:
                scores.append(float(enzyme.quality_score))
            except (TypeError, ValueError):
                continue

        average_score = "-"
        if scores:
            average_score = f"{sum(scores) / len(scores):.1f}"

        self.records_count_text.set(str(records_count))
        self.reviewed_count_text.set(str(reviewed_count))
        self.average_score_text.set(average_score)
        self.missing_count_text.set(str(missing_count))

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

            uniprot_ids = load_uniprot_ids_from_files(
                file_paths
            )

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
            messagebox.showerror(
                "Błąd pliku",
                str(error),
            )

    def start_download(self):
        uniprot_ids = parse_uniprot_ids(self.ids_text.get())

        if not uniprot_ids:
            messagebox.showwarning(
                "Brak danych",
                "Wpisz przynajmniej jeden identyfikator UniProt.",
            )
            return

        self.enzymes = []
        self._reset_summary()
        self._set_all_result_buttons("disabled")
        self.download_button.configure(state="disabled")
        self.files_button.configure(state="disabled")
        self.ids_entry.configure(state="disabled")
        self.status_text.set(f"Pobieranie rekordów: {len(uniprot_ids)}...")

        for item in self.table.get_children():
            self.table.delete(item)

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
                len(uniprot_ids),
            )
        except Exception as error:
            logging.exception("Błąd podczas pracy GUI.")
            self.root.after(0, self._show_error, str(error))

    def _display_results(self, enzymes, errors, total):
        self.enzymes = enzymes
        save_processed_records(enzymes)
        self._update_summary(enzymes, total)

        if enzymes:
            best_enzyme = enzymes[0]
            self.best_candidate_title.set(
                f"Najlepszy kandydat: {best_enzyme.uniprot_id} | "
                f"Ocena: {best_enzyme.quality_score}/10"
            )
            self.best_candidate_text.set(best_enzyme.interpretation)
        else:
            self.best_candidate_title.set("Najlepszy kandydat: brak danych")
            self.best_candidate_text.set("Nie znaleziono poprawnych rekordów.")

        for index, enzyme in enumerate(enzymes):
            tag = "even" if index % 2 else "odd"
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
                    enzyme.quality_score,
                ),
                tags=(tag,),
            )

        self.status_text.set(f"Pobrano poprawnie: {len(enzymes)} z {total}.")
        self.download_button.configure(state="normal")
        self.ids_entry.configure(state="normal")
        self.files_button.configure(state="normal")

        if enzymes:
            self._set_all_result_buttons("normal")
        else:
            self._set_all_result_buttons("disabled")

        if errors:
            messagebox.showwarning("Niepełne wyniki", "\n".join(errors))

    def _save_report(self, exporter, output_file: Path, report_name: str):
        try:
            exporter(self.enzymes, output_file)
            display_path = str(output_file)
            self.status_text.set(f"Zapisano raport: {display_path}")
            logging.info("Zapisano raport %s: %s", report_name, output_file)
            messagebox.showinfo(
                "Raport zapisany",
                f"Utworzono raport {report_name}:\n{display_path}",
            )
        except OSError as error:
            logging.exception("Błąd zapisu raportu.")
            messagebox.showerror("Błąd zapisu", str(error))

    def show_selected_details(self):
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

        details = (
            f"Identyfikator UniProt: {enzyme.uniprot_id}\n"
            f"Nazwa białka: {enzyme.protein_name}\n"
            f"Organizm: {enzyme.organism}\n"
            f"Numer EC: {enzyme.ec_number}\n"
            f"Masa cząsteczkowa: {enzyme.molecular_weight}\n"
            f"Długość sekwencji: {enzyme.sequence_length}\n"
            f"Status rekordu: {enzyme.reviewed_status}\n"
            f"Quality score: {enzyme.quality_score}/10\n\n"
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

        text.insert("1.0", details)
        text.configure(state="disabled")

    def save_csv(self):
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

        charts_window = tk.Toplevel(self.root)
        charts_window.title("Wykresy")
        charts_window.geometry("920x680")
        charts_window.minsize(760, 520)
        charts_window.configure(bg="#f4f7fb")
        charts_window.columnconfigure(0, weight=1)
        charts_window.rowconfigure(1, weight=1)

        header = ttk.Frame(charts_window, style="Main.TFrame", padding=(16, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Wykresy",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            header,
            text="Podgląd wykresów dla aktualnie pobranych rekordów.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        ttk.Button(
            header,
            text="Pobierz wykresy",
            command=lambda: self.save_charts(charts_window),
            style="Primary.TButton",
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(14, 0))

        content = ttk.Frame(charts_window, style="Main.TFrame", padding=(16, 0, 16, 16))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        try:
            temp_dir = tempfile.TemporaryDirectory()
            charts_window._chart_temp_dir = temp_dir
            chart_files = list(create_charts(self.enzymes, Path(temp_dir.name)))
            self._show_chart_images(charts_window, content, chart_files)
            self.status_text.set("Wyświetlono wykresy.")
        except OSError as error:
            logging.exception("Błąd tworzenia podglądu wykresów.")
            charts_window.destroy()
            messagebox.showerror("Błąd wykresów", str(error))

    def _show_chart_images(self, charts_window: tk.Toplevel, parent: ttk.Frame, chart_files):
        canvas = tk.Canvas(
            parent,
            bg="#f4f7fb",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="Main.TFrame")

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
                    text="Tego formatu nie udało się pokazać w oknie. Możesz zapisać wykresy przyciskiem u góry.",
                    style="KpiLabel.TLabel",
                    wraplength=720,
                ).grid(row=1, column=0, sticky="w")
                continue

            max_preview_width = 820
            scale = max(1, (image.width() + max_preview_width - 1) // max_preview_width)
            if scale > 1:
                image = image.subsample(scale, scale)

            charts_window._chart_images.append(image)
            ttk.Label(
                card,
                image=image,
                background="#ffffff",
            ).grid(row=1, column=0, sticky="w")
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

            self.status_text.set("Utworzono wykresy.")
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

            best_candidate_file = export_best_candidate_to_fasta(
                self.enzymes[0],
                output_dir,
            )
            all_enzymes_file = export_all_enzymes_to_fasta(
                self.enzymes,
                output_dir,
            )

            self.status_text.set("Zapisano pliki FASTA.")
            logging.info("Zapisano pliki FASTA z poziomu GUI.")

            messagebox.showinfo(
                "FASTA zapisane",
                "Utworzono pliki FASTA:\n"
                f"{best_candidate_file}\n"
                f"{all_enzymes_file}",
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
