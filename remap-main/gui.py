#!/usr/bin/env python3
"""
ECU Remap GUI - Interface Gráfica
Interface visual para remap de ECU automotiva
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ecu_remap import ECURemap, RemapProfile, PRESET_PROFILES


class ECURemapGUI:
    # Paleta de cores (tema escuro)
    BG       = '#0f172a'   # fundo principal
    CARD     = '#1e293b'   # cards / painéis
    INPUT    = '#334155'   # fundo de inputs / trilhos
    TEXT     = '#f1f5f9'   # texto principal
    MUTED    = '#94a3b8'   # texto secundário
    ACCENT   = '#818cf8'   # indigo — destaque
    SUCCESS  = '#34d399'   # verde — ganho positivo
    WARNING  = '#fbbf24'   # âmbar — ganho negativo / aviso
    DANGER   = '#f87171'   # vermelho
    BTN_SAVE = '#0e7490'   # ciano — salvar
    BTN_RPT  = '#059669'   # verde — relatório
    BTN_BCK  = '#b45309'   # laranja — backup
    BORDER   = '#334155'

    PRESET_COLORS = {
        'eco':     '#10b981',
        'stock':   '#64748b',
        'sport':   '#818cf8',
        'extreme': '#f87171',
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.ecu: ECURemap | None = None
        self.ecu_filepath: str | None = None

        # Variáveis dos sliders
        self.fuel_var      = tk.DoubleVar(value=20.0)
        self.ign_var       = tk.DoubleVar(value=8.0)
        self.turbo_lo_var  = tk.DoubleVar(value=1.2)
        self.turbo_hi_var  = tk.DoubleVar(value=1.5)
        self.rpm_var       = tk.IntVar(value=7500)
        self.lambda_var    = tk.DoubleVar(value=0.88)

        self._setup_window()
        self._build_ui()

        # Atualiza estimativas ao mover qualquer slider
        for var in (self.fuel_var, self.ign_var, self.turbo_lo_var,
                    self.turbo_hi_var, self.rpm_var, self.lambda_var):
            var.trace_add('write', lambda *_: self._update_estimates())

        # Carrega preset sport como padrão
        self._load_preset('sport')

    # ─── Setup ────────────────────────────────────────────────────

    def _setup_window(self):
        self.root.title("ECU Remap Tool  v1.1")
        self.root.configure(bg=self.BG)
        self.root.minsize(960, 640)
        self.root.geometry('1060x700')

        # Centraliza na tela
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = (sw - 1060) // 2
        y = (sh - 700) // 2
        self.root.geometry(f'1060x700+{x}+{y}')

    # ─── UI Builder ───────────────────────────────────────────────

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=self.BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        # Título
        hdr = tk.Frame(outer, bg=self.BG)
        hdr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(hdr, text="ECU REMAP", bg=self.BG, fg=self.TEXT,
                 font=('Helvetica', 17, 'bold')).pack(side=tk.LEFT)
        tk.Label(hdr, text="  Reprogramação Eletrônica Automotiva",
                 bg=self.BG, fg=self.MUTED, font=('Helvetica', 10)).pack(side=tk.LEFT, pady=3)

        # Corpo principal (esquerda + direita)
        body = tk.Frame(outer, bg=self.BG)
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg=self.BG, width=265)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)
        self._build_left(left)

        right = tk.Frame(body, bg=self.BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_right(right)

        # Log
        log_outer = tk.Frame(outer, bg=self.CARD, bd=0)
        log_outer.pack(fill=tk.X, pady=(10, 0))
        tk.Label(log_outer, text=" Log ", bg=self.CARD, fg=self.MUTED,
                 font=('Helvetica', 8, 'bold')).pack(anchor='w', padx=8, pady=(4, 0))
        self.log_text = scrolledtext.ScrolledText(
            log_outer, height=5, bg='#0a0f1e', fg='#94a3b8',
            font=('Courier', 9), bd=0, relief='flat',
            insertbackground=self.TEXT, wrap=tk.WORD,
            selectbackground=self.INPUT
        )
        self.log_text.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.log_text.configure(state='disabled')

    # ─── Painel Esquerdo ──────────────────────────────────────────

    def _build_left(self, parent):
        # Arquivo ECU
        fc = self._card(parent, "Arquivo ECU")
        fc.pack(fill=tk.X, pady=(0, 8))

        btn_row = tk.Frame(fc, bg=self.CARD)
        btn_row.pack(fill=tk.X, padx=8, pady=8)
        self._btn(btn_row, "Carregar .bin", self._load_ecu, self.ACCENT).pack(side=tk.LEFT)
        tk.Frame(btn_row, bg=self.CARD, width=6).pack(side=tk.LEFT)
        self._btn(btn_row, "Simulada", self._create_simulated, self.INPUT, small=True).pack(side=tk.LEFT)

        info = tk.Frame(fc, bg=self.CARD)
        info.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.lbl_file   = self._info_row(info, "Arquivo:")
        self.lbl_size   = self._info_row(info, "Tamanho:")
        self.lbl_model  = self._info_row(info, "Modelo:")
        self.lbl_status = self._info_row(info, "Status:")

        # Parâmetros atuais
        pc = self._card(parent, "Parâmetros atuais")
        pc.pack(fill=tk.X)

        p = tk.Frame(pc, bg=self.CARD)
        p.pack(fill=tk.X, padx=8, pady=8)

        rows = [
            ('fuel_injection', 'Combustível', '%'),
            ('ignition_timing', 'Ignição', '°'),
            ('turbo_boost_low', 'Turbo Baixo', 'bar'),
            ('turbo_boost_high', 'Turbo Alto', 'bar'),
            ('rpm_limit', 'RPM Limite', 'rpm'),
            ('lambda_target', 'Lambda', 'λ'),
            ('cooling_temp', 'Arrefecimento', '°C'),
        ]
        self.param_labels: dict[str, tuple[tk.Label, str]] = {}
        for key, name, unit in rows:
            row = tk.Frame(p, bg=self.CARD)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=name + ":", bg=self.CARD, fg=self.MUTED,
                     font=('Helvetica', 9), width=14, anchor='w').pack(side=tk.LEFT)
            lbl = tk.Label(row, text=f"— {unit}", bg=self.CARD, fg=self.TEXT,
                           font=('Helvetica', 9), anchor='e')
            lbl.pack(side=tk.RIGHT)
            self.param_labels[key] = (lbl, unit)

    # ─── Painel Direito ───────────────────────────────────────────

    def _build_right(self, parent):
        # Perfil de Remap
        pf = self._card(parent, "Perfil de Remap")
        pf.pack(fill=tk.X, pady=(0, 8))

        # Linha de botões preset
        preset_row = tk.Frame(pf, bg=self.CARD)
        preset_row.pack(fill=tk.X, padx=10, pady=(10, 6))
        tk.Label(preset_row, text="Presets:", bg=self.CARD, fg=self.MUTED,
                 font=('Helvetica', 9)).pack(side=tk.LEFT, padx=(0, 8))
        for pname in ('eco', 'stock', 'sport', 'extreme'):
            color = self.PRESET_COLORS[pname]
            self._btn(preset_row, pname.upper(),
                      lambda p=pname: self._load_preset(p),
                      color, small=True).pack(side=tk.LEFT, padx=3)

        # Sliders
        sf = tk.Frame(pf, bg=self.CARD)
        sf.pack(fill=tk.X, padx=10, pady=(0, 10))

        slider_cfg = [
            ('Combustível',  self.fuel_var,     -50,  50,   0.5,  '{:+.1f}%'),
            ('Ignição',      self.ign_var,       -15,  15,   0.5,  '{:+.1f}°'),
            ('Turbo Baixo',  self.turbo_lo_var,  0.5,  2.0,  0.05, '{:.2f} bar'),
            ('Turbo Alto',   self.turbo_hi_var,  0.5,  2.5,  0.05, '{:.2f} bar'),
            ('RPM Limite',   self.rpm_var,      5000, 9000, 100,   '{:.0f} rpm'),
            ('Lambda',       self.lambda_var,    0.8,  1.2,  0.01, '{:.2f} λ'),
        ]
        self._slider_val_labels: dict[str, tuple[tk.Label, str]] = {}

        for name, var, from_, to, res, fmt in slider_cfg:
            row = tk.Frame(sf, bg=self.CARD)
            row.pack(fill=tk.X, pady=3)

            tk.Label(row, text=name + ":", bg=self.CARD, fg=self.TEXT,
                     font=('Helvetica', 9), width=13, anchor='w').pack(side=tk.LEFT)

            scale = tk.Scale(
                row, variable=var, from_=from_, to=to, orient=tk.HORIZONTAL,
                resolution=res, showvalue=False, length=310,
                bg=self.CARD, fg=self.MUTED, troughcolor=self.INPUT,
                activebackground=self.ACCENT, highlightthickness=0,
                bd=0, sliderlength=16, sliderrelief='flat'
            )
            scale.pack(side=tk.LEFT, padx=6)

            val_lbl = tk.Label(row, text=fmt.format(float(var.get())),
                               bg=self.CARD, fg=self.ACCENT,
                               font=('Courier', 9, 'bold'), width=12, anchor='e')
            val_lbl.pack(side=tk.LEFT)
            self._slider_val_labels[name] = (val_lbl, fmt)

            def _make_trace(lbl, fmtstr, v):
                def _update(*_):
                    try:
                        lbl.config(text=fmtstr.format(float(v.get())))
                    except Exception:
                        pass
                return _update
            var.trace_add('write', _make_trace(val_lbl, fmt, var))

        # Ganhos estimados
        gf = self._card(parent, "Ganhos estimados")
        gf.pack(fill=tk.X, pady=(0, 8))

        gi = tk.Frame(gf, bg=self.CARD)
        gi.pack(fill=tk.X, padx=12, pady=10)

        self.power_canvas, self.power_lbl = self._gauge_row(gi, "Potência")
        self.torque_canvas, self.torque_lbl = self._gauge_row(gi, "Torque")

        # Botões de ação
        af = tk.Frame(parent, bg=self.BG)
        af.pack(fill=tk.X)

        self._btn(af, "Aplicar Remap",       self._apply_remap,    self.ACCENT).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(af, "Salvar ECU",          self._save_ecu,       self.BTN_SAVE).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(af, "Exportar Relatório",  self._export_report,  self.BTN_RPT).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(af, "Backup Original",     self._create_backup,  self.BTN_BCK).pack(side=tk.LEFT)

    # ─── Gauge bar ────────────────────────────────────────────────

    def _gauge_row(self, parent, name: str):
        row = tk.Frame(parent, bg=self.CARD)
        row.pack(fill=tk.X, pady=4)

        tk.Label(row, text=name + ":", bg=self.CARD, fg=self.TEXT,
                 font=('Helvetica', 10), width=10, anchor='w').pack(side=tk.LEFT)

        canvas = tk.Canvas(row, bg=self.CARD, height=18, width=310,
                           bd=0, highlightthickness=0)
        canvas.pack(side=tk.LEFT, padx=8)
        canvas.bind('<Configure>', lambda e: self._update_estimates())

        lbl = tk.Label(row, text="+0.0%", bg=self.CARD, fg=self.SUCCESS,
                       font=('Courier', 10, 'bold'), width=9, anchor='e')
        lbl.pack(side=tk.LEFT)
        return canvas, lbl

    def _draw_gauge(self, canvas: tk.Canvas, lbl: tk.Label, percent: float):
        canvas.delete('all')
        w = canvas.winfo_width() or 310
        h = canvas.winfo_height() or 18

        MAX_PCT = 60.0
        canvas.create_rectangle(0, 4, w, h - 4, fill=self.INPUT, outline='')

        mid = w // 2
        color = self.SUCCESS if percent >= 0 else self.WARNING
        clamped = max(-MAX_PCT, min(percent, MAX_PCT))

        if percent >= 0:
            bar_w = int(clamped / MAX_PCT * mid)
            if bar_w > 0:
                canvas.create_rectangle(mid, 4, mid + bar_w, h - 4, fill=color, outline='')
        else:
            bar_w = int(abs(clamped) / MAX_PCT * mid)
            if bar_w > 0:
                canvas.create_rectangle(mid - bar_w, 4, mid, h - 4, fill=color, outline='')

        # Linha de zero
        canvas.create_rectangle(mid - 1, 2, mid + 1, h - 2, fill=self.MUTED, outline='')

        sign = '+' if percent >= 0 else ''
        lbl.config(text=f"{sign}{percent:.1f}%", fg=color)

    # ─── Helpers de widget ────────────────────────────────────────

    def _card(self, parent, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=self.CARD, bd=1, relief='flat',
                         highlightbackground=self.BORDER, highlightthickness=1)
        tk.Label(outer, text=f" {title} ", bg=self.CARD, fg=self.MUTED,
                 font=('Helvetica', 8, 'bold')).pack(anchor='w', padx=6, pady=(4, 0))
        return outer

    def _info_row(self, parent, label: str) -> tk.Label:
        row = tk.Frame(parent, bg=self.CARD)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=label, bg=self.CARD, fg=self.MUTED,
                 font=('Helvetica', 9), width=9, anchor='w').pack(side=tk.LEFT)
        lbl = tk.Label(row, text="—", bg=self.CARD, fg=self.TEXT,
                       font=('Helvetica', 9), anchor='w')
        lbl.pack(side=tk.LEFT)
        return lbl

    def _btn(self, parent, text: str, cmd, color: str, small: bool = False) -> tk.Label:
        """Cria botão como Label (funciona no macOS onde tk.Button ignora bg)."""
        px, py = (8, 4) if small else (14, 6)
        fs = 9 if small else 10
        btn = tk.Label(
            parent, text=text,
            bg=color, fg=self.TEXT,
            padx=px, pady=py,
            font=('Helvetica', fs),
            cursor='hand2'
        )
        btn.bind('<Button-1>', lambda e: cmd())
        btn.bind('<Enter>', lambda e: btn.config(bg=self._lighten(color)))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        return btn

    @staticmethod
    def _lighten(hex_color: str) -> str:
        r = min(255, int(hex_color[1:3], 16) + 30)
        g = min(255, int(hex_color[3:5], 16) + 30)
        b = min(255, int(hex_color[5:7], 16) + 30)
        return f'#{r:02x}{g:02x}{b:02x}'

    # ─── Lógica / Actions ─────────────────────────────────────────

    def _log(self, msg: str, level: str = 'info'):
        colors = {'info': self.MUTED, 'ok': self.SUCCESS, 'warn': self.WARNING, 'err': self.DANGER}
        ts = datetime.now().strftime('%H:%M:%S')
        full = f"[{ts}] {msg}\n"
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, full)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def _load_preset(self, name: str):
        profile = PRESET_PROFILES[name]
        self.fuel_var.set(profile.fuel_boost)
        self.ign_var.set(profile.ignition_advance)
        self.turbo_lo_var.set(profile.turbo_pressure['low'])
        self.turbo_hi_var.set(profile.turbo_pressure['high'])
        self.rpm_var.set(profile.rpm_limit)
        self.lambda_var.set(profile.lambda_target)
        self._log(f"Preset '{name}' carregado: {profile.name}")

    def _build_profile_from_sliders(self) -> RemapProfile:
        return RemapProfile(
            name="Custom",
            fuel_boost=self.fuel_var.get(),
            ignition_advance=self.ign_var.get(),
            turbo_pressure={
                'low': round(self.turbo_lo_var.get(), 2),
                'high': round(self.turbo_hi_var.get(), 2),
            },
            rpm_limit=int(self.rpm_var.get()),
            lambda_target=round(self.lambda_var.get(), 2),
        )

    def _update_estimates(self):
        try:
            profile = self._build_profile_from_sliders()
            gains = ECURemap.calculate_performance_gain(profile)
            self._draw_gauge(self.power_canvas, self.power_lbl, gains['power_gain_percent'])
            self._draw_gauge(self.torque_canvas, self.torque_lbl, gains['torque_gain_percent'])
        except Exception:
            pass

    def _refresh_param_labels(self):
        if self.ecu is None:
            return
        for key, (lbl, unit) in self.param_labels.items():
            val = self.ecu.parameters[key].value
            if val is not None:
                lbl.config(text=f"{val:.2f} {unit}")
            else:
                lbl.config(text=f"— {unit}")

    # ─── Botões ───────────────────────────────────────────────────

    def _load_ecu(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo ECU",
            filetypes=[("Arquivos binários", "*.bin"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return
        try:
            self.ecu = ECURemap.load_from_file(path)
            self.ecu_filepath = path
            name = Path(path).name
            size_kb = len(self.ecu.ecu_data) // 1024
            valid = self.ecu._validate_ecu_file()

            self.lbl_file.config(text=name[:28] + ('…' if len(name) > 28 else ''))
            self.lbl_size.config(text=f"{size_kb} KB")
            self.lbl_model.config(text=self.ecu.model)
            self.lbl_status.config(
                text="✓ Válido" if valid else "⚠ Header inválido",
                fg=self.SUCCESS if valid else self.WARNING
            )
            self._refresh_param_labels()
            self._log(f"ECU carregada: {name} ({size_kb} KB)", 'ok')
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar o arquivo:\n{e}")
            self._log(f"Erro ao carregar ECU: {e}", 'err')

    def _create_simulated(self):
        data = bytearray(512 * 1024)
        data[0:4] = b'ECU!'
        self.ecu = ECURemap(data, validate=False)
        self.ecu_filepath = None

        self.lbl_file.config(text="[ECU Simulada]")
        self.lbl_size.config(text="512 KB")
        self.lbl_model.config(text="generic")
        self.lbl_status.config(text="✓ Simulada", fg=self.ACCENT)
        self._refresh_param_labels()
        self._log("ECU simulada criada (512 KB)", 'ok')

    def _apply_remap(self):
        if self.ecu is None:
            messagebox.showwarning("Atenção", "Carregue ou crie uma ECU primeiro.")
            return

        profile = self._build_profile_from_sliders()
        try:
            self.ecu.apply_remap(profile)
            self._refresh_param_labels()
            gains = self.ecu.calculate_performance_gain(profile)
            sign = '+' if gains['power_gain_percent'] >= 0 else ''
            self._log(
                f"Remap aplicado — Potência: {sign}{gains['power_gain_percent']:.1f}%  "
                f"Torque: {sign}{gains['torque_gain_percent']:.1f}%",
                'ok'
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao aplicar remap:\n{e}")
            self._log(f"Erro ao aplicar remap: {e}", 'err')

    def _save_ecu(self):
        if self.ecu is None:
            messagebox.showwarning("Atenção", "Nenhuma ECU carregada.")
            return

        default = (Path(self.ecu_filepath).stem + "_remapped.bin"
                   if self.ecu_filepath else "ecu_remapped.bin")
        path = filedialog.asksaveasfilename(
            title="Salvar ECU",
            initialfile=default,
            defaultextension=".bin",
            filetypes=[("Arquivos binários", "*.bin"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return
        try:
            create_backup = messagebox.askyesno(
                "Backup", "Criar backup do arquivo original antes de salvar?"
            )
            self.ecu.save_to_file(path, create_backup=create_backup)
            self._log(f"ECU salva: {Path(path).name}", 'ok')
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")
            self._log(f"Erro ao salvar ECU: {e}", 'err')

    def _export_report(self):
        if self.ecu is None:
            messagebox.showwarning("Atenção", "Nenhuma ECU carregada.")
            return

        path = filedialog.asksaveasfilename(
            title="Exportar Relatório",
            initialfile="remap_report.txt",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return
        try:
            self.ecu.export_report(path)
            self._log(f"Relatório exportado: {Path(path).name}", 'ok')
            if messagebox.askyesno("Relatório", f"Relatório salvo em:\n{path}\n\nAbrir agora?"):
                import subprocess, platform
                if platform.system() == 'Darwin':
                    subprocess.call(['open', path])
                elif platform.system() == 'Windows':
                    subprocess.call(['start', path], shell=True)
                else:
                    subprocess.call(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar relatório:\n{e}")
            self._log(f"Erro ao exportar relatório: {e}", 'err')

    def _create_backup(self):
        if self.ecu is None:
            messagebox.showwarning("Atenção", "Nenhuma ECU carregada.")
            return

        default = (Path(self.ecu_filepath).stem + "_backup.bin"
                   if self.ecu_filepath else "ecu_backup.bin")
        path = filedialog.asksaveasfilename(
            title="Salvar Backup",
            initialfile=default,
            defaultextension=".bin",
            filetypes=[("Arquivos binários", "*.bin"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, 'wb') as f:
                f.write(self.ecu._original_data)
            self._log(f"Backup do original salvo: {Path(path).name}", 'ok')
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao criar backup:\n{e}")
            self._log(f"Erro ao criar backup: {e}", 'err')


def main():
    root = tk.Tk()
    app = ECURemapGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
